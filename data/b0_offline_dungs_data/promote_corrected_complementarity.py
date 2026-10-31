"""Preserve stale outputs, then promote checked locked-checkpoint rebuilds."""
import json
import shutil
from pathlib import Path

p=Path(__file__).resolve().parent
expected={'devign': (303,580), 'reveal': (218,201)}
for ds,(repair,harm) in expected.items():
    candidate=p/'runs'/f'complementarity_{ds}.rebuild.json'
    data=json.loads(candidate.read_text(encoding='utf8'))
    totals=data['repair_harm_test']['total']
    assert (totals['repair'],totals['harm']) == (repair,harm)
    assert data['provenance']['gate_threshold'] == {'devign':.53,'reveal':.14}[ds]
for ds in expected:
    candidate=p/'runs'/f'complementarity_{ds}.rebuild.json'
    for destination in (p/'runs'/f'complementarity_{ds}.json',p/f'complementarity_{ds}_fpt_mixed.json'):
        backup=destination.with_name(destination.stem+'.stale_20261029'+destination.suffix)
        if destination.exists() and not backup.exists(): shutil.copy2(destination,backup)
        shutil.copy2(candidate,destination)
        print('updated',destination)
