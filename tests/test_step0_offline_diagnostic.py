"""Unit tests cho pipeline phân tích chẩn đoán Bước 0 (scripts/run_step0_offline_diagnostic.py)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.generate_step0_mock_data import generate_all_step0_mock_data, generate_mock_step0_data
from scripts.run_step0_offline_diagnostic import resolve_cluster_unit, run_offline_diagnostic


@pytest.fixture(scope="module")
def mock_dataset_dir(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("test_step0_mock")
    data_files = generate_mock_step0_data(
        output_dir=temp_dir,
        n_samples=50,
        dataset="devign",
        seed=123,
        invalid_rate=0.06,
        generate_2split=True,
    )
    return temp_dir, data_files


def test_mock_data_generation(mock_dataset_dir):
    temp_dir, files = mock_dataset_dir
    # Kiểm tra single split files
    assert files["gate_csv"].exists()
    assert files["llm_jsonl"].exists()
    assert files["xpre_npz"].exists()

    npz = np.load(files["xpre_npz"])
    assert "X" in npz
    assert npz["X"].shape == (50, 34)
    assert len(npz["ids"]) == 50

    # Kiểm tra 2-split files
    assert files["gate_val"].exists()
    assert files["gate_test"].exists()
    assert files["llm_val"].exists()
    assert files["llm_test"].exists()
    assert files["xpre_val"].exists()
    assert files["xpre_test"].exists()

    npz_val = np.load(files["xpre_val"])
    assert npz_val["X"].shape == (50, 34)
    npz_test = np.load(files["xpre_test"])
    assert npz_test["X"].shape == (50, 34)


def test_generate_all_step0_mock_data(tmp_path):
    mock_dir = tmp_path / "all_mock"
    all_files = generate_all_step0_mock_data(output_dir=mock_dir, n_val=20, n_test=20, seed=42)
    assert "devign" in all_files
    assert "reveal" in all_files

    for ds in ["devign", "reveal"]:
        assert all_files[ds]["gate_val"].exists()
        assert all_files[ds]["gate_test"].exists()
        assert all_files[ds]["llm_val"].exists()
        assert all_files[ds]["llm_test"].exists()
        assert all_files[ds]["xpre_val"].exists()
        assert all_files[ds]["xpre_test"].exists()


def test_offline_diagnostic_2split_pipeline(mock_dataset_dir, tmp_path):
    """Kiểm tra luồng chuẩn 2-Split (Validation fit meta-model, Test áp mô hình độc lập)."""
    _, files = mock_dataset_dir
    out_dir = tmp_path / "runs_test_2split"

    report_dict, json_path, md_path = run_offline_diagnostic(
        gate_val_path=files["gate_val"],
        gate_test_path=files["gate_test"],
        llm_val_path=files["llm_val"],
        llm_test_path=files["llm_test"],
        xpre_val_path=files["xpre_val"],
        xpre_test_path=files["xpre_test"],
        dataset="devign",
        tau=0.5,
        output_dir=out_dir,
        seed=42,
        n_boot=200,
        n_folds=3,
    )

    assert json_path.exists()
    assert md_path.exists()

    # Canonical files cho cả 2 split
    assert (out_dir / "canonical_devign_val.csv").exists()
    assert (out_dir / "canonical_devign_test.csv").exists()

    # Kiểm tra metadata và chế độ 2-split
    assert report_dict["metadata"]["evaluation_mode"] == "2_split"
    assert report_dict["metadata"]["n_samples_val"] == 50
    assert report_dict["metadata"]["n_samples_test"] == 50
    assert report_dict["metadata"]["n_samples"] == 50

    # Kiểm tra verdict và matched meta-model
    assert "verdict" in report_dict
    assert "delta_mcc" in report_dict["verdict"]
    assert "delta_f1" in report_dict["verdict"]
    assert "delta_auroc" in report_dict["verdict"]

    meta_m = report_dict["matched_meta_model"]
    assert meta_m["evaluation_split"] == "test"
    assert meta_m["threshold_origin"] == "validation_oof"
    assert "validation_oof" in meta_m
    assert "metrics_pre" in meta_m
    assert "metrics_post" in meta_m

    # Kiểm tra ma trận Sửa/Hỏng, tham chiếu, oracle
    assert "repair_harm_matrix" in report_dict
    assert "reference_experts" in report_dict
    assert "oracle_ceiling" in report_dict
    assert "mcnemar_tests" in report_dict

    # Kiểm tra selective routing curves có đủ các chính sách định tuyến
    routing_rows = report_dict["selective_routing_curves"]
    policies = {r["policy"] for r in routing_rows}
    assert "gate_only" in policies
    assert "full_expert_with_fallback" in policies
    assert "confidence" in policies
    assert "benefit" in policies
    assert "oracle" in policies
    assert "random" in policies

    # Kiểm tra markdown có đúng định dạng và chứa thông tin 2-split
    md_text = md_path.read_text(encoding="utf-8")
    assert "# BÁO CÁO CHẨN ĐOÁN OFFLINE BƯỚC 0" in md_text
    assert "Chuẩn 2-Split Độc lập" in md_text
    assert "Validation Split" in md_text
    assert "Định tuyến theo Ngân sách" in md_text


def test_offline_diagnostic_2split_fallback_noxpre(mock_dataset_dir, tmp_path):
    """Kiểm tra luồng 2-Split khi không có ma trận đặc trưng nền X_pre (tự fallback logit p_gate)."""
    _, files = mock_dataset_dir
    out_dir = tmp_path / "runs_test_2split_noxpre"

    report_dict, json_path, md_path = run_offline_diagnostic(
        gate_val_path=files["gate_val"],
        gate_test_path=files["gate_test"],
        llm_val_path=files["llm_val"],
        llm_test_path=files["llm_test"],
        xpre_val_path=None,
        xpre_test_path=None,
        dataset="devign",
        tau=0.5,
        output_dir=out_dir,
        seed=42,
        n_boot=100,
        n_folds=2,
    )

    assert json_path.exists()
    assert md_path.exists()
    assert report_dict["metadata"]["evaluation_mode"] == "2_split"


def test_offline_diagnostic_single_split_fallback(mock_dataset_dir, tmp_path):
    """Kiểm tra tính tương thích ngược với chế độ Single-Split."""
    _, files = mock_dataset_dir
    out_dir = tmp_path / "runs_test_single_split"

    report_dict, json_path, md_path = run_offline_diagnostic(
        gate_csv_path=files["gate_csv"],
        llm_path=files["llm_jsonl"],
        xpre_path=files["xpre_npz"],
        dataset="devign",
        tau=0.5,
        output_dir=out_dir,
        seed=42,
        n_boot=100,
        n_folds=2,
    )

    assert json_path.exists()
    assert md_path.exists()
    assert report_dict["metadata"]["evaluation_mode"] == "single_split_fallback"
    assert report_dict["metadata"]["n_samples"] == 50


def test_offline_diagnostic_string_paths(mock_dataset_dir, tmp_path):
    """Kiểm tra truyền đối số đường dẫn dưới dạng chuỗi (str) thay vì Path."""
    _, files = mock_dataset_dir
    out_dir = str(tmp_path / "runs_str_paths")

    report_dict, json_path, md_path = run_offline_diagnostic(
        gate_val_path=str(files["gate_val"]),
        gate_test_path=str(files["gate_test"]),
        llm_val_path=str(files["llm_val"]),
        llm_test_path=str(files["llm_test"]),
        xpre_val_path=str(files["xpre_val"]),
        xpre_test_path=str(files["xpre_test"]),
        dataset="devign",
        tau=0.5,
        output_dir=out_dir,
        seed=42,
        n_boot=100,
        n_folds=2,
    )

    assert json_path.exists()
    assert md_path.exists()
    assert report_dict["metadata"]["evaluation_mode"] == "2_split"
    # Kiểm tra tính nhất quán của ngưỡng
    meta = report_dict["matched_meta_model"]
    assert meta["tau_pre"] is not None
    assert meta["tau_post"] is not None


def test_resolve_cluster_unit_logic():
    """Kiểm tra logic phân giải đơn vị bootstrap theo protocol.yaml dòng 55."""
    # 1. Không có group -> luôn là sample
    g, unit = resolve_cluster_unit(None, cluster_unit="auto")
    assert g is None and unit == "sample"

    # 2. Ít hơn 10 nhóm duy nhất (ví dụ ReVeal có 2 dự án debian/chrome)
    reveal_groups = ["debian", "chrome"] * 10
    g_auto, unit_auto = resolve_cluster_unit(reveal_groups, cluster_unit="auto")
    assert g_auto is None and unit_auto == "sample"

    g_commit, unit_commit = resolve_cluster_unit(reveal_groups, cluster_unit="commit")
    assert g_commit is not None and "cluster" in unit_commit

    g_sample, unit_sample = resolve_cluster_unit(reveal_groups, cluster_unit="sample")
    assert g_sample is None and unit_sample == "sample"

    # 3. >= 10 nhóm duy nhất (ví dụ Devign có commit IDs)
    devign_groups = [f"commit_{i}" for i in range(50)]
    g_auto_d, unit_auto_d = resolve_cluster_unit(devign_groups, cluster_unit="auto")
    assert g_auto_d is not None and "cluster" in unit_auto_d

    g_commit_d, unit_commit_d = resolve_cluster_unit(devign_groups, cluster_unit="commit")
    assert g_commit_d is not None and "cluster" in unit_commit_d

    g_sample_d, unit_sample_d = resolve_cluster_unit(devign_groups, cluster_unit="sample")
    assert g_sample_d is None and unit_sample_d == "sample"

    # 4. Kiểm tra xử lý khoảng trắng và chữ hoa chữ thường
    g_ws, unit_ws = resolve_cluster_unit(devign_groups, cluster_unit="  COMMIT  ")
    assert g_ws is not None and "cluster" in unit_ws

    # 5. Tham số không hợp lệ -> ném ValueError
    with pytest.raises(ValueError, match="cluster_unit"):
        resolve_cluster_unit(devign_groups, cluster_unit="invalid_unit")


def test_offline_diagnostic_cluster_unit_argument(mock_dataset_dir, tmp_path):
    """Kiểm tra việc tích hợp tham số cluster_unit trong pipeline 2-split."""
    _, files = mock_dataset_dir
    out_dir = tmp_path / "runs_cluster_unit_test"

    report_dict, json_path, md_path = run_offline_diagnostic(
        gate_val_path=files["gate_val"],
        gate_test_path=files["gate_test"],
        llm_val_path=files["llm_val"],
        llm_test_path=files["llm_test"],
        xpre_val_path=files["xpre_val"],
        xpre_test_path=files["xpre_test"],
        dataset="devign",
        tau=0.5,
        output_dir=out_dir,
        seed=20261117,
        n_boot=100,
        n_folds=2,
        cluster_unit="sample",
    )

    assert json_path.exists()
    assert report_dict["metadata"]["cluster_unit_arg"] == "sample"
    assert report_dict["metadata"]["bootstrap_unit"] == "sample"
    md_text = md_path.read_text(encoding="utf-8")
    assert "Sample Bootstrap" in md_text


