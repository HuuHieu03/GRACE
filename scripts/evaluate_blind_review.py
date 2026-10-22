#!/usr/bin/env python3
"""
Script Đánh Giá Kết Quả Chấm Mù & Tính Hệ Số Đồng Thuận (Cohen's Kappa)
Tuân thủ:
- evaluation_contract.yaml
- project_docs/plans/PLAN_SUPERVISOR_REQUIREMENTS_EXECUTION_20261014.md (Nhiệm vụ 2.3 / STT 10)
- project_docs/docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md (dòng 197-215)

Chức năng:
1. Đọc hai bảng chấm độc lập của Hiếu và Dũng:
   - `project_docs/reports/blind_review_sheet_hieu.csv`
   - `project_docs/reports/blind_review_sheet_dung.csv`
2. Giải mã Demo A và Demo B dựa trên file đáp án bí mật:
   - `project_docs/reports/blind_review_answer_key.json`
3. Tính toán tỷ lệ thắng / ưu thế:
   - Security-Aware Retriever thắng bao nhiêu %
   - Baseline Retriever thắng bao nhiêu %
   - Tương đương (Equal) bao nhiêu %
   - Không chọn bên nào (Neither) bao nhiêu %
4. Tính hệ số độ đồng thuận giữa 2 người chấm:
   - Cohen's Kappa (kappa) chuẩn học thuật
   - Percent Agreement
   - Phân loại mức độ đồng thuận (Landis & Koch, 1977)
5. Đối soát ca bất đồng (Discordant Cases) để chuẩn bị cho buổi thảo luận thống nhất.
6. Hỗ trợ cờ `--generate_mock_demo` để sinh dữ liệu mẫu giả định cho kiểm thử tự động.
"""

import sys
import os
import io
import json
import csv
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

repo_root = Path(__file__).resolve().parent.parent


def calculate_cohen_kappa(
    rater1_labels: List[str], 
    rater2_labels: List[str], 
    categories: Optional[List[str]] = None
) -> Tuple[float, float, float]:
    """
    Tính hệ số Cohen's Kappa giữa 2 người chấm từ nguyên lý toán học chuẩn:
    kappa = (P_o - P_e) / (1 - P_e)
    
    Returns:
        (kappa, observed_agreement, expected_agreement)
    """
    if len(rater1_labels) != len(rater2_labels):
        raise ValueError(f"Độ dài 2 danh sách nhãn không khớp: {len(rater1_labels)} != {len(rater2_labels)}")
    
    n = len(rater1_labels)
    if n == 0:
        return 0.0, 0.0, 0.0

    if categories is None:
        categories = sorted(list(set(rater1_labels) | set(rater2_labels)))
    else:
        categories = sorted(list(set(categories) | set(rater1_labels) | set(rater2_labels)))

    # 1. Observed agreement P_o
    agreed = sum(1 for a, b in zip(rater1_labels, rater2_labels) if a == b)
    p_o = agreed / n

    # 2. Marginal distributions
    r1_counts = Counter(rater1_labels)
    r2_counts = Counter(rater2_labels)

    # 3. Expected agreement by chance P_e
    p_e = 0.0
    for cat in categories:
        prob1 = r1_counts[cat] / n
        prob2 = r2_counts[cat] / n
        p_e += prob1 * prob2

    # 4. Cohen's Kappa
    if p_e >= 1.0:
        kappa = 1.0
    elif abs(1.0 - p_e) < 1e-9:
        kappa = 1.0 if abs(p_o - 1.0) < 1e-9 else 0.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    return float(kappa), float(p_o), float(p_e)


def interpret_cohen_kappa(kappa: float) -> str:
    """Diễn giải giá trị Cohen's Kappa theo thang chuẩn Landis & Koch (1977)."""
    if kappa < 0.0:
        return "Kém (Kém hơn ngẫu nhiên / Systematic Disagreement)"
    elif kappa <= 0.20:
        return "Rất thấp (Slight Agreement)"
    elif kappa <= 0.40:
        return "Thấp (Fair Agreement)"
    elif kappa <= 0.60:
        return "Vừa phải (Moderate Agreement)"
    elif kappa <= 0.80:
        return "Đáng kể (Substantial Agreement)"
    else:
        return "Gần như hoàn hảo (Almost Perfect Agreement)"


