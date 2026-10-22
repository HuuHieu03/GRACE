"""E1/E1.1 development regression and fresh dev annotation packet preparation.

The old 50 functions are now development data for E1.1. New input selection
uses no vulnerability labels or model predictions and never opens final test.
"""
import hashlib
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT))
from security_signature.sink_evidence import extract_sink_evidence as e1
from security_signature.sink_evidence_v11 import extract_sink_evidence as e11, NEW_WRAPPER_RULES, REGISTRY_SHA256
from scripts.evaluate_sink_evidence_annotations import set_metrics, totals_metrics

OLD = ROOT/'project_docs/reports/sink_evidence_h1'
OUT = ROOT/'project_docs/reports/sink_evidence_v11'


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalized_digest(code):
    return digest(re.sub(r'\s+', '', code))


def prepare_fresh_packet():
    split = json.loads((ROOT/'data/splits/devign_dev_clean_100_ids.json').read_text(encoding='utf-8'))
    excluded_ids = {str(row['id']) for row in split['sample_details']}
    excluded_codes = {normalized_digest(row['func']) for row in split['sample_details']}
    directory = ROOT/'data/raw_c_files/devign/validation'
    candidates = [path for path in sorted(directory.glob('*.c'), key=lambda path: path.name)
                  if path.name not in excluded_ids]
    random.Random(20261021).shuffle(candidates)
    selected, seen = [], set(excluded_codes)
    for path in candidates:
        code = path.read_text(encoding='utf-8-sig')
        code_hash = normalized_digest(code)
        if code_hash in seen:
            continue
        seen.add(code_hash)
        selected.append((path.name, code))
        if len(selected) == 50:
            break
    assert len(selected) == 50
    samples = [{'opaque_id': f'E11-{idx:03d}', 'source_id': source_id,
                'code_sha256': digest(code), 'whitespace_normalized_sha256': normalized_digest(code)}
               for idx, (source_id, code) in enumerate(selected, 1)]
    e11_source_hash = hashlib.sha256((ROOT/'src/security_signature/sink_evidence_v11.py').read_bytes()).hexdigest()
    manifest = {'purpose': 'Fresh dev inputs for E1.1 annotation; accuracy not yet measured',
                'source': 'data/raw_c_files/devign/validation', 'seed': 20261021,
                'excluded_canonical_dev100': True, 'whitespace_duplicate_exclusion': True,
                'independent_human_annotation': False, 'target_labels_used_for_selection': False,
                'model_outputs_used_for_selection': False,
                'limits': 'Same Devign validation corpus; not final test, not audited for train overlap or near clones.',
                'E11_source_sha256': e11_source_hash, 'registry_sha256': REGISTRY_SHA256, 'samples': samples}
    target = OUT/'fresh_dev50_manifest_private.json'
    if target.exists():
        assert json.loads(target.read_text(encoding='utf-8')) == manifest, 'Frozen fresh-dev inputs/source changed'
    else:
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    packet = [{'opaque_id': row['opaque_id'], 'code_sha256': row['code_sha256'],
               'code': code, 'expected_callsite_annotations': None, 'annotator_notes': ''}
              for row, (_, code) in zip(samples, selected)]
    (OUT/'fresh_dev50_annotation_packet.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return {'samples': len(packet), 'excluded_previous_dev100': True,
            'predictions_written': False, 'annotation_status': 'PENDING',
            'scope': 'Fresh dev relative to H1 reviewed 100; no final test or train-clean claim'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    new_packet_summary = prepare_fresh_packet()
    source = ROOT/'src/security_signature/sink_evidence.py'
    frozen = json.loads((OLD/'summary.json').read_text(encoding='utf-8'))['E1_source_sha256']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == frozen
    packet = json.loads((OLD/'verification_annotation_packet.json').read_text(encoding='utf-8'))
    by_id = {row['opaque_id']: row for row in packet}
    gold = json.loads((OLD/'verification_annotations_technical.json').read_text(encoding='utf-8'))
    assert len(gold['samples']) == len(by_id) == 50
    totals = {key: [0,0,0] for key in ['E1_API','E11_API','E1_callsite','E11_callsite','E11_family_callsite']}
    records, remaining = [], []
    promotions = 0
    for row in gold['samples']:
        sample = by_id[row['opaque_id']]
        code = sample['code']
        assert digest(code) == sample['code_sha256'] == row['code_sha256']
        before, after = e1(code), e11(code)
        expected = row['callsite_annotations']
        sites = {(x['api_name'],x['start'],x['end']) for x in expected}
        families = {(x['api_name'],x['start'],x['end'],x['family']) for x in expected}
        api_names = {x['api_name'] for x in expected}
        before_sites = {(x['api_name'],x['start'],x['end']) for x in before['recognized']}
        after_sites = {(x['api_name'],x['start'],x['end']) for x in after['recognized']}
        after_families = {(x['api_name'],x['start'],x['end'],x['family']) for x in after['recognized']}
        comparisons = {'E1_API':(set(before['sink_apis']),api_names), 'E11_API':(set(after['sink_apis']),api_names),
                       'E1_callsite':(before_sites,sites),'E11_callsite':(after_sites,sites),
                       'E11_family_callsite':(after_families,families)}
        for key, values in comparisons.items():
            for idx, value in enumerate(set_metrics(*values)):
                totals[key][idx] += value
        # Registry extension cannot rewrite or remove evidence from E1.
        assert before_sites <= after_sites
        before_unknown = {(x['api_name'],x['start'],x['end']) for x in before['unknown_calls']}
        assert after_sites-before_sites <= before_unknown
        promotions += len(after_sites-before_sites)
        for call in expected:
            if (call['api_name'],call['start'],call['end']) not in after_sites:
                remaining.append({'opaque_id':row['opaque_id'], **call})
        records.append({'opaque_id':row['opaque_id'],'E1':before,'E11':after,
                        'expected_apis':sorted(api_names),'gold_sites':len(sites),
                        'E11_false_positive_sites':sorted(after_sites-sites),
                        'E11_false_negative_sites':sorted(sites-after_sites)})
    summary = {'date':'2026-10-21','experiment':'E1.1 exact wrapper extension',
               'new_exact_name_rules':len(NEW_WRAPPER_RULES),'registry_sha256':REGISTRY_SHA256,
               'frozen_E1_source_sha256':frozen,
               'development_regression':{'samples':50,'annotated_sites':sum(len(r['callsite_annotations']) for r in gold['samples']),
                                          'promoted_unknown_sites':promotions,
                                          'metrics':{key:totals_metrics(value) for key,value in totals.items()},
                                          'independent_validation':False,
                                          'scope':'These annotations informed the 25 rules; scores are in-sample regression only.'},
               'fresh_dev50':new_packet_summary,
               'production_changed':False,'LLM_calls':0,
               'strict_H2_gate':'NOT_PASSED: fresh-dev annotation, semantic audit and shared CodeT5 candidate archive still required.'}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'development_regression_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'remaining_development_misses.json').write_text(json.dumps(remaining,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    registry_report = [{'api_name':api,'family':family,'implementation_status':'IMPLEMENTED_IN_EXPERIMENTAL_E11',
                        'basis':'H1 technical caller-context annotation',
                        'semantic_validation':'NOT_INDEPENDENTLY_AUDITED'} for api,family in NEW_WRAPPER_RULES.items()]
    (OUT/'implemented_registry.json').write_text(json.dumps(registry_report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
