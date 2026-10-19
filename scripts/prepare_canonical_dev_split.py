"""
Prepare Canonical Clean Dev Split (Stage 2 - Step 1)
Tuân thủ Hợp đồng Đánh giá: evaluation_contract.yaml

Chức năng:
1. Tải tập validation theo chuẩn evaluation_contract.yaml:
   - Devign: DetectVul/devign@main#validation (ưu tiên local metadata/processed)
   - ReVeal: claudios/ReVeal@main#validation (ưu tiên local metadata/processed)
2. Đối soát với báo cáo kiểm toán rò rỉ:
   - project_docs/reports/code_leakage_audit_report.json
   - Xây dựng bảng băm tập Train để loại bỏ 100% các mẫu Exact Duplicate với Train
   - Loại bỏ 100% các mẫu bị mâu thuẫn gán nhãn (Contradictory Labels)
3. Trích xuất 100 mẫu phân tầng ngẫu nhiên với seed: 42:
   - Đúng 50 mẫu Vulnerable (target: 1)
   - Đúng 50 mẫu Safe (target: 0)
4. Xuất danh sách ID ra:
   - data/splits/devign_dev_clean_100_ids.json
   - data/splits/reveal_dev_clean_100_ids.json
"""

import sys
import io
import os
import re
import json
import hashlib
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def strip_c_comments(code: str) -> str:
    """Loại bỏ toàn bộ chú thích C/C++ (block & line comments), giữ chuỗi ký tự."""
    def replacer(match):
        s = match.group(0)
        return " " if s.startswith('/') else s

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, code)


def normalize_code_semantic(code: str) -> str:
    """Chuẩn hóa ngữ nghĩa mã nguồn: xóa comment, thu gọn khoảng trắng."""
    no_comments = strip_c_comments(code)
    literals = []
    literal_pattern = re.compile(r'\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"', re.DOTALL)

    def save_literal(match):
        idx = len(literals)
        literals.append(match.group(0))
        return f"\x00__LIT_{idx}__\x00"

    masked = literal_pattern.sub(save_literal, no_comments)
    normalized = re.sub(r'\s+', ' ', masked).strip()
    normalized = re.sub(r'(\w)\s+\(', r'\1(', normalized)
    normalized = re.sub(r'\(\s+', '(', normalized)
    normalized = re.sub(r'\s+\)', ')', normalized)
    normalized = re.sub(r'(\w)\s+\[', r'\1[', normalized)

    def restore_literal(match):
        idx = int(match.group(1))
        return literals[idx]

    return re.sub(r'\x00__LIT_(\d+)__\x00', restore_literal, normalized)