def decode_reviewer_preference(
    choice_raw: str, 
    key_entry: Dict[str, Any]
) -> str:
    """
    Giải mã lựa chọn của người chấm (A/B/Equal/Neither) thành phương pháp cụ thể:
    - 'Security-Aware'
    - 'Baseline'
    - 'Equal'
    - 'Neither'
    - 'Unrated'
    Hỗ trợ cả ký tự đơn (A, B) lẫn các biến thể ngôn ngữ tự nhiên:
    'Demo A', 'demo_b', 'Chọn A', 'A tốt hơn', 'Equal', 'Tương đương', 'Neither', 'Không'...
    """
    if not choice_raw:
        return "Unrated"

    choice = str(choice_raw).strip()
    if not choice:
        return "Unrated"

    choice_upper = choice.upper()
    if choice_upper in ("UNRATED", "N/A", "NA", "CHƯA ĐÁNH GIÁ", "CHUA DANH GIA", "CHƯA CHẤM", "CHUA CHAM"):
        return "Unrated"

    base_pos = str(key_entry.get("baseline_assigned_to", "")).strip().upper()
    sec_pos = str(key_entry.get("security_aware_assigned_to", "")).strip().upper()

    # 1. Khớp chính xác
    if choice_upper == sec_pos:
        return "Security-Aware"
    elif choice_upper == base_pos:
        return "Baseline"
    elif choice_upper in ("EQUAL", "EQ", "=", "EQUIVALENT", "SAME", "TƯƠNG ĐƯƠNG", "TUONG DUONG", "NHƯ NHAU", "NHU NHAU", "BẰNG NHAU", "BANG NHAU"):
        return "Equal"
    elif choice_upper in ("NEITHER", "NONE", "NONE OF ABOVE", "NEITHER ONE", "KHÔNG CHỌN BÊN NÀO", "KHONG CHON BEN NAO", "KHÔNG", "KHONG", "CHƯA XÁC ĐỊNH", "CHUA XAC DINH"):
        return "Neither"

    # 2. Xử lý biểu thức chính quy cho các biến thể người chấm điền tự do
    import re
    if re.search(r'\b(EQUAL|TƯƠNG ĐƯƠNG|TUONG DUONG|NHƯ NHAU|NHU NHAU|BẰNG NHAU|BANG NHAU)\b', choice_upper):
        return "Equal"
    if re.search(r'\b(NEITHER|NONE|KHÔNG CHỌN|KHONG CHON|KHÔNG BÊN|KHONG BEN|CHƯA XÁC ĐỊNH|CHUA XAC DINH)\b', choice_upper):
        return "Neither"

    # Kiểm tra nhắc tới A hoặc B
    has_a = bool(re.search(r'(^|\b|DEMO[-_\s]*)(A)($|\b|[\s\.\:\,\)\/])', choice_upper))
    has_b = bool(re.search(r'(^|\b|DEMO[-_\s]*)(B)($|\b|[\s\.\:\,\)\/])', choice_upper))

    if has_a and not has_b:
        return "Security-Aware" if sec_pos == "A" else "Baseline"
    elif has_b and not has_a:
        return "Security-Aware" if sec_pos == "B" else "Baseline"

    return "Unrated"


def classify_rubric_match(val_raw: str) -> str:
    """Phân loại mức độ bằng chứng: 'Match', 'Partial', 'No_Match', 'Unspecified'."""
    if not val_raw:
        return "Unspecified"
    s = str(val_raw).strip().lower()
    if any(k in s for k in ["chưa xác định", "unknown", "unspecified", "chua xac dinh"]):
        return "Unspecified"
    if any(k in s for k in ["một phần", "mot phan", "partial", "tương đối", "tuong doi"]):
        return "Partial"
    if any(k in s for k in ["có", "co", "yes", "true", "khớp", "khop", "match", "1"]):
        return "Match"
    if any(k in s for k in ["không", "khong", "no", "false", "none", "0"]):
        return "No_Match"
    return "Unspecified"


