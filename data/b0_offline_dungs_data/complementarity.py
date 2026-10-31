"""Giá trị bổ sung của nhánh LLM so với bộ phân loại nhẹ (RQ5b).

Ba mức, tính hoàn toàn offline từ dự đoán đã có:
1. Bổ sung "có sẵn": phân rã sửa/hỏng theo lớp (R_y, H_y) và trần oracle — luôn đặt cạnh
   đối chứng expert hằng (ALL-0/ALL-1) và expert ngẫu nhiên cùng tỷ lệ đoán 1, vì một expert
   gần ngẫu nhiên cũng "sửa" được rất nhiều lỗi của bộ phân loại.
2. Bổ sung khai thác được SAU truy vấn: cặp meta-model ghép đôi P_pre (34 đặc trưng nền)
   và P_post (34 + 4 đặc trưng expert), cùng fold, cùng scaler, cùng lưới ngưỡng, cùng OOF.
3. Bổ sung khai thác được TRƯỚC truy vấn: đường chất lượng theo ngân sách gọi LLM với các
   policy random (20 seed), confidence (|logit p − logit τ|), benefit-router (Ridge), oracle.

Đầu vào tối thiểu (CSV): id, y, p_gate, s_llm, valid[, group]; tùy chọn X_pre (npz) là ma
trận đặc trưng nền 34 cột của H3-B. Nếu không có X_pre, P_pre dùng [logit p_gate] và các
đặc trưng số của mã nguồn (numeric view) nếu có cột code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.special import logit as _logit
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import stats as S


def logit(p: np.ndarray) -> np.ndarray:
    return _logit(np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6))


# ---------------------------------------------------------------------------
# 1. Sửa / hỏng theo lớp và trần oracle
# ---------------------------------------------------------------------------
def repair_harm(y, h, g, valid=None) -> Dict[str, Dict[str, int]]:
    """R_y: classifier sai, expert đúng; H_y: classifier đúng, expert sai; theo nhãn thật y."""
    y, h, g = (np.asarray(v).astype(int) for v in (y, h, g))
    ok = np.ones(len(y), dtype=bool) if valid is None else np.asarray(valid).astype(bool)
    out = {}
    for cls in (0, 1):
        m = (y == cls) & ok
        out[f"y={cls}"] = {
            "n": int(m.sum()),
            "repair": int((m & (h != y) & (g == y)).sum()),
            "harm": int((m & (h == y) & (g != y)).sum()),
            "both_right": int((m & (h == y) & (g == y)).sum()),
            "both_wrong": int((m & (h != y) & (g != y)).sum()),
        }
    out["total"] = {k: sum(out[f"y={c}"][k] for c in (0, 1)) for k in ("n", "repair", "harm", "both_right", "both_wrong")}
    out["total"]["invalid_expert"] = int((~ok).sum())
    return out


def oracle_ceiling(y, h, g, valid=None) -> Dict[str, float]:
    """Accuracy nếu biết nhãn thật để chọn bên đúng. Chỉ là trần chẩn đoán, không triển khai được."""
    y, h, g = (np.asarray(v).astype(int) for v in (y, h, g))
    ok = np.ones(len(y), dtype=bool) if valid is None else np.asarray(valid).astype(bool)
    either = (h == y) | ((g == y) & ok)
    return {"oracle_accuracy": float(either.mean()), "classifier_accuracy": float((h == y).mean()),
            "expert_accuracy_valid": float((g[ok] == y[ok]).mean()) if ok.any() else float("nan")}


def reference_experts(y, h, positive_rate: float, n_random: int = 20, seed: int = 42) -> Dict[str, Dict]:
    """Đối chứng cho bảng sửa/hỏng: expert hằng và expert ngẫu nhiên cùng tỷ lệ đoán 1.

    Lý do: số ca "expert sửa lỗi classifier" chỉ có nghĩa khi lớn hơn rõ rệt số ca mà một
    expert không mang thông tin (tung đồng xu với cùng tỷ lệ đoán 1) cũng sửa được."""
    y, h = np.asarray(y).astype(int), np.asarray(h).astype(int)
    rng = np.random.default_rng(seed)
    out: Dict[str, Dict] = {}
    for name, g in (("ALL-0", np.zeros_like(y)), ("ALL-1", np.ones_like(y))):
        rh = repair_harm(y, h, g)
        out[name] = {"repair": rh["total"]["repair"], "harm": rh["total"]["harm"], **oracle_ceiling(y, h, g)}
    reps, harms, oracles = [], [], []
    for _ in range(n_random):
        g = (rng.random(len(y)) < positive_rate).astype(int)
        rh = repair_harm(y, h, g)
        reps.append(rh["total"]["repair"]); harms.append(rh["total"]["harm"]); oracles.append(oracle_ceiling(y, h, g)["oracle_accuracy"])
    out[f"RANDOM(rate={positive_rate:.3f})"] = {
        "repair_mean": float(np.mean(reps)), "repair_lo": float(np.percentile(reps, 2.5)), "repair_hi": float(np.percentile(reps, 97.5)),
        "harm_mean": float(np.mean(harms)), "harm_lo": float(np.percentile(harms, 2.5)), "harm_hi": float(np.percentile(harms, 97.5)),
        "oracle_accuracy_mean": float(np.mean(oracles)), "n_random": n_random}
    return out


# ---------------------------------------------------------------------------
# 2. Cặp meta-model P_pre / P_post
# ---------------------------------------------------------------------------
def expert_features(s: np.ndarray, valid: np.ndarray, p_gate: np.ndarray) -> np.ndarray:
    """Đúng bốn đặc trưng expert như H3-B: giá trị, cờ hợp lệ, giá trị×p, giá trị−p.
    Expert invalid được gán 0,5 và cờ 0 (quy ước phải ghi trong giao thức)."""
    v = np.where(np.asarray(valid).astype(bool), np.asarray(s, dtype=float), 0.5)
    return np.column_stack([v, np.asarray(valid).astype(float), v * p_gate, v - p_gate])


@dataclass
class PrePostResult:
    oof_pre: np.ndarray
    oof_post: np.ndarray
    tau_pre: float
    tau_post: float
    metrics_pre: Dict
    metrics_post: Dict
    delta_mcc: S.PairedCI
    delta_auroc: S.PairedCI
    verdict_mcc: str
    n_folds: int
    seed: int


def fit_pre_post(X_pre: np.ndarray, s: np.ndarray, valid: np.ndarray, p_gate: np.ndarray, y: np.ndarray,
                 n_folds: int = 3, seed: int = 42, C: float = 1.0, margin_mcc: float = 0.02,
                 n_boot: int = 5000, groups=None) -> PrePostResult:
    """Fit hai meta-LR giống hệt nhau trừ bốn cột expert; dự đoán OOF trên validation;
    chọn ngưỡng từ OOF; so ΔMCC/ΔAUROC ghép cặp. Nhãn test không bao giờ vào đây —
    hàm này chạy trên validation (meta-fit) và được áp lại trên test bằng `apply_pre_post`.

    Khi expert invalid, P_post dùng đúng dự đoán của P_pre ở mẫu đó (fallback đối xứng)."""
    y = np.asarray(y).astype(int)
    X_pre = np.asarray(X_pre, dtype=float)
    X_post = np.column_stack([X_pre, expert_features(s, valid, p_gate)])
    oof_pre, oof_post = np.zeros(len(y)), np.zeros(len(y))
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    for tr, te in skf.split(X_pre, y):
        m_pre = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000, random_state=seed)).fit(X_pre[tr], y[tr])
        m_post = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000, random_state=seed)).fit(X_post[tr], y[tr])
        oof_pre[te] = m_pre.predict_proba(X_pre[te])[:, 1]
        oof_post[te] = m_post.predict_proba(X_post[te])[:, 1]
    inval = ~np.asarray(valid).astype(bool)
    oof_post[inval] = oof_pre[inval]                      # fallback đối xứng
    tau_pre, _ = S.pick_threshold(y, oof_pre)
    tau_post, _ = S.pick_threshold(y, oof_post)
    pred_pre, pred_post = (oof_pre >= tau_pre).astype(int), (oof_post >= tau_post).astype(int)
    d_mcc = S.paired_bootstrap(y, pred_pre, pred_post, S.mcc, n_boot=n_boot, seed=seed, groups=groups)
    d_auc = S.paired_bootstrap(y, oof_pre, oof_post, S.auroc, n_boot=n_boot, seed=seed, groups=groups)
    return PrePostResult(oof_pre, oof_post, tau_pre, tau_post,
                         {**S.thresholded_metrics(y, pred_pre), "auroc": S.auroc(y, oof_pre)},
                         {**S.thresholded_metrics(y, pred_post), "auroc": S.auroc(y, oof_post)},
                         d_mcc, d_auc, S.verdict(d_mcc, margin_mcc), n_folds, seed)


def apply_pre_post(X_pre_val, s_val, valid_val, p_val, y_val, X_pre_test, s_test, valid_test, p_test,
                   seed: int = 42, C: float = 1.0):
    """Refit trên toàn bộ validation rồi áp sang test với ngưỡng đã chọn trên validation."""
    pp = fit_pre_post(X_pre_val, s_val, valid_val, p_val, y_val, seed=seed, C=C, n_boot=200)
    X_post_val = np.column_stack([X_pre_val, expert_features(s_val, valid_val, p_val)])
    X_post_test = np.column_stack([X_pre_test, expert_features(s_test, valid_test, p_test)])
    m_pre = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000, random_state=seed)).fit(X_pre_val, y_val)
    m_post = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000, random_state=seed)).fit(X_post_val, y_val)
    sp, spost = m_pre.predict_proba(X_pre_test)[:, 1], m_post.predict_proba(X_post_test)[:, 1]
    inval = ~np.asarray(valid_test).astype(bool)
    spost[inval] = sp[inval]
    return {"score_pre": sp, "score_post": spost, "tau_pre": pp.tau_pre, "tau_post": pp.tau_post,
            "pred_pre": (sp >= pp.tau_pre).astype(int), "pred_post": (spost >= pp.tau_post).astype(int)}


# ---------------------------------------------------------------------------
# 3. Routing theo ngân sách (batch routing: chọn trước top ceil(qN) theo điểm pre-expert)
# ---------------------------------------------------------------------------
def route(h: np.ndarray, g: np.ndarray, valid: np.ndarray, rank_score: np.ndarray, q: float, ids: Sequence) -> Tuple[np.ndarray, np.ndarray]:
    """Gọi expert cho ceil(qN) mẫu có rank_score cao nhất (phá hòa bằng hash id cố định);
    mẫu được gọi nhưng expert invalid giữ nhãn classifier."""
    n = len(h)
    k = int(np.ceil(q * n))
    tie = np.asarray([int(__import__("hashlib").sha256(str(i).encode()).hexdigest()[:8], 16) for i in ids])
    order = np.lexsort((tie, -np.asarray(rank_score, dtype=float)))
    mask = np.zeros(n, dtype=bool)
    mask[order[:k]] = True
    final = np.where(mask & np.asarray(valid).astype(bool), g, h).astype(int)
    return final, mask


def fit_benefit_router(X_pre_val, y_val, h_val, g_val, valid_val, alpha: float = 10.0):
    """Ridge trên validation với target +1 (expert sửa), −1 (expert làm hỏng), 0 (như nhau).
    Chỉ dùng đặc trưng có trước khi gọi expert."""
    ok = np.asarray(valid_val).astype(bool)
    target = ((h_val != y_val) & (g_val == y_val)).astype(float) - ((h_val == y_val) & (g_val != y_val)).astype(float)
    model = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(np.asarray(X_pre_val)[ok], target[ok])
    return model


def routing_curves(y, h, g, valid, p_gate, tau, ids, budgets=(0.05, 0.10, 0.25), benefit_scores=None,
                   n_random: int = 20, seed: int = 42) -> List[Dict]:
    """Bảng MCC/BA/F1 theo ngân sách q cho các policy: random (phân bố qua n_random seed),
    confidence (gần biên τ gọi trước), benefit (điểm từ fit_benefit_router), oracle (chỉ gọi ca sửa đúng)."""
    y, h, g = (np.asarray(v).astype(int) for v in (y, h, g))
    valid = np.asarray(valid).astype(bool)
    rows: List[Dict] = []
    conf = -np.abs(logit(p_gate) - logit(np.full(len(y), tau)))   # càng gần biên càng ưu tiên
    oracle_score = ((h != y) & (g == y) & valid).astype(float)
    rng = np.random.default_rng(seed)
    base = S.thresholded_metrics(y, h)
    rows.append({"policy": "gate_only", "q": 0.0, **{k: base[k] for k in ("mcc", "balanced_accuracy", "f1")}, "queries": 0})
    full = np.where(valid, g, h)
    fm = S.thresholded_metrics(y, full)
    rows.append({"policy": "full_expert_with_fallback", "q": 1.0, **{k: fm[k] for k in ("mcc", "balanced_accuracy", "f1")}, "queries": int(len(y))})
    for q in budgets:
        for name, score in (("confidence", conf), ("benefit", benefit_scores), ("oracle", oracle_score)):
            if score is None:
                continue
            final, mask = route(h, g, valid, score, q, ids)
            if name == "oracle":   # oracle không gọi ca gây hại cho đủ quota
                final = np.where(mask & (oracle_score > 0), g, h)
            m = S.thresholded_metrics(y, final)
            rh = repair_harm(y, h, final)["total"]
            rows.append({"policy": name, "q": q, **{k: m[k] for k in ("mcc", "balanced_accuracy", "f1")},
                         "queries": int(mask.sum()), "repair": rh["repair"], "harm": rh["harm"]})
        vals = {"mcc": [], "balanced_accuracy": [], "f1": []}
        for _ in range(n_random):
            final, mask = route(h, g, valid, rng.random(len(y)), q, ids)
            m = S.thresholded_metrics(y, final)
            for k in vals:
                vals[k].append(float("nan") if m[k] is None else m[k])
        rows.append({"policy": "random", "q": q, "queries": int(np.ceil(q * len(y))),
                     **{k: float(np.nanmean(v)) for k, v in vals.items()},
                     **{k + "_lo": float(np.nanpercentile(v, 2.5)) for k, v in vals.items()},
                     **{k + "_hi": float(np.nanpercentile(v, 97.5)) for k, v in vals.items()}})
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _main():
    import argparse, csv, json
    ap = argparse.ArgumentParser(description="Phân tích giá trị bổ sung LLM vs bộ phân loại nhẹ (offline)")
    ap.add_argument("--val", required=True, help="CSV validation: id,y,p_gate,s_llm,valid[,group]")
    ap.add_argument("--test", required=True, help="CSV test: cùng cột")
    ap.add_argument("--xpre-val", help="npz với mảng X (n_val×34)")
    ap.add_argument("--xpre-test", help="npz với mảng X (n_test×34)")
    ap.add_argument("--tau", type=float, required=True, help="ngưỡng chung của gate (chọn trên validation)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    def read(path):
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        ids = [r["id"] for r in rows]
        y = np.array([int(r["y"]) for r in rows]); p = np.array([float(r["p_gate"]) for r in rows])
        s = np.array([float(r["s_llm"]) if r["s_llm"] not in ("", "nan") else 0.5 for r in rows])
        v = np.array([r["valid"].lower() in ("1", "true") for r in rows])
        grp = [r.get("group") for r in rows] if rows and "group" in rows[0] else None
        return ids, y, p, s, v, grp

    ids_v, y_v, p_v, s_v, v_v, g_v = read(a.val)
    ids_t, y_t, p_t, s_t, v_t, g_t = read(a.test)
    Xv = np.load(a.xpre_val)["X"] if a.xpre_val else logit(p_v)[:, None]
    Xt = np.load(a.xpre_test)["X"] if a.xpre_test else logit(p_t)[:, None]
    h_v, h_t = (p_v >= a.tau).astype(int), (p_t >= a.tau).astype(int)
    g_v, g_t = (s_v >= 0.5).astype(int), (s_t >= 0.5).astype(int)

    out = {"repair_harm_test": repair_harm(y_t, h_t, g_t, v_t), "oracle_test": oracle_ceiling(y_t, h_t, g_t, v_t),
           "reference_experts_test": reference_experts(y_t, h_t, float(g_t[v_t].mean()), seed=a.seed)}
    pp = fit_pre_post(Xv, s_v, v_v, p_v, y_v, seed=a.seed, groups=g_v)
    out["pre_post_validation_oof"] = {"tau_pre": pp.tau_pre, "tau_post": pp.tau_post, "metrics_pre": pp.metrics_pre,
                                      "metrics_post": pp.metrics_post, "delta_mcc": pp.delta_mcc.to_dict(),
                                      "delta_auroc": pp.delta_auroc.to_dict(), "verdict_mcc": pp.verdict_mcc}
    applied = apply_pre_post(Xv, s_v, v_v, p_v, y_v, Xt, s_t, v_t, p_t, seed=a.seed)
    d = S.paired_bootstrap(y_t, applied["pred_pre"], applied["pred_post"], S.mcc, seed=a.seed, groups=g_t)
    out["pre_post_test"] = {"metrics_pre": S.thresholded_metrics(y_t, applied["pred_pre"]),
                            "metrics_post": S.thresholded_metrics(y_t, applied["pred_post"]),
                            "delta_mcc": d.to_dict(), "verdict_mcc": S.verdict(d, 0.02)}
    router = fit_benefit_router(Xv, y_v, h_v, g_v, v_v)
    out["routing_test"] = routing_curves(y_t, h_t, g_t, v_t, p_t, a.tau, ids_t, benefit_scores=router.predict(Xt), seed=a.seed)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=float)
    print("wrote", a.out)


if __name__ == "__main__":
    _main()
