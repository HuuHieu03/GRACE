import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from grace_diag import stats as S  # noqa: E402
from grace_diag import complementarity as C  # noqa: E402
from grace_diag.llm_backend import parse_top_logprobs, FirstTokenScorer  # noqa: E402


def synth(n=600, seed=0, signal=1.2, llm_signal=0.0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.4).astype(int)
    X = rng.normal(size=(n, 5)) + signal * y[:, None] * np.array([1, 0.5, 0, 0, 0])
    p_gate = 1 / (1 + np.exp(-(X[:, 0] + 0.5 * X[:, 1] - 0.6)))
    s_llm = 1 / (1 + np.exp(-(llm_signal * (2 * y - 1) + rng.normal(size=n))))
    valid = rng.random(n) > 0.01
    return y, X, p_gate, s_llm, valid


def test_mcc_none_for_constant():
    y = np.array([0, 1, 1, 0]); assert S.mcc(y, np.zeros(4, dtype=int)) is None
    assert S.mcc(y, y) == 1.0


def test_pick_threshold_deterministic():
    y, X, p, s, v = synth()
    t1, m1 = S.pick_threshold(y, p); t2, m2 = S.pick_threshold(y, p)
    assert t1 == t2 and 0.01 <= t1 <= 0.99 and m1 > 0.2


def test_paired_bootstrap_and_verdict():
    y, X, p, s, v = synth()
    strong = (p >= 0.5).astype(int); weak = (s >= 0.5).astype(int)
    ci = S.paired_bootstrap(y, weak, strong, S.mcc, n_boot=300, seed=1)
    assert ci.lo > 0 and S.verdict(ci, 0.03) == "benefit"
    ci2 = S.paired_bootstrap(y, strong, strong, S.mcc, n_boot=300, seed=1)
    assert ci2.lo == 0 == ci2.hi and S.verdict(ci2, 0.03) == "no_meaningful_benefit"
    groups = np.arange(len(y)) // 10
    ci3 = S.paired_bootstrap(y, weak, strong, S.mcc, n_boot=100, seed=1, groups=groups)
    assert ci3.unit == "cluster"


def test_mcnemar_and_holm():
    y = np.array([1] * 50 + [0] * 50); a = y.copy(); b = y.copy(); b[:10] = 0
    r = S.mcnemar_test(y, a, b); assert r["b"] == 10 and r["c"] == 0 and r["p_value"] < 0.01 and r["method"] == "exact"
    adj = S.holm({"x": 0.01, "y": 0.04, "z": 0.2}); assert adj["x"] == pytest.approx(0.03) and adj["z"] == pytest.approx(0.2)


def test_label_sensitivity():
    y = np.array([0, 1, 1, 0, 1]); b = np.array([0, 1, 0, 0, 1]); f = np.array([1, 0, 0, 0, 1]); r = b.copy()
    out = S.label_sensitivity(y, b, f, r)
    assert out["flip"] == pytest.approx(0.4) and out["natural"] == 0 and out["net"] == pytest.approx(0.4)


def test_repair_harm_reference_and_oracle():
    y, X, p, s, v = synth(llm_signal=0.0)
    h = (p >= 0.5).astype(int); g = (s >= 0.5).astype(int)
    rh = C.repair_harm(y, h, g, v); tot = rh["total"]
    assert tot["repair"] + tot["harm"] + tot["both_right"] + tot["both_wrong"] + tot["invalid_expert"] == len(y)
    ref = C.reference_experts(y, h, float(g.mean()), n_random=5)
    assert "ALL-0" in ref and ref["ALL-0"]["repair"] == int(((y == 0) & (h == 1)).sum())
    oc = C.oracle_ceiling(y, h, g, v); assert oc["oracle_accuracy"] >= oc["classifier_accuracy"]


def test_pre_post_no_signal_is_not_benefit():
    y, X, p, s, v = synth(llm_signal=0.0)
    res = C.fit_pre_post(X, s, v, p, y, n_boot=200, seed=3)
    assert res.verdict_mcc in ("inconclusive", "no_meaningful_benefit", "harm")
    y2, X2, p2, s2, v2 = synth(llm_signal=1.5, seed=5)
    res2 = C.fit_pre_post(X2, s2, v2, p2, y2, n_boot=200, seed=3)
    assert res2.delta_mcc.delta > 0.05


def test_routing_curves_shapes():
    y, X, p, s, v = synth()
    h = (p >= 0.5).astype(int); g = (s >= 0.5).astype(int)
    router = C.fit_benefit_router(X, y, h, g, v)
    rows = C.routing_curves(y, h, g, v, p, 0.5, ids=list(range(len(y))), benefit_scores=router.predict(X), n_random=3)
    pols = {r["policy"] for r in rows}
    assert {"gate_only", "full_expert_with_fallback", "random", "confidence", "benefit", "oracle"} <= pols
    q10 = [r for r in rows if r["policy"] == "oracle" and r["q"] == 0.10][0]
    assert q10["queries"] == int(np.ceil(0.10 * len(y)))


def test_parse_top_logprobs_and_response():
    out = parse_top_logprobs({"1": -0.2, " 0": -1.8, "The": -5.0})
    assert out["valid"] and out["pred_argmax"] == 1 and 0.8 < out["s"] < 0.9
    assert parse_top_logprobs({"The": -0.1})["valid"] is False
    top = [SimpleNamespace(token="0", logprob=-0.1), SimpleNamespace(token="1", logprob=-2.4)]
    resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="0"),
                                                    logprobs=SimpleNamespace(content=[SimpleNamespace(token="0", logprob=-0.1, top_logprobs=top)]))],
                           usage=SimpleNamespace(prompt_tokens=1500, completion_tokens=1))
    r = FirstTokenScorer.parse_response(resp, 0.1)
    assert r.valid and r.pred_argmax == 0 and r.s < 0.2 and r.usage["prompt_tokens"] == 1500


def test_apply_pre_post_locked_thresholds():
    y1, X1, p1, s1, v1 = synth(n=200, seed=1)
    y2, X2, p2, s2, v2 = synth(n=200, seed=2)
    # 1. Khóa ngưỡng cụ thể từ validation
    app = C.apply_pre_post(
        X1, s1, v1, p1, y1,
        X2, s2, v2, p2,
        seed=42,
        tau_pre=0.45,
        tau_post=0.55,
    )
    assert app["tau_pre"] == 0.45
    assert app["tau_post"] == 0.55
    assert np.array_equal(app["pred_pre"], (app["score_pre"] >= 0.45).astype(int))
    assert np.array_equal(app["pred_post"], (app["score_post"] >= 0.55).astype(int))

