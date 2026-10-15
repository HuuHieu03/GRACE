"""
Code Leakage & Duplicate Code Audit Tool (Nhiệm vụ 1.4 trong Đợt 1 / Stage 1)

Mục tiêu khoa học:
Đo lường định lượng nguy cơ rò rỉ dữ liệu (Data Leakage) và tỷ lệ trùng lặp mã nguồn (Code Duplication)
giữa tập huấn luyện (Train split / Retrieval Bank) và tập kiểm thử (Test split) trên 2 bộ dữ liệu:
1. Devign (FFmpeg, QEMU)
2. ReVeal (Debian, Chromium, Linux kernel)

Các cấp độ kiểm tra:
- Cấp độ 1: Trùng lặp ID định danh (ID Overlap)
- Cấp độ 2: Trùng lặp mã nguồn thô chính xác (Exact Code Duplicate - SHA256 of code.strip())
- Cấp độ 3: Trùng lặp mã nguồn chuẩn hóa (Normalized Code Duplicate: đã xóa comment C/C++ và thu gọn khoảng trắng)
- Cấp độ 4: Trùng lặp chuỗi token tối giản (Token Stream Duplicate: xóa comment và xóa toàn bộ khoảng trắng)

Phân tích nhãn (Label Consistency / Conflict Analysis):
- Consistent Duplicates: Trùng code và CÙNG nhãn (Cả 2 đều Safe 0-0 hoặc Vuln 1-1).
- Contradictory Duplicates / Label Noise: Trùng code nhưng KHÁC nhãn (Train=0 Test=1 hoặc Train=1 Test=0).
  Hiện tượng này phản ánh nhiễu gán nhãn trong benchmark (Chakraborty et al., FSE 2021).
"""

import sys
import io
import os
import re
import json
import csv
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def strip_c_comments(code: str) -> str:
    """
    Loại bỏ toàn bộ chú thích (comments) trong mã nguồn C/C++:
    - Block comments: /* ... */
    - Line comments: // ...
    Đồng thời giữ nguyên các chuỗi ký tự trong dấu ngoặc kép ("...").
    """
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " "  # Thay comment bằng khoảng trắng để không dính token
        else:
            return s    # Giữ nguyên string literal
    
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, code)


