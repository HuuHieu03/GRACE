"""Đóng băng dữ liệu: chuẩn hóa mã, băm SHA-256, gắn cờ trùng chính xác và gần trùng,
xuất manifest JSONL cho từng split và kho donor (train đã khử trùng với validation/test).

  python scripts/build_manifests.py --train data/raw/devign_train.jsonl \
      --validation data/raw/devign_validation.jsonl --test data/raw/devign_test.jsonl \
      --dataset devign --out data/manifests

Mỗi dòng đầu vào: {id, func, target[, nodes, edges, commit_id, project]}.
Chuẩn hóa để băm: bỏ chú thích /* */ và //, gộp khoảng trắng, bỏ dòng trống (chỉ dùng để
nhận diện trùng; prompt vẫn dùng mã gốc). Gần trùng: Jaccard token-3-gram >= 0,9 so với
validation/test, tính bằng MinHash đơn giản (chỉ gắn cờ, không loại).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from grace_diag.supervised_anchor import TOKEN_RE  # noqa: E402

COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def normalize(code: str) -> str:
    code = COMMENT_RE.sub(" ", code)
    return re.sub(r"\s+", " ", code).strip()


def sha(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def shingles(code: str, k: int = 3):
    t = TOKEN_RE.findall(code)
    return {" ".join(t[i:i + k]) for i in range(max(0, len(t) - k + 1))}


class MinHash:
    def __init__(self, n_perm: int = 64, seed: int = 42):
        rng = np.random.default_rng(seed)
        self.a = rng.integers(1, 2 ** 61 - 1, n_perm, dtype=np.int64)
        self.b = rng.integers(0, 2 ** 61 - 1, n_perm, dtype=np.int64)
        self.p = 2 ** 61 - 1

    def sig(self, items):
        if not items:
            return np.zeros(len(self.a), dtype=np.int64)
        h = np.array([int(hashlib.md5(x.encode()).hexdigest()[:15], 16) for x in items], dtype=np.int64)
        return ((np.outer(h, self.a) + self.b) % self.p).min(axis=0)


def read(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", required=True, type=Path)
    ap.add_argument("--validation", required=True, type=Path)
    ap.add_argument("--test", required=True, type=Path)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--near-threshold", type=float, default=0.9)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    splits = {"train": read(a.train), "validation": read(a.validation), "test": read(a.test)}
    for name, rows in splits.items():
        for r in rows:
            r["norm_sha256"] = sha(normalize(r["func"]))
            r["code_sha256"] = sha(r["func"].replace("\r\n", "\n").strip())
    eval_hashes = {r["norm_sha256"] for s in ("validation", "test") for r in splits[s]}
    train_hashes = Counter(r["norm_sha256"] for r in splits["train"])
    mh = MinHash()
    eval_sigs = [(r["norm_sha256"], mh.sig(shingles(normalize(r["func"])))) for s in ("validation", "test") for r in splits[s]]
    # LSH thô: nhóm theo 8 băng × 8 hàng
    bands = defaultdict(set)
    for i, (_, sg) in enumerate(eval_sigs):
        for b in range(8):
            bands[(b, tuple(sg[b * 8:(b + 1) * 8]))].add(i)
    stats = {"dataset": a.dataset, "near_threshold": a.near_threshold, "per_split": {}}
    labels_by_hash = defaultdict(set)
    for r in splits["train"]:
        labels_by_hash[r["norm_sha256"]].add(int(r["target"]))
    for name, rows in splits.items():
        n_exact, n_near, n_conflict = 0, 0, 0
        seen_repr = set()
        with open(a.out / f"{a.dataset}_{name}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                flags = {}
                if name == "train":
                    flags["overlaps_eval_exact"] = r["norm_sha256"] in eval_hashes
                    sg = mh.sig(shingles(normalize(r["func"])))
                    cand = set()
                    for b in range(8):
                        cand |= bands.get((b, tuple(sg[b * 8:(b + 1) * 8])), set())
                    near = any((sg == eval_sigs[i][1]).mean() >= a.near_threshold for i in cand)
                    flags["near_eval"] = bool(near)
                    flags["label_conflict_in_train"] = len(labels_by_hash[r["norm_sha256"]]) > 1
                    flags["duplicate_in_train"] = train_hashes[r["norm_sha256"]] > 1
                    flags["keep_in_bank"] = not (flags["overlaps_eval_exact"] or flags["label_conflict_in_train"]
                                                 or (flags["duplicate_in_train"] and r["norm_sha256"] in seen_repr))
                    seen_repr.add(r["norm_sha256"])
                    n_exact += flags["overlaps_eval_exact"]; n_near += flags["near_eval"]; n_conflict += flags["label_conflict_in_train"]
                else:
                    flags["dup_of_train_exact"] = r["norm_sha256"] in train_hashes
                    n_exact += flags["dup_of_train_exact"]
                out = {"id": str(r["id"]), "dataset": a.dataset, "split": name, "code_sha256": r["code_sha256"],
                       "norm_sha256": r["norm_sha256"], "label": int(r["target"]), "n_nodes": len(r.get("nodes") or []),
                       "group": r.get("commit_id") or r.get("project"), **flags}
                f.write(json.dumps(out, ensure_ascii=False) + "\n")
        pos = sum(int(r["target"]) for r in rows)
        stats["per_split"][name] = {"n": len(rows), "n_pos": pos, "pos_rate": pos / max(1, len(rows)),
                                    "exact_overlap_flags": n_exact, "near_flags": n_near, "label_conflicts": n_conflict}
    # kho donor: train giữ lại trong bank, kèm graph để B1-shuf
    with open(a.out / f"{a.dataset}_donors.jsonl", "w", encoding="utf-8") as f:
        for r in splits["train"]:
            if r["norm_sha256"] in eval_hashes or len(labels_by_hash[r["norm_sha256"]]) > 1:
                continue
            f.write(json.dumps({"function_uid": str(r["id"]), "func": r["func"], "target": int(r["target"]),
                                "nodes": r.get("nodes") or [], "edges": r.get("edges") or []}, ensure_ascii=False) + "\n")
    manifest_hash = hashlib.sha256(b"".join((a.out / f"{a.dataset}_{s}.jsonl").read_bytes() for s in splits)).hexdigest()
    stats["manifest_sha256"] = manifest_hash
    (a.out / f"{a.dataset}_manifest_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
