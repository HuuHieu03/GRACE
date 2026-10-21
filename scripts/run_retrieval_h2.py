"""Offline H2: genuine CodeT5 shared top-50, E1.2-adapted R0 vs R1.

No LLM calls. Input labels and source identifiers never enter ranking.
Run from repository root; see project_docs/reports/retrieval_h2/README.md.
"""
import argparse
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from security_signature.sink_evidence_v12 import extract_sink_evidence
from security_signature.extractor import extract_security_signature
from security_signature.similarity import compute_security_signature_similarity, compute_jaccard_set


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def project(rows, prefix):
    """Only code and graph structure survive; paths and labels are private."""
    output = []
    for i, row in enumerate(rows):
        code = row.get('func')
        if not isinstance(code, str) or not code.strip():
            raise ValueError('Missing function at row ' + str(i))
        # Graph scorer uses node type/label only, never source filenames/IDs.
        nodes = [dict(type=n.get('type', n.get('label', 'UNKNOWN')))
                 if isinstance(n, dict) else dict(type='UNKNOWN')
                 for n in row.get('nodes', [])]
        output.append(dict(id=f'{prefix}-{i+1:05d}', func=code,
                           nodes=nodes, edge_count=len(row.get('edges', []))))
    return output


def active(evidence, field):
    return {r[field] for r in evidence['recognized'] if r['preprocessor_state'] == 'active'}


def features(row):
    # Retain the legacy lexical sanitizer/memory/clue components. E1.2 does
    # not establish guard effectiveness; no guard claim is made here.
    return (extract_sink_evidence(row['func']),
            extract_security_signature(code=row['func'], nodes=[], edges=[]))


def score(query, candidate, qf, cf):
    import difflib
    qev, qsig = qf
    cev, csig = cf
    _, parts = compute_security_signature_similarity(qsig, csig)
    sink = (.6 * compute_jaccard_set(active(qev, 'api_name'), active(cev, 'api_name'))
            + .4 * compute_jaccard_set(active(qev, 'family'), active(cev, 'family')))
    security = (.35 * sink + .25 * parts['sanitizer_similarity']
                + .2 * parts['memory_similarity'] + .2 * parts['clues_similarity'])
    lexical = compute_jaccard_set(set(query['func'].split()), set(candidate['func'].split()))

    def graph(row):
        return f"N:{len(row['nodes'])}_" + '_'.join(str(n['type']) for n in row['nodes'][:30]) + f"|E:{row['edge_count']}|"

    graph_score = 0.
    if (query['nodes'] or query['edge_count']) and (candidate['nodes'] or candidate['edge_count']):
        graph_score = difflib.SequenceMatcher(None, graph(query), graph(candidate)).ratio()
    hybrid = .7 * lexical + .3 * graph_score
    return dict(final=round(.3 * hybrid + .7 * security, 4), hybrid=hybrid,
                security=security, sink=sink, lexical=lexical, graph=graph_score,
                legacy_non_sink=parts)


def choose(ranked, query_families):
    if not ranked:
        raise ValueError('Empty shared pool')
    eligible = [r for r in ranked if query_families.intersection(r['active_families'])]
    reason = ('same_active_family' if eligible else
              'query_has_no_active_family' if not query_families else 'no_matching_candidate')
    return ranked[0]['id'], (eligible[0] if eligible else ranked[0])['id'], reason, len(eligible)


def validate_vectors(vectors, count):
    if vectors.shape != (count, 768) or vectors.dtype != np.float32 or not np.isfinite(vectors).all():
        raise ValueError('Expected finite float32 CodeT5 vectors of shape (N, 768)')


