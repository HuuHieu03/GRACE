"""
Unit Tests for Stage 5: Vulnerability-Aware Demonstration Retrieval Engine
Kiểm thử khởi tạo, truy xuất Top-N candidates, Security-Aware Reranker, và annotate_dataset.
"""

import pytest
import numpy as np
from retrieval_security_engine import SecurityAwareRetriever
from data_loader import generate_mock_dataset


@pytest.fixture
def mock_dataset():
    """Tạo tập dữ liệu giả lập cho huấn luyện và kiểm thử."""
    train_data = generate_mock_dataset(num_samples=30)
    test_data = generate_mock_dataset(num_samples=10)
    return train_data, test_data


def test_security_retriever_initialization():
    """Kiểm thử khởi tạo SecurityAwareRetriever với các tham số lambda khác nhau."""
    retriever = SecurityAwareRetriever(lambda_weight=0.3)
    assert retriever.lambda_weight == 0.3
    assert len(retriever.train_samples) == 0
    assert retriever.train_vecs is None


def test_security_retriever_fit(mock_dataset):
    """Kiểm thử quá trình xây dựng index và tiền trích xuất Security Signatures."""
    train_data, _ = mock_dataset
    retriever = SecurityAwareRetriever(lambda_weight=0.3)
    retriever.fit(train_data, precompute_signatures=True)
    
    assert len(retriever.train_samples) == len(train_data)
    assert retriever.train_vecs is not None
    assert len(retriever.train_signatures) == len(train_data)
    assert retriever.train_vecs.shape[0] == len(train_data)


def test_security_retriever_retrieve(mock_dataset):
    """Kiểm thử chu trình truy xuất hoàn chỉnh cho 1 mẫu kiểm tra."""
    train_data, test_data = mock_dataset
    retriever = SecurityAwareRetriever(lambda_weight=0.3)
    retriever.fit(train_data, precompute_signatures=True)
    
    query = test_data[0]
    res = retriever.retrieve(query, top_candidates=10, final_top_k=3)
    
    assert "best_example" in res
    assert "best_final_score" in res
    assert "best_security_score" in res
    assert "query_signature" in res
    assert len(res["top_candidates"]) <= 3
    assert res["total_candidates_evaluated"] <= 10
    assert res["best_final_score"] >= 0.0


def test_lambda_weight_effect(mock_dataset):
    """Kiểm thử ảnh hưởng của trọng số lambda (lambda=1.0 ưu tiên code sim vs lambda=0.0 ưu tiên security)."""
    train_data, test_data = mock_dataset
    retriever = SecurityAwareRetriever()
    retriever.fit(train_data, precompute_signatures=True)
    
    query = test_data[0]
    res_pure_grace = retriever.retrieve(query, top_candidates=15, lambda_weight=1.0)
    res_pure_sec = retriever.retrieve(query, top_candidates=15, lambda_weight=0.0)
    
    assert res_pure_grace["best_final_score"] == res_pure_grace["best_grace_score"]
    assert res_pure_sec["best_final_score"] == res_pure_sec["best_security_score"]


def test_annotate_dataset(mock_dataset):
    """Kiểm thử gán trực tiếp thông tin retrieval vào danh sách mẫu kiểm tra."""
    train_data, test_data = mock_dataset
    retriever = SecurityAwareRetriever(lambda_weight=0.3)
    retriever.fit(train_data, precompute_signatures=True)
    
    annotated = retriever.annotate_dataset(test_data[:3], top_candidates=10, final_top_k=2)
    assert len(annotated) == 3
    for item in annotated:
        assert "example" in item
        assert "security_signature" in item
        assert "retrieval_final_score" in item
        assert "top_ranked_candidates" in item
