"""E1.2 preprocessor development regression; never overwrite E1/E1.1 data."""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from security_signature.sink_evidence_v11 import extract_sink_evidence as e11
from security_signature.sink_evidence_v12 import extract_sink_evidence as e12
from scripts.evaluate_sink_evidence_annotations import set_metrics,totals_metrics

REPORTS=ROOT/'project_docs/reports'
OUT=REPORTS/'sink_evidence_v12'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(name,packet_path,gold_path):
    packet=json.loads(packet_path.read_text(encoding='utf-8'))
    annotation=json.loads(gold_path.read_text(encoding='utf-8'))
    inputs={row['opaque_id']:row for row in packet}
    gold=annotation['samples']
    if len(packet)!=50 or len(gold)!=50 or {row['opaque_id'] for row in gold}!=set(inputs):
        raise ValueError('Regression input mismatch: '+name)
    totals={key:[0,0,0] for key in ['E11_callsite','E12_callsite','E12_family_callsite']}
    records=[]
    errors=[]
    lost_true=[]
    removed=[]
    conditional=0
    for sample in gold:
        code=inputs[sample['opaque_id']]['code']
        digest=hashlib.sha256(code.encode('utf-8')).hexdigest()
        if digest!=sample['code_sha256'] or digest!=inputs[sample['opaque_id']]['code_sha256']:
            raise ValueError('Annotated source changed: '+sample['opaque_id'])
        before,after=e11(code),e12(code)
        sites=lambda rows:{(r['api_name'],r['start'],r['end']) for r in rows}
        families=lambda rows:{(r['api_name'],r['start'],r['end'],r['family']) for r in rows}
        expected=sites(sample['callsite_annotations'])
        old=sites(before['recognized']);new=sites(after['recognized'])
        for key,comparison in {
            'E11_callsite':(old,expected),'E12_callsite':(new,expected),
            'E12_family_callsite':(families(after['recognized']),families(sample['callsite_annotations']))}.items():
            totals[key]=[a+b for a,b in zip(totals[key],set_metrics(*comparison))]
        lost_true.extend({'opaque_id':sample['opaque_id'],'site':site} for site in (old&expected)-new)
        for row in before['recognized']:
            if (row['api_name'],row['start'],row['end']) not in new:
                removed.append({'opaque_id':sample['opaque_id'],**row,
                                'was_gold_positive':(row['api_name'],row['start'],row['end']) in expected})
        unknown=sites(after['unknown_calls'])
        for row in sample['callsite_annotations']:
            if (row['api_name'],row['start'],row['end']) not in new:
                errors.append({'dataset':name,'opaque_id':sample['opaque_id'],'error_type':'FN',
                               **{field:row[field] for field in ['api_name','family','start','end','expression']},
                               'status':'Unknown' if (row['api_name'],row['start'],row['end']) in unknown else 'Not detected'})
        for row in after['recognized']:
            if (row['api_name'],row['start'],row['end']) not in expected:
                errors.append({'dataset':name,'opaque_id':sample['opaque_id'],'error_type':'FP',
                               **{field:row[field] for field in ['api_name','family','start','end','expression']},'status':'recognized'})
        conditional+=sum(row['preprocessor_state']=='conditional' for row in after['recognized'])
        records.append({'opaque_id':sample['opaque_id'],'E11':before,'E12':after})
    summary={'samples':50,'annotated_sites':sum(len(row['callsite_annotations']) for row in gold),
             'metrics':{key:totals_metrics(value) for key,value in totals.items()},
             'previously_true_sites_lost':lost_true,'removed_recognized_sites':len(removed),
             'retained_conditional_recognized_sites':conditional,
             'packet_sha256':sha(packet_path),'annotation_sha256':sha(gold_path),
             'scope':'Development regression: these inputs informed E1.2; not new held-out validation'}
    (OUT/(name+'_records.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/(name+'_removed_sites.json')).write_text(json.dumps(removed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary,errors


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    baseline=json.loads((REPORTS/'sink_evidence_v11/fresh_dev50_manifest_private.json').read_text(encoding='utf-8'))
    if sha(ROOT/'src/security_signature/sink_evidence_v11.py')!=baseline['E11_source_sha256']:
        raise ValueError('Frozen E1.1 source changed')
    old_baseline=json.loads((REPORTS/'sink_evidence_h1/summary.json').read_text(encoding='utf-8'))
    if sha(ROOT/'src/security_signature/sink_evidence.py')!=old_baseline['E1_source_sha256']:
        raise ValueError('Frozen E1 source changed')
    runs={}
    errors=[]
    for name,directory,packet,gold in [
        ('h1_dev50','sink_evidence_h1','verification_annotation_packet.json','verification_annotations_technical.json'),
        ('v11_dev50','sink_evidence_v11','fresh_dev50_annotation_packet.json','fresh_dev50_annotations_technical.json')]:
        runs[name],dataset_errors=evaluate(name,REPORTS/directory/packet,REPORTS/directory/gold)
        errors.extend(dataset_errors)
    summary={'date':'2026-10-21','experiment':'E1.2 inactive-preprocessor evidence regression',
             'E12_source_sha256':sha(ROOT/'src/security_signature/sink_evidence_v12.py'),
             'E11_source_sha256':baseline['E11_source_sha256'],
             'E1_source_sha256':old_baseline['E1_source_sha256'],'datasets':runs,
             'annotation_independent':False,'production_changed':False,'LLM_calls':0,
             'runtime_guards_assessed':False,'build_configuration_supplied':False,
             'conditional_policy':'Keep potentially active sites with explicit conditional metadata; only proven-dead regions are masked.',
             'limits':'Partial boolean preprocessor evaluator; unsupported arithmetic/macros/build conditions remain unknown; does not resolve #include or macro expansion.'}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'remaining_errors.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        fields=['dataset','opaque_id','error_type','api_name','family','start','end','expression','status']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(errors)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
