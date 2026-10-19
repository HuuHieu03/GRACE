"""
Unit Tests for Stage 2 Label-Flip Sensitivity Test
Kiểm thử toàn diện logic Thí nghiệm Đảo Nhãn:
1. Logic sinh 3 điều kiện Prompt (Condition A, Condition B, Condition C)
2. Công thức toán học tính flip_rate, natural_variance, net_sensitivity
3. Phân rã hành vi: correct_to_wrong vs wrong_to_correct
4. Xử lý các ca dự đoán invalid / lỗi
5. Thực thi luồng end-to-end ở chế độ Mock Offline
"""

import json
import pytest
from pathlib import Path

repo_root = Path(__file__).parent.parent.resolve()
src_dir = repo_root / "src"
scripts_dir = repo_root / "scripts"

import sys
for p in [str(repo_root), str(src_dir), str(scripts_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.run_label_flip_test import (
    build_condition_prompts,
    compute_label_flip_statistics,
    MockLabelFlipLLM,
    call_model_with_contract_retry,
    run_experiment
)


def test_build_condition_prompts_vuln_demo():
    """Kiểm tra sinh prompt khi demo gốc là Vulnerable (target=1)."""
    target = {
        "id": "target_001",
        "func": "void check_buffer(char *str) { strcpy(buf, str); }",
        "target": 1,
        "nodes": [{"id": 0, "type": "FUNC"}],
        "edges": []
    }
    demo = {
        "id": "demo_001",
        "func": "void demo_fn(char *src) { strcpy(dest, src); }",
        "target": 1
    }

    prompt_a, prompt_b, prompt_c, y_demo, y_demo_flipped = build_condition_prompts(target, demo)

    assert y_demo == 1
    assert y_demo_flipped == 0

    # Condition A: Phải chứa nhãn gốc 1 (Vulnerable)
    assert "Label: Vulnerable (1)" in prompt_a
    assert "Label: Non-vulnerable (0)" not in prompt_a

    # Condition B: Phải chứa nhãn đảo 0 (Non-vulnerable)
    assert "Label: Non-vulnerable (0)" in prompt_b
    assert "Label: Vulnerable (1)" not in prompt_b

    # Condition C: Phải giống hệt Condition A
    assert prompt_c == prompt_a


def test_build_condition_prompts_safe_demo():
    """Kiểm tra sinh prompt khi demo gốc là Safe (target=0)."""
    target = {
        "id": "target_002",
        "func": "void safe_buffer(char *str) { strncpy(buf, str, sizeof(buf)-1); }",
        "target": 0,
        "nodes": [],
        "edges": []
    }
    demo = {
        "id": "demo_002",
        "func": "void demo_safe() { int a = 1; }",
        "target": 0
    }

    prompt_a, prompt_b, prompt_c, y_demo, y_demo_flipped = build_condition_prompts(target, demo)

    assert y_demo == 0
    assert y_demo_flipped == 1

    # Condition A: Non-vulnerable
    assert "Label: Non-vulnerable (0)" in prompt_a
    # Condition B: Flipped to Vulnerable
    assert "Label: Vulnerable (1)" in prompt_b
    # Condition C: Giống hệt A
    assert prompt_c == prompt_a


def test_compute_label_flip_statistics_exact_math():
    """Kiểm tra tính toán chính xác công thức toán học của các chỉ số."""
    # Giả lập 10 mẫu với kịch bản được định sẵn:
    records = [
        # Mẫu 0: Đúng ở A (1), Sai ở B (0), C giống A (1) -> Bị lừa bởi nhãn đảo (correct_to_wrong), Flip=1, Var=0
        {"target": 1, "demo_gt": 0, "pred_a": 1, "pred_b": 0, "pred_c": 1},
        # Mẫu 1: Đúng ở A (0), Sai ở B (1), C giống A (0) -> Bị lừa bởi nhãn đảo (correct_to_wrong), Flip=1, Var=0
        {"target": 0, "demo_gt": 1, "pred_a": 0, "pred_b": 1, "pred_c": 0},
        # Mẫu 2: Sai ở A (0), Đúng ở B (1), C giống A (0) -> May mắn đoán trúng (wrong_to_correct), Flip=1, Var=0
        {"target": 1, "demo_gt": 1, "pred_a": 0, "pred_b": 1, "pred_c": 0},
        # Mẫu 3: Đúng ở A (1), Đúng ở B (1), C khác A (0) -> Kiên định đúng, Flip=0, Var=1 (Natural Variance)
        {"target": 1, "demo_gt": 0, "pred_a": 1, "pred_b": 1, "pred_c": 0},
        # Mẫu 4: Sai ở A (0), Sai ở B (0), C giống A (0) -> Kiên định sai, Flip=0, Var=0
        {"target": 1, "demo_gt": 0, "pred_a": 0, "pred_b": 0, "pred_c": 0},
        # Mẫu 5-9: 5 mẫu hoàn hảo đúng ở cả A, B, C (Kiên định đúng, Flip=0, Var=0)
        {"target": 0, "demo_gt": 0, "pred_a": 0, "pred_b": 0, "pred_c": 0},
        {"target": 0, "demo_gt": 1, "pred_a": 0, "pred_b": 0, "pred_c": 0},
        {"target": 1, "demo_gt": 1, "pred_a": 1, "pred_b": 1, "pred_c": 1},
        {"target": 0, "demo_gt": 0, "pred_a": 0, "pred_b": 0, "pred_c": 0},
        {"target": 1, "demo_gt": 1, "pred_a": 1, "pred_b": 1, "pred_c": 1},
    ]

    stats = compute_label_flip_statistics(records)
    qf = stats["quantitative_findings"]
    bb = stats["behavioral_breakdown"]

    assert stats["total_samples"] == 10
    assert stats["valid_samples"] == 10
    assert stats["invalid_count"] == 0

    # Flips xuất hiện ở mẫu 0, 1, 2 -> 3 flips / 10 = 0.30 (30%)
    assert qf["flip_count"] == 3
    assert qf["flip_rate"] == 0.3
    assert qf["flip_rate_pct"] == 30.0

    # Natural Variance xuất hiện ở mẫu 3 -> 1 variance / 10 = 0.10 (10%)
    assert qf["natural_variance_count"] == 1
    assert qf["natural_variance_rate"] == 0.1
    assert qf["natural_variance_pct"] == 10.0

    # Net Sensitivity = Flip Rate - Natural Variance = 0.3 - 0.1 = 0.2 (20%)
    assert qf["net_label_sensitivity"] == 0.2
    assert qf["net_label_sensitivity_pct"] == 20.0

    # Phân rã hành vi:
    # correct_to_wrong: mẫu 0, 1 -> 2
    assert bb["correct_to_wrong"] == 2
    # wrong_to_correct: mẫu 2 -> 1
    assert bb["wrong_to_correct"] == 1
    # stayed_correct: mẫu 3, 5, 6, 7, 8, 9 -> 6
    assert bb["stayed_correct"] == 6
    # stayed_wrong: mẫu 4 -> 1
    assert bb["stayed_wrong"] == 1


def test_compute_label_flip_statistics_with_invalids():
    """Kiểm tra xử lý khi có mẫu bị lỗi / None."""
    records = [
        {"target": 1, "demo_gt": 0, "pred_a": 1, "pred_b": 0, "pred_c": 1},
        {"target": 0, "demo_gt": 1, "pred_a": None, "pred_b": 1, "pred_c": 0},  # Invalid A
        {"target": 1, "demo_gt": 1, "pred_a": 1, "pred_b": None, "pred_c": 1},  # Invalid B
        {"target": 0, "demo_gt": 0, "pred_a": 0, "pred_b": 0, "pred_c": 0},
    ]

    stats = compute_label_flip_statistics(records)
    assert stats["total_samples"] == 4
    assert stats["valid_samples"] == 2
    assert stats["invalid_count"] == 2
    assert stats["invalid_rate"] == 0.5


def test_mock_label_flip_llm():
    """Kiểm tra hoạt động của MockLabelFlipLLM."""
    mock = MockLabelFlipLLM(seed=42)
    prompt_safe = "int safe_func() { return 0; }\n--- DEMONSTRATION GROUND TRUTH LABEL ---\nLabel: Non-vulnerable (0)"
    resp_1 = mock.generate_response(prompt_safe, run_iteration=1)
    assert resp_1 in ["0", "1"]


def test_end_to_end_mock_experiment(tmp_path):
    """Kiểm thử end-to-end run_experiment ở chế độ mock."""
    # Tạo file dev split tạm thời
    fake_split_file = tmp_path / "fake_dev_split.json"
    fake_samples = []
    for i in range(4):
        stmt = 'strcpy(buf, "x");' if i % 2 == 0 else 'int a=0;'
        fake_samples.append({
            "id": f"sample_{i}",
            "target": 1 if i % 2 == 0 else 0,
            "code": f"void test_func_{i}() {{ char buf[10]; {stmt} }}",
            "nodes": [],
            "edges": [],
            "project": "qemu"
        })
    fake_payload = {
        "split_name": "test_mock_split",
        "dataset": "devign",
        "sample_details": fake_samples
    }
    with open(fake_split_file, "w", encoding="utf-8") as f:
        json.dump(fake_payload, f)

    output_report_file = tmp_path / "mock_report.json"

    report = run_experiment(
        dev_split_file=fake_split_file,
        dataset_name="devign",
        output_path=output_report_file,
        max_samples=4,
        max_train_samples=10,
        use_mock=True,
        seed=42
    )

    assert output_report_file.exists(), "Báo cáo JSON phải được xuất ra đĩa!"
    assert "quantitative_findings" in report
    assert "behavioral_breakdown" in report
    assert "condition_metrics" in report
    assert "experiment_metadata" in report
    assert report["experiment_metadata"]["model_name"] == "mock_model"
    assert report["experiment_metadata"]["provider"] == "Mock"
    assert len(report["detailed_samples"]) == 4

    # Kiểm tra truyền trực tiếp train_samples
    explicit_report_file = tmp_path / "mock_report_explicit.json"
    report_explicit = run_experiment(
        dev_split_file=fake_split_file,
        dataset_name="devign",
        output_path=explicit_report_file,
        max_samples=2,
        use_mock=True,
        seed=42,
        train_samples=fake_samples
    )
    assert explicit_report_file.exists()
    assert len(report_explicit["detailed_samples"]) == 2
    assert report_explicit["detailed_samples"][0]["demo_id"] in [s["id"] for s in fake_samples]
    assert report_explicit["detailed_samples"][0]["demo_gt"] in (0, 1)

    # Kiểm tra trường hợp train_samples=[] rỗng kích hoạt fallback tự động sang mock
    report_empty_pool = run_experiment(
        dev_split_file=fake_split_file,
        dataset_name="devign",
        output_path=tmp_path / "empty_pool_report.json",
        max_samples=2,
        use_mock=True,
        seed=42,
        train_samples=[]
    )
    assert len(report_empty_pool["detailed_samples"]) == 2


def test_call_model_with_contract_retry():
    """Kiểm tra chính sách retry và exhausted request trong call_model_with_contract_retry."""
    from scripts.run_label_flip_test import call_model_with_contract_retry

    # 1. Chế độ Mock
    mock_engine = MockLabelFlipLLM(seed=42)
    resp = call_model_with_contract_retry(mock_engine, "test prompt", use_mock=True)
    assert resp in ("0", "1")

    # 2. Mock engine gặp lỗi liên tục -> Kiệt sức trả về "" (invalid)
    class FailingEngine:
        def __init__(self):
            self.calls = 0
        def generate_response(self, prompt):
            self.calls += 1
            raise RuntimeError("API Timeout / 429 Rate Limit")

    fail_eng = FailingEngine()
    resp_fail = call_model_with_contract_retry(
        fail_eng,
        "test prompt",
        use_mock=False,
        max_attempts=3,
        min_backoff_sec=0.01,
        max_backoff_sec=0.05
    )
    assert resp_fail == "", "Khi kiệt sức request phải trả về chuỗi rỗng để parser đánh dấu invalid!"
    assert fail_eng.calls == 3, "Phải gọi đúng số lần max_attempts trước khi dừng!"

    # 3. Engine lỗi 2 lần đầu, thành công ở lần thứ 3
    class FlakyEngine:
        def __init__(self):
            self.calls = 0
        def generate_response(self, prompt):
            self.calls += 1
            if self.calls < 3:
                raise RuntimeError("Temporary glitch")
            return "1"

    flaky_eng = FlakyEngine()
    resp_flaky = call_model_with_contract_retry(
        flaky_eng,
        "test prompt",
        use_mock=False,
        max_attempts=5,
        min_backoff_sec=0.01,
        max_backoff_sec=0.05
    )
    assert resp_flaky == "1"
    assert flaky_eng.calls == 3

