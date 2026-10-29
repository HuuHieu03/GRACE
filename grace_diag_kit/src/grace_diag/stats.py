"""Thống kê dùng chung cho mọi bảng kết quả.

Mọi hàm ở đây chỉ nhận mảng numpy (nhãn, dự đoán, điểm số) và không đọc file,
để có thể kiểm thử độc lập và dùng lại cho mọi arm.

Quy ước:
- y      : nhãn thật 0/1
- pred   : nhãn dự đoán 0/1 (None/-1 = invalid)
- score  : điểm số liên tục trong [0, 1] (s = p1 / (p0 + p1))
- groups : mã nhóm (commit_id, project) để bootstrap theo cụm; None = từng mẫu độc lập
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import binomtest, chi2, rankdata

PARSER_VERSION = "logprob_binary_v1"


# ---------------------------------------------------------------------------
# Chỉ số có ngưỡng
# ---------------------------------------------------------------------------
def confusion(y: np.ndarray, pred: np.ndarray) -> Dict[str, int]:
    y = np.asarray(y).astype(int)
    pred = np.asarray(pred).astype(int)
    return {
        "TP": int(((y == 1) & (pred == 1)).sum()),
        "FP": int(((y == 0) & (pred == 1)).sum()),
        "TN": int(((y == 0) & (pred == 0)).sum()),
        "FN": int(((y == 1) & (pred == 0)).sum()),
    }


def mcc(y: np.ndarray, pred: np.ndarray) -> Optional[float]:
    """MCC; trả về None khi mẫu số bằng 0 (predictor hằng), không ép về 0."""
    c = confusion(y, pred)
    den = math.sqrt(float((c["TP"] + c["FP"]) * (c["TP"] + c["FN"]) * (c["TN"] + c["FP"]) * (c["TN"] + c["FN"])))
    if den == 0:
        return None
    return (c["TP"] * c["TN"] - c["FP"] * c["FN"]) / den


def mcc_or_nan(y, pred) -> float:
    v = mcc(y, pred)
    return float("nan") if v is None else float(v)


def balanced_accuracy(y, pred) -> float:
    c = confusion(y, pred)
    tpr = c["TP"] / (c["TP"] + c["FN"]) if (c["TP"] + c["FN"]) else 0.0
    tnr = c["TN"] / (c["TN"] + c["FP"]) if (c["TN"] + c["FP"]) else 0.0
    return (tpr + tnr) / 2.0


def f1(y, pred) -> float:
    c = confusion(y, pred)
    den = 2 * c["TP"] + c["FP"] + c["FN"]
    return 2 * c["TP"] / den if den else 0.0


def positive_rate(pred) -> float:
    pred = np.asarray(pred)
    return float((pred == 1).mean()) if len(pred) else 0.0


def thresholded_metrics(y, pred) -> Dict[str, Optional[float]]:
    c = confusion(y, pred)
    prec = c["TP"] / (c["TP"] + c["FP"]) if (c["TP"] + c["FP"]) else None
    rec = c["TP"] / (c["TP"] + c["FN"]) if (c["TP"] + c["FN"]) else None
    return {
        **c,
        "n": int(len(y)),
        "accuracy": (c["TP"] + c["TN"]) / len(y) if len(y) else None,
        "precision": prec,
        "recall": rec,
        "f1": f1(y, pred),
        "mcc": mcc(y, pred),
        "balanced_accuracy": balanced_accuracy(y, pred),
        "positive_rate": positive_rate(pred),
    }


def constant_baselines(y) -> Dict[str, Dict[str, Optional[float]]]:
    """ALL-1, ALL-0 và mốc ngẫu nhiên theo tỷ lệ lớp (kỳ vọng)."""
    y = np.asarray(y).astype(int)
    p = float(y.mean())
    return {
        "ALL-1": {"f1": 2 * p / (1 + p) if p > 0 else 0.0, "accuracy": p, "mcc": None, "balanced_accuracy": 0.5},
        "ALL-0": {"f1": 0.0, "accuracy": 1 - p, "mcc": None, "balanced_accuracy": 0.5},
        "RAND(p)": {"f1": 2 * p * p / (p + p) if p > 0 else 0.0, "accuracy": p * p + (1 - p) ** 2,
                    "mcc": 0.0, "balanced_accuracy": 0.5},
    }


# ---------------------------------------------------------------------------
# Chỉ số không ngưỡng
# ---------------------------------------------------------------------------
def auroc(y, score) -> Optional[float]:
    """AUROC bằng thống kê hạng Mann–Whitney (hòa chia đôi); nhanh hơn sklearn khi bootstrap."""
    y = np.asarray(y).astype(int)
    s = np.asarray(score, dtype=float)
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return None
    r = rankdata(s)
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def auprc(y, score) -> Optional[float]:
    """Average precision theo định nghĩa của sklearn (bậc thang, gộp các điểm số bằng nhau)."""
    y = np.asarray(y).astype(int)
    s = np.asarray(score, dtype=float)
    P = int(y.sum())
    if P == 0 or P == len(y):
        return None
    order = np.argsort(-s, kind="mergesort")
    ys, ss = y[order], s[order]
    distinct = np.flatnonzero(np.diff(ss)) 
    idx = np.r_[distinct, len(ss) - 1]            # vị trí cuối của mỗi nhóm điểm bằng nhau
    tp = np.cumsum(ys)[idx]
    fp = (idx + 1) - tp
    precision = tp / (tp + fp)
    recall = tp / P
    recall_prev = np.r_[0.0, recall[:-1]]
    return float(np.sum((recall - recall_prev) * precision))


def pick_threshold(y_val, s_val, grid: Optional[Sequence[float]] = None) -> Tuple[float, float]:
    """Ngưỡng τ* tối đa hóa MCC trên validation. Trả về (τ*, MCC tại τ*).

    Khi nhiều ngưỡng cho cùng MCC (sai khác < 1e-9) lấy ngưỡng gần 0,5 nhất
    để quy tắc chọn là tất định và được khai báo trước.
    """
    y_val = np.asarray(y_val).astype(int)
    s_val = np.asarray(s_val, dtype=float)
    grid = np.linspace(0.01, 0.99, 99) if grid is None else np.asarray(grid, dtype=float)
    best_t, best_m = 0.5, -2.0
    for t in grid:
        m = mcc(y_val, (s_val >= t).astype(int))
        if m is None:
            continue
        if m > best_m + 1e-9 or (abs(m - best_m) <= 1e-9 and abs(t - 0.5) < abs(best_t - 0.5)):
            best_t, best_m = float(t), float(m)
    if best_m == -2.0:          # không ngưỡng nào cho MCC xác định (điểm số hằng)
        return 0.5, float("nan")
    return best_t, best_m


# ---------------------------------------------------------------------------
# Bootstrap ghép cặp (từng mẫu hoặc theo cụm)
# ---------------------------------------------------------------------------
@dataclass
class PairedCI:
    delta: float
    lo: float
    hi: float
    n_boot: int
    n_degenerate: int
    seed: int
    unit: str

    def to_dict(self):
        return asdict(self)


def _resample_indices(rng: np.random.Generator, n: int, groups: Optional[np.ndarray]) -> np.ndarray:
    if groups is None:
        return rng.integers(0, n, n)
    uniq, inv = np.unique(groups, return_inverse=True)
    members = [np.flatnonzero(inv == g) for g in range(len(uniq))]
    picked = rng.integers(0, len(uniq), len(uniq))
    return np.concatenate([members[g] for g in picked])


def paired_bootstrap(y, a, b, metric: Callable, n_boot: int = 5000, seed: int = 20261117,
                     groups: Optional[Sequence] = None) -> PairedCI:
    """CI 95% của metric(y, b) − metric(y, a) trên cùng danh sách ID.

    - a, b là nhãn 0/1 (cho MCC/BA/F1) hoặc điểm số (cho AUROC/AUPRC).
    - Lượt bootstrap làm metric không xác định (ví dụ MCC với mẫu số 0, AUROC khi
      thiếu một lớp) được đếm vào n_degenerate và loại khỏi percentile; con số
      này phải được báo cáo cùng CI, không âm thầm bỏ.
    - groups: bootstrap theo cụm (commit/project) khi dataset có trường đó.
    """
    y = np.asarray(y)
    a = np.asarray(a)
    b = np.asarray(b)
    groups = None if groups is None else np.asarray(groups)
    rng = np.random.default_rng(seed)
    n = len(y)
    deltas: List[float] = []
    degenerate = 0
    for _ in range(n_boot):
        idx = _resample_indices(rng, n, groups)
        ma, mb = metric(y[idx], a[idx]), metric(y[idx], b[idx])
        if ma is None or mb is None or not np.isfinite(ma) or not np.isfinite(mb):
            degenerate += 1
            continue
        deltas.append(mb - ma)
    full_a, full_b = metric(y, a), metric(y, b)
    delta = float("nan") if (full_a is None or full_b is None) else float(full_b - full_a)
    if not deltas:
        return PairedCI(delta, float("nan"), float("nan"), n_boot, degenerate, seed,
                        "cluster" if groups is not None else "sample")
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return PairedCI(delta, float(lo), float(hi), n_boot, degenerate, seed,
                    "cluster" if groups is not None else "sample")


def mcnemar_test(y, pa, pb) -> Dict[str, float]:
    """McNemar trên hai ô bất đồng: A đúng/B sai (b) và A sai/B đúng (c).

    Kiểm định này so tỷ lệ lỗi, không so MCC/F1: MCC có thể khác rõ mà McNemar
    không có ý nghĩa (và ngược lại). Dùng exact binomial khi b + c < 25.
    """
    y = np.asarray(y)
    pa = np.asarray(pa)
    pb = np.asarray(pb)
    b = int(((pa == y) & (pb != y)).sum())
    c = int(((pa != y) & (pb == y)).sum())
    if b + c == 0:
        return {"b": b, "c": c, "p_value": 1.0, "method": "none"}
    if b + c < 25:
        p = binomtest(min(b, c), b + c, 0.5, alternative="two-sided").pvalue
        return {"b": b, "c": c, "p_value": float(p), "method": "exact"}
    stat = (abs(b - c) - 1) ** 2 / (b + c)
    return {"b": b, "c": c, "p_value": float(chi2.sf(stat, 1)), "method": "chi2_cc"}


def holm(p_values: Dict[str, float]) -> Dict[str, float]:
    """Hiệu chỉnh Holm cho một họ kiểm định; trả về p đã hiệu chỉnh theo tên."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted, running = {}, 0.0
    for rank, (name, p) in enumerate(items):
        running = max(running, (m - rank) * p)
        adjusted[name] = min(1.0, running)
    return adjusted


