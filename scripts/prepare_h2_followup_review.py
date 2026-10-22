"""Post-H2 technical inventory and unscored independent relevance packet.

Uses frozen selections only. Never changes E1.2, R0, R1 or human ballots.
"""
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random
import re

from scripts.run_retrieval_h2 import active, digest, project, write_json
from security_signature.sink_evidence import mask_noncode

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'project_docs/reports/retrieval_h2/followup_2026-10-22'


def table(path, rows, fields=None):
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def syntax_triage(query, call):
    """Triage cues, not inferred wrapper contracts or a semantic gold label."""
    name = call['api_name']
    if name == 'uint8_t' and query['id'] == 'Q-00045':
        assert 'uint8_t (*layout_map)[3]' in query['func']
        return 'reviewed_declaration_artifact'
    if name == 'RENAME':
        return 'unexpanded_symbol_macro_not_proven_runtime_call'
    if name == 'COPY' and query['id'] == 'Q-00062':
        assert '#define COPY(a) bak->a= src->a' in query['func']
        return 'reviewed_local_field_assignment_macro'
    if name in {'assert', 'av_assert0', 'av_assert2'}:
        return 'assertion_name_cue_not_sink_or_guard_proof'
    if name in {'av_log', 'qemu_log', 'tprintf', 'lwarn', 'dolog', 'lerr', 'DPRINTF', 'LOG_DISAS', 'LOG_INT'}:
        return 'logging_name_cue_requires_context'
    return 'unresolved_requires_definition_or_context'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = ROOT/'artifacts/retrieval_h2_kaggle_run/h2_output'
    records = json.loads((raw/'shared_top50.json').read_text(encoding='utf-8'))
    train = project(json.loads(gzip.decompress((ROOT/'data/processed/devign_train_compact_cpg.json.gz').read_bytes())), 'T')
    queries = project(json.loads((ROOT/'data/splits/devign_dev_clean_100_ids.json').read_text(encoding='utf-8'))['sample_details'], 'Q')
    manifest = json.loads((raw/'manifest.json').read_text(encoding='utf-8'))
    assert digest(train) == manifest['train_hash'] and digest(queries) == manifest['query_hash']
    assert len(records) == len(queries) == 100
    calls, query_inventory, diagnostics = [], [], []
    names = Counter()
    name_queries = defaultdict(set)
    review_packets = []
    selected_code = {}
    for query, record in zip(queries, records):
        assert query['id'] == record['query_id'] and record['r0'] == record['r1']
        selected = next(c for c in record['shared_pool'] if c['id'] == record['r0'])
        candidate = train[int(selected['id'].split('-')[1])-1]
        selected_code[query['id']] = candidate['func']
        qev, cev = record['query_evidence'], selected['evidence']
        qfamilies = active(qev, 'family')
        shared = qfamilies & active(cev, 'family')
        apis = active(qev, 'api_name') & active(cev, 'api_name')
        diagnostics.append(dict(query_id=query['id'], selected_id=selected['id'],
                                shared_families=';'.join(sorted(shared)), shared_apis=';'.join(sorted(apis)),
                                format_family_only=shared == {'format_string'},
                                family_without_same_api=bool(shared) and not apis,
                                query_active_family_count=len(qfamilies),
                                selected_l2_rank=selected['l2_rank']))
        review_packets.append(dict(query_code=query['func'], demonstration_code=candidate['func']))
        if not qfamilies and qev['unknown_calls']:
            for call in qev['unknown_calls']:
                assert query['func'][call['start']:call['end']] == call['expression']
                names[call['api_name']] += 1
                name_queries[call['api_name']].add(query['id'])
                calls.append(dict(query_id=query['id'], **call, technical_triage=syntax_triage(query, call)))
            query_inventory.append(dict(query_id=query['id'], code_sha256=hashlib.sha256(query['func'].encode()).hexdigest(),
                                        unknown_sites=len(qev['unknown_calls']),
                                        unknown_names=';'.join(sorted({c['api_name'] for c in qev['unknown_calls']})),
                                        code=query['func'], evidence=qev))
    assert len(query_inventory) == 58 and len(calls) == 492 and len(names) == 252

    # A corpus definition is a lead, not a resolved callee: static scope,
    # project revision and macro expansion may differ across dataset rows.
    definitions = defaultdict(list)
    for row in train:
        masked = mask_noncode(row['func'])
        header = masked.split('{', 1)[0]
        match = re.search(r'\b([A-Za-z_]\w*)\s*\([^{};]*\)\s*$', header, re.DOTALL)
        if match and match.group(1) in names:
            definitions[match.group(1)].append(dict(candidate_id=row['id'], code=row['func']))
    name_rows = [dict(api_name=name, call_sites=count, query_count=len(name_queries[name]),
                      query_ids=';'.join(sorted(name_queries[name])),
                      possible_definition_count=len(definitions[name]),
                      possible_definition_ids=';'.join(d['candidate_id'] for d in definitions[name]))
                 for name, count in names.most_common()]
    write_json(OUT/'unknown58_inventory.json', query_inventory)
    write_json(OUT/'unknown_callsite_inventory.json', calls)
    write_json(OUT/'possible_definitions_technical.json', dict(definitions))
    table(OUT/'unknown_name_inventory.csv', name_rows)
    table(OUT/'selection_diagnostics.csv', diagnostics)

    # Single-demo review: no fictitious R0/R1 pair when both selections match.
    # Remove policy, scores, evidence, source IDs, labels and private mapping.
    order = list(range(100))
    random.Random(20261022).shuffle(order)
    packets, private_map = [], []
    for i, source_index in enumerate(order, 1):
        review_id = f'H2R-{i:03d}'
        packets.append(dict(review_id=review_id, **review_packets[source_index]))
        private_map.append(dict(review_id=review_id, query_id=queries[source_index]['id'],
                                candidate_id=records[source_index]['r0']))
    write_json(OUT/'relevance_review_packet.json', packets)
    write_json(OUT/'relevance_review_map_private.json', private_map)
    fields = ['review_id', 'operation_alignment', 'object_role_alignment', 'guard_comparability',
              'overall_relevance', 'query_evidence', 'demo_evidence', 'notes']
    blank = [{field: p['review_id'] if field == 'review_id' else '' for field in fields} for p in packets]
    for reviewer in ['A', 'B']:
        path = OUT/f'relevance_sheet_reviewer_{reviewer}.csv'
        if not path.exists():  # Never overwrite a reviewer-completed sheet.
            table(path, blank, fields)
    markdown = ['# H2 single-demonstration relevance packet',
                'Assess each query/demo using rubric.md. Scores, source labels and policy are withheld.']
    for packet in packets:
        markdown.extend([f"## {packet['review_id']}", '### Query', '```c', packet['query_code'], '```',
                         '### Demonstration', '```c', packet['demonstration_code'], '```'])
    (OUT/'relevance_review_packet.md').write_text('\n\n'.join(markdown), encoding='utf-8')
    result = dict(queries=100, unknown_queries=58, unknown_sites=len(calls), unknown_names=len(names),
                  triage_site_counts=dict(Counter(c['technical_triage'] for c in calls)),
                  names_with_possible_definition=sum(bool(definitions[n]) for n in names),
                  format_family_only_query_ids=[d['query_id'] for d in diagnostics if d['format_family_only']],
                  family_overlap_without_same_api_query_ids=[d['query_id'] for d in diagnostics if d['family_without_same_api']],
                  reviewer_packet_count=len(packets), reviewer_scores_generated=0,
                  provenance='Technical inventory and selected code inspections prepared with Codex; not independent human relevance labels.',
                  raw_archive_sha256=hashlib.sha256((raw/'shared_top50.json').read_bytes()).hexdigest(),
                  limits=['Triage cues are not semantic classifications of every helper.',
                          'Possible definitions are unresolved corpus leads, not verified contracts.',
                          'Selected code inspections are purposive, not an unbiased error-rate estimate.'])
    write_json(OUT/'summary.json', result)
    notes = json.loads((OUT/'technical_case_notes.json').read_text(encoding='utf-8'))['cases']
    qmap = {q['id']: q['func'] for q in queries}
    for note in notes:
        assert note['query_anchor'] in qmap[note['query_id']]
        if 'demo_anchor' in note:
            assert note['demo_anchor'] in selected_code[note['query_id']]
    assert all(set(p) == {'review_id', 'query_code', 'demonstration_code'} for p in packets)
    files = ['relevance_review_packet.json', 'relevance_review_packet.md', 'rubric.md', 'technical_case_notes.json']
    write_json(OUT/'preparation_checks.json', dict(checks=dict(
        technical_case_anchors_validated=len(notes), packet_cases=len(packets),
        label_score_policy_metadata_absent=True, independent_scores_created=0),
        sha256={name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in files}))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
