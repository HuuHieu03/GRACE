"""Mốc có giám sát rẻ: SUP-LR, SUP-MLP trên embedding CodeT5 đóng băng và SUP-METRIC
chỉ trên 26 đặc trưng số của mã nguồn (đúng danh sách numeric view của H3-B, để kết quả
đối chiếu được với bài code-metrics của Weissberg et al., ICSE 2026).

Quy tắc: huấn luyện trên train, chọn ngưỡng τ* trên validation theo MCC, xuất điểm số cho
validation và test; 3 seed; không bao giờ nhìn nhãn test.

Đầu vào:
  --emb-{train,val,test}  npz có 'ids' (str) và 'X' (n×768) — embedding CodeT5 masked-mean
  --code-{train,val,test} JSONL có id, func, target (target chỉ dùng cho train/validation)
Đầu ra: CSV id,dataset,split,arm,seed,score; JSON tau và metrics theo arm/seed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import stats as S

TOKEN_RE = re.compile(r'0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?|[A-Za-z_]\w*|->|::|<<|>>|<=|>=|==|!=|&&|\|\||\+\+|--|[^\s]')
KEYWORDS = ('if', 'else', 'for', 'while', 'switch', 'case', 'return', 'goto', 'break', 'sizeof')


def numeric_features(codes: Sequence[str]) -> np.ndarray:
    """26 đặc trưng số: log(byte), log(dòng), log(token), 10 từ khóa, null, *, ->, [, so sánh,
    logic, số học, cấp phát, giải phóng, copy, input, error, assert — như features.py của H3-B."""
    rows = []
    for code in codes:
        t = TOKEN_RE.findall(code)
        lower = [w.lower() for w in t]
        count = lambda values: sum(w in values for w in lower)
        a = [np.log1p(len(code.encode("utf-8"))), np.log1p(len(code.splitlines())), np.log1p(len(t))]
        a += [lower.count(w) for w in KEYWORDS]
        a += [count({'null', 'nullptr'}), lower.count('*'), lower.count('->'), lower.count('['),
              count({'<', '>', '<=', '>=', '==', '!='}), count({'&&', '||', '!'}), count({'+', '-', '*', '/', '%'}),
              count({'malloc', 'calloc', 'realloc', 'alloca', 'new'}), count({'free', 'delete'}),
              count({'memcpy', 'memmove', 'strcpy', 'strncpy'}), count({'read', 'recv', 'scanf', 'gets'}),
              count({'errno', 'error', 'fail'}), lower.count('assert')]
        rows.append(a)
    return np.asarray(rows, dtype=np.float32)


def make_model(arm: str, seed: int):
    if arm == "SUP-LR" or arm == "SUP-METRIC":
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, random_state=seed))
    if arm == "SUP-MLP":
        return make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(128,), alpha=1e-3, batch_size=128,
                                                             learning_rate_init=1e-3, max_iter=200, early_stopping=True,
                                                             validation_fraction=0.1, n_iter_no_change=10, random_state=seed))
    raise ValueError(arm)


def run_anchor(X_tr, y_tr, X_val, y_val, X_te, arm: str, seeds: Sequence[int] = (42, 43, 44)) -> List[Dict]:
    out = []
    for seed in seeds:
        model = make_model(arm, seed).fit(X_tr, y_tr)
        s_val, s_te = model.predict_proba(X_val)[:, 1], model.predict_proba(X_te)[:, 1]
        tau, mcc_val = S.pick_threshold(y_val, s_val)
        out.append({"arm": arm, "seed": seed, "tau": tau, "mcc_val_at_tau": mcc_val,
                    "auroc_val": S.auroc(y_val, s_val), "score_val": s_val, "score_test": s_te})
    return out


def _load_npz(path):
    d = np.load(path, allow_pickle=False)
    return [str(i) for i in d["ids"]], np.asarray(d["X"], dtype=np.float32)


def _load_jsonl(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    return rows


def _main():
    import argparse, csv
    ap = argparse.ArgumentParser(description=__doc__)
    for split in ("train", "val", "test"):
        ap.add_argument(f"--emb-{split}")
        ap.add_argument(f"--code-{split}", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dataset", required=True, help="tên dataset ghi vào CSV (devign/reveal)")
    ap.add_argument("--seeds", default="42,43,44")
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",")]
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)

    code = {s: _load_jsonl(getattr(a, f"code_{s}")) for s in ("train", "val", "test")}
    y = {s: np.array([int(r["target"]) for r in code[s]]) for s in ("train", "val")}
    ids = {s: [str(r["id"]) for r in code[s]] for s in ("train", "val", "test")}
    Xnum = {s: numeric_features([r["func"] for r in code[s]]) for s in ("train", "val", "test")}

    arms = {"SUP-METRIC": Xnum}
    if a.emb_train and a.emb_val and a.emb_test:
        emb = {}
        for s in ("train", "val", "test"):
            eids, X = _load_npz(getattr(a, f"emb_{s}"))
            pos = {i: k for k, i in enumerate(eids)}
            missing = [i for i in ids[s] if i not in pos]
            if missing:
                raise ValueError(f"{len(missing)} id của {s} không có embedding (ví dụ {missing[:3]})")
            emb[s] = X[[pos[i] for i in ids[s]]]
        arms["SUP-LR"] = emb
        arms["SUP-MLP"] = emb

    summary = []
    with open(out_dir / "anchor_scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id", "dataset", "split", "arm", "seed", "score"])
        for arm, X in arms.items():
            for r in run_anchor(X["train"], y["train"], X["val"], y["val"], X["test"], arm, seeds):
                summary.append({k: v for k, v in r.items() if not k.startswith("score_")})
                for i, s in zip(ids["val"], r["score_val"]):
                    w.writerow([i, a.dataset, "validation", arm, r["seed"], f"{s:.6f}"])
                for i, s in zip(ids["test"], r["score_test"]):
                    w.writerow([i, a.dataset, "test", arm, r["seed"], f"{s:.6f}"])
    json.dump(summary, open(out_dir / "anchor_summary.json", "w", encoding="utf-8"), indent=2, default=float)
    print("wrote", out_dir)


if __name__ == "__main__":
    _main()
