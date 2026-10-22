"""Offline E0/E1 evidence experiment. Real-code coverage is not accuracy."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'src'))
from security_signature.extractor import extract_security_signature
from security_signature.sink_evidence import extract_sink_evidence, WRAPPER_RULES

OUT=ROOT/'project_docs/reports/sink_evidence_h1'

# Explicit authored expectations. These are development fixtures, not human
# annotations of the remaining Devign functions and not independent validation.
FIXTURES=[
    ('comment','void f(void) { /* memcpy(d,s,n); free(p); */ }',[]),
    ('line_comment','void f(void) { // read(fd,b,n);\n }',[]),
    ('string','void f(void) { puts("read(fd,b,n); free(p)"); }',[]),
    ('variable','void f(void) { int read=0; read++; }',[]),
    ('prototype','extern void *malloc(size_t n);',[]),
    ('local_prototype','void f(void) { extern void free(void *p); }',[]),
    ('definition','void free(void *p) { }',[]),
    ('macro_definition','#define COPY(d,s,n) memcpy(d,s,n)\nvoid f(void) {}',[]),
    ('copy','void f(void) { memcpy(d,s,n); }',['memcpy(d,s,n)']),
    ('nested','void f(void) { memcpy(d,malloc(n),n); }',['memcpy(d,malloc(n),n)','malloc(n)']),
    ('two_calls','void f(void) { free(a); free(b); }',['free(a)','free(b)']),
    ('return','void *f(void) { return malloc(n); }',['malloc(n)']),
    ('cast','void f(void) { (void)memcpy(d,s,n); }',['memcpy(d,s,n)']),
    ('conditional','void f(void) { if(ok) free(p); }',['free(p)']),
    ('wrong_guard','void f(void) { if(other < max) memcpy(d,s,n); }',['memcpy(d,s,n)']),
    ('late_guard','void f(void) { memcpy(d,s,n); if(n>max) return; }',['memcpy(d,s,n)']),
    ('log_only_guard','void f(void) { if(n>max) puts("error"); memcpy(d,s,n); }',['memcpy(d,s,n)']),
    ('wrapper_alloc','void f(void) { av_mallocz(n); g_free(p); }',['av_mallocz(n)','g_free(p)']),
    ('wrapper_read','void f(void) { bdrv_pread(bs,o,b,n); }',['bdrv_pread(bs,o,b,n)']),
    ('wrapper_packet','void f(void) { av_new_packet(pkt,n); }',['av_new_packet(pkt,n)']),
    ('unknown_wrapper','void f(void) { bdrv_mystery(bs); }',[]),
    ('unknown_macro','void f(void) { WRITEBGR24(x); }',[]),
    ('member','void f(void) { obj->free(p); }',[]),
    ('incomplete','void f(void) { memcpy(d,s,',[]),
]


def metrics(tp,fp,fn):
    return {'tp':tp,'fp':fp,'fn':fn,'precision':round(tp/(tp+fp),4) if tp+fp else None,
            'recall':round(tp/(tp+fn),4) if tp+fn else None}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    fixture_results=[]
    totals={'E0_api':[0,0,0],'E1_api':[0,0,0],'E1_callsite':[0,0,0]}
    for name,code,expressions in FIXTURES:
        gold=set()
        for expr in expressions:
            start=code.index(expr)
            gold.add((expr.split('(')[0],start,start+len(expr)))
        gold_apis={r[0] for r in gold}
        e0=extract_security_signature(code)
        e1=extract_sink_evidence(code)
        predicted={(r['api_name'],r['start'],r['end']) for r in e1['recognized']}
        for key,actual,expected in [('E0_api',set(e0.sink_apis),gold_apis),
                                    ('E1_api',set(e1['sink_apis']),gold_apis),
                                    ('E1_callsite',predicted,gold)]:
            for idx,value in enumerate([len(actual&expected),len(actual-expected),len(expected-actual)]):
                totals[key][idx]+=value
        fixture_results.append({'fixture':name,'code':code,'expected_expressions':expressions,
                                'E0_apis':sorted(e0.sink_apis),'E1':e1,
                                'E1_exact_callsite_match':predicted==gold})

    split=json.loads((ROOT/'data/splits/devign_dev_clean_100_ids.json').read_text(encoding='utf-8'))
    with (ROOT/'project_docs/reports/blind_review_sheet_hieu.csv').open(encoding='utf-8-sig',newline='') as stream:
        reviewed={r['target_id'] for r in csv.DictReader(stream)}
    remaining=sorted([r for r in split['sample_details'] if str(r['id']) not in reviewed],key=lambda r:str(r['id']))
    assert len(remaining)==50
    manifest={'purpose':'H1 real-code annotation pending; dev samples previously used in B2/B3, not untouched test',
              'reviewed_50_excluded':True,
              'samples':[{'opaque_id':f'H1-{i:03d}','source_id':r['id'],
                          'code_sha256':hashlib.sha256(r['func'].encode('utf-8')).hexdigest()} for i,r in enumerate(remaining,1)]}
    manifest_path=OUT/'verification_manifest_private.json'
    if manifest_path.exists():
        assert json.loads(manifest_path.read_text(encoding='utf-8'))==manifest, 'Frozen verification inputs changed'
    else:
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    coverage=[]
    packet=[]
    for item,source in zip(manifest['samples'],remaining):
        code=source['func']
        e0=extract_security_signature(code)
        e1=extract_sink_evidence(code)
        # Deliberately supply code alone. Labels and original ID never enter E1.
        assert extract_sink_evidence(dict(func=code,id='label_True',target=1)['func'])==extract_sink_evidence(dict(func=code,id='label_False',target=0)['func'])
        coverage.append({'opaque_id':item['opaque_id'],'E0_apis':';'.join(sorted(e0.sink_apis)),
                         'E1_apis':';'.join(e1['sink_apis']),'E1_recognized_sites':len(e1['recognized']),
                         'E1_unknown_calls':len(e1['unknown_calls']),'E1':e1})
        # Annotation packet excludes predictions, labels and original filename.
        packet.append({'opaque_id':item['opaque_id'],'code_sha256':item['code_sha256'],'code':code,
                       'expected_callsite_annotations':None,'annotator_notes':'',
                       'annotation_schema':{'api_name':'str','family':'str','start':'0-based inclusive','end':'exclusive',
                                            'status':'recognized/unknown/non_sink','evidence':'code-based justification'}})
    (OUT/'verification_annotation_packet.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'verification_predictions.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'fixture_results.json').write_text(json.dumps(fixture_results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary={'experiment':'H1 sink evidence E0 versus E1','date':'2026-10-21',
             'production_extractor_changed':False,
             'E1_source_sha256':hashlib.sha256((ROOT/'src/security_signature/sink_evidence.py').read_bytes()).hexdigest(),
             'wrapper_rules':WRAPPER_RULES,
             'authored_development_fixtures':{'count':len(FIXTURES),'E1_exact_callsite_passed':sum(r['E1_exact_callsite_match'] for r in fixture_results),
                                             'metrics':{k:metrics(*v) for k,v in totals.items()},
                                             'comparison_unit':'E0/E1 compare unique API sets per fixture; E1 additionally scored exact callsite spans',
                                             'independently_annotated':False},
             'verification_dev50':{'samples':50,'E0_with_sink_apis':sum(bool(r['E0_apis']) for r in coverage),
                                   'E1_with_sink_apis':sum(bool(r['E1_apis']) for r in coverage),
                                   'E1_with_unknown_calls':sum(bool(r['E1_unknown_calls']) for r in coverage),
                                   'real_code_precision_recall':None,'annotation_status':'PENDING',
                                   'scope':'Coverage only; no real-code accuracy claim; no final test opened'},
             'H2_gate':'NOT_PASSED: real-code callsite annotations and semantic precision audit are pending',
             'limits':['Lexical scanner cannot resolve all C/C++ declarations, shadowed functions, inactive preprocessor branches, indirect calls or macros.',
                       'Recognized operation is not proof of taint, guard efficacy or vulnerability.',
                       'Wrapper assignments are explicit hypotheses requiring annotation audit.']}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='wrapper_rules'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
