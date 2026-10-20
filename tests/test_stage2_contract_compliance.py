"""
Unit Tests for Stage 2 Contract Compliance
Kiểm tra tính tuân thủ 100% của hệ thống đối với evaluation_contract.yaml:
1. Xác thực schema cấu hình hợp đồng (evaluation_contract.yaml)
2. Kiểm tra chính sách cắt ngắn Prompt (Prompt Truncation Policy)
3. Kiểm tra khóa chặt quy tắc kho tìm kiếm ứng viên (keep_full_train_pool_when_running_subset)
4. Kiểm tra chính sách xử lý phản hồi kiệt sức / lỗi (Exhausted Request Policy)
5. Kiểm tra tính toán các chỉ số Trivial Baselines (Always Vuln, Always Safe)
"""

import os
import yaml
import pytest
from pathlib import Path

repo_root = Path(__file__).parent.parent.resolve()
src_dir = repo_root / "src"
scripts_dir = repo_root / "scripts"

import sys
for p in [str(repo_root), str(src_dir), str(scripts_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from prompt_engine import (
    build_grace_prompt,
    build_contrastive_prompt,
    format_node_information,
    format_edge_information,
    format_graph_structure
)
from evaluator import parse_llm_prediction
from metrics import compute_classification_metrics


def test_contract_file_exists_and_valid():
    """Kiểm tra file evaluation_contract.yaml tồn tại và có cú pháp YAML hợp lệ."""
    contract_path = repo_root / "evaluation_contract.yaml"
    assert contract_path.exists(), "File evaluation_contract.yaml bắt buộc phải tồn tại ở thư mục gốc!"

    with open(contract_path, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)

    assert isinstance(contract, dict), "Nội dung evaluation_contract.yaml phải là dictionary hợp lệ!"
    
    # Kiểm tra các mục cấu hình cốt lõi
    required_sections = [
        "dataset_split",
        "retrieval_pool",
        "backbone_llm",
        "inference_config",
        "prompt_context_policy",
        "evaluation_metrics",
        "run_tracking"
    ]
    for sec in required_sections:
        assert sec in contract, f"Thiếu mục bắt buộc '{sec}' trong evaluation_contract.yaml"


def test_contract_retrieval_pool_constraints():
    """Kiểm tra các ràng buộc về kho tìm kiếm ứng viên trong evaluation_contract.yaml."""
    contract_path = repo_root / "evaluation_contract.yaml"
    with open(contract_path, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)

    rp = contract.get("retrieval_pool", {})
    assert rp.get("source") == "train", "retrieval_pool.source bắt buộc phải là 'train'!"
    assert rp.get("candidate_pool_size") == 50, "retrieval_pool.candidate_pool_size bắt buộc là 50!"
    assert rp.get("keep_full_train_pool_when_running_subset") is True, (
        "keep_full_train_pool_when_running_subset bắt buộc là True để tránh ô nhiễm kết quả!"
    )


def test_contract_backbone_and_inference_config():
    """Kiểm tra cấu hình mô hình LLM và tham số suy luận theo hợp đồng."""
    contract_path = repo_root / "evaluation_contract.yaml"
    with open(contract_path, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)

    bb = contract.get("backbone_llm", {})
    assert "qwen3-coder-480b" in bb.get("model", ""), "Model backbone phải là qwen3-coder-480b!"

    inf = contract.get("inference_config", {})
    assert inf.get("temperature") == 0.0, "temperature bắt buộc phải là 0.0 để đảm bảo tính tất định!"
    assert inf.get("seed") == 42, "seed bắt buộc phải là 42!"
    assert inf.get("max_tokens") == 256, "max_tokens bắt buộc là 256!"


def test_prompt_truncation_policy_compliance():
    """
    Kiểm tra tính tuân thủ tuyệt đối của prompt_engine với truncation_policy:
    - target_code_max_chars <= 3000
    - standard_demo_max_chars <= 1500
    - graph_nodes_max <= 25
    - graph_edges_max <= 25
    """
    # Tạo mã nguồn mục tiêu rất dài (> 5000 ký tự)
    long_target_code = "int vulnerable_func() {\n" + "    char buf[1024];\n" * 200 + "}\n"
    assert len(long_target_code) > 3000

    # Tạo demo code rất dài (> 2500 ký tự)
    long_demo_code = "void demo_func() {\n" + "    int x = 42;\n" * 150 + "}\n"
    assert len(long_demo_code) > 1500

    # Tạo đồ thị có 60 nodes và 60 edges
    nodes = [{"id": i, "type": "AST_NODE", "code": f"node_code_{i}"} for i in range(60)]
    edges = [{"start": i, "end": i + 1, "type": "CFG"} for i in range(60)]

    sample = {
        "id": "test_compliance_sample",
        "func": long_target_code,
        "target": 1,
        "nodes": nodes,
        "edges": edges,
        "example": {
            "id": "demo_sample",
            "func": long_demo_code,
            "target": 0
        }
    }

    prompt = build_grace_prompt(sample, include_demonstration=True)

    # 1. Kiểm tra target code đã bị cắt ngắn và có dấu hiệu cắt
    assert "/* [TRUNCATED TO PREVENT MEMORY OVERFLOW] */" in prompt
    # Phần code target hiển thị không vượt quá 3000 ký tự trước marker
    target_part = prompt.split("--- TARGET CODE ---")[1].split("--- TARGET GRAPH STRUCTURE ---")[0]
    assert len(target_part) < 3200

    # 2. Kiểm tra demo code đã bị cắt ngắn và có dấu hiệu cắt
    assert "/* [TRUNCATED TO PRESERVE CONTEXT] */" in prompt
    demo_part = prompt.split("--- DEMONSTRATION CODE ---")[1].split("--- DEMONSTRATION GROUND TRUTH LABEL ---")[0]
    assert len(demo_part) < 1700

    # 3. Kiểm tra nodes và edges không vượt quá 25
    assert "Node 24:" in prompt
    assert "Node 25:" not in prompt  # 0-indexed 0..24 là đúng 25 nodes
    assert "Edge: Node 24 ->" in prompt
    assert "Edge: Node 25 ->" not in prompt


def test_exhausted_request_policy_in_parser():
    """
    Kiểm tra chính sách xử lý phản hồi kiệt sức / lỗi:
    Mẫu không hợp lệ hoặc lỗi API BẮT BUỘC trả về is_valid=False, prediction=None,
    TUYỆT ĐỐI KHÔNG BAO GIỜ được ép về 0 (Safe).
    """
    invalid_cases = [
        "",
        "   ",
        None,
        "I am not sure if this code is vulnerable or not.",
        "Unable to determine the vulnerability status.",
        "Both 0 and 1 are possible answers.",
        "Vulnerable (1) and Non-vulnerable (0) are both present in this code."
    ]

    for inv in invalid_cases:
        pred, method, is_valid = parse_llm_prediction(inv)
        assert is_valid is False, f"Chuỗi '{inv}' phải có is_valid=False!"
        assert pred is None, f"Chuỗi '{inv}' phải có prediction=None, không được ép về 0!"


def test_trivial_baselines_computation():
    """Kiểm tra tính toán chuẩn xác của 2 Trivial Baselines (Always 1, Always 0)."""
    # Tập ground truth cân bằng: 50 mẫu 1, 50 mẫu 0
    y_true = [1] * 50 + [0] * 50

    # 1. Trivial Baseline: Always predict 1
    y_pred_always_vuln = [1] * 100
    metrics_always_vuln = compute_classification_metrics(y_true, y_pred_always_vuln)
    
    assert metrics_always_vuln["accuracy"] == 0.5
    assert metrics_always_vuln["recall"] == 1.0
    assert metrics_always_vuln["precision"] == 0.5
    assert metrics_always_vuln["balanced_accuracy"] == 0.5
    assert metrics_always_vuln["mcc"] in [0.0, None]

    # 2. Trivial Baseline: Always predict 0
    y_pred_always_safe = [0] * 100
    metrics_always_safe = compute_classification_metrics(y_true, y_pred_always_safe)
    
    assert metrics_always_safe["accuracy"] == 0.5
    assert metrics_always_safe["recall"] == 0.0
    assert metrics_always_safe["balanced_accuracy"] == 0.5
    assert metrics_always_safe["mcc"] in [0.0, None]


def test_canonical_dev_splits_contract_compliance():
    """
    Kiểm tra tính tuân thủ 100% của 2 tập clean dev split (Devign & ReVeal):
    1. Tồn tại file split tại data/splits/
    2. Đạt chuẩn 100 mẫu phân tầng hoàn hảo (đúng 50 Vuln, 50 Safe, seed 42)
    3. 100% sample IDs là duy nhất (không trùng lặp nội bộ)
    4. Không giao cắt với blacklist rò rỉ mã và mâu thuẫn nhãn
    5. load_canonical_dev_split nạp đầy đủ mã nguồn (func không bị rỗng) cho 100% mẫu.
    """
    import json
    from scripts.run_label_flip_test import load_canonical_dev_split
    from scripts.prepare_canonical_dev_split import load_leakage_audit_blacklist

    leakage_report_path = repo_root / "project_docs" / "reports" / "code_leakage_audit_report.json"
    blacklist = load_leakage_audit_blacklist(leakage_report_path)

    split_configs = [
        ("devign", repo_root / "data" / "splits" / "devign_dev_clean_100_ids.json"),
        ("reveal", repo_root / "data" / "splits" / "reveal_dev_clean_100_ids.json")
    ]

    for ds_name, split_path in split_configs:
        assert split_path.exists(), f"File split {split_path} bắt buộc phải tồn tại!"
        with open(split_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["total_samples"] == 100, f"Tổng số mẫu {ds_name} phải đúng 100!"
        assert data["vulnerable_count"] == 50, f"Số mẫu Vuln {ds_name} phải đúng 50!"
        assert data["safe_count"] == 50, f"Số mẫu Safe {ds_name} phải đúng 50!"
        assert data["seed"] == 42, f"Seed {ds_name} phải đúng 42!"

        sample_ids = data["sample_ids"]
        assert len(sample_ids) == 100, "sample_ids phải có đúng 100 phần tử"
        assert len(set(sample_ids)) == 100, f"Tập {ds_name} chứa ID trùng lặp nội bộ!"

        # Kiểm tra không giao cắt với blacklist rò rỉ
        for sid in sample_ids:
            assert str(sid) not in blacklist, f"ID {sid} trong tập {ds_name} bị rò rỉ/nằm trong blacklist kiểm toán!"

        # Kiểm tra nạp dữ liệu thực tế và đảm bảo mã nguồn và đồ thị CPG không rỗng
        loaded_samples = load_canonical_dev_split(split_path)
        assert len(loaded_samples) == 100, f"load_canonical_dev_split phải nạp đủ 100 mẫu cho {ds_name}!"
        for idx, s in enumerate(loaded_samples):
            assert len(s["func"]) > 0, f"Mẫu {s['id']} (chỉ số {idx}) của {ds_name} có mã nguồn bị rỗng!"
            assert s["target"] in (0, 1), f"Target của mẫu {s['id']} phải là 0 hoặc 1!"
            assert len(s.get("nodes", [])) > 0, f"Mẫu {s['id']} (chỉ số {idx}) của {ds_name} thiếu thông tin nodes đồ thị CPG!"
            assert len(s.get("edges", [])) > 0, f"Mẫu {s['id']} (chỉ số {idx}) của {ds_name} thiếu thông tin edges đồ thị CPG!"

        # Rào chắn kiểm thử cứng: Xác nhận trực tiếp dữ liệu trên đĩa đã được cập nhật nodes và edges vĩnh viễn
        with open(split_path, "r", encoding="utf-8") as f_disk:
            disk_data = json.load(f_disk)
        for item in disk_data.get("sample_details", []):
            assert "nodes" in item and len(item["nodes"]) > 0, f"Mẫu {item['id']} ({ds_name}) chưa được lưu nodes trên đĩa!"
            assert "edges" in item and len(item["edges"]) > 0, f"Mẫu {item['id']} ({ds_name}) chưa được lưu edges trên đĩa!"


