"""
Common Evaluator & Audit Reparse Tool (STEP 2.2 & 2.3 trong Immediate Action Plan)

Chức năng:
1. Đọc các file JSON kết quả hoặc Checkpoint JSONL chứa 'llm_raw_response' và 'target'.
2. Reparse lại dự đoán bằng `parse_llm_prediction` đã sửa (KHÔNG gọi lại LLM).
3. Báo cáo chi tiết:
   - Số nhãn bị thay đổi (0 -> 1, 1 -> 0, valid -> invalid, etc.)
   - Phân bố parse_method mới
   - Confusion Matrix, Accuracy, Precision, Recall, F1, MCC, Balanced Accuracy
   - So sánh trực tiếp metric Trước vs Sau reparse.
4. Có thể chạy độc lập như một CLI tool:
   python src/common_evaluator.py --input output/results_grace_exp.json --reparse
"""

import sys
import io
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Đảm bảo import được từ src
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from evaluator import parse_llm_prediction
from metrics import compute_classification_metrics, print_metrics_summary


def load_records_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """Tự động nhận diện định dạng JSON, JSONL hoặc CSV để nạp records."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    records = []
    if file_path.suffix == ".csv":
        import csv
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Ép kiểu cho target và prediction nếu có
                rec = dict(row)
                if "target" in rec and rec["target"] != "":
                    try:
                        rec["target"] = int(rec["target"])
                    except ValueError:
                        pass
                if "prediction" in rec and rec["prediction"] != "":
                    try:
                        rec["prediction"] = int(rec["prediction"])
                    except ValueError:
                        pass
                records.append(rec)
    elif file_path.suffix == ".jsonl":
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                records = data.get("detailed_predictions", [])
                if not records and "results" in data:
                    records = data.get("results", [])
    return records


def audit_and_reparse(records: List[Dict[str, Any]], run_name: str = "Audit Run") -> Dict[str, Any]:
    """
    Thực hiện reparse lại toàn bộ records và phân tích sự thay đổi.
    """
    total = len(records)
    old_preds: List[Optional[int]] = []
    new_preds: List[Optional[int]] = []
    y_true: List[int] = []

    label_changed_count = 0
    changed_0_to_1 = 0
    changed_1_to_0 = 0
    changed_to_invalid = 0
    invalid_count = 0

    parse_method_dist: Dict[str, int] = {}
    changes_by_ground_truth: Dict[str, int] = {
        "true_1_fixed_to_1": 0,
        "true_0_fixed_to_0": 0,
        "true_1_corrupted_to_0": 0,
        "true_0_corrupted_to_1": 0,
    }

    reparsed_records = []

    for r in records:
        gt = r.get("target")
        if gt is None:
            continue
        y_true.append(int(gt))

        old_pred = r.get("prediction")
        # Lưu old pred (nếu có)
        old_preds.append(int(old_pred) if old_pred is not None else None)

        raw_resp = r.get("llm_raw_response", "")
        # Nếu không có llm_raw_response, fallback dùng raw_response hoặc chính prediction
        if not raw_resp and "raw_response" in r:
            raw_resp = r.get("raw_response", "")

        new_pred, method, is_valid = parse_llm_prediction(raw_resp)
        new_preds.append(new_pred)

        parse_method_dist[method] = parse_method_dist.get(method, 0) + 1

        if not is_valid or new_pred is None:
            invalid_count += 1

        # Kiểm tra sự thay đổi nhãn
        if old_pred != new_pred:
            label_changed_count += 1
            if old_pred == 0 and new_pred == 1:
                changed_0_to_1 += 1
                if gt == 1:
                    changes_by_ground_truth["true_1_fixed_to_1"] += 1
                else:
                    changes_by_ground_truth["true_0_corrupted_to_1"] += 1
            elif old_pred == 1 and new_pred == 0:
                changed_1_to_0 += 1
                if gt == 0:
                    changes_by_ground_truth["true_0_fixed_to_0"] += 1
                else:
                    changes_by_ground_truth["true_1_corrupted_to_0"] += 1
            elif new_pred is None:
                changed_to_invalid += 1

        rec_copy = dict(r)
        rec_copy["old_prediction"] = old_pred
        rec_copy["prediction"] = new_pred
        rec_copy["new_parse_method"] = method
        rec_copy["is_valid"] = is_valid
        reparsed_records.append(rec_copy)

    metrics_before = compute_classification_metrics(y_true, old_preds)
    metrics_after = compute_classification_metrics(y_true, new_preds)

    report = {
        "run_name": run_name,
        "total_records": total,
        "label_changed_count": label_changed_count,
        "changed_0_to_1": changed_0_to_1,
        "changed_1_to_0": changed_1_to_0,
        "changed_to_invalid": changed_to_invalid,
        "invalid_count": invalid_count,
        "parse_method_distribution": parse_method_dist,
        "changes_by_ground_truth": changes_by_ground_truth,
        "metrics_before": metrics_before,
        "metrics_after": metrics_after,
        "reparsed_records": reparsed_records
    }
    return report


def print_audit_report(report: Dict[str, Any]):
    """In báo cáo đối soát reparse trực quan."""
    print("\n" + "=" * 75)
    print(f"  BÁO CÁO ĐỐI SOÁT & REPARSE KẾT QUẢ CŨ: [{report['run_name']}]")
    print("=" * 75)
    print(f"[*] Tổng số mẫu kiểm tra: {report['total_records']}")
    print(f"[*] Tổng số mẫu bị đổi nhãn: {report['label_changed_count']} ({(report['label_changed_count']/report['total_records']*100 if report['total_records']>0 else 0):.2f}%)")
    print(f"    - Thay đổi từ 0 -> 1: {report['changed_0_to_1']}")
    print(f"    - Thay đổi từ 1 -> 0: {report['changed_1_to_0']}")
    print(f"    - Mẫu không hợp lệ / invalid: {report['invalid_count']}")
    print(f"\n[*] Phân tích theo Ground Truth:")
    for k, v in report['changes_by_ground_truth'].items():
        print(f"    - {k:<25}: {v}")

    print(f"\n[*] Phân phối phương thức bóc tách mới (Parse Method Distribution):")
    for method, count in report['parse_method_distribution'].items():
        print(f"    - {method:<45}: {count}")

    print("\n" + "-" * 75)
    print("  SO SÁNH METRIC: TRƯỚC vs SAU REPARSE")
    print("-" * 75)
    mb = report['metrics_before']
    ma = report['metrics_after']
    print(f"{'Chỉ số':<25} | {'Trước Reparse (Cũ)':<20} | {'Sau Reparse (Mới)':<20}")
    print("-" * 75)
    print(f"{'Accuracy':<25} | {mb.get('accuracy', 0.0):<20} | {ma.get('accuracy', 0.0):<20}")
    print(f"{'Precision':<25} | {str(mb.get('precision')):<20} | {str(ma.get('precision')):<20}")
    print(f"{'Recall':<25} | {str(mb.get('recall')):<20} | {str(ma.get('recall')):<20}")
    print(f"{'F1-Score':<25} | {mb.get('f1_score', 0.0):<20} | {ma.get('f1_score', 0.0):<20}")
    print(f"{'MCC':<25} | {str(mb.get('mcc')):<20} | {str(ma.get('mcc')):<20}")
    print(f"{'Balanced Accuracy':<25} | {mb.get('balanced_accuracy', 0.0):<20} | {ma.get('balanced_accuracy', 0.0):<20}")
    print(f"{'Invalid Rate':<25} | {mb.get('invalid_rate', 0.0):<20} | {ma.get('invalid_rate', 0.0):<20}")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="GRACE Unified Common Evaluator & Audit Reparse Tool")
    parser.add_argument("--input", type=str, required=True, help="Đường dẫn file kết quả (.json, .jsonl hoặc .csv)")
    parser.add_argument("--split_ids", type=str, default=None, help="Đường dẫn file split IDs chuẩn (ví dụ data/splits/devign_test_ids.json)")
    parser.add_argument("--run_name", type=str, default="Evaluation Run", help="Tên phiên chạy đánh giá")
    parser.add_argument("--reparse", action="store_true", help="Thực hiện reparse lại raw response của LLM bằng parser mới")
    parser.add_argument("--save_reparsed", type=str, default=None, help="Đường dẫn lưu file json sau reparse (optional)")
    args = parser.parse_args()

    records = load_records_from_file(Path(args.input))
    print(f"\n[*] Đã nạp {len(records)} mẫu từ: {args.input}")

    # Lọc theo canonical split nếu được cung cấp
    if args.split_ids:
        split_path = Path(args.split_ids)
        if split_path.exists():
            with open(split_path, "r", encoding="utf-8") as f:
                split_meta = json.load(f)
            
            raw_canonical_ids = split_meta.get("sample_ids", [])
            # Tập ID gốc và tập ID chuẩn hóa (ví dụ trích xuất số nếu có dạng id_10000_...)
            canonical_lookup = set()
            for cid in raw_canonical_ids:
                cid_str = str(cid)
                canonical_lookup.add(cid_str)
                if cid_str.startswith("id_") and "_" in cid_str:
                    parts = cid_str.split("_")
                    if len(parts) > 1 and parts[1].isdigit():
                        canonical_lookup.add(parts[1])

            filtered_records = []
            for r in records:
                rid = str(r.get("id"))
                if rid in canonical_lookup:
                    filtered_records.append(r)
                elif rid.startswith("id_") and "_" in rid:
                    parts = rid.split("_")
                    if len(parts) > 1 and parts[1] in canonical_lookup:
                        filtered_records.append(r)

            print(f"[*] Khớp với Canonical Split [{split_meta.get('split_name')}]: {len(filtered_records)} / {len(raw_canonical_ids)} mẫu (Độ phủ: {len(filtered_records)/len(raw_canonical_ids):.2%})")
            records = filtered_records
        else:
            print(f"[!] Cảnh báo: Không tìm thấy file split {args.split_ids}. Giữ nguyên toàn bộ {len(records)} mẫu.")

    if args.reparse:
        report = audit_and_reparse(records, run_name=args.run_name)
        print_audit_report(report)

        if args.save_reparsed:
            out_path = Path(args.save_reparsed)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"[✓] Đã lưu báo cáo reparse đầy đủ vào: {out_path}")
    else:
        # Chế độ đánh giá trực tiếp dựa trên nhãn hiện có
        y_true = []
        y_pred = []
        for r in records:
            gt = r.get("target")
            if gt is not None:
                y_true.append(int(gt))
                pred = r.get("prediction")
                y_pred.append(int(pred) if pred is not None else None)
        metrics = compute_classification_metrics(y_true, y_pred)
        print_metrics_summary(metrics, dataset_name=args.run_name)


if __name__ == "__main__":
    main()
