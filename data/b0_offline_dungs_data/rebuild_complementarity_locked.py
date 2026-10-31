"""Rebuild exploratory B0 complementarity from the locked H3-B inputs."""
import csv
import hashlib
import json
import os
import runpy
import sys
from collections import Counter
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import numpy as np

ROOT = Path(__file__).resolve().parent
KIT = ROOT.parent / 'GRACE-summary/01_Author_Baseline_Unified/diagnostic_kit/src'
sys.path.insert(0, str(KIT))

# Cache group membership across bootstrap iterations; draws and indices are
# identical to stats._resample_indices for the same RNG state.
from grace_diag import stats
_cache = {}
def cached_resample(rng, n, groups):
    if groups is None:
        return rng.integers(0, n, n)
    key = id(groups)
    if key not in _cache or _cache[key][0] is not groups:
        uniq, inv = np.unique(groups, return_inverse=True)
        _cache[key] = (groups, [np.flatnonzero(inv == g) for g in range(len(uniq))])
    members = _cache[key][1]
    picked = rng.integers(0, len(members), len(members))
    return np.concatenate([members[g] for g in picked])

# Verify the optimized draw against the original for both sample and clusters.
for groups in (None, np.array(['a','b','a','c','d'])):
    a, b = np.random.default_rng(42), np.random.default_rng(42)
    for _ in range(10):
        assert np.array_equal(stats._resample_indices(a, 5, groups), cached_resample(b, 5, groups))
stats._resample_indices = cached_resample

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def check(ds, split):
    csvpath = ROOT / (f'{ds}_validation_join_with_fpt.csv' if split == 'validation' else f'{ds}_test_join_exact.csv')
    nppath = ROOT / f'xpre_{split}_{ds}.npz'
    with csvpath.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    with np.load(nppath, allow_pickle=False) as data:
        ids, hashes, X = data['ids'].astype(str), data['code_sha256'].astype(str), data['X']
        assert len(rows) == len(ids) == len(set(ids)) and X.shape == (len(ids), 34)
        assert [r['id'] for r in rows] == ids.tolist()
        assert [r['code_sha256'] for r in rows] == hashes.tolist()
        assert np.allclose([float(r['p_gate']) for r in rows], X[:, 5], atol=1e-7, rtol=1e-7)
        assert all(r['y'] in ('0', '1') and r['valid'] in ('0', '1') for r in rows)
        return csvpath, nppath, rows

def main(ds, mode='validation_tuned'):
    ckpt = {'devign':'a93a831ac8416426a1d4','reveal':'b4564696e647259a09b9'}[ds]
    manifest = ROOT.parent / f'GRACE-H3-BenchmarkEnsemble/artifacts/h3v2/base/{ds}/42/{ckpt}/manifest.json'
    winner = json.loads(manifest.read_text(encoding='utf-8'))['winner']
    tau = float(winner['threshold']) if mode == 'train_oof' else {'devign': .53, 'reveal': .14}[ds]
    val, xv, val_rows = check(ds, 'validation')
    test, xt, test_rows = check(ds, 'test')
    suffix = '.train_oof' if mode == 'train_oof' else '.rebuild'
    output = ROOT / 'runs' / f'complementarity_{ds}{suffix}.json'
    sys.argv = ['complementarity_fixed.py', '--val', str(val), '--test', str(test),
                '--xpre-val', str(xv), '--xpre-test', str(xt), '--tau', str(tau),
                '--out', str(output), '--seed', '42']
    runpy.run_path(str(ROOT / 'complementarity_fixed.py'), run_name='__main__')
    data = json.loads(output.read_text(encoding='utf-8'))
    y = np.array([int(r['y']) for r in test_rows])
    h = np.array([float(r['p_gate']) >= tau for r in test_rows])
    g = np.array([int(float(r['s_llm']) >= .5) for r in test_rows])
    valid = np.array([r['valid'] == '1' for r in test_rows])
    assert data['repair_harm_test']['total']['repair'] == int(((h != y) & (g == y) & valid).sum())
    assert data['repair_harm_test']['total']['harm'] == int(((h == y) & (g != y) & valid).sum())
    assert abs(data['oracle_test']['classifier_accuracy'] - float((h == y).mean())) < 1e-12
    data['provenance'] = {
        'dataset': ds, 'gate_threshold': tau, 'seed': 42,
        'checkpoint': ckpt, 'gate_arm': winner['name'], 'threshold_policy': mode,
        'base_manifest_sha256': sha256(manifest),
        'validation_provider_counts': dict(Counter(r.get('llm_provider', 'unknown') for r in val_rows)),
        'test_provider_counts': dict(Counter(r.get('llm_provider', 'unknown') for r in test_rows)),
        'expert_score_semantics': 'historical binary 0/1 prediction, not logprob',
        'interpretation': 'exploratory historical analysis; validation provider differs from test',
        'inputs_sha256': {p.name: sha256(p) for p in (val, test, xv, xt)},
        'script_sha256': sha256(ROOT / 'complementarity_fixed.py'),
        'validation_invalid': sum(r['valid'] != '1' for r in val_rows),
        'test_invalid': sum(r['valid'] != '1' for r in test_rows),
    }
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(ds, data['repair_harm_test']['total'], data['oracle_test'], flush=True)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'validation_tuned')