def hash_string(s: str) -> str:
    """SHA-256 (32 ký tự hex đầu)."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32]


def parse_sample_record(raw_item: Dict[str, Any], idx: int, dataset_name: str) -> Dict[str, Any]:
    """Trích xuất và chuẩn hóa thông tin mẫu từ metadata / processed JSON."""
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

    project = raw_item.get("project", "unknown")
    c_file_path = raw_item.get("c_file_path", "")

    # Định danh ID theo chuẩn repo: ReVeal dùng hash string, Devign dùng filename .c
    if dataset_name.lower() == "reveal":
        raw_id = raw_item.get("id", raw_item.get("hash", raw_item.get("idx", f"sample_{idx}")))
        canonical_id = str(raw_id)
    elif c_file_path:
        # Nếu có c_file_path, lấy tên file làm canonical identifier
        canonical_id = Path(c_file_path).name
    elif dataset_name.lower() == "devign":
        raw_id = raw_item.get("id", raw_item.get("idx", idx))
        canonical_id = f"id_{raw_id}_label_{bool(target)}_{project}.c"
    else:
        raw_id = raw_item.get("id", raw_item.get("hash", raw_item.get("idx", f"sample_{idx}")))
        canonical_id = str(raw_id)

    raw_numeric_id = str(raw_item.get("id", raw_item.get("hash", raw_item.get("idx", idx))))

    return {
        "canonical_id": canonical_id,
        "raw_id": raw_numeric_id,
        "code": str(code),
        "target": target,
        "project": str(project),
        "c_file_path": str(c_file_path),
        "nodes": raw_item.get("node", raw_item.get("nodes", [])),
        "edges": raw_item.get("edge", raw_item.get("edges", [])),
        "raw": raw_item
    }


def stream_json_array(file_path: Path, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    """Đọc file JSON lớn theo cơ chế luồng để tiết kiệm RAM."""
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
                        items.append(obj)
                        idx += 1
                        if max_items is not None and len(items) >= max_items:
                            break
                    except Exception:
                        pass
    return items


def load_dataset_split(
    dataset_name: str,
    split: str,
    repo_root: Path
) -> List[Dict[str, Any]]:
    """
    Tải split dữ liệu:
    1. Ưu tiên tìm file metadata trong data/raw_c_files/{dataset}/{split}_metadata.json
    2. Nếu không có, tìm data/processed/{dataset}_{split}_processed.json
    3. Nếu không có, tải từ Hugging Face
    """
    ds_clean = dataset_name.lower()
    
    candidates = [
        repo_root / "data" / "raw_c_files" / ds_clean / f"{split}_metadata.json",
        repo_root / "data" / "raw_c_files" / ds_clean / f"{'valid' if split == 'validation' else split}_metadata.json",
        repo_root / "data" / "processed" / f"{ds_clean}_{split}_processed.json",
        repo_root / "data" / "processed" / f"{ds_clean}_{'valid' if split == 'validation' else split}_processed.json",
    ]

    raw_items = None
    for p in candidates:
        if p.exists() and p.stat().st_size > 10:
            file_size_mb = p.stat().st_size / (1024 * 1024)
            print(f"[*] Tìm thấy file cục bộ cho {dataset_name} ({split}): {p} ({file_size_mb:.1f} MB)")
            if file_size_mb > 500:
                raw_items = stream_json_array(p)
            else:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    raw_items = data
                elif isinstance(data, dict):
                    raw_items = data.get("items") or data.get("samples") or data.get("data") or []
            break

    if raw_items is None:
        hf_name = "DetectVul/devign" if ds_clean == "devign" else "claudios/ReVeal"
        print(f"[*] Đang tải {hf_name} (split='{split}') từ Hugging Face...")
        try:
            from datasets import load_dataset
            hf_ds = load_dataset(hf_name, split=split)
            raw_items = list(hf_ds)
            print(f"[✓] Tải thành công {len(raw_items)} mẫu từ Hugging Face.")
        except Exception as e:
            raise RuntimeError(f"Không thể tải {dataset_name} ({split}) từ cả local và Hugging Face: {e}")

    parsed = [parse_sample_record(item, i, dataset_name) for i, item in enumerate(raw_items)]
    print(f"[✓] Đã chuẩn hóa {len(parsed)} mẫu cho {dataset_name} ({split}).")
    return parsed


def load_leakage_audit_blacklist(leakage_report_path: Path) -> Set[str]:
    """
    Nạp danh sách blacklist các ID/mẫu bị đánh dấu rò rỉ hoặc mâu thuẫn nhãn
    từ file code_leakage_audit_report.json.
    """
    blacklisted_ids = set()
    if not leakage_report_path.exists():
        print(f"[!] Cảnh báo: Không tìm thấy báo cáo kiểm toán rò rỉ tại {leakage_report_path}. Bỏ qua nạp blacklist tĩnh.")
        return blacklisted_ids

    try:
        with open(leakage_report_path, "r", encoding="utf-8") as f:
            reports = json.load(f)

        if isinstance(reports, dict):
            reports = [reports]

        for rep in reports:
            # Kiểm tra exact_duplicates
            for sample in rep.get("exact_duplicates", {}).get("samples", []):
                tid = sample.get("test_id")
                if tid:
                    blacklisted_ids.add(str(tid))
                for mid in sample.get("matched_train_ids", []):
                    blacklisted_ids.add(str(mid))

            # Kiểm tra normalized_duplicates có mâu thuẫn nhãn
            for sample in rep.get("normalized_duplicates", {}).get("samples", []):
                if sample.get("is_contradictory"):
                    tid = sample.get("test_id")
                    if tid:
                        blacklisted_ids.add(str(tid))
                    for mid in sample.get("matched_train_ids", []):
                        blacklisted_ids.add(str(mid))

        print(f"[✓] Nạp {len(blacklisted_ids)} ID blacklist từ báo cáo kiểm toán rò rỉ.")
    except Exception as e:
        print(f"[!] Lỗi khi đọc báo cáo kiểm toán rò rỉ ({e}). Bỏ qua.")

    return blacklisted_ids


def build_train_code_maps(train_samples: List[Dict[str, Any]]) -> Tuple[Dict[str, Set[int]], Dict[str, Set[int]]]:
    """
    Xây dựng bảng băm mã nguồn tập Train:
    1. exact_map: sha256(raw_code.strip()) -> set of targets (0, 1)
    2. norm_map: sha256(normalize_code_semantic(raw_code)) -> set of targets (0, 1)
    """
    exact_map: Dict[str, Set[int]] = defaultdict(set)
    norm_map: Dict[str, Set[int]] = defaultdict(set)

    for s in train_samples:
        code_raw = s["code"].strip()
        if not code_raw:
            continue
        exact_h = hash_string(code_raw)
        exact_map[exact_h].add(s["target"])

        norm_code = normalize_code_semantic(code_raw)
        norm_h = hash_string(norm_code)
        norm_map[norm_h].add(s["target"])

    return exact_map, norm_map


def filter_clean_dev_samples(
    dev_samples: List[Dict[str, Any]],
    train_exact_map: Dict[str, Set[int]],
    train_norm_map: Dict[str, Set[int]],
    leakage_blacklist: Set[str]
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Lọc bỏ 100% mẫu validation bị:
    - Trùng lặp Exact Duplicate với tập Train
    - Bị mâu thuẫn gán nhãn với tập Train (Contradictory Labels)
    - Nằm trong blacklist báo cáo kiểm toán rò rỉ
    - Mã nguồn rỗng hoặc quá ngắn (< 15 ký tự)
    """
    clean_samples = []
    stats = {
        "total_dev": len(dev_samples),
        "excluded_exact_train_dup": 0,
        "excluded_contradictory_norm": 0,
        "excluded_leakage_blacklist": 0,
        "excluded_empty_code": 0,
        "clean_retained": 0
    }

    for s in dev_samples:
        code_raw = s["code"].strip()
        if len(code_raw) < 15:
            stats["excluded_empty_code"] += 1
            continue

        cid = s["canonical_id"]
        rid = s["raw_id"]
        if cid in leakage_blacklist or rid in leakage_blacklist:
            stats["excluded_leakage_blacklist"] += 1
            continue

        exact_h = hash_string(code_raw)
        if exact_h in train_exact_map:
            # Exact duplicate với tập train -> LOẠI BỎ 100%
            stats["excluded_exact_train_dup"] += 1
            continue

        norm_h = hash_string(normalize_code_semantic(code_raw))
        if norm_h in train_norm_map:
            train_targets = train_norm_map[norm_h]
            # Nếu nhãn trong train khác hoàn toàn với nhãn dev -> Contradictory Label
            if s["target"] not in train_targets:
                stats["excluded_contradictory_norm"] += 1
                continue

        clean_samples.append(s)

    stats["clean_retained"] = len(clean_samples)
    return clean_samples, stats


