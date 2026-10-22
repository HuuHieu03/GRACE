"""Frozen E0/E1/E1.1 scoring on the fresh 50 technical annotations.

This is out of the E1.1 rule-development sample, not an independent human
validation or a final test of vulnerability detection.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'src'))
from scripts.evaluate_sink_evidence_annotations import locate_reviewed_calls, set_metrics, totals_metrics

DIRECTORY = ROOT/'project_docs/reports/sink_evidence_v11'


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_annotations(packet, manifest, specs):
    inputs = {row['opaque_id']:row for row in packet}
    frozen = {row['opaque_id']:row for row in manifest['samples']}
    reviewed = {row['id']:row for row in specs['samples']}
    if not (len(packet)==len(manifest['samples'])==len(specs['samples'])==50
            and set(inputs)==set(frozen)==set(reviewed)):
        raise ValueError('Expected exactly 50 uniquely matched reviewed inputs')
    annotations=[]
    for opaque_id in sorted(inputs):
        sample=inputs[opaque_id]
        code=sample['code']
        code_hash=hashlib.sha256(code.encode('utf-8')).hexdigest()
        if code_hash != sample['code_sha256'] or code_hash != frozen[opaque_id]['code_sha256']:
            raise ValueError('Frozen input changed: '+opaque_id)
        review=reviewed[opaque_id]
        included, excluded=[],[]
        for api,family,count in review['calls']:
            spans=locate_reviewed_calls(code,api,count)
            skipped=review.get('exclude_occurrences',{}).get(api,[])
            if len(set(skipped))!=len(skipped) or any(i<1 or i>count for i in skipped):
                raise ValueError('Invalid manually excluded occurrence: '+opaque_id)
            for ordinal,(start,end) in enumerate(spans,1):
                call={'api_name':api,'family':family,'start':start,'end':end,
                      'line':code.count('\n',0,start)+1,'expression':code[start:end],
                      'evidence':review['notes']}
                if ordinal in skipped:
                    call['exclusion_reason']='explicit_if_zero_in_source_review'
                    excluded.append(call)
                else:
                    included.append(call)
        included.sort(key=lambda row:row['start'])
        annotations.append({'opaque_id':opaque_id,'code_sha256':code_hash,
                            'context_status':review.get('context_status','FUNCTION_TEXT_AVAILABLE'),
                            'callsite_annotations':included,'excluded_callsite_annotations':excluded,
                            'review_notes':review['notes']})
    return annotations


def main():
    packet=json.loads((DIRECTORY/'fresh_dev50_annotation_packet.json').read_text(encoding='utf-8'))
    manifest=json.loads((DIRECTORY/'fresh_dev50_manifest_private.json').read_text(encoding='utf-8'))
    specs_path=DIRECTORY/'fresh_dev50_annotation_specs.json'
    specs=json.loads(specs_path.read_text(encoding='utf-8'))
    source=ROOT/'src/security_signature/sink_evidence_v11.py'
    if digest_file(source)!=manifest['E11_source_sha256']:
        raise ValueError('E1.1 source changed since fresh input freeze')
    annotations=build_annotations(packet,manifest,specs)
    payload={key:specs[key] for key in ['annotation_type','scope','review_exposure']}
    payload.update(independent=False,samples=annotations)
    (DIRECTORY/'fresh_dev50_annotations_technical.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Only invoke methods after the complete technical annotation is persisted.
    from security_signature.extractor import extract_security_signature
    from security_signature.sink_evidence import extract_sink_evidence as e1
    from security_signature.sink_evidence_v11 import extract_sink_evidence as e11, REGISTRY_SHA256
    if REGISTRY_SHA256!=manifest['registry_sha256']:
        raise ValueError('E1.1 registry changed since fresh input freeze')
    baseline_hash=json.loads((ROOT/'project_docs/reports/sink_evidence_h1/summary.json').read_text(encoding='utf-8'))['E1_source_sha256']
    if digest_file(ROOT/'src/security_signature/sink_evidence.py')!=baseline_hash:
        raise ValueError('Frozen E1 source changed')
    inputs={row['opaque_id']:row for row in packet}
    totals={name:[0,0,0] for name in ['E0_API','E1_API','E11_API','E1_callsite','E11_callsite','E11_family_callsite']}
    errors=[]
    records=[]
    for sample in annotations:
        code=inputs[sample['opaque_id']]['code']
        before,after=e1(code),e11(code)
        base=extract_security_signature(code)
        gold=sample['callsite_annotations']
        gold_api={row['api_name'] for row in gold}
        sites=lambda rows:{(row['api_name'],row['start'],row['end']) for row in rows}
        family_sites=lambda rows:{(row['api_name'],row['start'],row['end'],row['family']) for row in rows}
        expected=sites(gold)
        checks={'E0_API':(set(base.sink_apis),gold_api),
                'E1_API':(set(before['sink_apis']),gold_api),'E11_API':(set(after['sink_apis']),gold_api),
                'E1_callsite':(sites(before['recognized']),expected),
                'E11_callsite':(sites(after['recognized']),expected),
                'E11_family_callsite':(family_sites(after['recognized']),family_sites(gold))}
        per_sample={}
        for name,comparison in checks.items():
            counts=set_metrics(*comparison)
            per_sample[name]=totals_metrics(counts)
            totals[name]=[a+b for a,b in zip(totals[name],counts)]
        unknown=sites(after['unknown_calls'])
        pred=sites(after['recognized'])
        inactive=sites(sample['excluded_callsite_annotations'])
        for row in gold:
            if (row['api_name'],row['start'],row['end']) not in pred:
                errors.append({'opaque_id':sample['opaque_id'],'error_type':'FN',**row,
                               'E11_status':'Unknown' if (row['api_name'],row['start'],row['end']) in unknown else 'Not detected'})
        for row in after['recognized']:
            site=(row['api_name'],row['start'],row['end'])
            if site not in expected:
                errors.append({'opaque_id':sample['opaque_id'],'error_type':'FP',
                               **{field:row[field] for field in ['api_name','family','start','end','line','expression']},
                               'evidence':'Explicit #if 0 site excluded from gold' if site in inactive else 'Not in reviewed scoped annotation',
                               'E11_status':'recognized'})
        records.append({'opaque_id':sample['opaque_id'],'context_status':sample['context_status'],
                        'metrics':per_sample,'E0_apis':sorted(base.sink_apis),
                        'E1':before,'E11':after,'annotated_callsites':len(gold),
                        'E0_false_positive_APIs':sorted(set(base.sink_apis)-gold_api)})
    summary={'date':'2026-10-21','experiment':'Frozen E1.1 fresh-dev50 technical evaluation',
             'samples':len(annotations),'annotated_callsites':sum(len(s['callsite_annotations']) for s in annotations),
             'gold_positive_samples':sum(bool(s['callsite_annotations']) for s in annotations),
             'explicit_inactive_sites_excluded':sum(len(s['excluded_callsite_annotations']) for s in annotations),
             'incomplete_input_samples':[s['opaque_id'] for s in annotations if s['context_status']=='INCOMPLETE_INPUT'],
             'metrics':{name:totals_metrics(counts) for name,counts in totals.items()},
             'annotation_independent':False,'annotation_type':specs['annotation_type'],'review_exposure':specs['review_exposure'],
             'scope':specs['scope'],'outside_rule_development_samples':True,'final_test':False,
             'E11_source_sha256':digest_file(source),'annotation_specs_sha256':digest_file(specs_path),
             'E11_registry_sha256':REGISTRY_SHA256,'E1_source_sha256':baseline_hash,
             'E11_missed_API_names':sorted({row['api_name'] for row in errors if row['error_type']=='FN'}),
             'E11_inactive_call_false_positives':sum(row['error_type']=='FP' and row['evidence'].startswith('Explicit #if 0') for row in errors),
             'strict_H2_gate':'NOT_PASSED: real-code errors and independent semantic validation remain; no LLM/candidate evaluation run',
             'production_changed':False,'LLM_calls':0}
    (DIRECTORY/'fresh_dev50_scored_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DIRECTORY/'fresh_dev50_scored_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (DIRECTORY/'fresh_dev50_E11_errors.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        fields=['opaque_id','error_type','api_name','family','start','end','line','expression','evidence','E11_status']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(errors)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
