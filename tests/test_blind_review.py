"""
Unit Tests Độc Lập Cho Thí Nghiệm 2.3: Bảng Chấm Mù Thủ Công (Blind Human Review Protocol)
Tuân thủ:
- evaluation_contract.yaml
- project_docs/plans/PLAN_SUPERVISOR_REQUIREMENTS_EXECUTION_20261014.md (Nhiệm vụ 2.3 / STT 10)
- project_docs/docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md (dòng 197-215)
"""

import sys
import json
import csv
import random
import pytest
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
src_dir = repo_root / "src"
scripts_dir = repo_root / "scripts"

for p in [str(repo_root), str(src_dir), str(scripts_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.generate_blind_review_sheets import (
    load_devign_dev_clean_samples,
    select_stratified_targets,
    generate_blind_sheets
)
from scripts.evaluate_blind_review import (
    calculate_cohen_kappa,
    interpret_cohen_kappa,
    decode_reviewer_preference,
    generate_mock_reviews,
    evaluate_review_sheets
)


@pytest.fixture
def dev_split_file():
    split_path = repo_root / "data" / "splits" / "devign_dev_clean_100_ids.json"
    assert split_path.exists(), f"File split chuẩn bắt buộc phải tồn tại: {split_path}"
    return split_path


def test_stratified_sample_distribution(dev_split_file):
    """
    Kiểm tra tính phân tầng đúng 25 Vuln và 25 Safe:
    - 50 mẫu được chọn từ 100 mẫu dev sạch.
    - Chính xác 25 mẫu target=1 (Vulnerable) và 25 mẫu target=0 (Safe).
    - 100% ID duy nhất, không trùng lặp.
    - Seed=42 bảo đảm tính tái lập hoàn toàn (reproducibility).
    """
    samples = load_devign_dev_clean_samples(dev_split_file, repo_root)
    assert len(samples) == 100, f"Tập dev sạch phải có 100 mẫu, thực tế có {len(samples)}"

    selected = select_stratified_targets(samples, num_samples=50, seed=42)
    assert len(selected) == 50, f"Tổng số mẫu được chọn phải đúng 50, thực tế: {len(selected)}"

    vuln_count = sum(1 for s in selected if s["target"] == 1)
    safe_count = sum(1 for s in selected if s["target"] == 0)

    assert vuln_count == 25, f"Số mẫu Vulnerable phải đúng 25, thực tế: {vuln_count}"
    assert safe_count == 25, f"Số mẫu Safe phải đúng 25, thực tế: {safe_count}"

    ids = [s["id"] for s in selected]
    assert len(set(ids)) == 50, "50 mẫu được chọn phải có ID hoàn toàn duy nhất"

    # Kiểm tra tính tất định: Chạy lại với seed=42 phải ra danh sách y hệt
    selected_repeat = select_stratified_targets(samples, num_samples=50, seed=42)
    assert [s["id"] for s in selected] == [s["id"] for s in selected_repeat]

    # Khác seed phải ra tập hoặc thứ tự khác
    selected_diff = select_stratified_targets(samples, num_samples=50, seed=999)
    assert [s["id"] for s in selected] != [s["id"] for s in selected_diff]


def test_blinding_zero_leakage():
    """
    Kiểm tra tính bảo mật tuyệt đối của Chấm Mù:
    - Bảng chấm cho Hiếu và Dũng phải tồn tại.
    - Đúng 50 dòng đánh giá.
    - Cột bắt buộc theo đúng hợp đồng.
    - Không rò rỉ bất kỳ tên phương pháp hay điểm số nào trong CSV.
    """
    hieu_csv = repo_root / "project_docs" / "reports" / "blind_review_sheet_hieu.csv"
    dung_csv = repo_root / "project_docs" / "reports" / "blind_review_sheet_dung.csv"

    expected_cols = [
        "sample_idx",
        "target_id",
        "target_label",
        "target_code_snippet",
        "demo_A_snippet",
        "demo_B_snippet",
        "sink_match_A",
        "variable_match_A",
        "guard_match_A",
        "sink_match_B",
        "variable_match_B",
        "guard_match_B",
        "better_demo (A/B/Equal/Neither)",
        "evidence_notes"
    ]

    for csv_file in [hieu_csv, dung_csv]:
        assert csv_file.exists(), f"File bảng chấm không tồn tại: {csv_file}"

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        assert fieldnames == expected_cols, f"Tiêu đề cột trong {csv_file} không đúng chuẩn hợp đồng"
        assert len(rows) == 50, f"{csv_file} phải có đúng 50 hàng, thực tế: {len(rows)}"

        # Kiểm tra rò rỉ từ khóa nhạy cảm
        forbidden_keywords = [
            "baseline",
            "security-aware",
            "security_aware",
            "securityaware",
            "codet5",
            "graphsim",
            "retrieval_score",
            "hybrid_score"
        ]

        for r_idx, r in enumerate(rows, start=1):
            # Các cột thông tin demo không được chứa từ khóa phương pháp
            demo_a = r["demo_A_snippet"].lower()
            demo_b = r["demo_B_snippet"].lower()
            for kw in forbidden_keywords:
                assert kw not in demo_a, f"Rò rỉ từ khóa '{kw}' trong Demo A tại hàng {r_idx}"
                assert kw not in demo_b, f"Rò rỉ từ khóa '{kw}' trong Demo B tại hàng {r_idx}"

            # Các cột đánh giá ban đầu phải để trống cho người chấm điền
            assert r["better_demo (A/B/Equal/Neither)"] in ("", "A", "B", "Equal", "Neither")


def test_answer_key_decoding_integrity():
    """
    Kiểm tra tính toàn vẹn 100% của file đáp án bí mật (blind_review_answer_key.json):
    - Đủ 50 bản ghi.
    - Đúng 25 Vuln và 25 Safe.
    - Vị trí A và B gán song ánh (bijective) cho Baseline và Security-Aware.
    - Cả 2 vị trí A và B đều được gán ngẫu nhiên (không thiên lệch 1 bên).
    """
    key_path = repo_root / "project_docs" / "reports" / "blind_review_answer_key.json"
    assert key_path.exists(), f"File đáp án không tồn tại: {key_path}"

    with open(key_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]
    assert meta["total_samples"] == 50
    assert meta["vuln_samples"] == 25
    assert meta["safe_samples"] == 25
    assert meta["seed"] == 42

    entries = data["answer_key"]
    assert len(entries) == 50

    base_in_a = 0
    base_in_b = 0

    for idx, e in enumerate(entries, start=1):
        assert e["sample_idx"] == idx
        assert e["target_label"] in (0, 1)

        base_pos = e["baseline_assigned_to"]
        sec_pos = e["security_aware_assigned_to"]

        assert base_pos in ("A", "B")
        assert sec_pos in ("A", "B")
        assert base_pos != sec_pos, f"Mẫu {idx}: Baseline và Security-Aware không được cùng nằm ở vị trí {base_pos}"

        if base_pos == "A":
            base_in_a += 1
            assert e["demo_A_source"] == "baseline"
            assert e["demo_B_source"] == "security_aware"
        else:
            base_in_b += 1
            assert e["demo_A_source"] == "security_aware"
            assert e["demo_B_source"] == "baseline"

        assert len(e["demo_A_id"]) > 0
        assert len(e["demo_B_id"]) > 0

    # Phải có sự xáo trộn thực sự giữa A và B (không thiên lệch cứng về 1 bên)
    assert 15 <= base_in_a <= 35, f"Tỷ lệ phân bổ Baseline vào A phải cân bằng ngẫu nhiên, thực tế: {base_in_a}/50"
    assert 15 <= base_in_b <= 35, f"Tỷ lệ phân bổ Baseline vào B phải cân bằng ngẫu nhiên, thực tế: {base_in_b}/50"


def test_cohen_kappa_exact_calculation():
    """
    Kiểm tra thuật toán tính Cohen's Kappa hoạt động chính xác theo chuẩn học thuật:
    1. Perfect agreement -> kappa == 1.0
    2. Chance agreement (độc lập ngẫu nhiên) -> kappa xấp xỉ 0.0
    3. Systematic disagreement -> kappa < 0.0
    4. Bảng liên định mẫu (Contingency Table) đối chiếu với tính toán tay chuẩn xác.
    """
    # 1. Đồng thuận 100%
    r1 = ["Security-Aware", "Baseline", "Equal", "Security-Aware"] * 10
    r2 = list(r1)
    k_perf, po_perf, pe_perf = calculate_cohen_kappa(r1, r2)
    assert po_perf == 1.0
    assert k_perf == 1.0
    assert interpret_cohen_kappa(k_perf) == "Gần như hoàn hảo (Almost Perfect Agreement)"

    # 2. Bất đồng có hệ thống
    r1_opp = ["A"] * 20 + ["B"] * 20
    r2_opp = ["B"] * 20 + ["A"] * 20
    k_opp, po_opp, pe_opp = calculate_cohen_kappa(r1_opp, r2_opp)
    assert po_opp == 0.0
    assert k_opp < 0.0

    # 3. Đối chứng với bài toán sách giáo khoa:
    # 50 mẫu, 2 lớp (A, B)
    # R1: 30 A, 20 B
    # R2: 25 A, 25 B
    # Số mẫu cùng chọn A: 20
    # Số mẫu cùng chọn B: 15
    # Tổng đồng thuận: 35/50 = 0.70
    # P_e = (30/50)*(25/50) + (20/50)*(25/50) = 0.30 + 0.20 = 0.50
    # Kappa = (0.70 - 0.50) / (1 - 0.50) = 0.20 / 0.50 = 0.40
    known_r1 = ["A"] * 20 + ["A"] * 10 + ["B"] * 5 + ["B"] * 15
    known_r2 = ["A"] * 20 + ["B"] * 10 + ["A"] * 5 + ["B"] * 15
    k_known, po_known, pe_known = calculate_cohen_kappa(known_r1, known_r2, categories=["A", "B"])
    assert abs(po_known - 0.70) < 1e-6
    assert abs(pe_known - 0.50) < 1e-6
    assert abs(k_known - 0.40) < 1e-6
    assert interpret_cohen_kappa(k_known) == "Thấp (Fair Agreement)"


def test_decoder_logic():
    """Kiểm tra hàm giải mã lựa chọn decode_reviewer_preference."""
    key_entry_base_a = {
        "baseline_assigned_to": "A",
        "security_aware_assigned_to": "B"
    }

    assert decode_reviewer_preference("A", key_entry_base_a) == "Baseline"
    assert decode_reviewer_preference("a", key_entry_base_a) == "Baseline"
    assert decode_reviewer_preference("B", key_entry_base_a) == "Security-Aware"
    assert decode_reviewer_preference("b", key_entry_base_a) == "Security-Aware"
    assert decode_reviewer_preference("Equal", key_entry_base_a) == "Equal"
    assert decode_reviewer_preference("eq", key_entry_base_a) == "Equal"
    assert decode_reviewer_preference("Neither", key_entry_base_a) == "Neither"
    assert decode_reviewer_preference("none", key_entry_base_a) == "Neither"
    assert decode_reviewer_preference("", key_entry_base_a) == "Unrated"

    key_entry_sec_a = {
        "baseline_assigned_to": "B",
        "security_aware_assigned_to": "A"
    }

    assert decode_reviewer_preference("A", key_entry_sec_a) == "Security-Aware"
    assert decode_reviewer_preference("B", key_entry_sec_a) == "Baseline"

    # Các biến thể ngôn ngữ tự nhiên từ người chấm
    assert decode_reviewer_preference("Demo A", key_entry_base_a) == "Baseline"
    assert decode_reviewer_preference("demo_a", key_entry_base_a) == "Baseline"
    assert decode_reviewer_preference("Demo B", key_entry_base_a) == "Security-Aware"
    assert decode_reviewer_preference("Chọn A", key_entry_base_a) == "Baseline"
    assert decode_reviewer_preference("A tốt hơn", key_entry_base_a) == "Baseline"
    assert decode_reviewer_preference("B (tốt hơn)", key_entry_base_a) == "Security-Aware"
    assert decode_reviewer_preference("Tương đương", key_entry_base_a) == "Equal"
    assert decode_reviewer_preference("Như nhau", key_entry_base_a) == "Equal"
    assert decode_reviewer_preference("Không chọn bên nào", key_entry_base_a) == "Neither"
    assert decode_reviewer_preference("Chưa xác định", key_entry_base_a) == "Neither"
    assert decode_reviewer_preference("Chưa đánh giá", key_entry_base_a) == "Unrated"
    assert decode_reviewer_preference("Unrated", key_entry_base_a) == "Unrated"


def test_evaluation_pipeline_with_mock_data(tmp_path):
    """
    Kiểm tra toàn diện pipeline evaluate_review_sheets với dữ liệu mẫu giả định:
    - Sinh mock cho cả 2 người chấm.
    - Chạy đánh giá và xuất báo cáo JSON.
    - Xác nhận các chỉ số tổng hợp hợp lệ và rubric evidence summary.
    """
    key_path = repo_root / "project_docs" / "reports" / "blind_review_answer_key.json"
    with open(key_path, "r", encoding="utf-8") as f:
        key_data = json.load(f)

    mock_hieu = tmp_path / "mock_hieu.csv"
    mock_dung = tmp_path / "mock_dung.csv"
    mock_report = tmp_path / "mock_report.json"

    generate_mock_reviews(
        answer_key_entries=key_data["answer_key"],
        output_hieu_csv=mock_hieu,
        output_dung_csv=mock_dung,
        seed=42
    )

    assert mock_hieu.exists()
    assert mock_dung.exists()

    report = evaluate_review_sheets(
        hieu_sheet_path=mock_hieu,
        dung_sheet_path=mock_dung,
        answer_key_path=key_path,
        output_report_path=mock_report
    )

    assert mock_report.exists()
    assert report["metadata"]["total_samples"] == 50
    assert report["metadata"]["paired_rated_samples"] == 50

    # Kiểm tra Cohen Kappa nằm trong khoảng chuẩn hợp lệ
    kappa = report["inter_rater_reliability"]["cohen_kappa"]
    assert 0.40 <= kappa <= 1.0, f"Cohen Kappa phải đạt mức đồng thuận thực tế, thực tế: {kappa}"

    # Kiểm tra tỷ lệ thắng của Security-Aware vượt trội so với Baseline
    avg_pref = report["preference_summary"]["average"]
    assert avg_pref["security_aware_win_pct"] > avg_pref["baseline_win_pct"]
    assert (
        avg_pref["security_aware_win_pct"]
        + avg_pref["baseline_win_pct"]
        + avg_pref["equal_pct"]
        + avg_pref["neither_pct"]
        + avg_pref.get("unrated_pct", 0.0)
    ) == pytest.approx(100.0, abs=0.1)

    # Kiểm tra Rubric Evidence Summary (Sink, Variable, Guard)
    assert "rubric_evidence_summary" in report
    rubric = report["rubric_evidence_summary"]["average"]
    assert rubric["sink_match_security_aware_pct"] >= rubric["sink_match_baseline_pct"]
    assert rubric["variable_match_security_aware_pct"] >= rubric["variable_match_baseline_pct"]
    assert rubric["guard_match_security_aware_pct"] >= rubric["guard_match_baseline_pct"]


def test_evaluation_robust_to_row_permutation(tmp_path):
    """
    Kiểm tra tính bất biến trước việc sắp xếp lại hàng trong CSV:
    Nếu một người chấm sắp xếp lại thứ tự hàng (ví dụ: theo target_id hoặc target_label),
    kết quả đánh giá và hệ số Cohen's Kappa phải hoàn toàn trùng khớp 100%.
    """
    key_path = repo_root / "project_docs" / "reports" / "blind_review_answer_key.json"
    with open(key_path, "r", encoding="utf-8") as f:
        key_data = json.load(f)

    mock_hieu = tmp_path / "perm_hieu.csv"
    mock_dung = tmp_path / "perm_dung.csv"
    mock_dung_shuffled = tmp_path / "perm_dung_shuffled.csv"

    generate_mock_reviews(
        answer_key_entries=key_data["answer_key"],
        output_hieu_csv=mock_hieu,
        output_dung_csv=mock_dung,
        seed=42
    )

    # Đọc lại bảng của Dũng và xáo trộn ngẫu nhiên thứ tự các hàng
    with open(mock_dung, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    rng_perm = random.Random(123)
    shuffled_rows = list(rows)
    rng_perm.shuffle(shuffled_rows)

    with open(mock_dung_shuffled, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in shuffled_rows:
            writer.writerow(r)

    # Chạy đánh giá trên cả 2 phiên bản
    rep_orig = evaluate_review_sheets(
        hieu_sheet_path=mock_hieu,
        dung_sheet_path=mock_dung,
        answer_key_path=key_path
    )

    rep_shuffled = evaluate_review_sheets(
        hieu_sheet_path=mock_hieu,
        dung_sheet_path=mock_dung_shuffled,
        answer_key_path=key_path
    )

    # Đảm bảo kết quả giống hệt nhau
    assert rep_orig["inter_rater_reliability"]["cohen_kappa"] == rep_shuffled["inter_rater_reliability"]["cohen_kappa"]
    assert rep_orig["inter_rater_reliability"]["total_concordant_samples"] == rep_shuffled["inter_rater_reliability"]["total_concordant_samples"]
    assert rep_orig["preference_summary"]["average"]["security_aware_win_pct"] == rep_shuffled["preference_summary"]["average"]["security_aware_win_pct"]


def test_unrated_and_partially_rated_handling(tmp_path):
    """
    Kiểm tra xử lý các trường hợp chưa chấm hoặc chấm một phần:
    - Nếu 1 người chấm để trống, mẫu đó phải được tính là partially_or_unrated_samples.
    - Tỷ lệ unrated_pct phải được phản ánh chính xác.
    """
    key_path = repo_root / "project_docs" / "reports" / "blind_review_answer_key.json"
    with open(key_path, "r", encoding="utf-8") as f:
        key_data = json.load(f)

    mock_hieu = tmp_path / "unrated_hieu.csv"
    mock_dung = tmp_path / "unrated_dung.csv"

    generate_mock_reviews(
        answer_key_entries=key_data["answer_key"],
        output_hieu_csv=mock_hieu,
        output_dung_csv=mock_dung,
        seed=42
    )

    # Xóa 5 đánh giá của Dũng
    with open(mock_dung, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    for i in range(5):
        rows[i]["better_demo (A/B/Equal/Neither)"] = ""

    with open(mock_dung, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    rep = evaluate_review_sheets(
        hieu_sheet_path=mock_hieu,
        dung_sheet_path=mock_dung,
        answer_key_path=key_path
    )

    assert rep["metadata"]["paired_rated_samples"] == 45
    assert rep["inter_rater_reliability"]["partially_or_unrated_samples"] == 5
    assert rep["preference_summary"]["reviewer_dung"]["unrated_count"] == 5
    assert rep["preference_summary"]["reviewer_dung"]["unrated_pct"] == 10.0

