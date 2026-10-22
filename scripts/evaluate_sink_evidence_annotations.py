"""Score frozen E0/E1 against explicit technical annotations of real code.

Gold spans are located from manually listed APIs/counts, never copied from E1.
This is exploratory source review, not independent human ground truth.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent.parent
DIRECTORY=ROOT/'project_docs/reports/sink_evidence_h1'


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def locate_reviewed_calls(code, api_name, expected_count):
    """Resolve offsets of an explicitly reviewed API; verify the manual count.

    Does not discover which APIs are sinks. Quotes/comments inside arguments
    are skipped to balance parentheses correctly in the original source.
    """
    matches=list(re.finditer(r'\b'+re.escape(api_name)+r'\s*\(',code))
    if len(matches)!=expected_count:
        raise ValueError(f'{api_name}: reviewed count {expected_count}, raw matches {len(matches)}')
    sites=[]
    for match in matches:
        idx=code.index('(',match.start())
        depth=0
        while idx<len(code):
            char=code[idx]
            if code.startswith('//',idx):
                idx=code.find('\n',idx)
                if idx<0:
                    raise ValueError(f'{api_name}: unclosed annotated expression')
                continue
            if code.startswith('/*',idx):
                idx=code.find('*/',idx+2)
                if idx<0:
                    raise ValueError(f'{api_name}: unclosed comment')
                idx+=2
                continue
            if char in {'"',"'"}:
                quote=char
                idx+=1
                while idx<len(code) and code[idx]!=quote:
                    idx+=2 if code[idx]=='\\' else 1
            elif char=='(':
                depth+=1
            elif char==')':
                depth-=1
                if depth==0:
                    sites.append((match.start(),idx+1))
                    break
            idx+=1
        else:
            raise ValueError(f'{api_name}: unclosed annotated expression')
    return sites


def set_metrics(actual,expected):
    return len(actual&expected),len(actual-expected),len(expected-actual)


def totals_metrics(counts):
    tp,fp,fn=counts
    return {'tp':tp,'fp':fp,'fn':fn,
            'precision':round(tp/(tp+fp),6) if tp+fp else None,
            'recall':round(tp/(tp+fn),6) if tp+fn else None}


def main():
    packet=json.loads((DIRECTORY/'verification_annotation_packet.json').read_text(encoding='utf-8'))
    manifest=json.loads((DIRECTORY/'verification_manifest_private.json').read_text(encoding='utf-8'))
    specs=json.loads((DIRECTORY/'technical_annotation_specs.json').read_text(encoding='utf-8'))
    by_id={r['opaque_id']:r for r in packet}
    reviewed={r['id']:r for r in specs['samples']}
    frozen={r['opaque_id']:r for r in manifest['samples']}
    assert len(packet)==len(reviewed)==50 and set(by_id)==set(reviewed)==set(frozen)
    annotations=[]
    for opaque_id in sorted(by_id):
        sample=by_id[opaque_id]
        code=sample['code']
        assert sha_text(code)==sample['code_sha256']==frozen[opaque_id]['code_sha256']
        spec=reviewed[opaque_id]
        sites=[]
        for api,family,count in spec['calls']:
            for start,end in locate_reviewed_calls(code,api,count):
                sites.append({'api_name':api,'family':family,'start':start,'end':end,
                              'line':code.count('\n',0,start)+1,'expression':code[start:end],
                              'evidence':spec['notes'],
                              'annotation_basis':'Explicit technical source review; wrapper bodies may be unavailable'})
        sites.sort(key=lambda r:r['start'])
        assert len({(r['api_name'],r['start'],r['end']) for r in sites})==len(sites)
        annotations.append({'opaque_id':opaque_id,'code_sha256':sha_text(code),
                            'context_status':spec.get('context_status','FUNCTION_TEXT_AVAILABLE'),
                            'callsite_annotations':sites,'review_notes':spec['notes']})
    annotation_payload={'annotation_type':specs['annotation_type'],'scope':specs['scope'],
                        'review_exposure':specs['review_exposure'],'independent':False,'samples':annotations}
    gold_path=DIRECTORY/'verification_annotations_technical.json'
    gold_path.write_text(json.dumps(annotation_payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Gold is written before invoking either method. E1 source is unchanged.
    sys.path.insert(0,str(ROOT/'src'))
    from security_signature.extractor import extract_security_signature
    from security_signature.sink_evidence import extract_sink_evidence
    # Prior script hashed raw file bytes, including repository line endings.
    e1_byte_hash=hashlib.sha256((ROOT/'src/security_signature/sink_evidence.py').read_bytes()).hexdigest()
    initial=json.loads((DIRECTORY/'summary.json').read_text(encoding='utf-8'))
    assert initial['E1_source_sha256']==e1_byte_hash,'E1 changed since frozen coverage experiment'
    totals={k:[0,0,0] for k in ['E0_API','E1_API','E1_callsite','E1_family_callsite']}
    records=[]
    misses=[]
    for sample in annotations:
        code=by_id[sample['opaque_id']]['code']
        e0=extract_security_signature(code)
        e1=extract_sink_evidence(code)
        gold=sample['callsite_annotations']
        gold_apis={r['api_name'] for r in gold}
        gold_sites={(r['api_name'],r['start'],r['end']) for r in gold}
        pred_sites={(r['api_name'],r['start'],r['end']) for r in e1['recognized']}
        gold_families={(r['api_name'],r['start'],r['end'],r['family']) for r in gold}
        pred_families={(r['api_name'],r['start'],r['end'],r['family']) for r in e1['recognized']}
        sets={'E0_API':(set(e0.sink_apis),gold_apis),'E1_API':(set(e1['sink_apis']),gold_apis),
              'E1_callsite':(pred_sites,gold_sites),'E1_family_callsite':(pred_families,gold_families)}
        result={key:totals_metrics(set_metrics(*values)) for key,values in sets.items()}
        for key,values in sets.items():
            for idx,value in enumerate(set_metrics(*values)):
                totals[key][idx]+=value
        unknown_sites={(r['api_name'],r['start'],r['end']) for r in e1['unknown_calls']}
        for row in gold:
            site=(row['api_name'],row['start'],row['end'])
            if site not in pred_sites:
                misses.append({'opaque_id':sample['opaque_id'],**row,
                               'E1_status':'Unknown' if site in unknown_sites else 'Not detected',
                               'next_action':'Audit family and add exact-name rule only on a new development version; do not tune frozen E1 before recording results'})
        records.append({'opaque_id':sample['opaque_id'],'context_status':sample['context_status'],
                        'gold_apis':sorted(gold_apis),'E0_apis':sorted(e0.sink_apis),'E1_apis':e1['sink_apis'],
                        'E0_false_positive_apis':sorted(set(e0.sink_apis)-gold_apis),
                        'E1_false_positive_apis':sorted(set(e1['sink_apis'])-gold_apis),
                        'metrics':result})
    summary={'date':'2026-10-21','samples':50,'annotation_type':specs['annotation_type'],
             'review_exposure':specs['review_exposure'],'annotation_independent':False,
             'scope':specs['scope'],'gold_callsite_count':sum(len(r['callsite_annotations']) for r in annotations),
             'gold_positive_samples':sum(bool(r['callsite_annotations']) for r in annotations),
             'incomplete_input_samples':[r['opaque_id'] for r in annotations if r['context_status']=='INCOMPLETE_INPUT'],
             'metrics':{k:totals_metrics(v) for k,v in totals.items()},
             'E1_missed_callsite_count':len(misses),
             'E1_missed_API_names':sorted({r['api_name'] for r in misses}),
             'E1_source_frozen_sha256':e1_byte_hash,
             'annotation_specs_sha256':hashlib.sha256((DIRECTORY/'technical_annotation_specs.json').read_bytes()).hexdigest(),
             'strict_H2_gate':'NOT_PASSED: independent semantic annotation audit remains unverified; real-code FN must be assessed',
             'interpretation':'Exploratory scored technical review, not independently validated real-code accuracy. Unknown calls that are annotated positive count as FN, not dropped.',
             'unit_notes':'E0/E1 API metrics use unique API names per sample; E1 callsite includes repeated syntactic sites and exact offsets. No TN/accuracy for unenumerated negative sites.',
             'production_changed':False,'LLM_calls':0}
    (DIRECTORY/'verification_scored_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DIRECTORY/'verification_scored_records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (DIRECTORY/'verification_E1_missed_calls.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(misses[0]) if misses else ['opaque_id','api_name'])
        writer.writeheader();writer.writerows(misses)
    wrapper_proposals=[]
    for api in sorted({r['api_name'] for r in misses}):
        examples=[r for r in misses if r['api_name']==api]
        wrapper_proposals.append({'api_name':api,'proposed_families':sorted({r['family'] for r in examples}),
                                  'missed_callsites':len(examples),
                                  'samples':sorted({r['opaque_id'] for r in examples}),
                                  'example_expression':examples[0]['expression'],
                                  'rationale':examples[0]['evidence'],
                                  'status':'PROPOSED_NOT_INSTALLED',
                                  'validation_needed':'Exact call-name rule only; comment/string/prototype negatives, family review and wrapper contract audit; evaluate next version on new data'})
    (DIRECTORY/'wrapper_registry_proposals.json').write_text(json.dumps(wrapper_proposals,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
