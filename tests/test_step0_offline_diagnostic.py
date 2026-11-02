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


def test_stratified_group_kfold_fit_pre_post():
    """Kiểm tra fit_pre_post sử dụng StratifiedGroupKFold khi có groups và fallback khi groups None."""
    from grace_diag import complementarity as C
    rng = np.random.default_rng(42)
    n = 60
    y = np.array([0, 1] * 30)
    X = rng.normal(size=(n, 5))
    p = np.clip(1 / (1 + np.exp(-X[:, 0])), 0.01, 0.99)
    s = np.clip(1 / (1 + np.exp(-X[:, 1])), 0.01, 0.99)
    v = np.ones(n, dtype=bool)

    # 1. Có groups với 6 nhóm duy nhất
    groups = np.repeat(np.arange(6), 10)
    res_group = C.fit_pre_post(X, s, v, p, y, n_folds=3, seed=42, n_boot=50, groups=groups)
    assert res_group.oof_pre.shape == (n,)
    assert res_group.oof_post.shape == (n,)
    assert res_group.delta_mcc.unit == "cluster"

    # 2. Không có groups (None) -> fallback StratifiedKFold
    res_nogroup = C.fit_pre_post(X, s, v, p, y, n_folds=3, seed=42, n_boot=50, groups=None)
    assert res_nogroup.oof_pre.shape == (n,)
    assert res_nogroup.delta_mcc.unit == "sample"

    # 3. Số nhóm không đủ (< n_folds) -> fallback StratifiedKFold
    small_groups = np.repeat(np.array([0, 1]), 30)
    res_small = C.fit_pre_post(X, s, v, p, y, n_folds=3, seed=42, n_boot=50, groups=small_groups)
    assert res_small.oof_pre.shape == (n,)


def test_reveal_file_hash_group_extraction(tmp_path):
    """Kiểm tra việc trích xuất file_hash từ ID dạng reveal:{split}:{file_hash}#{func_index}."""
    from scripts.run_step0_offline_diagnostic import build_canonical_table, load_gate_data
    csv_file = tmp_path / "reveal_sample.csv"
    csv_file.write_text(
        "id,y,p_gate\n"
        "reveal:test:hash_abc_123#0,0,0.12\n"
        "reveal:test:hash_abc_123#1,1,0.45\n"
        "reveal:test:hash_def_456#2,0,0.08\n",
        encoding="utf-8",
    )
    gate_data = load_gate_data(csv_file)
    assert gate_data["reveal:test:hash_abc_123#0"]["group"] == "hash_abc_123"
    assert gate_data["reveal:test:hash_abc_123#1"]["group"] == "hash_abc_123"
    assert gate_data["reveal:test:hash_def_456#2"]["group"] == "hash_def_456"

    llm_data = {
        "reveal:test:hash_abc_123#0": {"s_llm": 0.0, "valid": True},
        "reveal:test:hash_abc_123#1": {"s_llm": 1.0, "valid": True},
        "reveal:test:hash_def_456#2": {"s_llm": 0.0, "valid": True},
    }
    ids, y, p, s, v, groups, X = build_canonical_table(gate_data, llm_data, dataset="reveal")
    assert groups == ["hash_abc_123", "hash_abc_123", "hash_def_456"]


def test_routing_q10_contrast_present(mock_dataset_dir, tmp_path):
    """Kiểm tra kết quả routing tại q=10% được bổ sung vào report dictionary và markdown."""
    _, files = mock_dataset_dir
    out_dir = tmp_path / "runs_routing_test"

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
        n_boot=100,
        n_folds=2,
    )

    assert "routing_q10_contrast" in report_dict
    q10 = report_dict["routing_q10_contrast"]
    assert q10["budget"] == 0.10
    assert q10["contrast"] == "benefit_minus_confidence"
    assert "delta_balanced_accuracy" in q10
    assert "delta_mcc" in q10
    assert "delta" in q10["delta_balanced_accuracy"]
    assert "lo" in q10["delta_balanced_accuracy"]
    assert "hi" in q10["delta_balanced_accuracy"]
    assert "delta" in q10["delta_mcc"]

    md_text = md_path.read_text(encoding="utf-8")
    assert "So sánh Đối chứng Ghép cặp tại Ngân sách" in md_text
    assert "Balanced Accuracy" in md_text


def test_stratified_group_kfold_imbalanced_class_fallback():
    """Kiểm tra fit_pre_post tự động fallback StratifiedKFold khi một fold train của StratifiedGroupKFold chỉ có 1 class."""
    from grace_diag import complementarity as C
    X = np.ones((5, 2))
    y = np.array([0, 0, 0, 1, 1])
    groups = np.array(["g1", "g2", "g3", "g_pos", "g_pos"])
    s = np.zeros(5)
    v = np.ones(5, dtype=bool)
    p = np.full(5, 0.5)

    res = C.fit_pre_post(X, s, v, p, y, n_folds=3, groups=groups, seed=42, n_boot=20)
    assert res.oof_pre.shape == (5,)
    assert res.oof_post.shape == (5,)