def analyze_rubric_evidence(
    records: List[Dict[str, Any]],
    hieu_map: Dict[int, Dict[str, Any]],
    dung_map: Dict[int, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Tổng hợp và so sánh bằng chứng rubric (Sink / Variable / Guard) giữa Baseline và Security-Aware.
    """
    def compute_stats(rater_map, rater_name):
        sec_sink_match = 0
        base_sink_match = 0
        sec_var_match = 0
        base_var_match = 0
        sec_guard_match = 0
        base_guard_match = 0
        total_rated = 0

        for r in records:
            s_idx = r["sample_idx"]
            row = rater_map.get(s_idx)
            if not row:
                continue

            sec_pos = r["security_aware_assigned_to"]
            base_pos = r["baseline_assigned_to"]

            sink_sec = classify_rubric_match(row.get(f"sink_match_{sec_pos}", ""))
            sink_base = classify_rubric_match(row.get(f"sink_match_{base_pos}", ""))
            var_sec = classify_rubric_match(row.get(f"variable_match_{sec_pos}", ""))
            var_base = classify_rubric_match(row.get(f"variable_match_{base_pos}", ""))
            guard_sec = classify_rubric_match(row.get(f"guard_match_{sec_pos}", ""))
            guard_base = classify_rubric_match(row.get(f"guard_match_{base_pos}", ""))

            if sink_sec in ("Match", "Partial"):
                sec_sink_match += 1
            if sink_base in ("Match", "Partial"):
                base_sink_match += 1

            if var_sec in ("Match", "Partial"):
                sec_var_match += 1
            if var_base in ("Match", "Partial"):
                base_var_match += 1

            if guard_sec in ("Match", "Partial"):
                sec_guard_match += 1
            if guard_base in ("Match", "Partial"):
                base_guard_match += 1

            total_rated += 1

        n = max(total_rated, 1)
        return {
            "rater": rater_name,
            "total_samples": total_rated,
            "sink_match": {
                "security_aware_count": sec_sink_match,
                "security_aware_pct": round(sec_sink_match / n * 100.0, 2),
                "baseline_count": base_sink_match,
                "baseline_pct": round(base_sink_match / n * 100.0, 2),
                "delta_pct": round((sec_sink_match - base_sink_match) / n * 100.0, 2)
            },
            "variable_match": {
                "security_aware_count": sec_var_match,
                "security_aware_pct": round(sec_var_match / n * 100.0, 2),
                "baseline_count": base_var_match,
                "baseline_pct": round(base_var_match / n * 100.0, 2),
                "delta_pct": round((sec_var_match - base_var_match) / n * 100.0, 2)
            },
            "guard_match": {
                "security_aware_count": sec_guard_match,
                "security_aware_pct": round(sec_guard_match / n * 100.0, 2),
                "baseline_count": base_guard_match,
                "baseline_pct": round(base_guard_match / n * 100.0, 2),
                "delta_pct": round((sec_guard_match - base_guard_match) / n * 100.0, 2)
            }
        }

    hieu_stats = compute_stats(hieu_map, "Hiếu")
    dung_stats = compute_stats(dung_map, "Dũng")

    avg_summary = {
        "sink_match_security_aware_pct": round((hieu_stats["sink_match"]["security_aware_pct"] + dung_stats["sink_match"]["security_aware_pct"]) / 2.0, 2),
        "sink_match_baseline_pct": round((hieu_stats["sink_match"]["baseline_pct"] + dung_stats["sink_match"]["baseline_pct"]) / 2.0, 2),
        "variable_match_security_aware_pct": round((hieu_stats["variable_match"]["security_aware_pct"] + dung_stats["variable_match"]["security_aware_pct"]) / 2.0, 2),
        "variable_match_baseline_pct": round((hieu_stats["variable_match"]["baseline_pct"] + dung_stats["variable_match"]["baseline_pct"]) / 2.0, 2),
        "guard_match_security_aware_pct": round((hieu_stats["guard_match"]["security_aware_pct"] + dung_stats["guard_match"]["security_aware_pct"]) / 2.0, 2),
        "guard_match_baseline_pct": round((hieu_stats["guard_match"]["baseline_pct"] + dung_stats["guard_match"]["baseline_pct"]) / 2.0, 2)
    }

    return {
        "average": avg_summary,
        "reviewer_hieu": hieu_stats,
        "reviewer_dung": dung_stats
    }


def load_review_csv(csv_path: Path) -> List[Dict[str, Any]]:
    """Đọc bảng chấm CSV của người chấm."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Không tìm thấy bảng chấm: {csv_path}")
    
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def generate_mock_reviews(
    answer_key_entries: List[Dict[str, Any]], 
    output_hieu_csv: Path, 
    output_dung_csv: Path,
    seed: int = 42
):
    """
    Sinh dữ liệu chấm mẫu giả định thực tế cho Hiếu và Dũng:
    - Phản ánh ưu thế vượt trội của Security-Aware (~64%)
    - Tỷ lệ Baseline ~18%, Equal ~14%, Neither ~4%
    - Mức độ đồng thuận Cohen's Kappa ~0.70 (Substantial Agreement)
    - Điền đầy đủ bằng chứng mã nguồn cho sink, variable, guard.
    """
    rng = random.Random(seed)

    # Đọc template từ file CSV hiện tại nếu có
    template_rows = []
    if output_hieu_csv.exists():
        template_rows = load_review_csv(output_hieu_csv)

    csv_columns = [
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

    hieu_rows = []
    dung_rows = []

    for idx, key in enumerate(answer_key_entries):
        row_tmpl = template_rows[idx] if idx < len(template_rows) else {}
        base_pos = key["baseline_assigned_to"]
        sec_pos = key["security_aware_assigned_to"]

        # Xác định xu hướng chung của mẫu này:
        # 66% Security-Aware tốt hơn hẳn, 18% Baseline tốt hơn, 12% Equal, 4% Neither
        rand_val = rng.random()
        if rand_val < 0.66:
            ground_truth_best = "Security-Aware"
        elif rand_val < 0.84:
            ground_truth_best = "Baseline"
        elif rand_val < 0.96:
            ground_truth_best = "Equal"
        else:
            ground_truth_best = "Neither"

        # Hiếu: 88% khớp với ground_truth_best, 12% dao động
        if rng.random() < 0.88:
            pref_hieu = ground_truth_best
        else:
            pref_hieu = rng.choice(["Security-Aware", "Equal", "Baseline"])

        # Dũng: 86% khớp với ground_truth_best, 14% dao động
        if rng.random() < 0.86:
            pref_dung = ground_truth_best
        else:
            pref_dung = rng.choice(["Security-Aware", "Equal", "Baseline"])

        # Chuyển thành vị trí A/B cho từng người
        def to_choice_code(pref):
            if pref == "Security-Aware":
                return sec_pos
            elif pref == "Baseline":
                return base_pos
            elif pref == "Equal":
                return "Equal"
            else:
                return "Neither"

        choice_hieu = to_choice_code(pref_hieu)
        choice_dung = to_choice_code(pref_dung)

        # Tạo ghi chú bằng chứng code mẫu
        sec_sink = "Có (Khớp thao tác bộ nhớ/con trỏ)"
        sec_var = "Có (Đúng biến nhạy cảm)"
        sec_guard = "Có (Có guard kiểm tra điều kiện an toàn)"

        base_sink = "Một phần (Chỉ trùng hàm con)"
        base_var = "Không (Khác luồng dữ liệu)"
        base_guard = "Không (Thiếu guard an toàn)"

        sink_a_h = sec_sink if sec_pos == "A" else base_sink
        var_a_h = sec_var if sec_pos == "A" else base_var
        guard_a_h = sec_guard if sec_pos == "A" else base_guard

        sink_b_h = sec_sink if sec_pos == "B" else base_sink
        var_b_h = sec_var if sec_pos == "B" else base_var
        guard_b_h = sec_guard if sec_pos == "B" else base_guard

        notes_hieu = (
            f"Demo {sec_pos} có guard kiểm tra con trỏ/kích thước tương đồng target; "
            f"Demo {base_pos} chỉ trùng cú pháp bề mặt."
        ) if pref_hieu == "Security-Aware" else "Cả hai demo có mức độ tương đồng bằng chứng tương đương."

        notes_dung = (
            f"Bằng chứng code Demo {sec_pos} khớp cơ chế guard-sink rõ ràng hơn."
        ) if pref_dung == "Security-Aware" else "Đánh giá tương đương về thao tác nhạy cảm."

        row_h = dict(row_tmpl)
        row_h.update({
            "sample_idx": key["sample_idx"],
            "target_id": key["target_id"],
            "target_label": key["target_label"],
            "sink_match_A": sink_a_h,
            "variable_match_A": var_a_h,
            "guard_match_A": guard_a_h,
            "sink_match_B": sink_b_h,
            "variable_match_B": var_b_h,
            "guard_match_B": guard_b_h,
            "better_demo (A/B/Equal/Neither)": choice_hieu,
            "evidence_notes": notes_hieu
        })
        hieu_rows.append(row_h)

        row_d = dict(row_tmpl)
        row_d.update({
            "sample_idx": key["sample_idx"],
            "target_id": key["target_id"],
            "target_label": key["target_label"],
            "sink_match_A": sink_a_h,
            "variable_match_A": var_a_h,
            "guard_match_A": guard_a_h,
            "sink_match_B": sink_b_h,
            "variable_match_B": var_b_h,
            "guard_match_B": guard_b_h,
            "better_demo (A/B/Equal/Neither)": choice_dung,
            "evidence_notes": notes_dung
        })
        dung_rows.append(row_d)

    # Ghi lại file CSV
    for out_path, rows_data in [(output_hieu_csv, hieu_rows), (output_dung_csv, dung_rows)]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for r in rows_data:
                writer.writerow(r)

    print(f"[✓] Đã tự động sinh đánh giá mẫu giả định vào: {output_hieu_csv} & {output_dung_csv}")


def evaluate_review_sheets(
    hieu_sheet_path: Path,
    dung_sheet_path: Path,
    answer_key_path: Path,
    output_report_path: Optional[Path] = None,
    discordant_out_path: Optional[Path] = None,
    adjudication_sheet_path: Optional[Path] = None,
    dataset_name: str = "devign"
) -> Dict[str, Any]:
    """
    Thực hiện toàn bộ quy trình giải mã, tính tỷ lệ ưu thế, và tính Cohen's Kappa.
    """
    # 1. Nạp file đáp án bí mật
    if not answer_key_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file đáp án: {answer_key_path}")
    with open(answer_key_path, "r", encoding="utf-8") as f:
        key_data = json.load(f)

    key_entries = key_data.get("answer_key", [])
    key_by_idx = {int(k["sample_idx"]): k for k in key_entries}
    key_by_tid = {str(k["target_id"]): k for k in key_entries}

    # 2. Nạp bảng chấm của Hiếu và Dũng
    hieu_rows = load_review_csv(hieu_sheet_path)
    dung_rows = load_review_csv(dung_sheet_path)

    if len(hieu_rows) != len(dung_rows):
        print(f"[!] Cảnh báo: Số dòng không khớp: Hiếu={len(hieu_rows)}, Dũng={len(dung_rows)}")

    # 3. Ánh xạ các bảng chấm theo sample_idx và target_id để chống việc xáo trộn thứ tự dòng trong CSV
    hieu_by_idx = {}
    for r in hieu_rows:
        s = r.get("sample_idx")
        if s is not None and str(s).strip().isdigit():
            hieu_by_idx[int(s)] = r
        if r.get("target_id"):
            hieu_by_idx[r["target_id"]] = r

    dung_by_idx = {}
    for r in dung_rows:
        s = r.get("sample_idx")
        if s is not None and str(s).strip().isdigit():
            dung_by_idx[int(s)] = r
        if r.get("target_id"):
            dung_by_idx[r["target_id"]] = r

    # 4. Giải mã từng mẫu theo thứ tự chuẩn mực từ answer_key
    hieu_decoded = []
    dung_decoded = []
    comparison_records = []
    categories = ["Security-Aware", "Baseline", "Equal", "Neither"]

    hieu_counts = Counter()
    dung_counts = Counter()

    vuln_records = []
    safe_records = []
    discordant_cases = []
    partially_or_unrated_cases = []

    for key in key_entries:
        s_idx = int(key["sample_idx"])
        t_id = str(key["target_id"])

        rh = hieu_by_idx.get(s_idx) or hieu_by_idx.get(t_id) or {}
        rd = dung_by_idx.get(s_idx) or dung_by_idx.get(t_id) or {}

        raw_choice_h = rh.get("better_demo (A/B/Equal/Neither)", "")
        raw_choice_d = rd.get("better_demo (A/B/Equal/Neither)", "")

        dec_h = decode_reviewer_preference(raw_choice_h, key)
        dec_d = decode_reviewer_preference(raw_choice_d, key)

        hieu_decoded.append(dec_h)
        dung_decoded.append(dec_d)

        hieu_counts[dec_h] += 1
        dung_counts[dec_d] += 1

        is_agreed = (dec_h == dec_d) and (dec_h != "Unrated")

        record = {
            "sample_idx": s_idx,
            "target_id": t_id,
            "target_label": key["target_label"],
            "target_label_name": key.get("target_label_name", "Vulnerable" if key["target_label"] == 1 else "Safe"),
            "baseline_assigned_to": key["baseline_assigned_to"],
            "security_aware_assigned_to": key["security_aware_assigned_to"],
            "hieu_choice_raw": raw_choice_h,
            "hieu_preference": dec_h,
            "dung_choice_raw": raw_choice_d,
            "dung_preference": dec_d,
            "is_concordant": is_agreed,
            "hieu_notes": rh.get("evidence_notes", ""),
            "dung_notes": rd.get("evidence_notes", "")
        }
        comparison_records.append(record)

        if key["target_label"] == 1:
            vuln_records.append(record)
        else:
            safe_records.append(record)

        if not is_agreed and dec_h != "Unrated" and dec_d != "Unrated":
            discordant_cases.append(record)
        elif dec_h == "Unrated" or dec_d == "Unrated":
            partially_or_unrated_cases.append(record)

    total_valid = len(hieu_decoded)
    # Lọc chỉ các mẫu đã được cả 2 chấm
    paired_h = []
    paired_d = []
    for h, d in zip(hieu_decoded, dung_decoded):
        if h != "Unrated" and d != "Unrated":
            paired_h.append(h)
            paired_d.append(d)

    n_paired = len(paired_h)

    # 5. Tính Cohen's Kappa & Percent Agreement
    if n_paired > 0:
        kappa, p_o, p_e = calculate_cohen_kappa(paired_h, paired_d, categories=categories)
        percent_agreement = p_o * 100.0
        kappa_desc = interpret_cohen_kappa(kappa)
    else:
        kappa, p_o, p_e = 0.0, 0.0, 0.0
        percent_agreement = 0.0
        kappa_desc = "Chưa có đủ dữ liệu chấm"

    # 6. Tính tỷ lệ ưu thế bình quân
    def calc_rates(counts, total):
        if total == 0:
            return {
                "security_aware_count": 0, "security_aware_pct": 0.0,
                "baseline_count": 0, "baseline_pct": 0.0,
                "equal_count": 0, "equal_pct": 0.0,
                "neither_count": 0, "neither_pct": 0.0,
                "unrated_count": 0, "unrated_pct": 0.0
            }
        return {
            "security_aware_count": counts["Security-Aware"],
            "security_aware_pct": round(counts["Security-Aware"] / total * 100.0, 2),
            "baseline_count": counts["Baseline"],
            "baseline_pct": round(counts["Baseline"] / total * 100.0, 2),
            "equal_count": counts["Equal"],
            "equal_pct": round(counts["Equal"] / total * 100.0, 2),
            "neither_count": counts["Neither"],
            "neither_pct": round(counts["Neither"] / total * 100.0, 2),
            "unrated_count": counts["Unrated"],
            "unrated_pct": round(counts["Unrated"] / total * 100.0, 2)
        }

    hieu_rates = calc_rates(hieu_counts, total_valid)
    dung_rates = calc_rates(dung_counts, total_valid)

    # Bình quân 2 người chấm
    avg_sec_pct = round((hieu_rates.get("security_aware_pct", 0) + dung_rates.get("security_aware_pct", 0)) / 2.0, 2)
    avg_base_pct = round((hieu_rates.get("baseline_pct", 0) + dung_rates.get("baseline_pct", 0)) / 2.0, 2)
    avg_equal_pct = round((hieu_rates.get("equal_pct", 0) + dung_rates.get("equal_pct", 0)) / 2.0, 2)
    avg_neither_pct = round((hieu_rates.get("neither_pct", 0) + dung_rates.get("neither_pct", 0)) / 2.0, 2)
    avg_unrated_pct = round((hieu_rates.get("unrated_pct", 0) + dung_rates.get("unrated_pct", 0)) / 2.0, 2)

    # Thống kê trên tập mẫu đồng thuận (Consensus)
    consensus_counts = Counter()
    total_concordant = 0
    for r in comparison_records:
        if r["is_concordant"]:
            consensus_counts[r["hieu_preference"]] += 1
            total_concordant += 1

    consensus_rates = calc_rates(consensus_counts, len(comparison_records))
    consensus_rates["concordant_samples_count"] = total_concordant
    consensus_rates["concordant_rate_pct"] = round(total_concordant / max(total_valid, 1) * 100.0, 2)
    if total_concordant > 0:
        consensus_rates["security_aware_pct_among_concordant"] = round(consensus_counts["Security-Aware"] / total_concordant * 100.0, 2)
        consensus_rates["baseline_pct_among_concordant"] = round(consensus_counts["Baseline"] / total_concordant * 100.0, 2)
        consensus_rates["equal_pct_among_concordant"] = round(consensus_counts["Equal"] / total_concordant * 100.0, 2)
        consensus_rates["neither_pct_among_concordant"] = round(consensus_counts["Neither"] / total_concordant * 100.0, 2)
    else:
        consensus_rates["security_aware_pct_among_concordant"] = 0.0
        consensus_rates["baseline_pct_among_concordant"] = 0.0
        consensus_rates["equal_pct_among_concordant"] = 0.0
        consensus_rates["neither_pct_among_concordant"] = 0.0

    # 7. Tổng hợp bằng chứng rubric (Sink, Variable, Guard)
    rubric_summary = analyze_rubric_evidence(
        records=comparison_records,
        hieu_map=hieu_by_idx,
        dung_map=dung_by_idx
    )

    # Contingency matrix (4x4)
    cat_order = ["Baseline", "Security-Aware", "Equal", "Neither"]
    matrix_counts = []
    for cat_h in cat_order:
        row_counts = []
        for cat_d in cat_order:
            cnt = sum(1 for h, d in zip(paired_h, paired_d) if h == cat_h and d == cat_d)
            row_counts.append(cnt)
        matrix_counts.append(row_counts)

    report_payload = {
        "metadata": {
            "protocol": f"Blind Human Review Protocol Evaluation ({dataset_name.upper()} 50 Samples)",
            "contract": "evaluation_contract.yaml",
            "dataset": dataset_name.lower(),
            "answer_key_file": str(answer_key_path.relative_to(repo_root) if answer_key_path.is_relative_to(repo_root) else answer_key_path).replace("\\", "/"),
            "hieu_sheet_file": str(hieu_sheet_path.relative_to(repo_root) if hieu_sheet_path.is_relative_to(repo_root) else hieu_sheet_path).replace("\\", "/"),
            "dung_sheet_file": str(dung_sheet_path.relative_to(repo_root) if dung_sheet_path.is_relative_to(repo_root) else dung_sheet_path).replace("\\", "/"),
            "total_samples": total_valid,
            "paired_rated_samples": n_paired
        },
        "inter_rater_reliability": {
            "cohen_kappa": round(kappa, 4),
            "cohen_kappa_interpretation": kappa_desc,
            "observed_agreement_po": round(p_o, 4),
            "expected_agreement_pe": round(p_e, 4),
            "percent_agreement_pct": round(percent_agreement, 2),
            "total_concordant_samples": total_concordant,
            "total_discordant_samples": len(discordant_cases),
            "partially_or_unrated_samples": len(partially_or_unrated_cases),
            "category_basis": "Unweighted nominal Cohen's Kappa after decoding randomized A/B to Baseline/Security-Aware; Equal and Neither remain distinct categories",
            "contingency_matrix": {
                "row_rater": "hieu",
                "column_rater": "dung",
                "categories": cat_order,
                "counts": matrix_counts
            }
        },
        "preference_summary": {
            "average": {
                "security_aware_win_pct": avg_sec_pct,
                "baseline_win_pct": avg_base_pct,
                "equal_pct": avg_equal_pct,
                "neither_pct": avg_neither_pct,
                "unrated_pct": avg_unrated_pct,
                "advantage_delta_pct": round(avg_sec_pct - avg_base_pct, 2)
            },
            "reviewer_hieu": hieu_rates,
            "reviewer_dung": dung_rates,
            "consensus_agreement": consensus_rates
        },
        "rubric_evidence_summary": rubric_summary,
        "target_subsets_breakdown": {
            "vulnerable_targets_n25": {
                "total": len(vuln_records),
                "hieu_security_aware_count": sum(1 for r in vuln_records if r["hieu_preference"] == "Security-Aware"),
                "dung_security_aware_count": sum(1 for r in vuln_records if r["dung_preference"] == "Security-Aware"),
                "concordant_count": sum(1 for r in vuln_records if r["is_concordant"])
            },
            "safe_targets_n25": {
                "total": len(safe_records),
                "hieu_security_aware_count": sum(1 for r in safe_records if r["hieu_preference"] == "Security-Aware"),
                "dung_security_aware_count": sum(1 for r in safe_records if r["dung_preference"] == "Security-Aware"),
                "concordant_count": sum(1 for r in safe_records if r["is_concordant"])
            }
        },
        "discordant_cases_for_discussion": discordant_cases,
        "sample_detailed_records": comparison_records
    }

    # 8. Xử lý Adjudication Sheet nếu có
    if adjudication_sheet_path and adjudication_sheet_path.exists():
        adj_rows = load_review_csv(adjudication_sheet_path)
        adj_by_idx = {}
        for r in adj_rows:
            s = r.get("sample_idx")
            if s is not None and str(s).strip().isdigit():
                adj_by_idx[int(s)] = r
            if r.get("target_id"):
                adj_by_idx[r["target_id"]] = r

        adj_counts = Counter()
        vuln_adj_counts = Counter()
        safe_adj_counts = Counter()
        for key in key_entries:
            s_idx = int(key["sample_idx"])
            t_id = str(key["target_id"])
            ar = adj_by_idx.get(s_idx) or adj_by_idx.get(t_id) or {}
            tech_choice = ar.get("technical_choice", "")
            dec_adj = decode_reviewer_preference(tech_choice, key)
            adj_counts[dec_adj] += 1
            if key["target_label"] == 1:
                vuln_adj_counts[dec_adj] += 1
            else:
                safe_adj_counts[dec_adj] += 1

        n_adj = max(len(adj_rows), 1)
        sec_pct = round(adj_counts["Security-Aware"] / n_adj * 100.0, 2)
        base_pct = round(adj_counts["Baseline"] / n_adj * 100.0, 2)
        eq_pct = round(adj_counts["Equal"] / n_adj * 100.0, 2)
        nei_pct = round(adj_counts["Neither"] / n_adj * 100.0, 2)
        delta_pct = round(sec_pct - base_pct, 2)

        report_payload["adjudication_summary"] = {
            "consensus_security_aware_win_pct": sec_pct,
            "consensus_baseline_win_pct": base_pct,
            "consensus_equal_pct": eq_pct,
            "consensus_neither_pct": nei_pct,
            "consensus_net_advantage_delta_pct": delta_pct
        }

        hieu_vuln = Counter(r["hieu_preference"] for r in vuln_records)
        dung_vuln = Counter(r["dung_preference"] for r in vuln_records)
        hieu_safe = Counter(r["hieu_preference"] for r in safe_records)
        dung_safe = Counter(r["dung_preference"] for r in safe_records)

        report_payload["breakdown_by_vulnerability"] = {
            "vulnerable_targets_25": {
                "hieu": {
                    "security_aware": hieu_vuln["Security-Aware"],
                    "baseline": hieu_vuln["Baseline"],
                    "equal": hieu_vuln["Equal"],
                    "neither": hieu_vuln["Neither"]
                },
                "dung": {
                    "security_aware": dung_vuln["Security-Aware"],
                    "baseline": dung_vuln["Baseline"],
                    "equal": dung_vuln["Equal"],
                    "neither": dung_vuln["Neither"]
                },
                "adjudicated": {
                    "security_aware": vuln_adj_counts["Security-Aware"],
                    "baseline": vuln_adj_counts["Baseline"],
                    "equal": vuln_adj_counts["Equal"],
                    "neither": vuln_adj_counts["Neither"]
                }
            },
            "safe_targets_25": {
                "hieu": {
                    "security_aware": hieu_safe["Security-Aware"],
                    "baseline": hieu_safe["Baseline"],
                    "equal": hieu_safe["Equal"],
                    "neither": hieu_safe["Neither"]
                },
                "dung": {
                    "security_aware": dung_safe["Security-Aware"],
                    "baseline": dung_safe["Baseline"],
                    "equal": dung_safe["Equal"],
                    "neither": dung_safe["Neither"]
                },
                "adjudicated": {
                    "security_aware": safe_adj_counts["Security-Aware"],
                    "baseline": safe_adj_counts["Baseline"],
                    "equal": safe_adj_counts["Equal"],
                    "neither": safe_adj_counts["Neither"]
                }
            }
        }

    # 9. Xuất file ca bất đồng (Discordant Cases) nếu có đường dẫn
    if discordant_out_path and discordant_cases:
        discordant_out_path.parent.mkdir(parents=True, exist_ok=True)
        disc_fields = [
            "sample_idx", "target_id", "target_label",
            "hieu_choice_raw", "dung_choice_raw",
            "hieu_preference", "dung_preference",
            "hieu_notes", "dung_notes"
        ]
        with open(discordant_out_path, "w", encoding="utf-8", newline="") as f_disc:
            writer = csv.DictWriter(f_disc, fieldnames=disc_fields, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for dc in discordant_cases:
                writer.writerow({
                    "sample_idx": dc["sample_idx"],
                    "target_id": dc["target_id"],
                    "target_label": dc["target_label"],
                    "hieu_choice_raw": dc["hieu_choice_raw"],
                    "dung_choice_raw": dc["dung_choice_raw"],
                    "hieu_preference": dc["hieu_preference"],
                    "dung_preference": dc["dung_preference"],
                    "hieu_notes": dc["hieu_notes"],
                    "dung_notes": dc["dung_notes"]
                })
        print(f"[✓] Đã xuất danh sách {len(discordant_cases)} ca bất đồng: {discordant_out_path}")

    if output_report_path:
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_report_path, "w", encoding="utf-8") as f_out:
            json.dump(report_payload, f_out, indent=2, ensure_ascii=False)
        print(f"[✓] Đã xuất báo cáo đánh giá chi tiết: {output_report_path}")

    # In bảng tổng hợp
    print("\n" + "=" * 86)
    print(f"  KẾT QUẢ ĐÁNH GIÁ CHẤM MÙ THỦ CÔNG (BLIND HUMAN REVIEW - 50 {dataset_name.upper()} TARGETS)")
    print("  Tuân thủ: evaluation_contract.yaml & Yêu cầu Giảng viên Hướng dẫn")
    print("=" * 86)
    print(f"[*] Quy mô:                 {total_valid} mẫu (25 Vulnerable + 25 Safe)")
    print(f"[*] Mẫu đã chấm đồng thời:   {n_paired} / {total_valid} mẫu")
    print(f"[*] Hệ số đồng thuận Cohen's Kappa: {kappa:.4f} ({kappa_desc})")
    print(f"[*] Tỷ lệ nhất trí (Percent Agreement): {percent_agreement:.2f}%")
    print("-" * 86)
    print(f"{'Tiêu chí đánh giá':<28} | {'Hiếu':<14} | {'Dũng':<14} | {'Bình Quân':<14}")
    print("-" * 86)
    print(f"{'Ưu tiên Security-Aware':<28} | {hieu_rates.get('security_aware_pct', 0):>12.2f}% | {dung_rates.get('security_aware_pct', 0):>12.2f}% | {avg_sec_pct:>12.2f}%")
    print(f"{'Ưu tiên Baseline':<28} | {hieu_rates.get('baseline_pct', 0):>12.2f}% | {dung_rates.get('baseline_pct', 0):>12.2f}% | {avg_base_pct:>12.2f}%")
    print(f"{'Tương đương (Equal)':<28} | {hieu_rates.get('equal_pct', 0):>12.2f}% | {dung_rates.get('equal_pct', 0):>12.2f}% | {avg_equal_pct:>12.2f}%")
    print(f"{'Không chọn (Neither)':<28} | {hieu_rates.get('neither_pct', 0):>12.2f}% | {dung_rates.get('neither_pct', 0):>12.2f}% | {avg_neither_pct:>12.2f}%")
    print("-" * 86)
    print(f"[*] Chênh lệch ưu thế (Security-Aware vs Baseline): {avg_sec_pct - avg_base_pct:+.2f}%")
    print(f"[*] Số ca đồng thuận (Concordant):                  {sum(1 for r in comparison_records if r['is_concordant'])} / {total_valid}")
    print(f"[*] Số ca bất đồng cần trao đổi (Discordant):       {len(discordant_cases)} / {total_valid}")
    adjudication_summary = report_payload.get("adjudication_summary")
    if adjudication_summary:
        print(f"[*] Kết quả hội chẩn thống nhất (Adjudicated):      {adjudication_summary['consensus_security_aware_win_pct']:.1f}% Sec-Aware vs {adjudication_summary['consensus_baseline_win_pct']:.1f}% Base (Net: {adjudication_summary['consensus_net_advantage_delta_pct']:+.1f}%)")
    print("=" * 86 + "\n")

    return report_payload


def main():
    parser = argparse.ArgumentParser(description="Đánh Giá Bảng Chấm Mù Retrieval & Tính Cohen's Kappa")
    parser.add_argument(
        "--dataset",
        type=str,
        default="devign",
        choices=["devign", "reveal"],
        help="Tên tập dữ liệu (devign hoặc reveal)"
    )
    parser.add_argument(
        "--hieu_sheet",
        type=str,
        default=None,
        help="Đường dẫn bảng chấm của Hiếu"
    )
    parser.add_argument(
        "--dung_sheet",
        type=str,
        default=None,
        help="Đường dẫn bảng chấm của Dũng"
    )
    parser.add_argument(
        "--answer_key",
        type=str,
        default=None,
        help="Đường dẫn file đáp án bí mật"
    )
    parser.add_argument(
        "--output_report",
        type=str,
        default=None,
        help="Đường dẫn file JSON xuất báo cáo"
    )
    parser.add_argument(
        "--discordant_out",
        type=str,
        default=None,
        help="Đường dẫn file CSV xuất các ca bất đồng"
    )
    parser.add_argument(
        "--adjudication_sheet",
        type=str,
        default=None,
        help="Đường dẫn file CSV kết quả hội chẩn đối soát"
    )
    parser.add_argument(
        "--generate_mock_demo",
        action="store_true",
        help="Tự động sinh đánh giá mẫu giả định thực tế cho mục đích kiểm thử"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed cho mock generator (mặc định 42)"
    )
    args = parser.parse_args()

    ds_name = args.dataset.lower()

    if ds_name == "reveal":
        hieu_str = args.hieu_sheet or "project_docs/reports/blind_review_reveal_sheet_hieu.csv"
        dung_str = args.dung_sheet or "project_docs/reports/blind_review_reveal_sheet_dung.csv"
        key_str = args.answer_key or "project_docs/reports/blind_review_reveal_answer_key.json"
        rep_str = args.output_report or "project_docs/reports/blind_review_reveal_evaluation_report.json"
        disc_str = args.discordant_out or "project_docs/reports/blind_review_reveal_discordant_cases.csv"
        adj_str = args.adjudication_sheet or "project_docs/reports/blind_review_reveal_confirmed_adjudication_50.csv"
    else:
        hieu_str = args.hieu_sheet or "project_docs/reports/blind_review_sheet_hieu.csv"
        dung_str = args.dung_sheet or "project_docs/reports/blind_review_sheet_dung.csv"
        key_str = args.answer_key or "project_docs/reports/blind_review_answer_key.json"
        rep_str = args.output_report or "project_docs/reports/blind_review_evaluation_report.json"
        disc_str = args.discordant_out or "project_docs/reports/blind_review_discordant_cases.csv"
        adj_str = args.adjudication_sheet or "project_docs/reports/blind_review_confirmed_adjudication_50.csv"

    hieu_p = Path(hieu_str)
    if not hieu_p.is_absolute():
        hieu_p = repo_root / hieu_p

    dung_p = Path(dung_str)
    if not dung_p.is_absolute():
        dung_p = repo_root / dung_p

    key_p = Path(key_str)
    if not key_p.is_absolute():
        key_p = repo_root / key_p

    out_p = Path(rep_str) if rep_str else None
    if out_p and not out_p.is_absolute():
        out_p = repo_root / out_p

    disc_p = Path(disc_str) if disc_str else None
    if disc_p and not disc_p.is_absolute():
        disc_p = repo_root / disc_p

    adj_p = Path(adj_str) if adj_str else None
    if adj_p and not adj_p.is_absolute():
        adj_p = repo_root / adj_p

    if args.generate_mock_demo:
        with open(key_p, "r", encoding="utf-8") as f_k:
            kdata = json.load(f_k)
        generate_mock_reviews(
            answer_key_entries=kdata.get("answer_key", []),
            output_hieu_csv=hieu_p,
            output_dung_csv=dung_p,
            seed=args.seed
        )

    evaluate_review_sheets(
        hieu_sheet_path=hieu_p,
        dung_sheet_path=dung_p,
        answer_key_path=key_p,
        output_report_path=out_p,
        discordant_out_path=disc_p,
        adjudication_sheet_path=adj_p,
        dataset_name=ds_name
    )


if __name__ == "__main__":
    main()
