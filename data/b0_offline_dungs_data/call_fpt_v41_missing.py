from __future__ import annotations
import csv, hashlib, json, pathlib, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace

repo=pathlib.Path(r'D:\JUNIOR\LabThayTho\GRACE-H3-BenchmarkEnsemble')
stage=pathlib.Path(r'D:\JUNIOR\LabThayTho\tmp\b0_h3b_exact_sjh9nczr')
out=pathlib.Path(r'D:\JUNIOR\LabThayTho\B0_offline')
sys.path.insert(0,str(repo))
from grace_h1.fpt_provider import load_fpt_settings, FPTClient
from grace_h1.parser import parse_prediction
from grace_h1.io import iter_jsonl, write_json, write_jsonl, sha256

missing=list(csv.DictReader(open(out/'missing_validation_expert_ids.csv',encoding='utf-8-sig')))
expected={ds: {r['id']:r for r in missing if r['dataset']==ds} for ds in ('devign','reveal')}
settings=load_fpt_settings()
if settings is None or not settings.get('api_key'): raise RuntimeError('FPT_API missing in shared environment')
# Match the requested FPT V4.1 Flash identity; leave the shared .env unchanged.
settings['model']='DeepSeek-V4.1-Flash'
client=FPTClient(settings)

jobs=[]
for ds in ('devign','reveal'):
    runs=list((stage/'runs'/ds/'validation'/'baseline_whitening').glob('*/prompts.jsonl'))
    if len(runs)!=1: raise RuntimeError(f'{ds}: expected one regenerated prompt file, got {len(runs)}')
    prompts=list(iter_jsonl(runs[0]))
    byid={p['record_id']:p for p in prompts}
    if len(byid)!=len(prompts) or set(byid)!=set(expected[ds]):
        raise RuntimeError(f'{ds}: regenerated prompt IDs do not exactly match missing IDs')
    for rid,p in byid.items():
        if sha256(p['prompt'])!=p['prompt_sha256'] or p['dataset']!=ds or p['split']!='validation':
            raise RuntimeError(f'{ds}/{rid}: prompt integrity/split check failed')
        jobs.append((ds,rid,p,runs[0]))
print(f'Prepared FPT calls: {len(jobs)}',flush=True)

def call(job):
    ds,rid,p,prompt_path=job
    cfg=SimpleNamespace(temperature=0.0,seed=42,max_output_tokens=256)
    error=None; response=None; attempts=0
    for attempts in range(1,6):
        try:
            response=client.generate_content(model=settings['model'],contents=p['prompt'],config=cfg)
            if not response.text or not response.text.strip(): raise ValueError('empty response')
            error=None; break
        except Exception as exc:
            error=repr(exc)
            code=getattr(exc,'code',getattr(exc,'status',None))
            if code in (400,401,403,404) or attempts==5: break
            time.sleep(min(120,5*2**(attempts-1)))
    if response is None:
        raw=''
        usage=None
    else:
        raw=response.text
        usage=None if response.usage_metadata is None else {k:getattr(response.usage_metadata,k,None) for k in ('prompt_token_count','candidates_token_count','total_token_count')}
    parsed=parse_prediction(raw)
    return {'dataset':ds,'split':'validation','id':rid,'code_sha256':p['code_sha256'],
            'prompt_sha256':p['prompt_sha256'],'prompt_path':str(prompt_path),
            'provider':'FPT AI Factory','model':settings['model'],'base_url':settings['base_url'].rstrip('/'),
            'temperature':0.0,'seed':42,'max_tokens':256,'thinking':False,
            'attempts':attempts,'request_status':'ok' if error is None else 'exhausted','request_error':error,
            'raw_response':raw,'raw_response_sha256':sha256(raw),'usage':usage,
            'parse_status':parsed.parse_status,'parse_method':parsed.parse_method,'prediction':parsed.prediction}

results=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(call,j) for j in jobs]
    for i,f in enumerate(as_completed(futures),1):
        r=f.result(); results.append(r)
        if i%10==0 or i==len(jobs): print(f'FPT responses {i}/{len(jobs)}',flush=True)
results.sort(key=lambda x:(x['dataset'],x['id']))
write_jsonl(out/'fpt_v41_validation_fill_raw.jsonl',results)
write_jsonl(out/'fpt_v41_validation_fill_predictions.jsonl',[
 {'dataset':r['dataset'],'split':r['split'],'id':r['id'],'code_sha256':r['code_sha256'],
  'prediction':r['prediction'],'valid':int(r['parse_status']=='valid' and r['request_status']=='ok'),
  'provider':r['provider'],'model':r['model'],'prompt_sha256':r['prompt_sha256']} for r in results])
manifest={'purpose':'fill only validation IDs omitted from archived prompt cohort',
 'provider':'FPT AI Factory','model':settings['model'],'base_url':settings['base_url'].rstrip('/'),
 'prompt_source':'H3-B validation prompt pipeline freshly prepared for the omitted IDs',
 'temperature':0.0,'seed':42,'max_tokens':256,'thinking':False,
 'count':len(results),'valid':sum(r['parse_status']=='valid' and r['request_status']=='ok' for r in results),
 'invalid_or_failed':sum(not (r['parse_status']=='valid' and r['request_status']=='ok') for r in results),
 'datasets':{ds:{'count':sum(r['dataset']==ds for r in results),'valid':sum(r['dataset']==ds and r['parse_status']=='valid' and r['request_status']=='ok' for r in results)} for ds in ('devign','reveal')},
 'note':'These are new FPT outputs, not the archived Vertex validation responses. Do not merge without recording mixed provider provenance.'}
write_json(out/'fpt_v41_validation_fill_manifest.json',manifest)
print(json.dumps(manifest,ensure_ascii=False,indent=2),flush=True)
