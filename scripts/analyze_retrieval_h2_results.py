"""Audit downloaded H2 outputs against local frozen inputs, then summarize."""
from collections import Counter
import contextlib
import csv
import gzip
import hashlib
import io
import json
import subprocess
from pathlib import Path

import numpy as np
from scripts.run_retrieval_h2 import project, digest, compare, active, validate_vectors, write_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT/'artifacts/retrieval_h2_kaggle_run/h2_output'
    out = ROOT/'project_docs/reports/retrieval_h2/results_2026-10-22'
    summary = json.loads((source/'summary.json').read_text(encoding='utf-8'))
    revision = json.loads((source/'git_revision.json').read_text())['revision']
    for path, expected in summary['manifest']['sources'].items():
        blob = subprocess.check_output(['git', '-c', 'safe.directory='+ROOT.as_posix(),
                                        'show', revision+':'+path])
        assert hashlib.sha256(blob).hexdigest() == expected, path
    records = json.loads((source/'shared_top50.json').read_text(encoding='utf-8'))
    train_raw = json.loads(gzip.decompress((ROOT/'data/processed/devign_train_compact_cpg.json.gz').read_bytes()))
    query_raw = json.loads((ROOT/'data/splits/devign_dev_clean_100_ids.json').read_text(encoding='utf-8'))['sample_details']
    train, queries = project(train_raw, 'T'), project(query_raw, 'Q')
    assert len(train) == 21854 and len(queries) == 100 and len(records) == 100
    assert digest(train) == summary['manifest']['train_hash']
    assert digest(queries) == summary['manifest']['query_hash']
    tv = np.load(source/'train.npy', mmap_mode='r')
    qv = np.load(source/'queries.npy', mmap_mode='r')
    validate_vectors(tv, len(train))
    validate_vectors(qv, len(queries))
    for name, rows in [('train', train), ('queries', queries)]:
        metadata = json.loads((source/(name+'.json')).read_text(encoding='utf-8'))
        assert metadata['completed'] == len(rows)
        assert metadata['identity']['inputs'] == digest([r['func'] for r in rows])
        assert metadata['identity']['encoder'] == summary['encoder']
    # Re-run exact full-bank search, scoring and selection using downloaded
    # real embeddings. No encoder inference or LLM call is needed.
    with contextlib.redirect_stdout(io.StringIO()):
        replay, replay_summary = compare(train, queries, tv, qv)
    for saved, actual in zip(records, replay):
        assert saved['query_id'] == actual['query_id']
        assert saved['r0_order'] == actual['r0_order']
        for key in ['r0', 'r1', 'reason', 'eligible_count', 'changed', 'query_evidence']:
            assert saved[key] == actual[key], (saved['query_id'], key)
        assert len(saved['shared_pool']) == 50
        assert len({r['id'] for r in saved['shared_pool']}) == 50
        for a, b in zip(saved['shared_pool'], actual['shared_pool']):
            assert a['id'] == b['id'] and a['evidence'] == b['evidence']
            assert a['scores'] == b['scores']
            assert np.isclose(a['l2_distance'], b['l2_distance'], rtol=1e-6, atol=1e-6)
    for key, value in replay_summary.items():
        assert summary[key] == value, key
    normalize = lambda code: ''.join(code.split())
    bank = {normalize(r['func']) for r in train}
    overlap = [q['id'] for q in queries if normalize(q['func']) in bank]
    families = Counter()
    no_evidence_unknown = 0
    rows = []
    for query, record in zip(queries, records):
        evidence = record['query_evidence']
        fs = active(evidence, 'family')
        families.update(fs)
        no_evidence_unknown += int(not fs and bool(evidence['unknown_calls']))
        selected = next(r for r in record['shared_pool'] if r['id'] == record['r0'])
        rows.append(dict(query_id=query['id'], active_families=';'.join(sorted(fs)),
                         unknown_calls=len(evidence['unknown_calls']), eligible_count=record['eligible_count'],
                         r0=record['r0'], r1=record['r1'], changed=record['changed'], reason=record['reason'],
                         r0_l2_rank=selected['l2_rank'], r0_score=selected['scores']['final']))
    eligible = [r['eligible_count'] for r in records if r['eligible_count']]
    report = dict(status='COMPLETE_AUDITED', checks=dict(
        input_hashes_match=True, full_bank_vectors_finite=True,
        pinned_git_source_hashes_verified=len(summary['manifest']['sources']),
        complete_embedding_checkpoints=True, shared_top50_replayed=100,
        reranking_and_both_selections_replayed=100, summary_recomputed=True),
        metrics=replay_summary, active_family_query_counts=dict(families),
        matching_candidates_when_available=dict(min=min(eligible), median=float(np.median(eligible)), max=max(eligible)),
        no_active_evidence_with_unknown_calls=no_evidence_unknown,
        whitespace_normalized_train_query_overlap=overlap,
        r0_l2_rank_counts=dict(Counter(r['r0_l2_rank'] for r in rows)),
        unique_selected_candidates=len({r['r0'] for r in records}),
        encoder=summary['encoder'], git_revision=json.loads((source/'git_revision.json').read_text()),
        interpretation='R1 makes no changes on this split. Both arms are observationally identical; this does not establish relevance or vulnerability prediction quality.')
    write_json(out/'audit_summary.json', report)
    with (out/'per_query.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