def load_encoder(model_path, tokenizer_path, device):
    import torch
    import transformers
    from transformers import RobertaTokenizer, T5Config, T5EncoderModel
    source = Path(model_path)
    tokenizer_source = Path(tokenizer_path)
    if not source.is_dir() or not tokenizer_source.is_dir():
        raise ValueError('Use explicit local model and tokenizer directories')
    arguments = dict(local_files_only=True)
    if (source / 'model.safetensors').exists():
        arguments['use_safetensors'] = True
    model, loading = T5EncoderModel.from_pretrained(
        str(source), config=T5Config.from_pretrained(str(tokenizer_source), local_files_only=True),
        output_loading_info=True, **arguments)
    if loading.get('missing_keys') or loading.get('mismatched_keys') or loading.get('error_msgs'):
        raise ValueError('Incomplete encoder weights: ' + str(loading))
    modern = 'vocab' in inspect.signature(RobertaTokenizer.__init__).parameters
    tokenizer = RobertaTokenizer(**{
        'vocab' if modern else 'vocab_file': str(tokenizer_source / 'vocab.json'),
        'merges' if modern else 'merges_file': str(tokenizer_source / 'merges.txt')})
    probes = tokenizer(['int f(){ return 123; }', 'void g(){ memcpy(dst, src, n); }'])['input_ids']
    if tokenizer.vocab_size != 32100 or probes[0] == probes[1] or min(map(len, probes)) < 6:
        raise ValueError('CodeT5 tokenizer failed vocabulary/content validation')
    model = model.to(device).eval()
    assets = {}
    for folder, names in [(source, ['model.safetensors', 'pytorch_model.bin']),
                          (tokenizer_source, ['config.json', 'vocab.json', 'merges.txt'])]:
        for name in names:
            path = folder / name
            if path.exists():
                h = hashlib.sha256()
                with path.open('rb') as handle:
                    for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
                        h.update(block)
                assets[name] = h.hexdigest()
    return model, tokenizer, dict(assets=assets, vocabulary=tokenizer.vocab_size,
                                 max_length=512, pooling='attention_mask_mean',
                                 device=device, torch=torch.__version__, transformers=transformers.__version__,
                                 runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def embed(rows, path, model, tokenizer, provenance, batch_size):
    import torch
    path = Path(path)
    metadata_path = path.with_suffix('.json')
    identity = dict(inputs=digest([r['func'] for r in rows]), count=len(rows),
                    encoder=provenance, schema=1)
    completed = 0
    if path.exists() or metadata_path.exists():
        if not (path.exists() and metadata_path.exists()):
            raise ValueError('Incomplete cache pair; move it aside before restarting')
        previous = json.loads(metadata_path.read_text(encoding='utf-8'))
        if previous['identity'] != identity:
            raise ValueError('Embedding cache identity mismatch')
        completed = previous['completed']
        vectors = np.lib.format.open_memmap(path, mode='r+')
        if vectors.shape != (len(rows), 768) or vectors.dtype != np.float32:
            raise ValueError('Invalid checkpoint matrix')
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        vectors = np.lib.format.open_memmap(path, mode='w+', dtype='float32', shape=(len(rows), 768))
        write_json(metadata_path, dict(identity=identity, completed=0))
    for start in range(completed, len(rows), batch_size):
        end = min(start + batch_size, len(rows))
        tokens = tokenizer([r['func'] for r in rows[start:end]], padding=True,
                           truncation=True, max_length=512, return_tensors='pt').to(next(model.parameters()).device)
        with torch.inference_mode():
            hidden = model(**tokens).last_hidden_state
            mask = tokens['attention_mask'].unsqueeze(-1)
            batch = ((hidden * mask).sum(1) / mask.sum(1).clamp(min=1)).float().cpu().numpy()
        validate_vectors(batch, end-start)
        vectors[start:end] = batch
        vectors.flush()
        write_json(metadata_path, dict(identity=identity, completed=end))
        print(f'{path.name}: {end}/{len(rows)}', flush=True)
    validate_vectors(vectors, len(rows))
    return vectors


def compare(train, queries, train_vecs, query_vecs):
    validate_vectors(train_vecs, len(train))
    validate_vectors(query_vecs, len(queries))
    if len(train) < 50:
        raise ValueError('Shared pool requires at least 50 training samples')
    cache, records = {}, []
    for qi, query in enumerate(queries):
        distances = np.linalg.norm(train_vecs - query_vecs[qi], axis=1)
        indices = np.argsort(distances, kind='stable')[:50]
        qf = features(query)
        candidates = []
        for rank, index in enumerate(indices):
            index = int(index)
            if index not in cache:
                cache[index] = features(train[index])
            cf = cache[index]
            candidates.append(dict(id=train[index]['id'], l2_rank=rank+1,
                                   l2_distance=float(distances[index]), scores=score(query, train[index], qf, cf),
                                   active_families=sorted(active(cf[0], 'family')), evidence=cf[0]))
        ranked = sorted(candidates, key=lambda r: (-r['scores']['final'], r['l2_rank']))
        r0, r1, reason, eligible = choose(ranked, active(qf[0], 'family'))
        records.append(dict(query_id=query['id'], query_evidence=qf[0],
                            shared_pool=candidates, r0_order=[r['id'] for r in ranked],
                            r0=r0, r1=r1, reason=reason, eligible_count=eligible, changed=r0 != r1))
        print(f'Compared {qi+1}/{len(queries)}', flush=True)
    summary = dict(queries=len(records), changed=sum(r['changed'] for r in records),
                   queries_with_active_evidence=sum(bool(active(r['query_evidence'], 'family')) for r in records),
                   queries_with_matching_candidate=sum(r['eligible_count'] > 0 for r in records),
                   conditional_only=sum(not active(r['query_evidence'], 'family') and
                                        bool(r['query_evidence']['recognized']) for r in records),
                   fallback=sum(r['reason'] != 'same_active_family' for r in records),
                   interpretation='Selection diagnostics only; no independent relevance or prediction-quality conclusion.')
    return records, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', default='data/processed/devign_train_compact_cpg.json.gz')
    parser.add_argument('--queries', default='data/splits/devign_dev_clean_100_ids.json')
    parser.add_argument('--model', required=True)
    parser.add_argument('--tokenizer', required=True)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--output', default='artifacts/retrieval_h2')
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error('batch-size must be positive')
    train_path = Path(args.train)
    train_text = (gzip.decompress(train_path.read_bytes()).decode('utf-8')
                  if train_path.suffix == '.gz' else train_path.read_text(encoding='utf-8'))
    train_raw = json.loads(train_text)
    query_raw = json.loads(Path(args.queries).read_text(encoding='utf-8'))
    if isinstance(query_raw, dict):
        query_raw = query_raw['sample_details']
    if len(train_raw) != 21854 or len(query_raw) != 100:
        raise ValueError('H2 requires the complete frozen 21854 train / 100 query split')
    train, queries = project(train_raw, 'T'), project(query_raw, 'Q')
    out = Path(args.output)
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in [Path(__file__).resolve(), *sorted((ROOT/'src/security_signature').glob('*.py'))]}
    if source_hashes['src/security_signature/sink_evidence_v12.py'] != '319f18a3e53eb36987cb6798253805949c8ce3c7ee44571703beb2cafe8ad336':
        raise ValueError('Frozen E1.2 extractor changed; review protocol before running H2')
    manifest = dict(train_hash=digest(train), query_hash=digest(queries), sources=source_hashes,
                    scoring='R0 E1.2 active sink adapter + legacy non-sink lexical components; R1 first active-family match in R0 order',
                    graph='node type/label sequence + counts; IDs stripped; no graph-derived guard claims',
                    labels_used=False, llm_calls=0, pool_size=50)
    if (out/'manifest.json').exists() and json.loads((out/'manifest.json').read_text(encoding='utf-8')) != manifest:
        raise ValueError('Existing output belongs to a different protocol/input; choose another output directory')
    write_json(out/'manifest.json', manifest)
    write_json(out/'private_source_map.json', {
        prefix: [dict(opaque_id=row['id'], source_id=raw.get('id'), target=raw.get('target'))
                 for row, raw in zip(safe, original)]
        for prefix, safe, original in [('train', train, train_raw), ('queries', queries, query_raw)]})
    model, tokenizer, provenance = load_encoder(args.model, args.tokenizer, args.device)
    train_vecs = embed(train, out/'train.npy', model, tokenizer, provenance, args.batch_size)
    query_vecs = embed(queries, out/'queries.npy', model, tokenizer, provenance, args.batch_size)
    records, summary = compare(train, queries, train_vecs, query_vecs)
    write_json(out/'shared_top50.json', records)
    write_json(out/'summary.json', dict(**summary, manifest=manifest, encoder=provenance))


if __name__ == '__main__':
    main()