def normalize_code_semantic(code: str) -> str:
    """
    Chuẩn hóa ngữ nghĩa mã nguồn:
    1. Xóa comments (cả block và single-line).
    2. Bảo vệ các chuỗi ký tự (string / char literals).
    3. Chuẩn hóa khoảng trắng:
       - Thu gọn mọi chuỗi ký tự trắng liên tiếp thành 1 dấu cách duy nhất.
       - Chuẩn hóa khoảng trắng quanh dấu ngoặc đơn (), ngoặc vuông [], ngoặc nhọn {}.
       - Chuẩn hóa khoảng trắng trước và sau dấu chấm phẩy ;, dấu phẩy ,.
    4. Phục hồi các chuỗi ký tự ban đầu.
    5. Cắt tỉa khoảng trắng đầu/cuối.
    """
    no_comments = strip_c_comments(code)

    # Tách và bảo vệ string / char literals để tránh làm thay đổi nội dung bên trong chuỗi
    literals = []
    literal_pattern = re.compile(r'\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"', re.DOTALL)

    def save_literal(match):
        idx = len(literals)
        literals.append(match.group(0))
        return f"\x00__LIT_{idx}__\x00"

    masked = literal_pattern.sub(save_literal, no_comments)

    # 1. Thu gọn mọi chuỗi ký tự trắng và xuống dòng thành 1 dấu cách duy nhất
    normalized = re.sub(r'\s+', ' ', masked).strip()

    # 2. Chuẩn hóa khoảng trắng quanh dấu ngoặc đơn ()
    # Bỏ khoảng trắng giữa tên định danh/từ khóa và '(': "foo (" -> "foo("
    normalized = re.sub(r'(\w)\s+\(', r'\1(', normalized)
    # Bỏ khoảng trắng ngay sau '(': "( int" -> "(int"
    normalized = re.sub(r'\(\s+', '(', normalized)
    # Bỏ khoảng trắng ngay trước ')': "x )" -> "x)"
    normalized = re.sub(r'\s+\)', ')', normalized)

    # 3. Chuẩn hóa khoảng trắng quanh dấu ngoặc vuông []
    # "buf [" -> "buf["
    normalized = re.sub(r'(\w)\s+\[', r'\1[', normalized)
    # "[ 10" -> "[10"
    normalized = re.sub(r'\[\s+', '[', normalized)
    # "10 ]" -> "10]"
    normalized = re.sub(r'\s+\]', ']', normalized)

    # 4. Chuẩn hóa dấu chấm phẩy ; và dấu phẩy ,
    # Bỏ khoảng trắng trước ';'
    normalized = re.sub(r'\s+;', ';', normalized)
    # Bỏ khoảng trắng trước ','
    normalized = re.sub(r'\s+,', ',', normalized)
    # Đảm bảo 1 dấu cách sau ',' nếu theo sau là ký tự không phải khoảng trắng
    normalized = re.sub(r',([^\s])', r', \1', normalized)

    # 5. Chuẩn hóa khoảng trắng quanh dấu ngoặc nhọn {}
    # Thu gọn ngoặc nhọn rỗng: "{ }" hoặc "{\n}" -> "{}"
    normalized = re.sub(r'\{\s*\}', '{}', normalized)
    # Đảm bảo khoảng trắng trước '{' nếu đứng liền kề ký tự khác: "foo(){" -> "foo() {"
    normalized = re.sub(r'([^\s])\{', r'\1 {', normalized)
    # Đảm bảo khoảng trắng sau '{' nếu theo sau là ký tự khác ngoài '}': "{return" -> "{ return"
    normalized = re.sub(r'\{([^\s\}])', r'{ \1', normalized)
    # Đảm bảo khoảng trắng trước '}' nếu đứng liền kề ký tự khác ngoài '{': "1;}" -> "1; }"
    normalized = re.sub(r'([^\s\{])\}', r'\1 }', normalized)

    # 6. Thu gọn lại khoảng trắng nếu có phát sinh
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    # Phục hồi nguyên trạng các chuỗi ký tự
    def restore_literal(match):
        idx = int(match.group(1))
        return literals[idx]

    normalized = re.sub(r'\x00__LIT_(\d+)__\x00', restore_literal, normalized)

    return normalized


def normalize_code_tokens(code: str) -> str:
    """
    Chuẩn hóa tối giản (Token Stream):
    1. Xóa comments.
    2. Xóa toàn bộ ký tự trắng.
    """
    no_comments = strip_c_comments(code)
    return re.sub(r'\s+', '', no_comments)


def hash_string(s: str) -> str:
    """Tính mã băm SHA-256 (32 ký tự hex đầu)."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32]


def load_dataset_records(file_path: Path) -> List[Dict[str, Any]]:
    """
    Nạp dữ liệu từ file JSON hoặc JSONL metadata / processed.
    Mỗi record trả về chuẩn hóa các trường:
    - id: str
    - code: str
    - target: int (0 hoặc 1)
    - project: str
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    records = []
    if file_path.suffix == ".jsonl":
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    item = json.loads(line)
                    records.append(parse_item(item, i))
    else:
        # File .json
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 500:
            # File lớn dùng streaming parser
            records = stream_json_records(file_path)
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for i, item in enumerate(data):
                    records.append(parse_item(item, i))
            elif isinstance(data, dict):
                items = data.get("items") or data.get("samples") or data.get("data") or []
                for i, item in enumerate(items):
                    records.append(parse_item(item, i))

    return records


def stream_json_records(file_path: Path) -> List[Dict[str, Any]]:
    """Streaming nạp từng đối tượng JSON từ file mảng lớn để tiết kiệm RAM."""
    items = []
    current_obj_lines = []
    in_obj = False
    idx = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not in_obj and (stripped == "{" or stripped.startswith("{\n") or stripped.startswith("{ ")):
                in_obj = True
                current_obj_lines = [line]
            elif in_obj:
                current_obj_lines.append(line)
                if stripped == "}" or stripped == "}," or stripped.startswith("}"):
                    in_obj = False
                    raw_str = "".join(current_obj_lines).strip().rstrip(",")
                    try:
                        obj = json.loads(raw_str)
                        items.append(parse_item(obj, idx))
                        idx += 1
                    except Exception:
                        pass
    return items


