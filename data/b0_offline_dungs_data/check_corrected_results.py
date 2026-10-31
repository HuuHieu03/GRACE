import json
from pathlib import Path
p=Path(__file__).resolve().parent
for ds in ('devign','reveal'):
 data=json.loads((p/'runs'/f'complementarity_{ds}.json').read_text(encoding='utf8'))
 print(ds, 'repair_harm',data['repair_harm_test'],'oracle',data['oracle_test'])
 print('pre_post_test',data['pre_post_test']['delta_mcc'],data['pre_post_test']['verdict_mcc'])
 print('providers',data['provenance']['validation_provider_counts'])
 assert data == json.loads((p/f'complementarity_{ds}_fpt_mixed.json').read_text(encoding='utf8'))
