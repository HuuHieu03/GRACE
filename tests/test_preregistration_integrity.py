#!/usr/bin/env python3
"""Kiểm thử tự động toàn diện cho Bước 4: Preregistration Integrity & Contract Compliance.

Xác nhận tính toàn vẹn, tính nhất quán và tính bất biến của Giao thức Đăng ký trước:
1. Xác nhận định danh mô hình (Provenance): Qwen3-Coder-30B-A3B-Instruct (UD-Q4_K_XL, 16.45 GB, llama-server, --n_ctx 8192, Kaggle GPU 2x T4).
2. Xác nhận loại bỏ hoàn toàn các vết sót cũ về mô hình 7B Q4_K_M trong tài liệu preregistration và cấu hình protocol.
3. Xác nhận định nghĩa đơn vị gom nhóm (cluster units): Devign (commit_id, 2068 cụm) và ReVeal (file_hash, 646 cụm).
4. Xác nhận khóa chặt chẽ các giả thuyết khoa học: H1.1, H1.2, H5.3 (routing q=10% paired bootstrap CI) và quy tắc quyết định với biên thực chất delta = 0.02.
5. Xác nhận đồng bộ 14 ngưỡng tối ưu tau* khóa từ Validation trong configs/thresholds.json và configs/thresholds_flat.json.
6. Xác nhận tính đồng bộ tuyệt đối giữa configs/protocol.yaml và grace_diag_kit/configs/protocol.yaml.
7. Xác nhận chữ ký băm SHA-256 của protocol.yaml khớp hoàn toàn với metadata trong thresholds.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PREREG_MD = REPO_ROOT / "preregistration.md"
PROTOCOL_ROOT = REPO_ROOT / "configs" / "protocol.yaml"
PROTOCOL_KIT = REPO_ROOT / "grace_diag_kit" / "configs" / "protocol.yaml"
THRESHOLDS_JSON = REPO_ROOT / "configs" / "thresholds.json"
THRESHOLDS_FLAT = REPO_ROOT / "configs" / "thresholds_flat.json"


def test_preregistration_document_provenance():
    """Kiểm tra tài liệu preregistration.md chứa đầy đủ thông số Provenance chuẩn hóa của Qwen3-Coder-30B."""
    assert PREREG_MD.exists(), "Tệp preregistration.md không tồn tại!"
    text = PREREG_MD.read_text(encoding="utf-8")

    # 1. Provenance mô hình mục tiêu
    assert "Qwen3-Coder-30B-A3B-Instruct" in text, "Thiếu định danh mô hình Qwen3-Coder-30B-A3B-Instruct!"
    assert "UD-Q4_K_XL" in text, "Thiếu định dạng lượng tử hóa UD-Q4_K_XL!"
    assert "16.45 GB" in text, "Thiếu dung lượng mô hình 16.45 GB!"
    assert "llama-server" in text, "Thiếu serving backend llama-server!"
    assert "--n_ctx 8192" in text, "Thiếu tham số context length --n_ctx 8192!"
    assert "Kaggle" in text, "Thiếu môi trường Kaggle!"
    assert "Tesla T4" in text, "Thiếu cấu hình phần cứng Tesla T4!"

    # 2. Không còn tồn dư 7B hoặc Q4_K_M trong preregistration.md
    assert "7B" not in text, "Vẫn còn vết sót mô hình 7B trong preregistration.md!"
    assert "Q4_K_M" not in text, "Vẫn còn vết sót lượng tử hóa Q4_K_M trong preregistration.md!"


def test_preregistration_cluster_units():
    """Kiểm tra đơn vị gom nhóm (cluster units) được định nghĩa chuẩn xác theo Bước 0."""
    text = PREREG_MD.read_text(encoding="utf-8")
    assert "commit_id" in text, "Thiếu định danh commit_id cho Devign!"
    assert "2,068" in text or "2068" in text, "Thiếu số lượng 2,068 clusters cho Devign!"
    assert "file_hash" in text or "File-level Hashes" in text, "Thiếu định danh file_hash cho ReVeal!"
    assert "646" in text, "Thiếu số lượng 646 clusters cho ReVeal!"


def test_preregistration_hypotheses_and_decision_rules():
    """Kiểm tra khóa chặt chẽ các giả thuyết H1.1, H1.2, H5.3 và quy tắc biên thực chất delta = 0.02."""
    text = PREREG_MD.read_text(encoding="utf-8")

    # Giả thuyết
    assert "H1.1" in text
    assert "H1.2" in text
    assert "H5.3" in text
    assert "Benefit Router" in text or "benefit-router" in text
    assert "Confidence Router" in text or "confidence" in text
    assert "Paired Bootstrap CI" in text or "paired bootstrap" in text

    # Tiêu chuẩn phán quyết
    assert "benefit" in text
    assert "no_meaningful_benefit" in text
    assert "harm" in text
    assert "inconclusive" in text
    assert "0.02" in text, "Thiếu biên thực chất khoa học delta = 0.02!"


def test_protocol_yaml_consistency_and_provenance():
    """Kiểm tra tính nhất quán giữa protocol.yaml ở configs/ và grace_diag_kit/configs/."""
    assert PROTOCOL_ROOT.exists(), "configs/protocol.yaml không tồn tại!"
    assert PROTOCOL_KIT.exists(), "grace_diag_kit/configs/protocol.yaml không tồn tại!"

    content_root = PROTOCOL_ROOT.read_text(encoding="utf-8")
    content_kit = PROTOCOL_KIT.read_text(encoding="utf-8")
    assert content_root == content_kit, "Hai tệp protocol.yaml không đồng nhất 100%!"

    proto = yaml.safe_load(content_root)
    assert proto["study_id"] == "grace_diag_replication_v1"
    assert proto["version"] == "prereg-v1"

    # Backend
    backend = proto["backend"]
    assert backend["primary_model"] == "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    assert "Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf" in backend["quantization_note"]
    assert "--n_ctx 8192" in backend["quantization_note"]

    # Cluster units
    stats = proto["stats"]
    assert stats["n_boot"] == 5000
    assert stats["bootstrap_seed"] == 20261117
    assert "2,068" in str(stats["cluster_unit"]) or "2068" in str(stats["cluster_unit"])
    assert "646" in str(stats["cluster_unit"])

    # Margins
    margins = stats["margins"]
    assert margins["routing"] == 0.02
    assert margins["auroc"] == 0.02
    assert margins["mcc"] == 0.03

    # Primary contrasts
    contrast_names = [c["name"] for c in proto["primary_contrasts"]]
    assert "H1.1" in contrast_names
    assert "H1.2" in contrast_names
    assert "H5.3" in contrast_names


def test_thresholds_json_synchronization():
    """Kiểm tra tính toàn vẹn của bảng 14 ngưỡng tối ưu tau* khóa từ Validation."""
    assert THRESHOLDS_JSON.exists(), "configs/thresholds.json không tồn tại!"
    assert THRESHOLDS_FLAT.exists(), "configs/thresholds_flat.json không tồn tại!"

    data = json.loads(THRESHOLDS_JSON.read_text(encoding="utf-8"))
    flat = json.loads(THRESHOLDS_FLAT.read_text(encoding="utf-8"))

    meta = data["metadata"]
    assert meta["study_id"] == "grace_diag_replication_v1"
    assert meta["version"] == "prereg-v1"
    assert meta["optimized_on_split"] == "validation"
    assert "STRICTLY_NONE" in meta["test_exposure"]
    assert meta["total_thresholds_locked"] == 14

    thresholds = data["thresholds"]
    assert len(thresholds) == 14, f"Mong đợi 14 ngưỡng nhưng có {len(thresholds)}"
    assert len(flat) == 14, f"Mong đợi 14 flat ngưỡng nhưng có {len(flat)}"

    # 14 keys cụ thể
    expected_keys = [
        "devign|B0|42",
        "devign|B1|42",
        "devign|B2|42",
        "devign|B2-flip|42",
        "devign|B2-rep|42",
        "reveal|B0|42",
        "reveal|B1|42",
        "reveal|B2|42",
        "reveal|B2-flip|42",
        "reveal|B2-rep|42",
        "devign|P-PRE|42",
        "devign|P-POST|42",
        "reveal|P-PRE|42",
        "reveal|P-POST|42",
    ]
    for k in expected_keys:
        assert k in thresholds, f"Thiếu key {k} trong thresholds.json!"
        assert k in flat, f"Thiếu key {k} trong thresholds_flat.json!"
        assert thresholds[k] == pytest.approx(flat[k], abs=1e-6)
        assert 0.01 <= thresholds[k] <= 0.99

    # Kiểm tra chữ ký băm protocol_sha256
    expected_sha = hashlib.sha256(PROTOCOL_ROOT.read_bytes()).hexdigest()
    assert meta["protocol_sha256"] == expected_sha, (
        f"Chữ ký protocol_sha256 trong thresholds.json ({meta['protocol_sha256']}) "
        f"không khớp với SHA-256 thực tế của protocol.yaml ({expected_sha})!"
    )
