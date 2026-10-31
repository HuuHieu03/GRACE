"""Compare threshold policies with locked H3-B manifests and available archives."""
import csv,json
from pathlib import Path
p=Path(__file__).resolve().parent
r=p.parent
for ds in ('devign','reveal'):
 data=json.loads((p/'runs'/f'complementarity_{ds}.train_oof.json').read_text(encoding='utf8'))
 val=json.loads((p/'runs'/f'complementarity_{ds}.json').read_text(encoding='utf8'))
 pr=data['provenance']; print(ds,'train',pr['gate_threshold'],pr['gate_arm'],'validation',val['provenance']['gate_threshold'])
 rows=list(csv.DictReader((p/f'{ds}_test_join_exact.csv').open(encoding='utf-8-sig',newline='')))
 pred={x['id']:int(float(x['p_gate'])>=pr['gate_threshold']) for x in rows}
 for path in (r/'GRACE-H3-BenchmarkEnsemble/runs/h3v2/notebook_sessions/deepseek_v41_hieu_8192_seed42/test'/ds/'42/gate_train_threshold.jsonl',r/'GRACE-H3-BenchmarkEnsemble/runs/h3v2/5fc21bd7cafff9846aff/predictions'/ds/'42/gate_train_threshold.jsonl'):
  if not path.exists():continue
  saved=[json.loads(x) for x in path.open(encoding='utf8')]
  savedmap={x['record_id']:x for x in saved}
  if set(savedmap)!=set(pred): print('different IDs',path); continue
  agree=sum(pred[i]==int(x['prediction']) for i,x in savedmap.items())/len(pred)
  print('archive',path,'agreement',agree)
 print('repair/harm',data['repair_harm_test']['total'],'prepost',data['pre_post_test']['delta_mcc'])
