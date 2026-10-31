#!/usr/bin/env python3
"""Export H3-B pre-feature arrays from an exact local H3-B experiment snapshot.

Run from GRACE-H3-BenchmarkEnsemble with its pinned Python environment:
  python export_xpre_test.py --dataset devign --manifest artifacts/h3v2/base/devign/42/<id>/manifest.json --output xpre_test_devign.npz

The generated values are valid only for the manifest, source tree, model files,
embeddings, and data identified by that experiment. Do not pair with predictions
from a different run without verifying IDs, code hashes, and score equality.
"""
import argparse
from pathlib import Path
import numpy as np
from grace_h1.io import read_json
from grace_h3v2.base import arm_scores, score_queries
from grace_h3v2.meta import pre_features


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', required=True, choices=['devign', 'reveal'])
    ap.add_argument('--manifest', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--split', default='test')
    args = ap.parse_args()
    root = Path.cwd().resolve()
    manifest_path = args.manifest.resolve()
    manifest = read_json(manifest_path)
    if not manifest_path.is_relative_to(root):
        ap.error('manifest must be inside the repository root')
    base = manifest
    rows, scores = score_queries(root, base, args.dataset, args.split)
    if base.get('dataset') not in (None, args.dataset):
        raise ValueError('manifest dataset does not match --dataset')
    probabilities = arm_scores(root, base, scores)
    winner = base['winner']['name']
    if winner not in probabilities:
        raise ValueError(f"winner {winner!r} is not present in generated score arms")
    probability = np.asarray(probabilities[winner], dtype=np.float64)
    X = np.asarray(pre_features(rows, scores, probability), dtype=np.float32)
    ids = np.asarray([r['record_id'] for r in rows], dtype=str)
    hashes = np.asarray([r['code_sha256'] for r in rows], dtype=str)
    if len(ids) != len(set(ids)) or len(ids) != len(hashes) or X.shape != (len(ids), 34):
        raise ValueError('row identity/feature shape validation failed')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, ids=ids, code_sha256=hashes, X=X,
                        winner=np.asarray(winner), manifest_path=np.asarray(manifest_path.as_posix()),
                        feature_names=np.asarray([f'f{i:02d}' for i in range(X.shape[1])]))
    print(f'Wrote {args.output}: rows={len(ids)}, features={X.shape[1]}, winner={winner}')


if __name__ == '__main__':
    main()
