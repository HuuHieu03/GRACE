"""
Unit Tests Độc Lập Cho Thí Nghiệm Chấm Mù Thủ Công ReVeal (ReVeal Blind Review Protocol)
Tuân thủ:
- evaluation_contract.yaml
- project_docs/docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md
"""

import sys
import json
import csv
import pytest
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
src_dir = repo_root / "src"
scripts_dir = repo_root / "scripts"

for p in [str(repo_root), str(src_dir), str(scripts_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.generate_blind_review_sheets import (
    load_dev_clean_samples,
    select_stratified_targets
)
from scripts.evaluate_blind_review import (
    calculate_cohen_kappa,
    interpret_cohen_kappa,
    decode_reviewer_preference,
    evaluate_review_sheets
)


@pytest.fixture
def reveal_split_file():
    split_path = repo_root / "data" / "splits" / "reveal_dev_clean_100_ids.json"
    assert split_path.exists(), f"File split ReVeal bắt buộc phải tồn tại: {split_path}"
    return split_path


def test_reveal_stratified_sample_distribution(reveal_split_file):
    """
    Kiểm tra tính phân tầng đúng 25 Vuln và 25 Safe cho ReVeal:
    - 50 mẫu được chọn từ 100 mẫu dev sạch ReVeal.
    - Chính xác 25 mẫu target=1 (Vulnerable) và 25 mẫu target=0 (Safe).
    - 100% ID duy nhất, không trùng lặp.
    - Seed=42 bảo đảm tính tái lập hoàn toàn (reproducibility).
    """
    samples = load_dev_clean_samples(reveal_split_file, repo_root, dataset_name="reveal")
    assert len(samples) == 100, f"Tập dev sạch ReVeal phải có 100 mẫu, thực tế có {len(samples)}"

    selected = select_stratified_targets(samples, num_samples=50, seed=42)
    assert len(selected) == 50, f"Tổng số mẫu được chọn phải đúng 50, thực tế: {len(selected)}"

    vuln_count = sum(1 for s in selected if s["target"] == 1)
    safe_count = sum(1 for s in selected if s["target"] == 0)

    assert vuln_count == 25, f"Số mẫu Vulnerable phải đúng 25, thực tế: {vuln_count}"
    assert safe_count == 25, f"Số mẫu Safe phải đúng 25, thực tế: {safe_count}"

    ids = [s["id"] for s in selected]
    assert len(set(ids)) == 50, "50 mẫu được chọn phải có ID hoàn toàn duy nhất"

    selected_repeat = select_stratified_targets(samples, num_samples=50, seed=42)
    assert [s["id"] for s in selected] == [s["id"] for s in selected_repeat]


def test_reveal_blinding_zero_leakage():
    """
    Kiểm tra tính bảo mật tuyệt đối của Chấm Mù trên ReVeal:
    - Bảng chấm cho Hiếu và Dũng phải tồn tại.
    - Đúng 50 dòng đánh giá.
    - Tiêu đề cột chuẩn hợp đồng.
    - Không rò rỉ bất kỳ tên phương pháp hay điểm số nào trong CSV.
    - Không có ô đánh giá nào bị bỏ trống.
    """
    hieu_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_sheet_hieu.csv"
    dung_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_sheet_dung.csv"

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

    for csv_file in [hieu_csv, dung_csv]:
        assert csv_file.exists(), f"File bảng chấm không tồn tại: {csv_file}"

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        assert fieldnames == expected_cols, f"Tiêu đề cột trong {csv_file} không đúng chuẩn hợp đồng"
        assert len(rows) == 50, f"{csv_file} phải có đúng 50 hàng, thực tế: {len(rows)}"

        for r_idx, r in enumerate(rows, start=1):
            demo_a = r["demo_A_snippet"].lower()
            demo_b = r["demo_B_snippet"].lower()
            for kw in forbidden_keywords:
                assert kw not in demo_a, f"Rò rỉ từ khóa '{kw}' trong Demo A tại hàng {r_idx}"
                assert kw not in demo_b, f"Rò rỉ từ khóa '{kw}' trong Demo B tại hàng {r_idx}"

            choice = r["better_demo (A/B/Equal/Neither)"]
            assert choice in ("A", "B", "Equal", "Neither"), f"Giá trị không hợp lệ tại hàng {r_idx}: {choice}"
            assert len(r["evidence_notes"].strip()) > 0, f"Thiếu evidence notes tại hàng {r_idx}"


def test_reveal_answer_key_decoding_integrity():
    """
    Kiểm tra tính toàn vẹn 100% của file đáp án bí mật (blind_review_reveal_answer_key.json):
    - Đủ 50 bản ghi.
    - Đúng 25 Vuln và 25 Safe.
    - Vị trí A và B gán song ánh cho Baseline và Security-Aware.
    - Phân bổ cân bằng ngẫu nhiên giữa A và B.
    """
    key_path = repo_root / "project_docs" / "reports" / "blind_review_reveal_answer_key.json"
    assert key_path.exists(), f"File đáp án không tồn tại: {key_path}"

    with open(key_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["metadata"]
    assert meta["total_samples"] == 50
    assert meta["vuln_samples"] == 25
    assert meta["safe_samples"] == 25
    assert meta["seed"] == 42
    assert meta["dataset"] == "reveal"

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
        assert base_pos != sec_pos, f"Mẫu {idx}: Baseline và Security-Aware trùng vị trí {base_pos}"

        if base_pos == "A":
            base_in_a += 1
            assert e["demo_A_source"] == "baseline"
            assert e["demo_B_source"] == "security_aware"
        else:
            base_in_b += 1
            assert e["demo_A_source"] == "security_aware"
            assert e["demo_B_source"] == "baseline"

    assert 15 <= base_in_a <= 35, f"Tỷ lệ phân bổ Baseline vào A phải ngẫu nhiên hợp lý, thực tế: {base_in_a}/50"
    assert 15 <= base_in_b <= 35, f"Tỷ lệ phân bổ Baseline vào B phải ngẫu nhiên hợp lý, thực tế: {base_in_b}/50"


def test_reveal_cohen_kappa_exact_calculation():
    """Kiểm tra tính toán Cohen's Kappa theo chuẩn học thuật."""
    r1 = ["Security-Aware", "Baseline", "Equal", "Neither"] * 10
    r2 = list(r1)
    k_perf, po_perf, pe_perf = calculate_cohen_kappa(r1, r2)
    assert po_perf == 1.0
    assert k_perf == 1.0


def test_reveal_evaluation_report():
    """
    Kiểm tra báo cáo JSON đánh giá ReVeal:
    - Cohen's Kappa = 0.3271 (Fair Agreement)
    - Percent Agreement = 48.0%
    - 24 ca concordant, 26 ca discordant.
    """
    rep_path = repo_root / "project_docs" / "reports" / "blind_review_reveal_evaluation_report.json"
    assert rep_path.exists(), f"File báo cáo không tồn tại: {rep_path}"

    with open(rep_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    irr = data["inter_rater_reliability"]
    assert abs(irr["cohen_kappa"] - 0.3271) < 1e-4, f"Kappa không khớp: {irr['cohen_kappa']}"
    assert abs(irr["percent_agreement_pct"] - 48.0) < 1e-4, f"Agreement không khớp: {irr['percent_agreement_pct']}"
    assert irr["total_concordant_samples"] == 24
    assert irr["total_discordant_samples"] == 26
    assert irr["partially_or_unrated_samples"] == 0

    adjudication = data["adjudication_summary"]
    assert adjudication["consensus_security_aware_win_pct"] == 42.0
    assert adjudication["consensus_baseline_win_pct"] == 20.0
    assert adjudication["consensus_net_advantage_delta_pct"] == 22.0


def test_reveal_adjudication_integrity():
    """
    Kiểm tra tính toàn vẹn của hồ sơ đối soát (Adjudication & Discordant Cases):
    - File discordant cases đúng 26 ca.
    - File confirmed adjudication đúng 50 ca, không có ca nào bị bỏ trống.
    """
    disc_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_discordant_cases.csv"
    adj_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_confirmed_adjudication_50.csv"

    assert disc_csv.exists(), f"Thiếu file: {disc_csv}"
    assert adj_csv.exists(), f"Thiếu file: {adj_csv}"

    with open(disc_csv, "r", encoding="utf-8") as f:
        disc_rows = list(csv.DictReader(f))
    assert len(disc_rows) == 26, f"Số ca bất đồng phải đúng 26, thực tế: {len(disc_rows)}"

    with open(adj_csv, "r", encoding="utf-8") as f:
        adj_rows = list(csv.DictReader(f))
    assert len(adj_rows) == 50, f"Số ca hội chẩn phải đúng 50, thực tế: {len(adj_rows)}"

    for idx, row in enumerate(adj_rows, start=1):
        assert row["technical_choice"] in ("A", "B", "Equal", "Neither"), f"Lựa chọn kỹ thuật không hợp lệ tại hàng {idx}: {row['technical_choice']}"
        assert len(row["technical_evidence"].strip()) > 0, f"Thiếu bằng chứng tại hàng {idx}"


def test_reveal_pipeline_direct_execution(tmp_path):
    """
    Kiểm tra thực thi trực tiếp evaluate_review_sheets trên dữ liệu ReVeal:
    - Chạy hàm đánh giá chính từ scripts/evaluate_blind_review.py.
    - Xuất báo cáo tạm thời ra tmp_path.
    - Xác nhận Cohen's Kappa đạt 0.3271 (Fair Agreement).
    - Xác nhận 24 ca concordant, 26 ca discordant.
    - Xác nhận 40% Security-Aware, 22% Baseline sau đối soát.
    """
    hieu_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_sheet_hieu.csv"
    dung_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_sheet_dung.csv"
    key_path = repo_root / "project_docs" / "reports" / "blind_review_reveal_answer_key.json"
    adj_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_confirmed_adjudication_50.csv"
    tmp_report = tmp_path / "test_reveal_report.json"
    tmp_disc = tmp_path / "test_reveal_disc.csv"

    rep = evaluate_review_sheets(
        hieu_sheet_path=hieu_csv,
        dung_sheet_path=dung_csv,
        answer_key_path=key_path,
        output_report_path=tmp_report,
        discordant_out_path=tmp_disc,
        adjudication_sheet_path=adj_csv,
        dataset_name="reveal"
    )

    assert tmp_report.exists()
    assert tmp_disc.exists()
    assert rep["metadata"]["total_samples"] == 50
    assert rep["metadata"]["paired_rated_samples"] == 50

    irr = rep["inter_rater_reliability"]
    assert abs(irr["cohen_kappa"] - 0.3271) < 1e-4
    assert abs(irr["percent_agreement_pct"] - 48.0) < 1e-4
    assert irr["total_concordant_samples"] == 24
    assert irr["total_discordant_samples"] == 26
    assert irr["partially_or_unrated_samples"] == 0

    adj = rep["adjudication_summary"]
    assert adj["consensus_security_aware_win_pct"] == 42.0
    assert adj["consensus_baseline_win_pct"] == 20.0
    assert adj["consensus_net_advantage_delta_pct"] == 22.0

    # Kiểm tra file discordant cases sinh ra đúng 26 ca
    with open(tmp_disc, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 26


def test_reveal_row_permutation_invariance(tmp_path):
    """
    Kiểm tra tính bất biến của đánh giá ReVeal khi xáo trộn ngẫu nhiên thứ tự hàng:
    - Bảng chấm của Dũng bị xáo trộn thứ tự dòng.
    - Kết quả Cohen's Kappa và phân loại phải hoàn toàn trùng khớp 100%.
    """
    import random
    hieu_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_sheet_hieu.csv"
    dung_csv = repo_root / "project_docs" / "reports" / "blind_review_reveal_sheet_dung.csv"
    key_path = repo_root / "project_docs" / "reports" / "blind_review_reveal_answer_key.json"

    with open(dung_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    rng = random.Random(789)
    shuffled_rows = list(rows)
    rng.shuffle(shuffled_rows)

    shuffled_dung_csv = tmp_path / "shuffled_dung.csv"
    with open(shuffled_dung_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in shuffled_rows:
            writer.writerow(r)

    rep_orig = evaluate_review_sheets(
        hieu_sheet_path=hieu_csv,
        dung_sheet_path=dung_csv,
        answer_key_path=key_path,
        dataset_name="reveal"
    )

    rep_shuffled = evaluate_review_sheets(
        hieu_sheet_path=hieu_csv,
        dung_sheet_path=shuffled_dung_csv,
        answer_key_path=key_path,
        dataset_name="reveal"
    )

    assert rep_orig["inter_rater_reliability"]["cohen_kappa"] == rep_shuffled["inter_rater_reliability"]["cohen_kappa"]
    assert rep_orig["inter_rater_reliability"]["total_concordant_samples"] == rep_shuffled["inter_rater_reliability"]["total_concordant_samples"]
    assert rep_orig["inter_rater_reliability"]["total_discordant_samples"] == rep_shuffled["inter_rater_reliability"]["total_discordant_samples"]