# ---------------------------------------------------------------------------
# Kết luận từ CI và biên tác dụng δ (tránh lẫn "chưa đủ bằng chứng" với "không có tác dụng")
# ---------------------------------------------------------------------------
VERDICTS = {
    "benefit": "Có bằng chứng lợi ích ≥ δ trong giao thức đã kiểm",
    "no_meaningful_benefit": "Có bằng chứng loại trừ lợi ích ≥ δ (cận trên CI < δ)",
    "harm": "Có bằng chứng bất lợi (CI nằm dưới 0)",
    "inconclusive": "Chưa đủ bằng chứng: CI chứa 0 và vẫn chứa mức ≥ δ",
}


def verdict(ci: PairedCI, margin: float) -> str:
    if not np.isfinite(ci.lo) or not np.isfinite(ci.hi):
        return "inconclusive"
    if ci.lo > 0 and ci.delta >= margin:
        return "benefit"
    if ci.hi < 0:
        return "harm"
    if ci.hi < margin:
        return "no_meaningful_benefit"
    return "inconclusive"


# ---------------------------------------------------------------------------
# Độ nhạy nhãn demo
# ---------------------------------------------------------------------------
def label_sensitivity(y, pred_base, pred_flip, pred_rep, valid_base=None, valid_flip=None, valid_rep=None) -> Dict[str, float]:
    """flip = tỷ lệ đổi dự đoán khi đảo nhãn demo; natural = tỷ lệ đổi giữa hai lần chạy
    cùng prompt; net = flip − natural. Chỉ tính trên các mẫu hợp lệ ở cả hai arm.
    Báo thêm đổi đúng→sai và sai→đúng để thấy chiều của tác động."""
    y = np.asarray(y)
    pb, pf, pr = (np.asarray(v) for v in (pred_base, pred_flip, pred_rep))
    ok = np.ones(len(y), dtype=bool)
    for v in (valid_base, valid_flip, valid_rep):
        if v is not None:
            ok &= np.asarray(v).astype(bool)
    y, pb, pf, pr = y[ok], pb[ok], pf[ok], pr[ok]
    changed = pb != pf
    return {
        "n": int(len(y)),
        "flip": float(changed.mean()) if len(y) else float("nan"),
        "natural": float((pb != pr).mean()) if len(y) else float("nan"),
        "net": float(changed.mean() - (pb != pr).mean()) if len(y) else float("nan"),
        "flip_correct_to_wrong": float(((pb == y) & changed).mean()) if len(y) else float("nan"),
        "flip_wrong_to_correct": float(((pb != y) & changed).mean()) if len(y) else float("nan"),
    }


def mask_valid(*preds) -> np.ndarray:
    """Mặt nạ các mẫu hợp lệ ở mọi arm được so (None hoặc -1 là invalid)."""
    ok = None
    for p in preds:
        arr = np.asarray([(-1 if v is None else v) for v in p])
        m = arr >= 0
        ok = m if ok is None else (ok & m)
    return ok
