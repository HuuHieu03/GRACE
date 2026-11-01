#!/usr/bin/env python3
"""Kiểm thử tự động toàn diện cho Bước 5: Matrix Inference Execution & Validation Threshold Locking.

Tuân thủ nghiêm ngặt Hợp đồng thực nghiệm (evaluation_contract.yaml) và Giao thức đăng ký trước (prereg-v1):
1. Kiểm tra trạng thái hạ tầng thực thi (backend offline, mock fallback).
2. Kiểm tra tính tất định và tuân thủ schema OpenAI của FirstTokenScorer (mock mode).
3. Kiểm tra công cụ suy luận ma trận run_matrix.py (schema B.2, manifest.json, tokenizer offline).
4. Kiểm tra tối ưu hóa và khóa ngưỡng tau* strictly trên Validation (bất biến phương pháp luận: không chạm test).
5. Kiểm tra rào chắn sẵn sàng cho tập Test (test readiness verification).
6. Kiểm tra tính tương thích của evaluate_final.py với file thresholds.json đã khóa.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
diag_src = REPO_ROOT / "grace_diag_kit" / "src"
if diag_src.exists() and str(diag_src) not in sys.path:
    sys.path.insert(0, str(diag_src))

from grace_diag.llm_backend import BackendConfig, FirstTokenScorer, load_backend_config
from grace_diag import stats as S
from scripts.run_step5_matrix import (
    check_backend_status,
    optimize_and_lock_thresholds,
    verify_test_readiness,
    TIER_DEFINITIONS,
)


def test_check_backend_status_offline():
    """Kiểm thử: Khi URL Cloudflare cũ hết hạn, hàm kiểm tra phải báo OFFLINE kèm hướng dẫn rõ ràng."""
    kaggle_cfg = REPO_ROOT / "configs" / "backend_kaggle.yaml"
    res = check_backend_status(kaggle_cfg)
    assert res["status"] == "offline"
    assert res["is_online"] is False
    assert "guidance" in res
    assert len(res["guidance"]) >= 3


def test_check_backend_status_mock():
    """Kiểm thử: Mock backend phải được nhận diện là MOCK và is_online=True."""
    mock_cfg = REPO_ROOT / "configs" / "backend_mock.yaml"
    res = check_backend_status(mock_cfg)
    assert res["status"] == "mock"
    assert res["is_online"] is True
    assert res["kind"] == "mock"


def test_first_token_scorer_mock_deterministic():
    """Kiểm thử: Mock scorer sinh điểm số s liên tục trong [0.05, 0.95], tất định 100%."""
    cfg = BackendConfig(kind="mock", seed=42)
    scorer = FirstTokenScorer(cfg)

    prompt_a = "You are an expert. Check if function foo() is vulnerable. Answer (0 or 1):"
    prompt_b = "You are an expert. Check if function bar() is vulnerable. Answer (0 or 1):"

    res_a1 = scorer.score(prompt_a, use_cache=False)
    res_a2 = scorer.score(prompt_a, use_cache=False)
    res_b = scorer.score(prompt_b, use_cache=False)

    # 1. Hợp lệ và nằm trong miền xác suất hợp thức
    assert res_a1.valid is True
    assert 0.05 <= res_a1.s <= 0.95
    assert res_a1.pred_argmax in (0, 1)
    assert res_a1.p0 + res_a1.p1 == pytest.approx(1.0, abs=1e-5)
    assert "0" in res_a1.top and "1" in res_a1.top

    # 2. Tất định: cùng prompt & seed cho kết quả giống hệt
    assert res_a1.s == res_a2.s
    assert res_a1.pred_argmax == res_a2.pred_argmax

    # 3. Phân biệt được các prompt khác nhau
    assert res_a1.s != res_b.s


def test_run_matrix_smoke_mock(tmp_path):
    """Kiểm thử: run_matrix.py chạy với mock backend trên 2 mẫu validation subset và tạo schema B.2."""
    out_dir = tmp_path / "matrix_out"
    specs_path = REPO_ROOT / "data" / "specs" / "devign_val_subset600.jsonl"
    tok_path = REPO_ROOT / "grace_diag_kit" / "tokenizer"

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_matrix.py"),
        "--dataset", "devign",
        "--split", "validation",
        "--specs", str(specs_path),
        "--arms", "B0", "B1",
        "--seeds", "42",
        "--backend", str(REPO_ROOT / "configs" / "backend_mock.yaml"),
        "--tokenizer", str(tok_path),
        "--limit", "2",
        "--out", str(out_dir),
    ]

    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"run_matrix.py failed: {res.stderr}"

    # Kiểm tra cấu trúc thư mục
    b0_dir = out_dir / "devign" / "validation" / "B0" / "42"
    assert b0_dir.exists()
    assert (b0_dir / "manifest.json").exists()
    assert (b0_dir / "records.jsonl").exists()

    # Kiểm tra schema B.2 trong records.jsonl
    records = [json.loads(line) for line in open(b0_dir / "records.jsonl", encoding="utf-8") if line.strip()]
    assert len(records) == 2
    r0 = records[0]
    expected_fields = [
        "id", "dataset", "split", "arm", "seed", "prompt_sha256", "tokens_code",
        "tokens_graph", "tokens_demo", "tokens_total", "truncated", "s", "p0", "p1",
        "pred_argmax", "valid", "label", "model", "backend_kind"
    ]
    for field in expected_fields:
        assert field in r0, f"Thiếu trường {field} theo schema B.2!"

    assert r0["dataset"] == "devign"
    assert r0["split"] == "validation"
    assert r0["arm"] == "B0"
    assert r0["seed"] == 42
    assert r0["valid"] is True
    assert 0.05 <= r0["s"] <= 0.95


def test_optimize_and_lock_thresholds_strictly_validation(tmp_path):
    """Kiểm thử: Tối ưu hóa tau* chỉ trên Validation, phát hiện và ném lỗi nếu có dữ liệu test."""
    runs_dir = tmp_path / "runs"
    val_b0 = runs_dir / "devign" / "validation" / "B0" / "42"
    val_b0.mkdir(parents=True, exist_ok=True)

    # Sinh 20 bản ghi validation mẫu
    rows = []
    rng = np.random.default_rng(42)
    for i in range(20):
        y = int(i % 2 == 0)
        s = float(0.2 + 0.6 * y + rng.normal(0, 0.1))
        s = np.clip(s, 0.01, 0.99)
        rows.append({
            "id": f"val_{i}",
            "dataset": "devign",
            "split": "validation",
            "arm": "B0",
            "seed": 42,
            "valid": True,
            "label": y,
            "s": s,
            "pred_argmax": int(s >= 0.5),
        })

    with open(val_b0 / "records.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    out_json = tmp_path / "thresholds.json"
    proto_path = REPO_ROOT / "configs" / "protocol.yaml"

    payload = optimize_and_lock_thresholds(
        runs_dir=runs_dir,
        out_thresholds_path=out_json,
        protocol_path=proto_path,
        include_step0_meta=False,
    )

    assert out_json.exists()
    assert "devign|B0|42" in payload["thresholds"]
    tau_star = payload["thresholds"]["devign|B0|42"]
    assert 0.01 <= tau_star <= 0.99
    assert payload["metadata"]["optimized_on_split"] == "validation"
    assert "STRICTLY_NONE" in payload["metadata"]["test_exposure"]

    # Kiểm tra rào chắn vi phạm: nếu có file test trong danh sách tối ưu, phải ném lỗi
    test_b0 = runs_dir / "devign" / "test" / "B0" / "42"
    test_b0.mkdir(parents=True, exist_ok=True)
    with open(test_b0 / "records.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"id": "test_1", "valid": True, "label": 1, "s": 0.9}) + "\n")

    # Hàm phải bỏ qua split test hoặc bắt lỗi nếu split_str != validation
    # Kiểm tra optimize_and_lock_thresholds chỉ duyệt glob validation
    payload2 = optimize_and_lock_thresholds(
        runs_dir=runs_dir,
        out_thresholds_path=out_json,
        protocol_path=proto_path,
        include_step0_meta=False,
    )
    # Xác nhận key của test không hề lọt vào thresholds.json
    assert "devign|B0|42|test" not in payload2["thresholds"]
    for k, v in payload2["details"].items():
        assert v["split"] == "validation"


def test_verify_test_readiness(tmp_path):
    """Kiểm thử: Rào chắn sẵn sàng kiểm tra đúng danh sách arm, stochastic seeds và meta models."""
    thresh_file = tmp_path / "thresholds.json"
    # 1. Khi file chưa tồn tại -> False
    assert verify_test_readiness(thresh_file, ["B0", "B1"], "devign", require_meta=False) is False

    # 2. Khi thiếu arm -> False
    thresh_file.write_text(json.dumps({"thresholds": {"devign|B0|42": 0.50}}), encoding="utf-8")
    assert verify_test_readiness(thresh_file, ["B0", "B1"], "devign", require_meta=False) is False

    # 3. Khi đủ mọi arm deterministic -> True
    thresh_file.write_text(json.dumps({"thresholds": {"devign|B0|42": 0.50, "devign|B1|42": 0.55}}), encoding="utf-8")
    assert verify_test_readiness(thresh_file, ["B0", "B1"], "devign", require_meta=False) is True

    # 4. Khi có arm stochastic B2-rand nhưng chỉ mới có seed 42 (thiếu 43, 44) -> False
    thresh_file.write_text(json.dumps({"thresholds": {"devign|B2-rand|42": 0.50}}), encoding="utf-8")
    assert verify_test_readiness(thresh_file, ["B2-rand"], "devign", require_meta=False) is False

    # 5. Khi B2-rand đủ cả 3 seeds 42, 43, 44 -> True
    thresh_file.write_text(json.dumps({"thresholds": {
        "devign|B2-rand|42": 0.50,
        "devign|B2-rand|43": 0.52,
        "devign|B2-rand|44": 0.48,
    }}), encoding="utf-8")
    assert verify_test_readiness(thresh_file, ["B2-rand"], "devign", require_meta=False) is True

    # 6. Kiểm tra require_meta: thiếu P-PRE hoặc P-POST -> False
    assert verify_test_readiness(thresh_file, ["B2-rand"], "devign", require_meta=True) is False

    # 7. Đủ cả meta arms -> True
    thresh_file.write_text(json.dumps({"thresholds": {
        "devign|B2-rand|42": 0.50,
        "devign|B2-rand|43": 0.52,
        "devign|B2-rand|44": 0.48,
        "devign|P-PRE|42": 0.54,
        "devign|P-POST|42": 0.60,
    }}), encoding="utf-8")
    assert verify_test_readiness(thresh_file, ["B2-rand"], "devign", require_meta=True) is True


def test_evaluate_final_with_locked_thresholds(tmp_path):
    """Kiểm thử: evaluate_final.py nhận file thresholds.json đã khóa và xuất báo cáo không chạm test."""
    eval_out = tmp_path / "eval_out"
    runs_dir = REPO_ROOT / "runs" / "final"
    proto_path = REPO_ROOT / "configs" / "protocol.yaml"
    thresh_path = REPO_ROOT / "configs" / "thresholds.json"

    cmd = [
        sys.executable,
        "-m", "grace_diag.evaluate_final",
        "--runs", str(runs_dir),
        "--protocol", str(proto_path),
        "--thresholds", str(thresh_path),
        "--out", str(eval_out),
    ]

    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert res.returncode == 0, f"evaluate_final.py failed: {res.stderr}"

    # Kiểm tra các tệp artifact sinh ra
    assert (eval_out / "thresholds.json").exists()
    assert (eval_out / "table_B_contrasts.csv").exists()

    # Kiểm tra metadata và các ngưỡng đã khóa được bảo tồn
    saved = json.loads((eval_out / "thresholds.json").read_text(encoding="utf-8"))
    assert "metadata" in saved
    assert saved["metadata"]["optimized_on_split"] == "validation"
    assert "STRICTLY_NONE" in saved["metadata"]["test_exposure"]
    assert "devign|B0|42" in saved["thresholds"]


def test_backend_retry_policy_on_failure():
    """Kiểm thử: FirstTokenScorer tuân thủ evaluation_contract.yaml retry_policy: retry tối đa max_attempts khi lỗi mạng."""
    from unittest.mock import MagicMock
    cfg = BackendConfig(kind="vllm", max_attempts=3)
    scorer = FirstTokenScorer(cfg)

    # Giả lập client ném lỗi mạng 2 lần rồi thành công ở lần 3
    attempts = 0
    mock_choice = MagicMock()
    mock_choice.message.content = "1"
    mock_choice.logprobs.content = [MagicMock(top_logprobs=[
        MagicMock(token="0", logprob=-2.0),
        MagicMock(token="1", logprob=-0.5),
    ])]
    mock_resp = MagicMock(choices=[mock_choice], usage=MagicMock(prompt_tokens=10, completion_tokens=1))

    def fake_create(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Temporary 504 Gateway Timeout from Cloudflare tunnel")
        return mock_resp

    scorer.client = MagicMock()
    scorer.client.chat.completions.create.side_effect = fake_create

    # Mock time.sleep để chạy tức thì
    import time
    orig_sleep = time.sleep
    time.sleep = lambda s: None
    try:
        res = scorer.score("Test prompt with transient error", use_cache=False)
        assert attempts == 3
        assert res.valid is True
        assert res.pred_argmax == 1
        assert res.error is None
    finally:
        time.sleep = orig_sleep


def test_backend_fail_fast_on_bad_request_or_context_exceeded():
    """Kiểm thử: FirstTokenScorer fail-fast lập tức (0 retry) khi gặp HTTP 400 hoặc context length exceeded."""
    from unittest.mock import MagicMock
    cfg = BackendConfig(kind="vllm", max_attempts=5)
    scorer = FirstTokenScorer(cfg)

    attempts = 0

    class MockBadRequestError(Exception):
        def __init__(self, msg, status_code=400):
            super().__init__(msg)
            self.status_code = status_code

    def fake_create_context_err(**kwargs):
        nonlocal attempts
        attempts += 1
        raise MockBadRequestError("Error code: 400 - This model's maximum context length is 4096 tokens. However, you requested 4419 tokens.")

    scorer.client = MagicMock()
    scorer.client.chat.completions.create.side_effect = fake_create_context_err

    import time
    orig_sleep = time.sleep
    time.sleep = lambda s: None
    try:
        res = scorer.score("Test prompt exceeding context length", use_cache=False)
        # Bắt buộc chỉ thực hiện đúng 1 lần gọi (fail-fast), không retry lãng phí 5 lần
        assert attempts == 1, f"Expected 1 attempt but got {attempts}"
        assert res.valid is False
        assert "400" in res.error or "context length" in res.error

        # Kiểm tra thêm nhánh httpx.HTTPStatusError với status_code nằm trong exc.response
        class MockResponse:
            status_code = 400

        class MockHTTPStatusError(Exception):
            def __init__(self, msg):
                super().__init__(msg)
                self.response = MockResponse()

        attempts_httpx = 0
        def fake_httpx_err(**kwargs):
            nonlocal attempts_httpx
            attempts_httpx += 1
            raise MockHTTPStatusError("Client error: generic 400 without keywords")

        scorer.client.chat.completions.create.side_effect = fake_httpx_err
        res_httpx = scorer.score("Another prompt with generic 400", use_cache=False)
        assert attempts_httpx == 1, f"Expected 1 attempt for httpx error but got {attempts_httpx}"
        assert res_httpx.valid is False
    finally:
        time.sleep = orig_sleep
        scorer.close()



def test_meta_model_subset_matching_no_dummy_pollution(tmp_path):
    """Kiểm thử: optimize_and_lock_thresholds khớp chính xác theo tập mẫu đã đánh giá và không bị ô nhiễm dummy data."""
    runs_dir = tmp_path / "runs"
    val_b2 = runs_dir / "devign" / "validation" / "B2" / "42"
    val_b2.mkdir(parents=True, exist_ok=True)

    # Giả lập 10 bản ghi B2 validation
    rows = []
    for i in range(10):
        rows.append({
            "id": f"devign_val_{i}",
            "dataset": "devign",
            "split": "validation",
            "arm": "B2",
            "seed": 42,
            "valid": True,
            "label": int(i % 2 == 0),
            "s": 0.8 if (i % 2 == 0) else 0.2,
            "pred_argmax": int(i % 2 == 0),
        })
    with open(val_b2 / "records.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    out_thresh = tmp_path / "thresholds.json"
    proto_path = REPO_ROOT / "configs" / "protocol.yaml"

    payload = optimize_and_lock_thresholds(
        runs_dir=runs_dir,
        out_thresholds_path=out_thresh,
        protocol_path=proto_path,
        include_step0_meta=False,
    )

    assert "devign|B2|42" in payload["thresholds"]
    assert payload["details"]["devign|B2|42"]["n_valid"] == 10
    assert payload["details"]["devign|B2|42"]["n_total"] == 10


def test_run_matrix_split_test_guardrail(tmp_path):
    """Kiểm thử: run_step5_matrix.py ngăn chặn chạy split=test nếu thresholds.json chưa khóa."""
    empty_thresh = tmp_path / "missing_thresholds.json"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_step5_matrix.py"),
        "run-matrix",
        "--dataset", "devign",
        "--split", "test",
        "--tier", "tier1",
        "--thresholds", str(empty_thresh),
        "--limit", "1",
        "--dry-run",
        "--out", str(tmp_path),
    ]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode != 0
    assert "VIOLATION" in res.stdout or "VIOLATION" in res.stderr

