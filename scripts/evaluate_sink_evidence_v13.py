"""E1.3 development regression and fresh-input consistency, not accuracy."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import random

from scripts.run_retrieval_h2 import write_json
from security_signature.sink_evidence_v12 import extract_sink_evidence as e12
from security_signature.sink_evidence_v13 import extract_sink_evidence as e13

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'project_docs/reports/sink_evidence_v13'


def norm(code):
    return hashlib.sha256(''.join(code.split()).encode()).hexdigest()


def compare(rows):
    records = []
    counts = Counter()
    for row in rows:
        code = row['code']
        before, after = e12(code), e13(code)
        old_recognized = before['recognized']
        new_recognized = [{k:v for k,v in r.items() if k not in {'output_role','role_assessment'}}
                          for r in after['recognized']]
        assert old_recognized == new_recognized, row['opaque_id']
        assert before['inactive_calls'] == after['inactive_calls']
        counts['samples'] += 1
        counts['recognized_sites_preserved'] += len(old_recognized)
        counts['syntax_exclusions'] += len(after['excluded_syntax'])
        for call in after['recognized']:
            counts['role:'+call['output_role']] += 1
            assert code[call['start']:call['end']] == call['expression']
        for call in after['excluded_syntax']:
            counts['excluded:'+call['exclusion_reason']] += 1
            assert code[call['start']:call['end']] == call['expression']
        if after['excluded_syntax']:
            records.append(dict(opaque_id=row['opaque_id'], excluded=after['excluded_syntax']))
    return dict(counts), records


def main():
    old_source = ROOT/'src/security_signature/sink_evidence_v12.py'
    assert hashlib.sha256(old_source.read_bytes()).hexdigest() == '319f18a3e53eb36987cb6798253805949c8ce3c7ee44571703beb2cafe8ad336'
    development = json.loads((ROOT/'data/splits/devign_dev_clean_100_ids.json').read_text(encoding='utf-8'))['sample_details']
    excluded = {norm(r['func']) for r in development}
    for row in json.loads((ROOT/'project_docs/reports/sink_evidence_v11/fresh_dev50_annotation_packet.json').read_text(encoding='utf-8')):
        excluded.add(norm(row['code']))
    train = json.loads(gzip.decompress((ROOT/'data/processed/devign_train_compact_cpg.json.gz').read_bytes()))
    excluded.update(norm(r['func']) for r in train)
    paths = sorted((ROOT/'data/raw_c_files/devign/validation').glob('*.c'))
    random.Random(20261022).shuffle(paths)
    packet, private = [], []
    for path in paths:
        code = path.read_text(encoding='utf-8')
        h = norm(code)
        if not code.strip() or h in excluded:
            continue
        excluded.add(h)
        oid = f'E13-{len(packet)+1:03d}'
        packet.append(dict(opaque_id=oid, code=code, reviewed_calls=[]))
        private.append(dict(opaque_id=oid, source_id=path.name, code_sha256=hashlib.sha256(code.encode()).hexdigest(),
                            normalized_sha256=h))
        if len(packet) == 50:
            break
    assert len(packet) == 50
    manifest = dict(seed=20261022, samples=private, excluded_train_and_prior_dev_code=True,
                    exact_whitespace_normalized_exclusion_only=True, labels_or_predictions_used=False,
                    E13_sha256=hashlib.sha256((ROOT/'src/security_signature/sink_evidence_v13.py').read_bytes()).hexdigest(),
                    semantic_annotations='PENDING', corpus='Devign validation; not final test',
                    purpose='Fresh-input consistency and later semantic validation; not independently scored')
    target = OUT/'fresh_dev50_manifest_private.json'
    if target.exists():
        assert json.loads(target.read_text(encoding='utf-8')) == manifest, 'Frozen fresh sample changed'
    write_json(target, manifest)
    packet_target = OUT/'fresh_dev50_annotation_packet.json'
    if not packet_target.exists():
        write_json(packet_target, packet)
    dev_stats, dev_excluded = compare([dict(opaque_id=f'Q-{i+1:05d}',code=r['func']) for i,r in enumerate(development)])
    fresh_stats, fresh_excluded = compare(packet)
    write_json(OUT/'excluded_declaration_sites.json', dict(development=dev_excluded,fresh=fresh_excluded))
    summary = dict(development=dev_stats, fresh_inputs=fresh_stats,
                   E12_frozen=True, H2_rerun=False, production_changed=False,
                   precision_recall=None, independent_relevance_scores=0,
                   conclusion='Syntax/offset/evidence preservation verified; output roles not independently semantically validated. Fresh inputs are not a relevance evaluation.')
    write_json(OUT/'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
