import csv,json,pathlib
root=pathlib.Path(r'D:\JUNIOR\LabThayTho')
bundle=root/'SHARE_36_RUNS_CONTEXT8192_20261020_205918'/'additional_runs'/'kaggle_deepseek_v41_h3b_validation_20261024'
out=root/'B0_offline'
# FPT raw and previously archived Vertex predictions
fpt={r['id']:r for r in (json.loads(l) for l in (out/'fpt_v41_validation_fill_raw.jsonl').open(encoding='utf-8'))}
assert len(fpt)==85 and all(r['request_status']=='ok' and r['parse_status']=='valid' and r['prediction'] in (0,1) for r in fpt.values())
for ds,expected_old in (('devign',2724),('reveal',2196)):
 gate=list(csv.DictReader((out/f'{ds}_gate_validation_exact.csv').open(encoding='utf-8-sig',newline='')))
 g={r['id']:r for r in gate}; assert len(g)==len(gate) and len(g)==(2732 if ds=='devign' else 2273)
 hist={}
 with (bundle/ds/'predictions.jsonl').open(encoding='utf-8') as h:
  for line in h:
   x=json.loads(line); hist[x['record_id']]=x
 assert len(hist)==expected_old,(ds,len(hist))
 assert set(hist).isdisjoint(fpt) or all(x['dataset']!=ds for x in fpt.values())
 rows=[]
 for rid,base in g.items():
  if rid in hist:
   p=hist[rid]; assert p['code_sha256']==base['code_sha256'] and p['request_status']=='valid' and p['prediction'] in (0,1),(ds,rid,p)
   score=int(p['prediction']);valid=1;provider='Vertex AI MaaS / DeepSeek V4.1 Flash'
  else:
   p=fpt.get(rid); assert p and p['dataset']==ds and p['code_sha256']==base['code_sha256'],(ds,rid)
   score=int(p['prediction']);valid=1;provider='FPT AI Factory / DeepSeek V4.1 Flash (new fill)'
  rows.append({'dataset':ds,'split':'validation','id':rid,'code_sha256':base['code_sha256'],'y':base['y'],'p_gate':base['p_gate'],'s_llm':score,'valid':valid,'group':base['group'],'llm_provider':provider})
 assert len(rows)==len(g) and len({r['id'] for r in rows})==len(rows)
 path=out/f'{ds}_validation_join_with_fpt.csv'
 with path.open('w',encoding='utf-8-sig',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print(ds,'joined',len(rows),'historical',len(hist),'FPT fill',len(rows)-len(hist),'output',path)
