import csv, json, os, pathlib, shutil, sys
src=pathlib.Path(r'D:\JUNIOR\LabThayTho\GRACE-H3-BenchmarkEnsemble')
stage=pathlib.Path(r'D:\JUNIOR\LabThayTho\tmp\b0_h3b_exact_sjh9nczr')
snapshot=pathlib.Path(r'D:\JUNIOR\LabThayTho\SHARE_36_RUNS_CONTEXT8192_20261020_205918\additional_runs\H3-BenchmarkEnsemble\validation8192_test24000_20261021')
missing=list(csv.DictReader(open(r'D:\JUNIOR\LabThayTho\B0_offline\missing_validation_expert_ids.csv',encoding='utf-8-sig')))
for name in ('reference_contract.yaml','prompt_template.txt'):
 (stage/'configs').mkdir(exist_ok=True)
 shutil.copy2(snapshot/'configs'/name,stage/'configs'/name)
(stage/'cache'/'legacy_candidates').mkdir(parents=True,exist_ok=True)
for p in (src/'cache'/'legacy_candidates').glob('*.jsonl'):
 shutil.copy2(p,stage/'cache'/'legacy_candidates'/p.name)
# use only local path settings needed for graph extraction; never read or print API secrets
for line in (pathlib.Path(r'D:\JUNIOR\LabThayTho')/'.env').read_text(encoding='utf-8-sig').splitlines():
 if line.startswith('JOERN_HOME='): os.environ['JOERN_HOME']=line.split('=',1)[1].strip().strip('"\'')
sys.path.insert(0,str(stage))
from grace_h1.pipeline import PipelineConfig, prepare_run
from grace_h1.graphs import GraphStore
orig=GraphStore.ensure
source_graphs=src/'cache'/'graphs'
def ensure_with_local_cache(self,row):
 h=row['code_sha256']; dst=self.root/'cache'/'graphs'/h; source=source_graphs/h
 if not self.exists(h) and source.is_dir():
  dst.parent.mkdir(parents=True,exist_ok=True)
  try: shutil.copytree(source,dst,dirs_exist_ok=True)
  except OSError: pass
 return orig(self,row)
GraphStore.ensure=ensure_with_local_cache
for ds in ('devign','reveal'):
 ids=[r['id'] for r in missing if r['dataset']==ds]
 print(f'Preparing {ds}: {len(ids)} omitted validation prompts',flush=True)
 out=prepare_run(stage,PipelineConfig(dataset=ds,split='validation',arm='baseline_whitening'),target_ids=ids)
 print(f'Prepared {ds}: {out}',flush=True)
