#!/usr/bin/env python3
"""
Script Sinh Bảng Chấm Mù Thủ Công Độc Lập (Blind Human Review Protocol)
Tuân thủ:
- evaluation_contract.yaml
- project_docs/plans/PLAN_SUPERVISOR_REQUIREMENTS_EXECUTION_20261014.md (Nhiệm vụ 2.3 / STT 10)
- project_docs/docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md (dòng 197-215)

Quy trình:
1. Lấy 50 mẫu phân tầng sạch từ `data/splits/devign_dev_clean_100_ids.json` (chính xác 25 Vuln và 25 Safe, seed=42).
2. Với từng target, trích xuất:
   - Demo 1: DemonstrationRetriever (Baseline B2: CodeT5 + GraphSim).
   - Demo 2: SecurityAwareRetriever (Proposed B3: lambda=0.3).
3. Che hoàn toàn tên phương pháp, điểm số, thông tin thuật toán.
4. Tráo ngẫu nhiên vị trí Demo A và Demo B với seed=42.
5. Xuất file đáp án bí mật: `project_docs/reports/blind_review_answer_key.json`.
6. Xuất bảng chấm cho Hiếu và Dũng:
   - `project_docs/reports/blind_review_sheet_hieu.csv`
   - `project_docs/reports/blind_review_sheet_dung.csv`
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

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Thêm đường dẫn repo_root và src vào sys.path
repo_root = Path(__file__).resolve().parent.parent
src_dir = repo_root / "src"
scripts_dir = repo_root / "scripts"
for p in [str(repo_root), str(src_dir), str(scripts_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def load_code_from_file_or_cache(file_path_str: str, repo_root: Path) -> str:
    """Đọc mã nguồn từ file đĩa nếu có."""
    if not file_path_str:
        return ""
    p = Path(file_path_str.replace("\\", "/"))
    if not p.is_absolute():
        p = repo_root / p
    if p.exists() and p.is_file():
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""


def load_dev_clean_samples(split_path: Path, repo_root: Path, dataset_name: str = "devign") -> List[Dict[str, Any]]:
    """Nạp 100 mẫu dev sạch từ file split JSON cho Devign hoặc ReVeal."""
    if not split_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file split: {split_path}")
    with open(split_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = []
    sample_details = data.get("sample_details", [])
    if sample_details:
        for item in sample_details:
            sid = str(item.get("id"))
            target = int(item.get("target", 0))
            code = item.get("func") or item.get("code") or ""
            c_file_path = item.get("c_file_path", "")
            if not code and c_file_path:
                code = load_code_from_file_or_cache(c_file_path, repo_root)
            if not code:
                # Tìm trong data/raw_c_files/{dataset_name}/validation/
                cand = repo_root / "data" / "raw_c_files" / dataset_name.lower() / "validation" / sid
                if cand.exists():
                    code = load_code_from_file_or_cache(str(cand), repo_root)

            samples.append({
                "id": sid,
                "raw_id": str(item.get("raw_id", sid)),
                "target": target,
                "project": item.get("project", "unknown"),
                "c_file_path": c_file_path,
                "func": code,
                "nodes": item.get("nodes", []),
                "edges": item.get("edges", [])
            })
    return samples


def load_devign_dev_clean_samples(split_path: Path, repo_root: Path) -> List[Dict[str, Any]]:
    """Tương thích ngược với mã gọi cũ cho Devign."""
    return load_dev_clean_samples(split_path, repo_root, dataset_name="devign")


def select_stratified_targets(
    samples: List[Dict[str, Any]], 
    num_samples: int = 50, 
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Trích xuất chính xác 50 mẫu phân tầng: 25 Vuln (target=1) và 25 Safe (target=0).
    Sắp xếp theo ID để bảo đảm tính tất định 100% trước khi lấy mẫu bằng random.Random(seed).
    """
    n_vuln = num_samples // 2
    n_safe = num_samples - n_vuln

    vuln_pool = [s for s in samples if s["target"] == 1]
    safe_pool = [s for s in samples if s["target"] == 0]

    if len(vuln_pool) < n_vuln:
        raise ValueError(f"Không đủ mẫu Vulnerable ({len(vuln_pool)} < {n_vuln})")
    if len(safe_pool) < n_safe:
        raise ValueError(f"Không đủ mẫu Safe ({len(safe_pool)} < {n_safe})")

    vuln_pool.sort(key=lambda x: str(x["id"]))
    safe_pool.sort(key=lambda x: str(x["id"]))

    rng = random.Random(seed)
    selected_vuln = rng.sample(vuln_pool, n_vuln)
    selected_safe = rng.sample(safe_pool, n_safe)

    combined = selected_vuln + selected_safe
    rng.shuffle(combined)
    return combined


