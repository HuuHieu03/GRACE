"""Build a traceable reporting registry without modifying historical artifacts."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from metrics import compute_classification_metrics
from evaluator import parse_llm_prediction

RUNS = [
    ("stage3_devign_ver03", "devign", "b3_vs_b2_comparison_report", "Ver03_B3_vs_B2_Comparison"),
    ("stage3_reveal_ver04", "reveal", "reveal_b3_vs_b2_comparison_report", "Ver04_ReVeal_B3_vs_B2"),
    ("stage3_devign_nodiff_ver05", "devign", "ablation_nodiff_comparison_report", "Ver05_Ablation_B3_NoDiff"),
]
CSV_METRICS = {"Accuracy": "accuracy", "Precision": "precision", "Recall": "recall",
               "F1-Score": "f1_score", "MCC": "mcc", "Balanced Accuracy": "balanced_accuracy",
               "Pred Vuln Rate": "predicted_vulnerable_rate", "Predicted Vulnerable Rate": "predicted_vulnerable_rate"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_records(records, labels):
    ids = [str(r["target_id"]) for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate target ID in experiment records")
    if set(ids) != set(labels):
        raise ValueError("Experiment IDs do not match the entire declared target split")
    for r in records:
        if r["target"] not in (0, 1) or labels[str(r["target_id"])] != r["target"]:
            raise ValueError("Ground truth mismatch between records and target split")
        for condition in "abc":
            pred_key = {"a": "pred_a", "b": "pred_b_inverted", "c": "pred_c_repeated"}[condition]
            if pred_key not in r:
                pred_key = "pred_" + condition
            p, valid = r.get(pred_key), r.get("valid_" + condition)
            if type(valid) is not bool or (valid and (type(p) is not int or p not in (0, 1))) or (not valid and p is not None):
                raise ValueError("Prediction and validity contract mismatch")


def check_csv(path, expected_columns):
    mismatches = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    seen = set()
    for row in rows:
        key = CSV_METRICS.get(row.get("Metric"))
        if key is None:
            continue
        seen.add(key)
        for column, metrics in expected_columns.items():
            try:
                actual = float(row[column])
                expected = metrics[key]
                matches = expected is not None and abs(actual - expected) <= 0.000051
            except (KeyError, TypeError, ValueError):
                matches = False
            if not matches:
                mismatches.append({"metric": key, "column": column, "csv_value": row.get(column),
                                   "json_value": metrics.get(key)})
    missing = set(CSV_METRICS.values()) - seen
    mismatches.extend({"metric": key, "reason": "missing metric row"} for key in sorted(missing))
    return mismatches


def build_registry(root=ROOT):
    sources, runs, tables = {}, [], []

    def register(path):
        relative = path.relative_to(root).as_posix()
        sources[relative] = {"sha256": digest(path), "bytes": path.stat().st_size}
        return relative

    for run_id, ds, stem, archive in RUNS:
        path = root / "output/stage3" / (stem + ".json")
        downloaded = root / "kaggle_notebooks/stage3_b3_vs_b2/downloaded_runs" / archive / (stem + ".json")
        register(path)
        register(downloaded)
        if read(path) != read(downloaded):
            raise ValueError(f"Working/archive JSON diverged: {run_id}")
        data = read(path)
        if data["metadata"]["dataset"] != ds or data["metadata"].get("use_mock") is not False:
            raise ValueError(f"Unexpected dataset or mock metadata: {run_id}")
        split_path = root / f"data/splits/{ds}_dev_clean_100_ids.json"
        register(split_path)
        details = read(split_path)["sample_details"]
        labels = {str(s["id"]): s["target"] for s in details}
        if len(labels) != len(details):
            raise ValueError("Duplicate IDs in target split")
        rows = data["detailed_records_b3"]
        validate_records(rows, labels)
        metrics = compute_classification_metrics([r["target"] for r in rows], [r["pred_a"] for r in rows])
        if metrics != data["b3_contrastive"]:
            raise ValueError(f"Recomputed metric mismatch: {run_id}")
        log = downloaded.parent / "grace-stage-3-b3-vs-b2-contrastive-demonstration.log"
        register(log)
        runs.append({"run_id": run_id, "dataset": ds, "source": register(path),
                     "archive_json_matches": True, "metrics": metrics,
                     "support": "metrics_recomputed_from_per_id_predictions",
                     "raw_response": "unavailable_in_export", "actual_prompt": "unavailable_in_export",
                     "b2_support": "reported_aggregate_only; not interchangeable with Stage2 baseline",
                     "reported_b2_metrics": data["b2_baseline"],
                     "reported_paired_ci": data["paired_bootstrap_95_ci"],
                     "paired_b2_statistics_support": "reported_only; B2 per-ID export unavailable",
                     "model_metadata": data["metadata"], "quality_claim": "NOT_ESTABLISHED"})
        columns = {"B2_Baseline": data["b2_baseline"]}
        if "b3_nodiff" in data:
            columns.update(B3_NoDiff=data["b3_nodiff"], B3_Full=data["b3_full"])
        else:
            columns["B3_Contrastive"] = metrics
        csv_path = path.with_suffix(".csv")
        mismatches = check_csv(csv_path, columns)
        tables.append({"path": register(csv_path), "status": "consistent_with_json" if not mismatches else "EXCLUDED_CONFLICT",
                       "mismatches": mismatches})

    stage2_path = root / "output/stage2/label_flip/label_flip_test_report.json"
    stage2 = read(stage2_path)
    records = stage2["detailed_samples"]
    labels = {str(s["id"]): s["target"] for s in read(root / "data/splits/devign_dev_clean_100_ids.json")["sample_details"]}
    validate_records(records, labels)
    reparse_changes = []
    for r in records:
        for condition in "abc":
            p, _, valid = parse_llm_prediction(r["raw_resp_" + condition])
            if (p, valid) != (r["pred_" + condition], r["valid_" + condition]):
                reparse_changes.append([r["target_id"], condition])
    if reparse_changes:
        raise ValueError("Stage2 raw responses no longer agree with stored predictions")
    metrics = compute_classification_metrics([r["target"] for r in records], [r["pred_a"] for r in records])
    if metrics != stage2["condition_metrics"]["condition_a_original"]:
        raise ValueError("Stage2 condition A metric mismatch")
    runs.append({"run_id": "stage2_devign_original_b2", "dataset": "devign", "source": register(stage2_path),
                 "metrics": metrics, "support": "metrics_recomputed_and_raw_reparsed", "raw_response": "available_300_responses",
                 "actual_prompt": "unavailable_in_export", "quality_claim": "NOT_ESTABLISHED"})
    summary = root / "output/stage3/b3_vs_b2_comparison_summary.csv"
    full = next(r for r in runs if r["run_id"] == "stage3_devign_ver03")
    mismatches = check_csv(summary, {"B2_Baseline": full["reported_b2_metrics"], "B3_Contrastive": full["metrics"]})
    tables.append({"path": register(summary), "status": "EXCLUDED_CONFLICT" if mismatches else "consistent_with_json",
                   "mismatches": mismatches, "reason": "No independently traceable run backing the conflicting summary has been established."})
    return {"schema_version": 1, "sources": sources, "runs": runs, "historical_tables": tables,
            "policy": "Preserve historical artifacts. Use regenerated metrics with explicit evidence scope; no positive improvement or independent human-review claims."}


def write_outputs(registry, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "source_registry.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["run_id", "dataset", "support", "raw_response", "actual_prompt", "total_samples", "valid_samples",
              "invalid_samples", "invalid_rate", "tp", "tn", "fp", "fn", "accuracy", "precision", "recall",
              "f1_score", "mcc", "balanced_accuracy", "predicted_vulnerable_rate", "always_vulnerable_f1",
              "always_vulnerable_acc", "always_safe_f1", "always_safe_acc"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for run in registry["runs"]:
        cm = run["metrics"]["confusion_matrix"]
        flat = {**run["metrics"], **run["metrics"]["baselines"],
                "tp": cm["TP (True Positive)"], "tn": cm["TN (True Negative)"],
                "fp": cm["FP (False Positive - Alarm)"], "fn": cm["FN (False Negative - Miss)"]}
        writer.writerow({k: run.get(k, flat.get(k)) for k in fields})
    (out / "verified_metrics.csv").write_text(buffer.getvalue(), encoding="utf-8")
    lines = ["---", 'version: "1.0.0"', 'date: "2026-10-22"', 'type: "report"', 'status: "COMPLETED"',
             'summary: "Đối soát nguồn số liệu; chỉ xác nhận trong phạm vi bằng chứng còn lưu."', "---", "",
             "# Nguồn số liệu được đối soát", "",
             "Đây là bảng tiến độ có giới hạn truy vết, không phải nghiệm thu cải tiến. Script tái tính metric B3 từ toàn bộ IDs/labels, so với JSON bản tải về và đối chiếu CSV. Các nguồn đầu vào có SHA-256 trong source_registry.json.", "",
             "| Run | N | F1 | MCC | Balanced accuracy | Raw / actual prompt |", "|---|---:|---:|---:|---:|---|"]
    for r in registry["runs"]:
        m = r["metrics"]
        lines.append(f"| {r['run_id']} | {m['total_samples']} | {m['f1_score']:.4f} | {m['mcc']:.4f} | {m['balanced_accuracy']:.4f} | {r['raw_response']} / {r['actual_prompt']} |")
    lines += ["", "`verified_metrics.csv` cung cấp đầy đủ TP/TN/FP/FN, precision/recall, coverage/invalid, predicted vulnerable rate và hai trivial baselines trên cùng IDs; JSON giữ metric cấu trúc và hash nguồn. Bảng rút gọn trên không thay thế các chỉ số đó.", "",
              "B2 aggregate và paired CI trong Stage 3 được giữ ở registry dưới nhãn reported-only vì thiếu export per-ID B2 của chính run. Stage2 B2 là run khác, không tự thay thế Stage3 B2.", "",
              "Các CI ΔMCC/ΔBA đã báo chứa 0; chưa đủ bằng chứng lợi ích. Không dùng các tỷ lệ order-swap để kết luận label sensitivity giảm. Full–NoDiff không chứng minh đóng góp nhân quả theo phần trăm.", "",
              "## Các bảng lịch sử", ""]
    lines += [f"- `{t['path']}`: **{t['status']}**, {len(t['mismatches'])} sai lệch metric được phát hiện." for t in registry["historical_tables"]]
    lines += ["", "CSV summary mâu thuẫn được giữ nguyên để truy vết nhưng loại khỏi nguồn dùng cho bảng/slide. Không suy đoán nguồn sinh của nó.", "",
              "## Phần chưa nghiệm thu", "", "- Split/UID/leakage và code/identity trong bộ chấm ReVeal còn lỗi đã nêu trong review lần hai.",
              "- Chưa xác nhận hai người chấm mù độc lập; không dùng kappa/confirmed CSV để tuyên bố ưu thế retrieval.",
              "- H2 là kết quả selection R1 đổi 0/100, chưa xác nhận relevance hoặc detection quality.", "",
              "Tái lập: `python scripts/reconcile_experiment_sources.py`. Script không gọi API hoặc sửa artifact gốc.", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "project_docs/reports/verified_sources_2026-10-22")
    args = parser.parse_args()
    result = build_registry()
    write_outputs(result, args.out)
    print(f"Reconciled {len(result['runs'])} runs; excluded {sum(t['status'] == 'EXCLUDED_CONFLICT' for t in result['historical_tables'])} conflicting table(s).")
