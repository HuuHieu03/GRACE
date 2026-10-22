#!/usr/bin/env python3
"""
Script Sửa Lỗi Mapping Code Target Cho Thí Nghiệm Chấm Mù Thủ Công ReVeal (GRACE).
Tuân thủ:
- evaluation_contract.yaml
- project_docs/reports/v1.1.0_2026-10-22_supervisor_readiness_second_review.md (Mục 3.D)

Chức năng:
1. Đọc danh sách 50 mẫu phân tầng sạch ReVeal từ blind_review_reveal_answer_key.json.
2. Trích xuất mã nguồn C canonical chuẩn xác 100% từ data/raw_c_files/reveal/validation/.
3. Cập nhật cột target_code_snippet trong:
   - project_docs/reports/blind_review_reveal_sheet_hieu.csv
   - project_docs/reports/blind_review_reveal_sheet_dung.csv
4. Bảo toàn nguyên vẹn 100% tất cả các cột đánh giá, mã rubric, ghi chú và nhãn chấm.
"""

import os
import sys
import csv
import json
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

repo_root = Path(__file__).resolve().parent.parent

CANONICAL_SOURCES = {
    1: ("7817292828288926681", "data/raw_c_files/reveal/validation/id_1906_hash_7817292828288926681_label_1_debian.c"),
    2: ("-2654475221056024278", "data/raw_c_files/reveal/validation/id_1926_hash_-2654475221056024278_label_1_debian.c"),
    3: ("1931051720960659129", "data/raw_c_files/reveal/validation/id_2013_hash_1931051720960659129_label_1_debian.c"),
    4: ("3528176083733952042", "data/raw_c_files/reveal/validation/id_2027_hash_3528176083733952042_label_1_debian.c"),
    5: ("453825853695477219", "data/raw_c_files/reveal/validation/id_2108_hash_453825853695477219_label_1_debian.c"),
    6: ("7078129966845159750", "data/raw_c_files/reveal/validation/id_2157_hash_7078129966845159750_label_1_debian.c"),
    7: ("4561548163749120103", "data/raw_c_files/reveal/validation/id_2234_hash_4561548163749120103_label_1_chrome.c"),
    8: ("-2614908340588220483", "data/raw_c_files/reveal/validation/id_277_hash_-2614908340588220483_label_1_chrome.c"),
    9: ("4620577553943347649", "data/raw_c_files/reveal/validation/id_297_hash_4620577553943347649_label_1_debian.c"),
    10: ("2930500905204315787", "data/raw_c_files/reveal/validation/id_366_hash_2930500905204315787_label_1_debian.c"),
    11: ("-8029592471297395650", "data/raw_c_files/reveal/validation/id_385_hash_-8029592471297395650_label_1_debian.c"),
    12: ("-4078760840682683657", "data/raw_c_files/reveal/validation/id_432_hash_-4078760840682683657_label_1_chrome.c"),
    13: ("-2971164434690241379", "data/raw_c_files/reveal/validation/id_485_hash_-2971164434690241379_label_1_debian.c"),
    14: ("1470723493451072803", "data/raw_c_files/reveal/validation/id_556_hash_1470723493451072803_label_1_debian.c"),
    15: ("8952659721822029396", "data/raw_c_files/reveal/validation/id_563_hash_8952659721822029396_label_1_debian.c"),
    16: ("1286774465219423144", "data/raw_c_files/reveal/validation/id_570_hash_1286774465219423144_label_1_debian.c"),
    17: ("-16551315108292821", "data/raw_c_files/reveal/validation/id_572_hash_-16551315108292821_label_1_debian.c"),
    18: ("8425497811998776592", "data/raw_c_files/reveal/validation/id_632_hash_8425497811998776592_label_1_debian.c"),
    19: ("-755883256379441954", "data/raw_c_files/reveal/validation/id_661_hash_-755883256379441954_label_1_chrome.c"),
    20: ("-4765077557530511796", "data/raw_c_files/reveal/validation/id_712_hash_-4765077557530511796_label_1_chrome.c"),
    21: ("1274314752608585941", "data/raw_c_files/reveal/validation/id_729_hash_1274314752608585941_label_1_chrome.c"),
    22: ("-3569070884878445567", "data/raw_c_files/reveal/validation/id_779_hash_-3569070884878445567_label_1_debian.c"),
    23: ("2518148041181868265", "data/raw_c_files/reveal/validation/id_782_hash_2518148041181868265_label_1_debian.c"),
    24: ("-4055702019813176658", "data/raw_c_files/reveal/validation/id_837_hash_-4055702019813176658_label_1_debian.c"),
    25: ("-4886619136962902359", "data/raw_c_files/reveal/validation/id_898_hash_-4886619136962902359_label_1_chrome.c"),
    26: ("-3819889754140204145", "data/raw_c_files/reveal/validation/id_0_hash_-3819889754140204145_label_0_debian.c"),
    27: ("-2607754285145856562", "data/raw_c_files/reveal/validation/id_1_hash_-2607754285145856562_label_0_debian.c"),
    28: ("-4552633429382740307", "data/raw_c_files/reveal/validation/id_2_hash_-4552633429382740307_label_0_debian.c"),
    29: ("-2064332158282087279", "data/raw_c_files/reveal/validation/id_3_hash_-2064332158282087279_label_0_debian.c"),
    30: ("2687336064028423153", "data/raw_c_files/reveal/validation/id_4_hash_2687336064028423153_label_0_chrome.c"),
    31: ("-3847447574854829409", "data/raw_c_files/reveal/validation/id_5_hash_-3847447574854829409_label_0_chrome.c"),
    32: ("-7777331401175181229", "data/raw_c_files/reveal/validation/id_7_hash_-7777331401175181229_label_0_debian.c"),
    33: ("-5992472514718425579", "data/raw_c_files/reveal/validation/id_8_hash_-5992472514718425579_label_0_debian.c"),
    34: ("-6856626433814917486", "data/raw_c_files/reveal/validation/id_9_hash_-6856626433814917486_label_0_debian.c"),
    35: ("6393050609822897742", "data/raw_c_files/reveal/validation/id_10_hash_6393050609822897742_label_0_debian.c"),
    36: ("-5357254031401749470", "data/raw_c_files/reveal/validation/id_11_hash_-5357254031401749470_label_0_debian.c"),
    37: ("1760449185745615462", "data/raw_c_files/reveal/validation/id_12_hash_1760449185745615462_label_0_debian.c"),
    38: ("-341028540041678099", "data/raw_c_files/reveal/validation/id_13_hash_-341028540041678099_label_0_debian.c"),
    39: ("8460430819945784394", "data/raw_c_files/reveal/validation/id_15_hash_8460430819945784394_label_0_debian.c"),
    40: ("4976989049001279223", "data/raw_c_files/reveal/validation/id_16_hash_4976989049001279223_label_0_debian.c"),
    41: ("-7187272991279783781", "data/raw_c_files/reveal/validation/id_17_hash_-7187272991279783781_label_0_debian.c"),
    42: ("-7136186224744987223", "data/raw_c_files/reveal/validation/id_18_hash_-7136186224744987223_label_0_debian.c"),
    43: ("-4558261210024070448", "data/raw_c_files/reveal/validation/id_20_hash_-4558261210024070448_label_0_chrome.c"),
    44: ("-1111775978048960297", "data/raw_c_files/reveal/validation/id_21_hash_-1111775978048960297_label_0_chrome.c"),
    45: ("8281630545066492937", "data/raw_c_files/reveal/validation/id_22_hash_8281630545066492937_label_0_debian.c"),
    46: ("5400542917484463750", "data/raw_c_files/reveal/validation/id_25_hash_5400542917484463750_label_0_chrome.c"),
    47: ("-2323311514228246061", "data/raw_c_files/reveal/validation/id_26_hash_-2323311514228246061_label_0_chrome.c"),
    48: ("-704025756752474526", "data/raw_c_files/reveal/validation/id_27_hash_-704025756752474526_label_0_debian.c"),
    49: ("-1315695702746584250", "data/raw_c_files/reveal/validation/id_29_hash_-1315695702746584250_label_0_debian.c"),
    50: ("-8115807672627724050", "data/raw_c_files/reveal/validation/id_31_hash_-8115807672627724050_label_0_debian.c"),
}


