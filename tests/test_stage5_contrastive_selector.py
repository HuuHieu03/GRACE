"""
Unit Tests for Stage 5: Contrastive Demonstration Selection & Contrastive Prompt Engine
Kiểm thử chọn cặp tương phản (1 Vulnerable + 1 Safe) và sinh Prompt Contrastive 2-shot chuẩn Figure 6.
"""

import pytest
from retrieval_security_engine import SecurityAwareRetriever
from contrastive_selector import ContrastiveDemonstrationSelector, ContrastivePair
from prompt_engine import build_contrastive_prompt, build_prompt
from data_loader import generate_mock_dataset


@pytest.fixture
def retriever_and_dataset():
    """Tạo retriever đã fit dữ liệu mock có cả mẫu Vulnerable và Safe."""
    train_data = generate_mock_dataset(num_samples=40)
    test_data = generate_mock_dataset(num_samples=10)
    
    retriever = SecurityAwareRetriever(lambda_weight=0.3)
    retriever.fit(train_data, precompute_signatures=True)
    return retriever, test_data


def test_contrastive_selector_counterexample_strategy(retriever_and_dataset):
    """Kiểm thử Strategy C: Cặp tương phản Counterexample (1 Lỗi + 1 An toàn)."""
    retriever, test_data = retriever_and_dataset
    selector = ContrastiveDemonstrationSelector(retriever)
    
    query = test_data[0]
    pair = selector.select_pair(query, strategy="counterexample_pair", top_candidates=20)
    
    assert pair is not None
    assert isinstance(pair, ContrastivePair)
    assert pair.vulnerable_example.get("target") == 1
    assert pair.safe_example.get("target") == 0
    assert pair.selection_strategy == "counterexample_pair"
    assert len(pair.security_critical_difference) > 0


def test_contrastive_selector_minimal_diff_and_label_contrast(retriever_and_dataset):
    """Kiểm thử Strategy B và Strategy A."""
    retriever, test_data = retriever_and_dataset
    selector = ContrastiveDemonstrationSelector(retriever)
    
    query = test_data[1]
    pair_b = selector.select_pair(query, strategy="minimal_security_diff", top_candidates=20)
    pair_a = selector.select_pair(query, strategy="label_contrast", top_candidates=20)
    
    assert pair_b.vulnerable_example.get("target") == 1 and pair_b.safe_example.get("target") == 0
    assert pair_a.vulnerable_example.get("target") == 1 and pair_a.safe_example.get("target") == 0


def test_annotate_dataset_contrastive(retriever_and_dataset):
    """Kiểm thử gán trực tiếp thông tin cặp tương phản vào danh sách mẫu test."""
    retriever, test_data = retriever_and_dataset
    selector = ContrastiveDemonstrationSelector(retriever)
    
    annotated = selector.annotate_dataset_contrastive(test_data[:3], strategy="counterexample_pair")
    assert len(annotated) == 3
    for sample in annotated:
        assert "contrastive_pair" in sample
        assert "contrastive_obj" in sample
        pair_dict = sample["contrastive_pair"]
        assert pair_dict["vulnerable"]["target"] == 1
        assert pair_dict["safe"]["target"] == 0


def test_build_contrastive_prompt_structure(retriever_and_dataset):
    """Kiểm thử định dạng Prompt Contrastive 2-shot tuân thủ 100% nguyên tắc Figure 6."""
    retriever, test_data = retriever_and_dataset
    selector = ContrastiveDemonstrationSelector(retriever)
    
    annotated = selector.annotate_dataset_contrastive(test_data[:1], strategy="counterexample_pair")
    sample = annotated[0]
    
    prompt = build_contrastive_prompt(sample)
    
    assert "### TASK INSTRUCTION" in prompt
    assert "### CONTRASTIVE DEMONSTRATION EXAMPLES" in prompt
    assert "--- EXAMPLE 1 (VULNERABLE REFERENCE) ---" in prompt
    assert "Label: Vulnerable (1)" in prompt
    assert "--- EXAMPLE 2 (SAFE / NON-VULNERABLE REFERENCE) ---" in prompt
    assert "Label: Non-vulnerable (0)" in prompt
    assert "### TARGET QUERY FOR EVALUATION" in prompt
    assert "### OUTPUT FORMAT REQUIREMENT" in prompt


def test_unified_build_prompt_dispatcher(retriever_and_dataset):
    """Kiểm thử hàm dispatcher build_prompt hỗ trợ cả 3 chế độ."""
    retriever, test_data = retriever_and_dataset
    selector = ContrastiveDemonstrationSelector(retriever)
    annotated = selector.annotate_dataset_contrastive(test_data[:1])
    sample = annotated[0]
    
    p_zero = build_prompt(sample, mode="zero_shot")
    p_1shot = build_prompt(sample, mode="standard_1shot")
    p_2shot = build_prompt(sample, mode="contrastive_2shot")
    
    assert "DEMONSTRATION" not in p_zero
    assert "DEMONSTRATION EXAMPLE (In-Context Reference)" in p_1shot
    assert "CONTRASTIVE DEMONSTRATION EXAMPLES" in p_2shot


def test_contrastive_selector_fallback_telemetry():
    """Kiểm thử cơ chế Telemetry ghi nhận Fallback khi tập ứng viên thiếu một nhãn."""
    from unittest.mock import MagicMock
    
    # Tạo mock retriever chỉ trả về ứng viên nhãn Safe (target=0)
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = {
        "top_candidates": [
            {"index": 0, "id": "safe_1", "target": 0, "security_score": 0.9, "grace_score": 0.8}
        ]
    }
    # Tập train có chứa cả safe và vuln
    mock_retriever.train_samples = [
        {"id": "train_safe_1", "target": 0, "func": "void f0(){}"},
        {"id": "train_vuln_1", "target": 1, "func": "void f1(){ char buf[10]; gets(buf); }"}
    ]
    
    selector = ContrastiveDemonstrationSelector(mock_retriever)
    query = {"id": "query_test", "func": "int main(){}"}
    
    pair = selector.select_pair(query, top_candidates=10)
    assert pair is not None
    
    report = selector.get_fallback_report()
    assert report["total_queries"] == 1
    assert report["fallback_count"] == 1
    assert report["fallback_rate_pct"] == 100.0
    assert report["missing_vuln_count"] == 1
    assert report["missing_safe_count"] == 0
    assert len(report["details_sample"]) == 1
    assert report["details_sample"][0]["query_id"] == "query_test"
    assert "train_vuln_1" in report["details_sample"][0]["fallback_selected_ids"]