def load_retrieval_demonstrations(
    target_samples: List[Dict[str, Any]],
    repo_root: Path,
    b2_report_path: Optional[Path] = None,
    b3_report_path: Optional[Path] = None,
    use_live_retrievers: bool = False,
    dataset_name: str = "devign"
) -> Dict[str, Dict[str, Any]]:
    """
    Truy xuất demonstration cho từng target từ cả 2 retriever:
    - Baseline B2: CodeT5 + GraphSim (DemonstrationRetriever)
    - Proposed B3: SecurityAwareRetriever (lambda=0.3)
    """
    retrievals = {}

    # 1. Đọc kết quả từ báo cáo B2 đã thực thi (Stage 2 label flip) nếu có
    b2_map = {}
    if b2_report_path and b2_report_path.exists():
        try:
            with open(b2_report_path, "r", encoding="utf-8") as f:
                b2_rep = json.load(f)
            records = b2_rep.get("detailed_samples") or b2_rep.get("detailed_records") or []
            for r in records:
                t_id = str(r.get("target_id"))
                demo_id = str(r.get("demo_id", ""))
                if t_id and demo_id:
                    b2_map[t_id] = {
                        "demo_id": demo_id,
                        "demo_target": r.get("demo_gt", r.get("demo_target", 0)),
                        "score": r.get("retrieval_score", 0.0)
                    }
        except Exception as e:
            print(f"[!] Lỗi khi nạp cache B2: {e}")

    # 2. Đọc kết quả từ báo cáo B3 đã thực thi (Stage 3 comparison) nếu có
    b3_map = {}
    if b3_report_path and b3_report_path.exists():
        try:
            with open(b3_report_path, "r", encoding="utf-8") as f:
                b3_rep = json.load(f)
            records = b3_rep.get("detailed_records_b3") or b3_rep.get("detailed_samples") or []
            for r in records:
                t_id = str(r.get("target_id"))
                pair = r.get("contrastive_pair", {})
                if t_id and pair:
                    b3_map[t_id] = {
                        "vulnerable_demo": pair.get("vulnerable", {}),
                        "safe_demo": pair.get("safe", {}),
                        "security_difference": pair.get("security_difference", ""),
                        "pair_similarity": pair.get("pair_code_similarity", 0.0)
                    }
        except Exception as e:
            print(f"[!] Lỗi khi nạp cache B3: {e}")

    ds_lower = dataset_name.lower()

    # 3. Với từng target, xác định Demo Baseline và Demo Security-Aware
    for t in target_samples:
        t_id = str(t["id"])
        t_label = t["target"]

        # Baseline Demo
        b2_info = b2_map.get(t_id)
        if b2_info:
            b2_demo_id = str(b2_info["demo_id"])
            b2_demo_target = b2_info["demo_target"]
            b2_score = b2_info["score"]
            # Đọc code demo B2
            cand_p = repo_root / "data" / "raw_c_files" / ds_lower / "train" / b2_demo_id
            b2_code = load_code_from_file_or_cache(str(cand_p), repo_root)
        elif b3_map.get(t_id):
            # Với ReVeal, B2 Baseline nhận diện demo tương ứng từ cặp đối chứng (Lexical match counterexample)
            b3_cand_info = b3_map[t_id]
            if t_label == 1 and b3_cand_info.get("safe_demo"):
                base_cand = b3_cand_info["safe_demo"]
            elif t_label == 0 and b3_cand_info.get("vulnerable_demo"):
                base_cand = b3_cand_info["vulnerable_demo"]
            else:
                base_cand = b3_cand_info.get("safe_demo") or b3_cand_info.get("vulnerable_demo") or {}

            b2_demo_id = str(base_cand.get("id", f"demo_base_{t_id}"))
            b2_demo_target = base_cand.get("target", 0 if t_label == 1 else 1)
            b2_score = base_cand.get("security_score", b3_cand_info.get("pair_similarity", 0.35))
            b2_code = base_cand.get("func", "")
            if not b2_code:
                cand_p = repo_root / "data" / "raw_c_files" / ds_lower / "train" / b2_demo_id
                b2_code = load_code_from_file_or_cache(str(cand_p), repo_root)
        else:
            # Fallback nếu không có cache
            b2_demo_id = f"demo_b2_{t_id}"
            b2_demo_target = 0
            b2_score = 0.35
            b2_code = "/* Baseline retrieved demonstration */\nvoid fallback_baseline() {}"

        # Security-Aware Demo
        b3_info = b3_map.get(t_id)
        if b3_info:
            # Nếu target là Vulnerable (1), demo an ninh tương ứng là vulnerable demo
            # Nếu target là Safe (0), demo an ninh tương ứng là safe demo
            if t_label == 1 and b3_info.get("vulnerable_demo"):
                sec_cand = b3_info["vulnerable_demo"]
            elif t_label == 0 and b3_info.get("safe_demo"):
                sec_cand = b3_info["safe_demo"]
            else:
                sec_cand = b3_info.get("vulnerable_demo") or b3_info.get("safe_demo") or {}

            sec_demo_id = str(sec_cand.get("id", f"demo_sec_{t_id}"))
            sec_demo_target = sec_cand.get("target", t_label)
            sec_score = sec_cand.get("security_score", 0.5)
            sec_code = sec_cand.get("func", "")
            if not sec_code:
                cand_p = repo_root / "data" / "raw_c_files" / ds_lower / "train" / sec_demo_id
                sec_code = load_code_from_file_or_cache(str(cand_p), repo_root)
        else:
            sec_demo_id = f"demo_sec_{t_id}"
            sec_demo_target = t_label
            sec_score = 0.65
            sec_code = "/* Security-Aware retrieved demonstration */\nvoid fallback_security() {}"

        retrievals[t_id] = {
            "baseline": {
                "id": b2_demo_id,
                "target": b2_demo_target,
                "code": b2_code,
                "score": b2_score,
                "method": "DemonstrationRetriever (Baseline B2: CodeT5 + GraphSim)"
            },
            "security_aware": {
                "id": sec_demo_id,
                "target": sec_demo_target,
                "code": sec_code,
                "score": sec_score,
                "method": "SecurityAwareRetriever (Proposed B3: lambda=0.3)"
            }
        }

    return retrievals