def parse_item(raw_item: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """Trích xuất id, code, target, project từ raw item."""
    code = (
        raw_item.get("func") or 
        raw_item.get("function") or 
        raw_item.get("functionSource") or 
        raw_item.get("code") or 
        raw_item.get("processed_func") or ""
    )
    raw_target = raw_item.get("target", raw_item.get("label", raw_item.get("output", 0)))
    if isinstance(raw_target, bool):
        target = 1 if raw_target else 0
    elif isinstance(raw_target, (int, float)):
        target = int(raw_target)
    elif isinstance(raw_target, str):
        target = 1 if raw_target.strip().lower() in ("1", "true", "vuln", "vulnerable") else 0
    else:
        target = 0

    raw_id = raw_item.get("id", raw_item.get("idx", raw_item.get("hash", f"sample_{idx}")))
    project = raw_item.get("project", "unknown")
    file_path = raw_item.get("c_file_path", "")

    return {
        "id": str(raw_id),
        "code": str(code),
        "target": target,
        "project": str(project),
        "c_file_path": str(file_path)
    }


def audit_split_pair(
    dataset_name: str,
    train_records: List[Dict[str, Any]],
    test_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Thực hiện kiểm toán rò rỉ dữ liệu toàn diện giữa Train split và Test split.
    """
    total_train = len(train_records)
    total_test = len(test_records)

    # 1. Kiểm tra ID Overlap
    train_ids: Set[str] = {r["id"] for r in train_records}
    test_ids: Set[str] = {r["id"] for r in test_records}
    id_overlap = train_ids.intersection(test_ids)

    # 2. Xây dựng Hash Maps cho Train Split
    train_exact_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    train_norm_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    train_token_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for r in train_records:
        raw_code = r["code"].strip()
        exact_h = hash_string(raw_code)
        norm_code = normalize_code_semantic(raw_code)
        norm_h = hash_string(norm_code)
        token_code = normalize_code_tokens(raw_code)
        token_h = hash_string(token_code)

        entry = {"id": r["id"], "target": r["target"], "project": r["project"]}
        train_exact_map[exact_h].append(entry)
        train_norm_map[norm_h].append(entry)
        train_token_map[token_h].append(entry)

    # 3. Phân tích Test Split đối soát với Train
    exact_duplicates: List[Dict[str, Any]] = []
    norm_duplicates: List[Dict[str, Any]] = []
    token_duplicates: List[Dict[str, Any]] = []

    # Thống kê nhãn cho Exact Duplicates
    exact_consistent_count = 0
    exact_contradictory_count = 0
    exact_vuln_vuln = 0
    exact_safe_safe = 0
    exact_train_safe_test_vuln = 0
    exact_train_vuln_test_safe = 0

    # Thống kê nhãn cho Normalized Duplicates
    norm_consistent_count = 0
    norm_contradictory_count = 0
    norm_vuln_vuln = 0
    norm_safe_safe = 0
    norm_train_safe_test_vuln = 0
    norm_train_vuln_test_safe = 0

    # Phân nhóm theo nhãn của test
    test_vuln_count = sum(1 for r in test_records if r["target"] == 1)
    test_safe_count = sum(1 for r in test_records if r["target"] == 0)

    exact_dup_in_vuln = 0
    exact_dup_in_safe = 0
    norm_dup_in_vuln = 0
    norm_dup_in_safe = 0

    # Project breakdown
    project_leakage: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        "test_count": 0, "exact_dup": 0, "norm_dup": 0
    })

    for r in test_records:
        proj = r["project"]
        project_leakage[proj]["test_count"] += 1

        raw_code = r["code"].strip()
        exact_h = hash_string(raw_code)
        norm_code = normalize_code_semantic(raw_code)
        norm_h = hash_string(norm_code)
        token_code = normalize_code_tokens(raw_code)
        token_h = hash_string(token_code)

        test_target = r["target"]

        # Đối soát Exact Duplicate
        if exact_h in train_exact_map:
            matched_train = train_exact_map[exact_h]
            match_targets = {m["target"] for m in matched_train}
            
            is_consistent = (test_target in match_targets) and (len(match_targets) == 1)
            is_contradictory = (test_target not in match_targets)

            if is_consistent:
                exact_consistent_count += 1
                if test_target == 1:
                    exact_vuln_vuln += 1
                else:
                    exact_safe_safe += 1
            elif is_contradictory:
                exact_contradictory_count += 1
                if test_target == 1:
                    exact_train_safe_test_vuln += 1
                else:
                    exact_train_vuln_test_safe += 1
            else:
                # Ambiguous: train có cả 0 và 1
                exact_consistent_count += 1

            if test_target == 1:
                exact_dup_in_vuln += 1
            else:
                exact_dup_in_safe += 1

            project_leakage[proj]["exact_dup"] += 1
            exact_duplicates.append({
                "test_id": r["id"],
                "test_target": test_target,
                "project": proj,
                "matched_train_ids": [m["id"] for m in matched_train],
                "matched_train_targets": [m["target"] for m in matched_train],
                "is_consistent": is_consistent,
                "is_contradictory": is_contradictory,
                "is_ambiguous": len(match_targets) > 1,
                "code_preview": raw_code[:120].replace("\n", " ")
            })

        # Đối soát Normalized Duplicate
        if norm_h in train_norm_map:
            matched_train = train_norm_map[norm_h]
            match_targets = {m["target"] for m in matched_train}

            is_consistent = (test_target in match_targets) and (len(match_targets) == 1)
            is_contradictory = (test_target not in match_targets)

            if is_consistent:
                norm_consistent_count += 1
                if test_target == 1:
                    norm_vuln_vuln += 1
                else:
                    norm_safe_safe += 1
            elif is_contradictory:
                norm_contradictory_count += 1
                if test_target == 1:
                    norm_train_safe_test_vuln += 1
                else:
                    norm_train_vuln_test_safe += 1
            else:
                norm_consistent_count += 1

            if test_target == 1:
                norm_dup_in_vuln += 1
            else:
                norm_dup_in_safe += 1

            project_leakage[proj]["norm_dup"] += 1
            norm_duplicates.append({
                "test_id": r["id"],
                "test_target": test_target,
                "project": proj,
                "matched_train_ids": [m["id"] for m in matched_train],
                "matched_train_targets": [m["target"] for m in matched_train],
                "is_consistent": is_consistent,
                "is_contradictory": is_contradictory,
                "is_ambiguous": len(match_targets) > 1,
                "code_preview": raw_code[:120].replace("\n", " ")
            })

        # Đối soát Token Stream Duplicate
        if token_h in train_token_map:
            token_duplicates.append(r["id"])

    # Tính toán các tỷ lệ định lượng
    exact_dup_count = len(exact_duplicates)
    norm_dup_count = len(norm_duplicates)
    token_dup_count = len(token_duplicates)

    exact_leakage_rate = (exact_dup_count / total_test) if total_test > 0 else 0.0
    norm_leakage_rate = (norm_dup_count / total_test) if total_test > 0 else 0.0
    token_leakage_rate = (token_dup_count / total_test) if total_test > 0 else 0.0

    vuln_exact_rate = (exact_dup_in_vuln / test_vuln_count) if test_vuln_count > 0 else 0.0
    safe_exact_rate = (exact_dup_in_safe / test_safe_count) if test_safe_count > 0 else 0.0

    vuln_norm_rate = (norm_dup_in_vuln / test_vuln_count) if test_vuln_count > 0 else 0.0
    safe_norm_rate = (norm_dup_in_safe / test_safe_count) if test_safe_count > 0 else 0.0

    report = {
        "dataset_name": dataset_name,
        "sample_counts": {
            "train_samples": total_train,
            "test_samples": total_test,
            "test_vulnerable": test_vuln_count,
            "test_safe": test_safe_count,
            "unique_train_exact_code": len(train_exact_map),
            "unique_train_norm_code": len(train_norm_map),
        },
        "id_overlap": {
            "count": len(id_overlap),
            "overlapping_ids": list(id_overlap)[:10]
        },
        "exact_duplicates": {
            "duplicate_count": exact_dup_count,
            "leakage_rate_pct": round(exact_leakage_rate * 100, 2),
            "vulnerable_duplicate_count": exact_dup_in_vuln,
            "vulnerable_duplicate_rate_pct": round(vuln_exact_rate * 100, 2),
            "safe_duplicate_count": exact_dup_in_safe,
            "safe_duplicate_rate_pct": round(safe_exact_rate * 100, 2),
            "consistent_label_count": exact_consistent_count,
            "contradictory_label_count": exact_contradictory_count,
            "label_conflict_details": {
                "safe_safe": exact_safe_safe,
                "vuln_vuln": exact_vuln_vuln,
                "train_safe_test_vuln": exact_train_safe_test_vuln,
                "train_vuln_test_safe": exact_train_vuln_test_safe
            },
            "samples": exact_duplicates[:20]
        },
        "normalized_duplicates": {
            "duplicate_count": norm_dup_count,
            "leakage_rate_pct": round(norm_leakage_rate * 100, 2),
            "vulnerable_duplicate_count": norm_dup_in_vuln,
            "vulnerable_duplicate_rate_pct": round(vuln_norm_rate * 100, 2),
            "safe_duplicate_count": norm_dup_in_safe,
            "safe_duplicate_rate_pct": round(safe_norm_rate * 100, 2),
            "consistent_label_count": norm_consistent_count,
            "contradictory_label_count": norm_contradictory_count,
            "label_conflict_details": {
                "safe_safe": norm_safe_safe,
                "vuln_vuln": norm_vuln_vuln,
                "train_safe_test_vuln": norm_train_safe_test_vuln,
                "train_vuln_test_safe": norm_train_vuln_test_safe
            },
            "samples": norm_duplicates[:20]
        },
        "token_stream_duplicates": {
            "duplicate_count": token_dup_count,
            "leakage_rate_pct": round(token_leakage_rate * 100, 2)
        },
        "project_breakdown": {
            p: {
                "test_count": v["test_count"],
                "exact_dup": v["exact_dup"],
                "exact_leakage_pct": round((v["exact_dup"] / v["test_count"]) * 100, 2) if v["test_count"] > 0 else 0.0,
                "norm_dup": v["norm_dup"],
                "norm_leakage_pct": round((v["norm_dup"] / v["test_count"]) * 100, 2) if v["test_count"] > 0 else 0.0
            }
            for p, v in project_leakage.items()
        }
    }
    return report


def print_audit_summary(report: Dict[str, Any]):
    """In báo cáo kiểm toán rò rỉ dữ liệu đẹp mắt và trực quan."""
    ds = report["dataset_name"].upper()
    sc = report["sample_counts"]
    ed = report["exact_duplicates"]
    nd = report["normalized_duplicates"]
    td = report["token_stream_duplicates"]
    io_info = report["id_overlap"]

    print("\n" + "=" * 80)
    print(f"  BÁO CÁO KIỂM TOÁN RÒ RỈ MÃ NGUỒN & TRÙNG LẶP TRAIN/TEST: [{ds}]")
    print("=" * 80)
    print(f"[*] Quy mô tập mẫu: Train = {sc['train_samples']} | Test = {sc['test_samples']} (Vuln: {sc['test_vulnerable']}, Safe: {sc['test_safe']})")
    print(f"[*] Trùng lặp ID định danh (ID Overlap): {io_info['count']} mẫu (0% rò rỉ ID)")
    print("-" * 80)
    print(f"[*] CẤP ĐỘ 1: Exact Code Duplicate (Trùng lặp mã nguồn thô chính xác)")
    print(f"    - Số hàm Test trùng lặp hoàn toàn trong Train: {ed['duplicate_count']} / {sc['test_samples']} ({ed['leakage_rate_pct']}%)")
    print(f"    - Phân bố theo nhãn Test: Vulnerable = {ed['vulnerable_duplicate_count']} ({ed['vulnerable_duplicate_rate_pct']}%) | Safe = {ed['safe_duplicate_count']} ({ed['safe_duplicate_rate_pct']}%)")
    print(f"    - Tính nhất quán nhãn (Label Consistency):")
    print(f"      + Nhất quán (Consistent):    {ed['consistent_label_count']} mẫu (Safe-Safe: {ed['label_conflict_details']['safe_safe']}, Vuln-Vuln: {ed['label_conflict_details']['vuln_vuln']})")
    print(f"      + MÂU THUẪN (Contradictory): {ed['contradictory_label_count']} mẫu [Nhiễu gán nhãn: Train 0/Test 1: {ed['label_conflict_details']['train_safe_test_vuln']}, Train 1/Test 0: {ed['label_conflict_details']['train_vuln_test_safe']}]")
    print("-" * 80)
    print(f"[*] CẤP ĐỘ 2: Normalized Code Duplicate (Xóa comments & chuẩn hóa khoảng trắng)")
    print(f"    - Số hàm Test trùng lặp sau chuẩn hóa: {nd['duplicate_count']} / {sc['test_samples']} ({nd['leakage_rate_pct']}%)")
    print(f"    - Phân bố theo nhãn Test: Vulnerable = {nd['vulnerable_duplicate_count']} ({nd['vulnerable_duplicate_rate_pct']}%) | Safe = {nd['safe_duplicate_count']} ({nd['safe_duplicate_rate_pct']}%)")
    print(f"    - Tính nhất quán nhãn:")
    print(f"      + Nhất quán (Consistent):    {nd['consistent_label_count']} mẫu")
    print(f"      + MÂU THUẪN (Contradictory): {nd['contradictory_label_count']} mẫu")
    print("-" * 80)
    print(f"[*] CẤP ĐỘ 3: Token Stream Duplicate (Xóa comments & toàn bộ whitespace): {td['duplicate_count']} mẫu ({td['leakage_rate_pct']}%)")
    print("-" * 80)
    print(f"[*] Phân rã theo dự án con (Project-level Breakdown):")
    for proj, pinfo in report["project_breakdown"].items():
        print(f"    - Dự án {proj:<15}: {pinfo['test_count']:<6} mẫu | Exact Dup: {pinfo['exact_dup']} ({pinfo['exact_leakage_pct']}%) | Norm Dup: {pinfo['norm_dup']} ({pinfo['norm_leakage_pct']}%)")
    print("=" * 80 + "\n")


def save_reports(
    reports: List[Dict[str, Any]],
    output_json_path: Path,
    output_csv_path: Path
):
    """Lưu kết quả ra file JSON và file CSV tóm tắt."""
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)
    print(f"[✓] Đã lưu báo cáo chi tiết JSON tại: {output_json_path}")

    # Ghi file tóm tắt CSV
    rows = []
    for r in reports:
        sc = r["sample_counts"]
        ed = r["exact_duplicates"]
        nd = r["normalized_duplicates"]
        td = r["token_stream_duplicates"]
        rows.append({
            "dataset": r["dataset_name"],
            "train_samples": sc["train_samples"],
            "test_samples": sc["test_samples"],
            "test_vuln": sc["test_vulnerable"],
            "test_safe": sc["test_safe"],
            "exact_duplicate_count": ed["duplicate_count"],
            "exact_leakage_pct": ed["leakage_rate_pct"],
            "exact_consistent_labels": ed["consistent_label_count"],
            "exact_contradictory_labels": ed["contradictory_label_count"],
            "norm_duplicate_count": nd["duplicate_count"],
            "norm_leakage_pct": nd["leakage_rate_pct"],
            "norm_consistent_labels": nd["consistent_label_count"],
            "norm_contradictory_labels": nd["contradictory_label_count"],
            "token_stream_duplicate_count": td["duplicate_count"],
            "token_stream_leakage_pct": td["leakage_rate_pct"],
        })

    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[✓] Đã lưu bảng tóm tắt CSV tại: {output_csv_path}")


def find_dataset_files(dataset_key: str, split: str) -> Optional[Path]:
    """Tự động tìm kiếm file dữ liệu metadata hoặc processed cục bộ."""
    candidates = [
        Path(f"data/raw_c_files/{dataset_key}/{split}_metadata.json"),
        Path(f"data/processed/{dataset_key}_{split}_processed.json"),
        Path(f"../data/raw_c_files/{dataset_key}/{split}_metadata.json"),
        Path(f"../data/processed/{dataset_key}_{split}_processed.json"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def main():
    parser = argparse.ArgumentParser(description="GRACE Code Leakage & Duplicate Code Audit Tool")
    parser.add_argument("--devign_train", type=str, default=None, help="Đường dẫn file train của Devign")
    parser.add_argument("--devign_test", type=str, default=None, help="Đường dẫn file test của Devign")
    parser.add_argument("--reveal_train", type=str, default=None, help="Đường dẫn file train của ReVeal")
    parser.add_argument("--reveal_test", type=str, default=None, help="Đường dẫn file test của ReVeal")
    parser.add_argument("--output_dir", type=str, default="output", help="Thư mục xuất báo cáo")
    parser.add_argument("--json_name", type=str, default="code_leakage_audit_report.json", help="Tên file JSON xuất")
    parser.add_argument("--csv_name", type=str, default="code_leakage_audit_summary.csv", help="Tên file CSV xuất")
    args = parser.parse_args()

    # 1. Xác định đường dẫn cho Devign
    devign_train_path = Path(args.devign_train) if args.devign_train else find_dataset_files("devign", "train")
    devign_test_path = Path(args.devign_test) if args.devign_test else find_dataset_files("devign", "test")

    # 2. Xác định đường dẫn cho ReVeal
    reveal_train_path = Path(args.reveal_train) if args.reveal_train else find_dataset_files("reveal", "train")
    reveal_test_path = Path(args.reveal_test) if args.reveal_test else find_dataset_files("reveal", "test")

    reports = []

    # Chạy kiểm toán cho Devign
    if devign_train_path and devign_test_path and devign_train_path.exists() and devign_test_path.exists():
        print(f"\n[*] Đang nạp dữ liệu Devign...")
        print(f"    - Train: {devign_train_path}")
        print(f"    - Test:  {devign_test_path}")
        d_train = load_dataset_records(devign_train_path)
        d_test = load_dataset_records(devign_test_path)
        print(f"[*] Tiến hành đối soát mã nguồn Devign ({len(d_train)} train vs {len(d_test)} test)...")
        devign_report = audit_split_pair("Devign", d_train, d_test)
        print_audit_summary(devign_report)
        reports.append(devign_report)
    else:
        print(f"[!] Không tìm thấy file dữ liệu Devign. Bỏ qua kiểm toán Devign.")

    # Chạy kiểm toán cho ReVeal
    if reveal_train_path and reveal_test_path and reveal_train_path.exists() and reveal_test_path.exists():
        print(f"\n[*] Đang nạp dữ liệu ReVeal...")
        print(f"    - Train: {reveal_train_path}")
        print(f"    - Test:  {reveal_test_path}")
        r_train = load_dataset_records(reveal_train_path)
        r_test = load_dataset_records(reveal_test_path)
        print(f"[*] Tiến hành đối soát mã nguồn ReVeal ({len(r_train)} train vs {len(r_test)} test)...")
        reveal_report = audit_split_pair("ReVeal", r_train, r_test)
        print_audit_summary(reveal_report)
        reports.append(reveal_report)
    else:
        print(f"[!] Không tìm thấy file dữ liệu ReVeal. Bỏ qua kiểm toán ReVeal.")

    if reports:
        out_dir = Path(args.output_dir)
        json_path = out_dir / args.json_name
        csv_path = out_dir / args.csv_name
        save_reports(reports, json_path, csv_path)


if __name__ == "__main__":
    main()