def test_cluster_unit_sample_preserves_group_in_canonical_csv(tmp_path):
    """Kiểm tra canonical CSV vẫn lưu cột group ngay cả khi chỉ định --cluster-unit sample."""
    gate_val = tmp_path / "gate_val.csv"
    gate_test = tmp_path / "gate_test.csv"
    llm_val = tmp_path / "llm_val.jsonl"
    llm_test = tmp_path / "llm_test.jsonl"
    out_dir = tmp_path / "runs_sample_preserves_group"

    gate_val.write_text(
        "id,y,p_gate,group\n"
        "mock_1,0,0.1,commit_a\n"
        "mock_2,1,0.9,commit_b\n"
        "mock_3,0,0.2,commit_a\n"
        "mock_4,1,0.8,commit_b\n",
        encoding="utf-8",
    )
    gate_test.write_text(
        "id,y,p_gate,group\n"
        "mock_5,0,0.2,commit_c\n"
        "mock_6,1,0.8,commit_d\n"
        "mock_7,0,0.3,commit_c\n"
        "mock_8,1,0.7,commit_d\n",
        encoding="utf-8",
    )
    llm_val.write_text(
        '{"id":"mock_1","s":0.0,"valid":true}\n'
        '{"id":"mock_2","s":1.0,"valid":true}\n'
        '{"id":"mock_3","s":0.0,"valid":true}\n'
        '{"id":"mock_4","s":1.0,"valid":true}\n',
        encoding="utf-8",
    )
    llm_test.write_text(
        '{"id":"mock_5","s":0.0,"valid":true}\n'
        '{"id":"mock_6","s":1.0,"valid":true}\n'
        '{"id":"mock_7","s":0.0,"valid":true}\n'
        '{"id":"mock_8","s":1.0,"valid":true}\n',
        encoding="utf-8",
    )

    report_dict, json_path, md_path = run_offline_diagnostic(
        gate_val_path=gate_val,
        gate_test_path=gate_test,
        llm_val_path=llm_val,
        llm_test_path=llm_test,
        xpre_val_path=None,
        xpre_test_path=None,
        dataset="devign",
        tau=0.5,
        output_dir=out_dir,
        seed=42,
        n_boot=20,
        n_folds=2,
        cluster_unit="sample",
    )

    canonical_val = out_dir / "canonical_devign_val.csv"
    assert canonical_val.exists()
    lines = canonical_val.read_text(encoding="utf-8").strip().splitlines()
    header = lines[0].split(",")
    assert "group" in header
    assert lines[1].split(",")[-1] == "commit_a"
    assert report_dict["metadata"]["bootstrap_unit"] == "sample"


def test_reveal_file_hash_group_label_formatting(tmp_path):
    """Kiểm tra báo cáo ReVeal hiển thị nhãn nhóm là file hashes chứ không phải commit IDs."""
    gate_val = tmp_path / "reveal_val.csv"
    gate_test = tmp_path / "reveal_test.csv"
    llm_val = tmp_path / "reveal_llm_val.jsonl"
    llm_test = tmp_path / "reveal_llm_test.jsonl"
    out_dir = tmp_path / "runs_reveal_label"

    # Tạo 12 nhóm file-level hash duy nhất để kích hoạt Cluster Bootstrap (>=10)
    lines_val = ["id,y,p_gate"]
    lines_test = ["id,y,p_gate"]
    llm_val_lines = []
    llm_test_lines = []
    for i in range(12):
        sid_v = f"reveal:validation:hash_{i:02d}#0"
        sid_t = f"reveal:test:hash_{i:02d}#0"
        y_val = i % 2
        lines_val.append(f"{sid_v},{y_val},0.3")
        lines_test.append(f"{sid_t},{y_val},0.4")
        llm_val_lines.append(f'{{"id":"{sid_v}","s":{float(y_val)},"valid":true}}')
        llm_test_lines.append(f'{{"id":"{sid_t}","s":{float(y_val)},"valid":true}}')

    gate_val.write_text("\n".join(lines_val) + "\n", encoding="utf-8")
    gate_test.write_text("\n".join(lines_test) + "\n", encoding="utf-8")
    llm_val.write_text("\n".join(llm_val_lines) + "\n", encoding="utf-8")
    llm_test.write_text("\n".join(llm_test_lines) + "\n", encoding="utf-8")

    report_dict, json_path, md_path = run_offline_diagnostic(
        gate_val_path=gate_val,
        gate_test_path=gate_test,
        llm_val_path=llm_val,
        llm_test_path=llm_test,
        dataset="reveal",
        tau=0.2,
        output_dir=out_dir,
        seed=42,
        n_boot=20,
        n_folds=2,
        cluster_unit="auto",
    )

    assert "file hashes" in report_dict["metadata"]["bootstrap_unit_test"]
    md_text = md_path.read_text(encoding="utf-8")
    assert "file hashes" in md_text