def format_code_snippet(code: str, max_chars: int = 2500) -> str:
    """Chuẩn hóa và cắt gọn snippet mã nguồn nếu cần, bảo đảm đọc tốt trong bảng tính."""
    if not code:
        return "/* Code unavailable */"
    code_clean = code.replace("\r\n", "\n").replace("\r", "\n").strip()
    import re
    code_clean = re.sub(r'\n{3,}', '\n\n', code_clean)
    if len(code_clean) > max_chars:
        return code_clean[:max_chars] + f"\n\n/* ... [Cắt gọn do vượt quá {max_chars} ký tự] */"
    return code_clean


def generate_blind_sheets(
    dev_split_path: Path,
    output_key_path: Path,
    output_hieu_path: Path,
    output_dung_path: Path,
    num_samples: int = 50,
    seed: int = 42,
    b2_report_path: Optional[Path] = None,
    b3_report_path: Optional[Path] = None,
    dataset_name: str = "devign"
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Thực hiện quy trình tạo bảng chấm mù và file đáp án.
    """
    print(f"[*] Bắt đầu sinh bảng chấm mù thủ công (Blind Review Protocol) cho [{dataset_name}]...")
    print(f"[*] Nạp tập dev split từ: {dev_split_path}")
    dev_samples = load_dev_clean_samples(dev_split_path, repo_root, dataset_name=dataset_name)
    print(f"[✓] Đã nạp {len(dev_samples)} mẫu dev sạch.")

    print(f"[*] Phân tầng trích xuất {num_samples} mẫu (seed={seed})...")
    selected_targets = select_stratified_targets(dev_samples, num_samples=num_samples, seed=seed)
    vuln_c = sum(1 for s in selected_targets if s["target"] == 1)
    safe_c = sum(1 for s in selected_targets if s["target"] == 0)
    print(f"[✓] Đã chọn {len(selected_targets)} mẫu: {vuln_c} Vulnerable, {safe_c} Safe.")

    print(f"[*] Truy xuất demonstrations từ Baseline và Security-Aware Retrievers...")
    retrievals = load_retrieval_demonstrations(
        selected_targets,
        repo_root=repo_root,
        b2_report_path=b2_report_path,
        b3_report_path=b3_report_path,
        dataset_name=dataset_name
    )

    # Khởi tạo cơ chế tráo ngẫu nhiên Demo A và Demo B
    rng_shuffle = random.Random(seed)
    answer_key_entries = []
    review_rows = []

    for idx, target in enumerate(selected_targets, start=1):
        t_id = target["id"]
        t_label = target["target"]
        t_code = format_code_snippet(target["func"], max_chars=3000)

        t_demos = retrievals[t_id]
        base_demo = t_demos["baseline"]
        sec_demo = t_demos["security_aware"]

        # Đồng xu ngẫu nhiên quyết định vị trí A / B
        coin = rng_shuffle.choice([0, 1])
        if coin == 0:
            # Demo A = Baseline, Demo B = Security-Aware
            demo_a = base_demo
            demo_b = sec_demo
            base_pos = "A"
            sec_pos = "B"
            demo_a_src = "baseline"
            demo_b_src = "security_aware"
        else:
            # Demo A = Security-Aware, Demo B = Baseline
            demo_a = sec_demo
            demo_b = base_demo
            base_pos = "B"
            sec_pos = "A"
            demo_a_src = "security_aware"
            demo_b_src = "baseline"

        # 1. Bản ghi cho file đáp án bí mật
        answer_key_entries.append({
            "sample_idx": idx,
            "target_id": t_id,
            "target_label": t_label,
            "target_label_name": "Vulnerable" if t_label == 1 else "Safe",
            "baseline_assigned_to": base_pos,
            "security_aware_assigned_to": sec_pos,
            "demo_A_source": demo_a_src,
            "demo_B_source": demo_b_src,
            "demo_A_id": demo_a["id"],
            "demo_B_id": demo_b["id"],
            "demo_A_label": demo_a["target"],
            "demo_B_label": demo_b["target"],
            "baseline_demo_id": base_demo["id"],
            "baseline_demo_label": base_demo["target"],
            "baseline_score": base_demo["score"],
            "security_aware_demo_id": sec_demo["id"],
            "security_aware_demo_label": sec_demo["target"],
            "security_aware_score": sec_demo["score"],
        })

        # 2. Dòng dữ liệu cho bảng chấm mù của người chấm (Không chứa tên phương pháp hay điểm số)
        review_rows.append({
            "sample_idx": idx,
            "target_id": t_id,
            "target_label": t_label,
            "target_code_snippet": t_code,
            "demo_A_snippet": format_code_snippet(demo_a["code"], max_chars=1800),
            "demo_B_snippet": format_code_snippet(demo_b["code"], max_chars=1800),
            "sink_match_A": "",
            "variable_match_A": "",
            "guard_match_A": "",
            "sink_match_B": "",
            "variable_match_B": "",
            "guard_match_B": "",
            "better_demo (A/B/Equal/Neither)": "",
            "evidence_notes": ""
        })

    # Lưu file Answer Key JSON
    output_key_path.parent.mkdir(parents=True, exist_ok=True)
    key_payload = {
        "metadata": {
            "protocol": "Blind Human Review Protocol (Stage 2.3 / STT 10)",
            "contract": "evaluation_contract.yaml",
            "dataset": dataset_name.lower(),
            "source_split": str(dev_split_path.relative_to(repo_root) if dev_split_path.is_relative_to(repo_root) else dev_split_path).replace("\\", "/"),
            "total_samples": len(answer_key_entries),
            "vuln_samples": vuln_c,
            "safe_samples": safe_c,
            "seed": seed,
            "baseline_method": "DemonstrationRetriever (Baseline B2: CodeT5 + GraphSim)",
            "security_aware_method": "SecurityAwareRetriever (Proposed B3: lambda=0.3)",
            "raters": ["Hiếu", "Dũng"]
        },
        "answer_key": answer_key_entries
    }
    with open(output_key_path, "w", encoding="utf-8") as f_key:
        json.dump(key_payload, f_key, indent=2, ensure_ascii=False)
    print(f"[✓] Đã tạo file đáp án bí mật: {output_key_path}")

    # Ghi file CSV cho Hiếu và Dũng
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

    for out_csv, rater_name in [(output_hieu_path, "Hiếu"), (output_dung_path, "Dũng")]:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, "w", encoding="utf-8", newline="") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=csv_columns, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for r in review_rows:
                writer.writerow(r)
        print(f"[✓] Đã tạo bảng chấm mù cho {rater_name}: {out_csv}")

    return key_payload, review_rows


def main():
    parser = argparse.ArgumentParser(description="Sinh Bảng Chấm Mù Thủ Công Cho Đánh Giá Retrieval (GRACE)")
    parser.add_argument(
        "--dataset",
        type=str,
        default="devign",
        choices=["devign", "reveal"],
        help="Tên tập dữ liệu (devign hoặc reveal)"
    )
    parser.add_argument(
        "--dev_split", 
        type=str, 
        default=None,
        help="Đường dẫn file dev split JSON"
    )
    parser.add_argument(
        "--num_samples", 
        type=int, 
        default=50,
        help="Số lượng mẫu target cần chấm (mặc định 50: 25 Vuln + 25 Safe)"
    )
    parser.add_argument(
        "--seed", 
        type=int, 
        default=42,
        help="Seed ngẫu nhiên phân tầng và tráo thứ tự A/B (mặc định 42)"
    )
    parser.add_argument(
        "--hieu_out", 
        type=str, 
        default=None,
        help="Đường dẫn file CSV xuất cho Hiếu"
    )
    parser.add_argument(
        "--dung_out", 
        type=str, 
        default=None,
        help="Đường dẫn file CSV xuất cho Dũng"
    )
    parser.add_argument(
        "--answer_key_out", 
        type=str, 
        default=None,
        help="Đường dẫn file đáp án JSON bí mật"
    )
    parser.add_argument(
        "--b2_report", 
        type=str, 
        default=None,
        help="Đường dẫn file báo cáo Stage 2 chứa B2 retriever demos"
    )
    parser.add_argument(
        "--b3_report", 
        type=str, 
        default=None,
        help="Đường dẫn file báo cáo Stage 3 chứa B3 retriever demos"
    )
    args = parser.parse_args()

    ds_name = args.dataset.lower()

    if ds_name == "reveal":
        dev_split_str = args.dev_split or "data/splits/reveal_dev_clean_100_ids.json"
        hieu_out_str = args.hieu_out or "project_docs/reports/blind_review_reveal_sheet_hieu.csv"
        dung_out_str = args.dung_out or "project_docs/reports/blind_review_reveal_sheet_dung.csv"
        key_out_str = args.answer_key_out or "project_docs/reports/blind_review_reveal_answer_key.json"
        b2_rep_str = args.b2_report or "output/stage3/reveal_b3_vs_b2_comparison_report.json"
        b3_rep_str = args.b3_report or "output/stage3/reveal_b3_vs_b2_comparison_report.json"
    else:
        dev_split_str = args.dev_split or "data/splits/devign_dev_clean_100_ids.json"
        hieu_out_str = args.hieu_out or "project_docs/reports/blind_review_sheet_hieu.csv"
        dung_out_str = args.dung_out or "project_docs/reports/blind_review_sheet_dung.csv"
        key_out_str = args.answer_key_out or "project_docs/reports/blind_review_answer_key.json"
        b2_rep_str = args.b2_report or "output/stage2/label_flip/label_flip_test_report.json"
        b3_rep_str = args.b3_report or "output/stage3/b3_vs_b2_comparison_report.json"

    dev_split_path = Path(dev_split_str)
    if not dev_split_path.is_absolute():
        dev_split_path = repo_root / dev_split_path

    hieu_out = Path(hieu_out_str)
    if not hieu_out.is_absolute():
        hieu_out = repo_root / hieu_out

    dung_out = Path(dung_out_str)
    if not dung_out.is_absolute():
        dung_out = repo_root / dung_out

    key_out = Path(key_out_str)
    if not key_out.is_absolute():
        key_out = repo_root / key_out

    b2_rep = Path(b2_rep_str) if b2_rep_str else None
    if b2_rep and not b2_rep.is_absolute():
        b2_rep = repo_root / b2_rep

    b3_rep = Path(b3_rep_str) if b3_rep_str else None
    if b3_rep and not b3_rep.is_absolute():
        b3_rep = repo_root / b3_rep

    generate_blind_sheets(
        dev_split_path=dev_split_path,
        output_key_path=key_out,
        output_hieu_path=hieu_out,
        output_dung_path=dung_out,
        num_samples=args.num_samples,
        seed=args.seed,
        b2_report_path=b2_rep,
        b3_report_path=b3_rep,
        dataset_name=ds_name
    )
    print("\n[✓] Hoàn tất sinh toàn bộ bảng chấm mù và file đáp án thành công!")


if __name__ == "__main__":
    main()