def format_code_snippet(code: str, max_chars: int = 3000) -> str:
    """Chuẩn hóa và cắt gọn snippet mã nguồn nếu cần, bảo đảm đọc tốt trong bảng tính."""
    if not code:
        return "/* Code unavailable */"
    code_clean = code.replace("\r\n", "\n").replace("\r", "\n").strip()
    code_clean = re.sub(r'\n{3,}', '\n\n', code_clean)
    if len(code_clean) > max_chars:
        return code_clean[:max_chars] + f"\n\n/* ... [Cắt gọn do vượt quá {max_chars} ký tự] */"
    return code_clean


def get_canonical_snippet(idx: int) -> str:
    target_id, rel_path = CANONICAL_SOURCES[idx]
    full_path = repo_root / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"Missing canonical C file: {full_path}")
    raw_c = full_path.read_text(encoding="utf-8", errors="replace")
    return format_code_snippet(raw_c, max_chars=3000)


def fix_sheet(sheet_path: Path):
    with sheet_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    updated_count = 0
    for r in rows:
        idx = int(r["sample_idx"])
        expected_id, _ = CANONICAL_SOURCES[idx]
        assert r["target_id"] == expected_id, f"ID mismatch at row {idx}: {r['target_id']} != {expected_id}"
        canonical_code = get_canonical_snippet(idx)
        if r["target_code_snippet"] != canonical_code:
            r["target_code_snippet"] = canonical_code
            updated_count += 1

    with sheet_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"[✓] Đã cập nhật {updated_count}/50 target snippets trong {sheet_path.name}")


def main():
    hieu_path = repo_root / "project_docs" / "reports" / "blind_review_reveal_sheet_hieu.csv"
    dung_path = repo_root / "project_docs" / "reports" / "blind_review_reveal_sheet_dung.csv"
    print("[*] Sửa lỗi mapping code target ReVeal...")
    fix_sheet(hieu_path)
    fix_sheet(dung_path)
    print("[✓] Hoàn tất 100% sửa lỗi mapping code target ReVeal!")


if __name__ == "__main__":
    main()
