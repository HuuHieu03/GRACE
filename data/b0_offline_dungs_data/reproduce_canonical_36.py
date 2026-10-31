import csv,hashlib,json,math,pathlib,sys
from collections import Counter
from sklearn.metrics import accuracy_score,balanced_accuracy_score,confusion_matrix,f1_score,matthews_corrcoef,precision_score,recall_score
root=pathlib.Path(r'D:\JUNIOR\LabThayTho\SHARE_36_RUNS_CONTEXT8192_20261020_205918')
out=pathlib.Path(r'D:\JUNIOR\LabThayTho\B0_offline')
files=sorted((root/'runs').rglob('predictions.jsonl'))
if len(files)!=36: raise RuntimeError(f'Expected 36 historical runs, found {len(files)}')
canonical=[]; summaries=[]
def parse(raw):
 lines=[x.strip() for x in str(raw or '').splitlines() if x.strip()]
 return int(lines[-1]) if lines and lines[-1] in ('0','1') else None
for file in files:
 run=file.parent.parent
 manifest_path=run/'run_manifest.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
 dataset=(manifest.get('dataset') or manifest.get('config',{}).get('dataset') or '').lower()
 if dataset not in ('devign','reveal'):
  parts=[x.lower() for x in file.parts]
  dataset=next((x for x in ('devign','reveal') if x in parts),None)
 if dataset not in ('devign','reveal'): raise ValueError(f'Cannot infer dataset: {file}')
 split=manifest.get('split') or manifest.get('config',{}).get('split') or ('test_v2' if 'test_v2' in file.parts else 'test')
 run_id=run.relative_to(root).as_posix()
 model=manifest.get('model') or manifest.get('config',{}).get('model') or manifest.get('inference',{}).get('model')
 provider=manifest.get('provider') or manifest.get('config',{}).get('provider') or manifest.get('inference',{}).get('provider')
 rows=[json.loads(line) for line in file.open(encoding='utf-8') if line.strip()]
 if len({r.get('record_id',r.get('id')) for r in rows})!=len(rows): raise ValueError(f'Duplicate IDs in {run_id}')
 ys=[];ps=[]; raw_path=run/'inference'/'raw_responses.jsonl'
 rawmap={}
 if raw_path.exists():
  for line in raw_path.open(encoding='utf-8'):
   if line.strip():
    rr=json.loads(line);rawmap[rr.get('record_id',rr.get('id'))]=rr
 for row in rows:
  rid=row.get('record_id',row.get('id')); y=row.get('sealed_label',row.get('ground_truth',row.get('y'))); pred=row.get('prediction')
  status=row.get('request_status','ok')
  raw=row.get('raw_response')
  if raw is None and rid in rawmap: raw=rawmap[rid].get('raw_response')
  parsed=parse(raw) if raw is not None else (int(pred) if pred in (0,1) else None)
  valid=int(status in ('ok','valid',None) and pred in (0,1) and parsed==int(pred))
  if y not in (0,1): raise ValueError(f'Missing label {run_id} {rid}')
  canonical.append({'run_id':run_id,'dataset':dataset,'split':split,'arm':run.parent.name if run.name in ('test','test_v2') else run.name,'id':rid,'y':int(y),'prediction':int(pred) if pred in (0,1) else '', 'valid':valid,'request_status':status,'model':model or '', 'provider':provider or '', 'raw_response_sha256':hashlib.sha256(str(raw or '').encode()).hexdigest()})
  if valid: ys.append(int(y));ps.append(int(pred))
 if not ys: met={k:None for k in ('accuracy','precision','recall','f1','mcc','balanced_accuracy')}; cm=[0,0,0,0]
 else:
  tn,fp,fn,tp=confusion_matrix(ys,ps,labels=[0,1]).ravel().tolist()
  met={'accuracy':accuracy_score(ys,ps),'precision':precision_score(ys,ps,zero_division=0),'recall':recall_score(ys,ps,zero_division=0),'f1':f1_score(ys,ps,zero_division=0),'mcc':matthews_corrcoef(ys,ps),'balanced_accuracy':balanced_accuracy_score(ys,ps)};cm=[tn,fp,fn,tp]
 eval_path=run/'evaluation'/'evaluation.json'; stored=json.loads(eval_path.read_text(encoding='utf-8')) if eval_path.exists() else {}
 compare={};
 for key in met:
  old=stored.get({'accuracy':'accuracy_valid'}.get(key,key))
  compare[key]=None if old is None or met[key] is None else abs(float(old)-met[key])
 summaries.append({'run_id':run_id,'dataset':dataset,'split':split,'n_targets':len(rows),'n_valid':len(ys),'n_invalid':len(rows)-len(ys),'tn_fp_fn_tp':cm,**met,'stored_metric_abs_diff':compare,'max_abs_diff':max((x for x in compare.values() if x is not None),default=None),'stored_eval':eval_path.exists()})
fields=list(canonical[0])
with (out/'canonical_historical_36.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(canonical)
(out/'metric_reproduction_historical_36.json').write_text(json.dumps({'scope':'36 historical test runs in SHARE_36_RUNS_CONTEXT8192_20261020_205918/runs','n_run':len(summaries),'n_canonical_rows':len(canonical),'n_unique_run_id_target_pairs':len({(r['run_id'],r['id']) for r in canonical}),'runs':summaries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (out/'metric_reproduction_historical_36.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
print('runs',len(summaries),'canonical_rows',len(canonical),'bytes', (out/'canonical_historical_36.csv').stat().st_size)
print('missing_eval',[r['run_id'] for r in summaries if not r['stored_eval']])
print('max diff',max(r['max_abs_diff'] or 0 for r in summaries),'over .001',[r['run_id'] for r in summaries if (r['max_abs_diff'] or 0)>.001])
print('coverage targets',sum(r['n_targets'] for r in summaries),'valid',sum(r['n_valid'] for r in summaries),'invalid',sum(r['n_invalid'] for r in summaries))