def stratified_sample_clean_dev(
    clean_samples: List[Dict[str, Any]],
    num_samples: int = 100,
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Trích xuất đúng 100 mẫu phân tầng ngẫu nhiên với seed: 42
    (đúng num_samples // 2 mẫu Vuln và num_samples // 2 mẫu Safe).
    """
    num_vuln = num_samples // 2
    num_safe = num_samples - num_vuln

    vuln_pool = [s for s in clean_samples if s["target"] == 1]
    safe_pool = [s for s in clean_samples if s["target"] == 0]

    if len(vuln_pool) < num_vuln:
        raise ValueError(f"Không đủ mẫu Vulnerable sạch (yêu cầu {num_vuln}, chỉ có {len(vuln_pool)})!")
    if len(safe_pool) < num_safe:
        raise ValueError(f"Không đủ mẫu Safe sạch (yêu cầu {num_safe}, chỉ có {len(safe_pool)})!")

    # Sắp xếp theo canonical_id trước để đảm bảo tính tất định hoàn hảo
    vuln_pool.sort(key=lambda x: str(x["canonical_id"]))
    safe_pool.sort(key=lambda x: str(x["canonical_id"]))

    rng = random.Random(seed)
    selected_vuln = rng.sample(vuln_pool, num_vuln)
    selected_safe = rng.sample(safe_pool, num_safe)

    combined = selected_vuln + selected_safe
    # Shuffle lại để phân bổ ngẫu nhiên nhãn trong tập kết quả
    rng.shuffle(combined)
    return combined


def create_split_record(
    dataset_name: str,
    dataset_version: str,
    source_split: str,
    selected_samples: List[Dict[str, Any]],
    seed: int = 42
) -> Dict[str, Any]:
    """Tạo payload JSON của file split tuân thủ hợp đồng."""
    sample_ids = [s["canonical_id"] for s in selected_samples]
    
    # Tính SHA-256 hash của danh sách IDs đã sắp xếp để bảo toàn tính toàn vẹn
    sorted_ids_str = ",".join(sorted(sample_ids))
    split_id_hash = hashlib.sha256(sorted_ids_str.encode("utf-8")).hexdigest()[:16]

    vuln_count = sum(1 for s in selected_samples if s["target"] == 1)
    safe_count = sum(1 for s in selected_samples if s["target"] == 0)

    sample_details = []
    for s in selected_samples:
        sample_details.append({
            "id": s["canonical_id"],
            "raw_id": s["raw_id"],
            "target": s["target"],
            "project": s["project"],
            "c_file_path": s["c_file_path"],
            "code": s["code"],
            "func": s["code"],
            "code_preview": s["code"][:120].replace("\n", " "),
            "nodes": s["nodes"],
            "edges": s["edges"],
            "num_nodes": len(s["nodes"]),
            "num_edges": len(s["edges"])
        })

    return {
        "split_name": f"{dataset_name.lower()}_dev_clean_{len(selected_samples)}",
        "dataset": dataset_name.lower(),
        "dataset_version": dataset_version,
        "source_split": source_split,
        "total_samples": len(selected_samples),
        "vulnerable_count": vuln_count,
        "safe_count": safe_count,
        "vulnerable_ratio": round(vuln_count / len(selected_samples), 4),
        "seed": seed,
        "split_id_hash_sha256_short": split_id_hash,
        "sample_ids": sample_ids,
        "sample_details": sample_details
    }


def process_dataset(
    dataset_name: str,
    dataset_version: str,
    source_split_uri: str,
    repo_root: Path,
    leakage_blacklist: Set[str],
    output_file: Path,
    num_samples: int = 100,
    seed: int = 42
) -> Dict[str, Any]:
    """Xử lý toàn diện cho 1 bộ dữ liệu (Devign hoặc ReVeal)."""
    print(f"\n{'='*75}")
    print(f"  XỬ LÝ CHUẨN HÓA TẬP DEV SẠCH: [{dataset_name.upper()}]")
    print(f"{'='*75}")

    # 1. Nạp validation split
    dev_samples = load_dataset_split(dataset_name, "validation", repo_root)

    # 2. Nạp train split để đối soát rò rỉ
    train_samples = load_dataset_split(dataset_name, "train", repo_root)

    # 3. Xây dựng train code hash maps
    print(f"[*] Xây dựng bảng băm cho {len(train_samples)} mẫu tập Train {dataset_name}...")
    exact_map, norm_map = build_train_code_maps(train_samples)
    print(f"[✓] Train exact unique hashes: {len(exact_map)} | norm unique hashes: {len(norm_map)}")

    # 4. Lọc sạch tập Dev
    print(f"[*] Tiến hành đối soát rò rỉ và làm sạch {len(dev_samples)} mẫu Validation...")
    clean_samples, filter_stats = filter_clean_dev_samples(dev_samples, exact_map, norm_map, leakage_blacklist)
    print(f"[*] Kết quả lọc:")
    print(f"    - Tổng mẫu Validation ban đầu:       {filter_stats['total_dev']}")
    print(f"    - Loại trừ Exact Duplicate với Train: {filter_stats['excluded_exact_train_dup']}")
    print(f"    - Loại trừ Mâu Thuẫn Nhãn (Contradict):{filter_stats['excluded_contradictory_norm']}")
    print(f"    - Loại trừ Blacklist Rò Rỉ:          {filter_stats['excluded_leakage_blacklist']}")
    print(f"    - Loại trừ Mã Nguồn Rỗng / Quá Ngắn: {filter_stats['excluded_empty_code']}")
    print(f"    - SỐ MẪU SẠCH GIỮ LẠI (CLEAN POOL):   {filter_stats['clean_retained']}")

    vuln_in_clean = sum(1 for s in clean_samples if s["target"] == 1)
    safe_in_clean = sum(1 for s in clean_samples if s["target"] == 0)
    print(f"    - Phân bố pool sạch: Vulnerable = {vuln_in_clean} | Safe = {safe_in_clean}")

    # 5. Stratified Sampling 100 mẫu với seed: 42
    print(f"[*] Trích xuất {num_samples} mẫu phân tầng ngẫu nhiên (seed={seed})...")
    selected = stratified_sample_clean_dev(clean_samples, num_samples=num_samples, seed=seed)

    split_payload = create_split_record(
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        source_split=source_split_uri,
        selected_samples=selected,
        seed=seed
    )

    # 6. Ghi file JSON
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(split_payload, f, indent=2, ensure_ascii=False)

    print(f"[✓] ĐÃ LƯU THÀNH CÔNG: {output_file}")
    print(f"    - Tổng số mẫu: {split_payload['total_samples']} (Vuln: {split_payload['vulnerable_count']}, Safe: {split_payload['safe_count']})")
    print(f"    - Hash toàn vẹn (SHA-256): {split_payload['split_id_hash_sha256_short']}")
    print(f"{'='*75}\n")
    return split_payload


def main():
    parser = argparse.ArgumentParser(description="GRACE Stage 2 Canonical Dev Split Preparation")
    parser.add_argument("--repo_root", type=str, default=".", help="Đường dẫn thư mục gốc repository")
    parser.add_argument("--num_samples", type=int, default=100, help="Số lượng mẫu dev cần trích xuất (mặc định 100)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (mặc định 42)")
    parser.add_argument("--skip_reveal", action="store_true", help="Bỏ qua ReVeal nếu chỉ cần Devign")
    parser.add_argument("--skip_devign", action="store_true", help="Bỏ qua Devign nếu chỉ cần ReVeal")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    leakage_report_candidates = [
        repo_root / "project_docs" / "reports" / "code_leakage_audit_report.json",
        repo_root / "output" / "code_leakage_audit_report.json"
    ]
    leakage_report_path = repo_root / "project_docs" / "reports" / "code_leakage_audit_report.json"
    for cand in leakage_report_candidates:
        if cand.exists():
            leakage_report_path = cand
            break

    leakage_blacklist = load_leakage_audit_blacklist(leakage_report_path)

    # Xử lý Devign
    if not args.skip_devign:
        devign_out = repo_root / "data" / "splits" / f"devign_dev_clean_{args.num_samples}_ids.json"
        process_dataset(
            dataset_name="devign",
            dataset_version="DetectVul/devign@main",
            source_split_uri="hf://datasets/DetectVul/devign@main#validation",
            repo_root=repo_root,
            leakage_blacklist=leakage_blacklist,
            output_file=devign_out,
            num_samples=args.num_samples,
            seed=args.seed
        )

    # Xử lý ReVeal
    if not args.skip_reveal:
        reveal_out = repo_root / "data" / "splits" / f"reveal_dev_clean_{args.num_samples}_ids.json"
        process_dataset(
            dataset_name="reveal",
            dataset_version="claudios/ReVeal@main",
            source_split_uri="hf://datasets/claudios/ReVeal@main#validation",
            repo_root=repo_root,
            leakage_blacklist=leakage_blacklist,
            output_file=reveal_out,
            num_samples=args.num_samples,
            seed=args.seed
        )

    print("[✓] Hoàn thành toàn bộ quy trình chuẩn bị tập Dev sạch chuẩn hợp đồng Đợt 2.")


if __name__ == "__main__":
    main()
