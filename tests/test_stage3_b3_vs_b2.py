"""
Unit Tests cho Đợt 3: Đối Đầu B3 (Contrastive Demonstration ICL) vs B2 (Baseline)
Tuân thủ Hợp đồng Đánh giá: evaluation_contract.yaml
"""

import pytest
import numpy as np
from pathlib import Path

repo_root = Path(__file__).parent.parent.resolve()
src_dir = repo_root / "src"
scripts_dir = repo_root / "scripts"

import sys
for p in [str(repo_root), str(src_dir), str(scripts_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from prompt_engine import build_contrastive_prompt, build_grace_prompt
from retrieval_security_engine import SecurityAwareRetriever
from contrastive_selector import ContrastiveDemonstrationSelector, ContrastivePair
from data_loader import generate_mock_dataset
from scripts.run_stage3_b3_vs_b2 import (
    compute_mcnemar_test,
    compute_paired_bootstrap_ci,
    run_stage3_experiment,
    MockStage3LLM
)


def test_b3_contrastive_prompt_contract_compliance():
    """
    Kiểm tra tính tuân thủ 100% của Prompt B3 đối với evaluation_contract.yaml:
    - Target Code <= 3000 ký tự
    - Target CPG <= 25 nodes, <= 25 edges
    - Vulnerable Demo <= 1200 ký tự
    - Safe Demo <= 1200 ký tự
    - Có phần phân tích khác biệt an ninh cốt lõi (CORE SECURITY DIFFERENCE)
    - Output format: ONLY '1' if Vulnerable, or '0' if Non-vulnerable.
    """
    long_code = "int func() {\n" + "    char buf[1024];\n" * 200 + "}\n"
    nodes = [{"id": i, "type": "AST_NODE", "code": f"n_{i}"} for i in range(50)]
    edges = [{"start": i, "end": i + 1, "type": "CFG"} for i in range(50)]

    sample = {
        "id": "query_test_01",
        "func": long_code,
        "nodes": nodes,
        "edges": edges,
        "contrastive_pair": {
            "vulnerable": {
                "id": "demo_vuln_1",
                "func": "void bad_copy() {\n" + "    char d[10];\n" * 150 + "}\n",
                "target": 1
            },
            "safe": {
                "id": "demo_safe_1",
                "func": "void good_copy() {\n" + "    char d[10]; if (l <= 10) memcpy();\n" * 150 + "}\n",
                "target": 0
            },
            "security_difference": "Safe demo contains sanitization guards (bounds_check) absent in Vulnerable demo"
        }
    }

    prompt = build_contrastive_prompt(sample, invert_order=False)

    # 1. Target code truncated to <= 3000 chars
    assert "/* [TRUNCATED TO PREVENT MEMORY OVERFLOW] */" in prompt
    target_part = prompt.split("--- TARGET CODE ---")[1].split("--- TARGET GRAPH STRUCTURE ---")[0]
    assert len(target_part) < 3200

    # 2. Graph truncated to 25 nodes and 25 edges
    assert "Node 24:" in prompt
    assert "Node 25:" not in prompt
    assert "Edge: Node 24 ->" in prompt
    assert "Edge: Node 25 ->" not in prompt

    # 3. Demos truncated to <= 1200 chars
    assert "/* [TRUNCATED TO PRESERVE CONTEXT] */" in prompt

    # 4. Core Security Difference
    assert "--- CORE SECURITY DIFFERENCE ---" in prompt
    assert "bounds_check" in prompt

    # 5. Output format requirement
    assert "### OUTPUT FORMAT REQUIREMENT" in prompt
    assert "You must output ONLY a single character: '1' if Vulnerable, or '0' if Non-vulnerable." in prompt


def test_b3_contrastive_prompt_inverted_order():
    """Kiểm tra chế độ invert_order để đo độ nhạy trật tự ví dụ mẫu."""
    sample = {
        "id": "query_test_02",
        "func": "int test_fn() { return 0; }",
        "nodes": [{"id": 0, "type": "FunctionDef"}],
        "edges": [{"start": 0, "end": 0, "type": "CFG"}],
        "contrastive_pair": {
            "vulnerable": {"id": "v1", "func": "void v(){ gets(b); }", "target": 1},
            "safe": {"id": "s1", "func": "void s(){ fgets(b, 10, f); }", "target": 0},
            "security_difference": "Safe uses fgets instead of gets"
        }
    }

    prompt_std = build_contrastive_prompt(sample, invert_order=False)
    prompt_inv = build_contrastive_prompt(sample, invert_order=True)

    # Prompt std: Vuln is Example 1, Safe is Example 2
    assert prompt_std.find("--- EXAMPLE 1 (VULNERABLE REFERENCE) ---") < prompt_std.find("--- EXAMPLE 2 (SAFE / NON-VULNERABLE REFERENCE) ---")

    # Prompt inv: Safe is Example 1, Vuln is Example 2
    assert prompt_inv.find("--- EXAMPLE 1 (SAFE / NON-VULNERABLE REFERENCE) ---") < prompt_inv.find("--- EXAMPLE 2 (VULNERABLE REFERENCE) ---")


def test_mcnemar_statistical_test_computation():
    """Kiểm tra tính toán chuẩn xác của kiểm định McNemar."""
    # Giả lập 100 mẫu:
    # 50 mẫu cả 2 cùng đúng, 10 mẫu cả 2 cùng sai
    # 30 mẫu B3 đúng / B2 sai (b = 30)
    # 10 mẫu B2 đúng / B3 sai (c = 10)
    y_true = [1] * 50 + [0] * 50
    # Cả 2 đúng: 50 mẫu (chỉ số 0..49) -> pb2 = 1, pb3 = 1
    # B3 đúng, B2 sai: 30 mẫu (chỉ số 50..79, yt=0) -> pb2 = 1, pb3 = 0
    # B2 đúng, B3 sai: 10 mẫu (chỉ số 80..89, yt=0) -> pb2 = 0, pb3 = 1
    # Cả 2 sai: 10 mẫu (chỉ số 90..99, yt=0) -> pb2 = 1, pb3 = 1
    y_pred_b2 = [1] * 50 + [1] * 30 + [0] * 10 + [1] * 10
    y_pred_b3 = [1] * 50 + [0] * 30 + [1] * 10 + [1] * 10

    res = compute_mcnemar_test(y_true, y_pred_b2, y_pred_b3)

    ct = res["contingency_table"]
    assert ct["both_correct"] == 50
    assert ct["b3_correct_b2_wrong"] == 30
    assert ct["b2_correct_b3_wrong"] == 10
    assert ct["both_wrong"] == 10
    assert ct["total_discordant"] == 40

    # (|30 - 10| - 1)^2 / 40 = 19^2 / 40 = 361 / 40 = 9.025
    assert abs(res["chi2_statistic"] - 9.025) < 0.01
    assert res["is_significant_p05"] is True
    assert res["is_significant_p01"] is True


def test_paired_bootstrap_confidence_interval():
    """Kiểm tra rút mẫu có hoàn lại 2000 lần (Paired Bootstrap 95% CI)."""
    y_true = [1] * 50 + [0] * 50
    # B3 vượt trội hơn B2: B3 đoán đúng 80%, B2 đoán đúng 50%
    y_pred_b2 = [1] * 25 + [0] * 25 + [1] * 25 + [0] * 25
    y_pred_b3 = [1] * 45 + [0] * 5 + [0] * 40 + [1] * 10

    boot_res = compute_paired_bootstrap_ci(y_true, y_pred_b2, y_pred_b3, n_resamples=500, seed=42)

    assert "delta_f1" in boot_res
    assert "delta_mcc" in boot_res
    assert "delta_balanced_accuracy" in boot_res
    assert boot_res["delta_f1"]["mean"] > 0
    assert boot_res["delta_f1"]["ci_95"][0] < boot_res["delta_f1"]["ci_95"][1]


def test_mock_stage3_llm_logic():
    """Kiểm tra hoạt động của MockStage3LLM cho cả B2 và B3."""
    mock = MockStage3LLM(seed=42)

    # Prompt B3 chứa strcpy nhưng không có guard
    prompt_vuln_b3 = (
        "### TASK INSTRUCTION\n"
        "### CONTRASTIVE DEMONSTRATION EXAMPLES\n"
        "Label: Vulnerable (1)\nLabel: Non-vulnerable (0)\n"
        "### TARGET QUERY FOR EVALUATION\n"
        "void bad(char *src) { char dest[10]; strcpy(dest, src); }\n"
        "### OUTPUT FORMAT REQUIREMENT\n"
    )
    resp = mock.generate_response(prompt_vuln_b3)
    assert resp == "1"

    # Prompt B3 chứa memcpy kèm bounds check guard
    prompt_safe_b3 = (
        "### TASK INSTRUCTION\n"
        "### CONTRASTIVE DEMONSTRATION EXAMPLES\n"
        "Label: Vulnerable (1)\nLabel: Non-vulnerable (0)\n"
        "### TARGET QUERY FOR EVALUATION\n"
        "void good(char *src, int len) { char dest[10]; if (len <= sizeof(dest)) memcpy(dest, src, len); }\n"
        "### OUTPUT FORMAT REQUIREMENT\n"
    )
    resp_safe = mock.generate_response(prompt_safe_b3)
    assert resp_safe == "0"


def test_stage3_e2e_mock_experiment(tmp_path):
    """Kiểm tra toàn bộ pipeline đối đầu B3 vs B2 chạy thành công với Mock LLM."""
    mock_train = generate_mock_dataset(num_samples=20)
    mock_dev = generate_mock_dataset(num_samples=6)

    # Lưu tạm mock_dev split ra file json
    import json
    dev_split_file = tmp_path / "test_dev_split.json"
    with open(dev_split_file, "w", encoding="utf-8") as f:
        json.dump({
            "dataset": "devign",
            "total_samples": len(mock_dev),
            "sample_details": [
                {
                    "id": f"dev_{i}",
                    "func": s.get("func", ""),
                    "target": s.get("target", 0),
                    "nodes": s.get("node", [{"id": 0, "type": "Func"}]),
                    "edges": s.get("edge", [{"start": 0, "end": 0, "type": "CFG"}])
                }
                for i, s in enumerate(mock_dev)
            ]
        }, f)

    out_file = tmp_path / "stage3_report.json"

    # Chạy experiment với use_mock=True
    report = run_stage3_experiment(
        dev_split_file=dev_split_file,
        dataset_name="devign",
        output_path=out_file,
        use_mock=True,
        use_fallback_embedder=True,
        max_samples=6,
        max_train_samples=20
    )

    assert out_file.exists()
    assert "b2_baseline" in report
    assert "b3_contrastive" in report
    assert "head_to_head_delta" in report
    assert "mcnemar_test" in report
    assert "paired_bootstrap_95_ci" in report
    assert "label_sensitivity_comparison" in report


def test_stage3_e2e_reveal_mock_experiment(tmp_path):
    """Kiểm tra toàn bộ pipeline đối đầu B3 vs B2 chạy thành công với dataset ReVeal."""
    reveal_split_file = repo_root / "data" / "splits" / "reveal_dev_clean_100_ids.json"
    reveal_train_cpg = repo_root / "data" / "processed" / "reveal_train_compact_cpg.json.gz"

    assert reveal_split_file.exists(), "Tập kiểm thử sạch ReVeal phải tồn tại"
    assert reveal_train_cpg.exists(), "Kho train compact CPG của ReVeal phải tồn tại"

    out_file = tmp_path / "stage3_reveal_report.json"

    # Chạy experiment với use_mock=True, giới hạn 6 mẫu kiểm thử và 20 mẫu train
    report = run_stage3_experiment(
        dev_split_file=reveal_split_file,
        dataset_name="reveal",
        output_path=out_file,
        use_mock=True,
        use_fallback_embedder=True,
        max_samples=6,
        max_train_samples=20
    )

    assert out_file.exists()
    assert report["metadata"]["dataset"] == "reveal"
    assert "b2_baseline" in report
    assert "b3_contrastive" in report
    assert "head_to_head_delta" in report
    assert "mcnemar_test" in report
    assert "paired_bootstrap_95_ci" in report


def test_reveal_train_compact_cpg_validity():
    """Kiểm tra tính hợp lệ và cấu trúc của file kho huấn luyện ReVeal compact CPG."""
    import gzip
    import json
    cpg_gz = repo_root / "data" / "processed" / "reveal_train_compact_cpg.json.gz"
    assert cpg_gz.exists(), "File reveal_train_compact_cpg.json.gz phải tồn tại"
    assert cpg_gz.stat().st_size > 1024 * 1024, "File nén compact CPG phải > 1 MB"

    with gzip.open(cpg_gz, "rt", encoding="utf-8") as f:
        samples = json.load(f)

    assert len(samples) > 1000, f"Kho huấn luyện ReVeal phải có > 1000 mẫu, thực tế: {len(samples)}"
    for s in samples[:20]:
        assert "id" in s and s["id"]
        assert "func" in s and s["func"]
        assert "target" in s and s["target"] in (0, 1)
        assert "nodes" in s and isinstance(s["nodes"], list)
        assert "edges" in s and isinstance(s["edges"], list)


def test_reveal_dev_split_validity():
    """Kiểm tra tập kiểm thử ReVeal 100 mẫu sạch có đầy đủ mã nguồn C và đồ thị CPG."""
    import json
    split_p = repo_root / "data" / "splits" / "reveal_dev_clean_100_ids.json"
    assert split_p.exists()
    with open(split_p, "r", encoding="utf-8") as f:
        data = json.load(f)
    samples = data.get("sample_details", [])
    assert len(samples) == 100, f"Phải có 100 mẫu kiểm thử, thực tế: {len(samples)}"
    for idx, s in enumerate(samples):
        func_code = s.get("func") or s.get("code") or ""
        assert len(func_code) > 0, f"Mẫu {s.get('id')} ở vị trí {idx} thiếu mã nguồn C!"
        assert len(s.get("nodes", [])) > 0, f"Mẫu {s.get('id')} thiếu CPG nodes!"
        assert len(s.get("edges", [])) > 0, f"Mẫu {s.get('id')} thiếu CPG edges!"


def test_stage3_kaggle_notebook_supports_reveal():
    """Kiểm tra Kaggle notebook stage3_b3_vs_b2_kaggle.ipynb cấu hình hỗ trợ ReVeal."""
    import json
    nb_path = repo_root / "kaggle_notebooks" / "stage3_b3_vs_b2" / "stage3_b3_vs_b2_kaggle.ipynb"
    assert nb_path.exists(), f"Notebook {nb_path} phải tồn tại"

    with open(nb_path, "r", encoding="utf-8") as f:
        nb_data = json.load(f)

    assert "cells" in nb_data and len(nb_data["cells"]) >= 7

    # Tìm các chuỗi khóa trong notebook
    all_text = " ".join("".join(c.get("source", [])) for c in nb_data["cells"])
    assert "reveal" in all_text.lower()
    assert "reveal_dev_clean_100_ids.json" in all_text
    assert "reveal_train_compact_cpg.json.gz" in all_text
    assert "--dataset" in all_text
    assert "--dev_split" in all_text

