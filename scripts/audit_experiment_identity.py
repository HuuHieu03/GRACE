"""Read local experiment identities and distributions; no writes or API calls.

Run: python scripts/audit_experiment_identity.py
The output can be redirected to a new audit snapshot.
"""
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.audit_code_leakage import normalize_code_semantic
from evaluator import parse_llm_prediction


def read(path):
    path = ROOT / path
    if path.suffix == ".gz":
        return json.loads(gzip.decompress(path.read_bytes()))
    return json.loads(path.read_text(encoding="utf-8"))


def audit():
    result = {"scope": "Current local files; historical run equivalence requires a run manifest."}
    datasets = {}
    for ds, report_file in [("devign", "b3_vs_b2_comparison_report.json"),
                            ("reveal", "reveal_b3_vs_b2_comparison_report.json")]:
        train = read(f"data/processed/{ds}_train_compact_cpg.json.gz")
        split = read(f"data/splits/{ds}_dev_clean_100_ids.json")
        targets = split["sample_details"]
        groups = defaultdict(list)
        code_groups = defaultdict(list)
        for index, row in enumerate(train):
            groups[str(row["id"])].append((index, row))
            code_groups[normalize_code_semantic(row["func"])].append((index, row))
        overlaps = []
        for q in targets:
            matches = code_groups.get(normalize_code_semantic(q["func"]), [])
            if matches:
                overlaps.append({"query_id": q["id"], "query_target": q["target"],
                                 "matches": [{"row": i, "id": t["id"], "target": t["target"],
                                              "exact_stripped_code": q["func"].strip() == t["func"].strip()}
                                             for i, t in matches]})
        report = read("output/stage3/" + report_file)
        missing_pair_members = []
        ambiguous_legacy_ids = 0
        nonunique_full_members = []
        for record in report["detailed_records_b3"]:
            for role in ["vulnerable", "safe"]:
                p = record["contrastive_pair"][role]
                choices = groups.get(str(p["id"]), [])
                matches = [i for i, row in choices if row["func"] == p["func"] and row["target"] == p["target"]]
                ambiguous_legacy_ids += len(choices) > 1
                if not matches:
                    missing_pair_members.append([record["target_id"], role])
                elif len(matches) > 1:
                    nonunique_full_members.append([record["target_id"], role])
        source_file_mismatches = []
        missing_source_files = []
        for q in targets:
            path = ROOT / q["c_file_path"].replace("\\", "/")
            if not path.exists():
                missing_source_files.append(q["id"])
            elif path.read_text(encoding="utf-8", errors="replace").strip() != q["func"].strip():
                source_file_mismatches.append(q["id"])
        datasets[ds] = {
            "train_rows": len(train), "unique_train_ids": len(groups),
            "id_groups_with_different_code": sum(len({r["func"] for _, r in rows}) > 1 for rows in groups.values()),
            "id_groups_with_both_labels": sum(len({r["target"] for _, r in rows}) > 1 for rows in groups.values()),
            "metadata_labels": {"vulnerable": split["vulnerable_count"], "safe": split["safe_count"]},
            "actual_labels": dict(Counter(q["target"] for q in targets)),
            "normalized_train_target_code_overlap": overlaps,
            "target_source_file_mismatches": source_file_mismatches,
            "target_source_files_missing": missing_source_files,
            "pair_member_count": 2 * len(report["detailed_records_b3"]),
            "pair_members_missing_in_train_by_id_code_label": missing_pair_members,
            "pair_members_nonunique_by_full_identity": nonunique_full_members,
            "pair_members_with_ambiguous_legacy_id": ambiguous_legacy_ids,
            "rendered_targets_over_3000_chars": sum(len(q["func"].strip()) > 3000 for q in targets),
        }
    result["datasets"] = datasets
    stage2 = {}
    paths = ["output/stage2/label_flip/label_flip_test_report.json",
             "output/stage2/label_flip/run1_no_graph/label_flip_test_report.json",
             "output/stage2/label_flip/run2_with_graph/label_flip_test_report.json"]
    for path in paths:
        rows = read(path)["detailed_samples"]
        changes = []
        raw_count = 0
        methods = Counter()
        for r in rows:
            for condition in "abc":
                pred, method, valid = parse_llm_prediction(r["raw_resp_" + condition])
                raw_count += 1
                methods[method] += 1
                if pred != r["pred_" + condition] or valid != r["valid_" + condition]:
                    changes.append([r["target_id"], condition])
        stage2[path] = {"raw_responses": raw_count, "reparse_changes": changes, "parse_methods": dict(methods)}
    a = {r["target_id"]: r for r in read(paths[1])["detailed_samples"]}
    b = {r["target_id"]: r for r in read(paths[2])["detailed_samples"]}
    stage2["graph_comparison"] = {"common_ids": len(a.keys() & b.keys()),
                                  "demo_ids_changed": sum(a[k]["demo_id"] != b[k]["demo_id"] for k in a.keys() & b.keys())}
    result["stage2"] = stage2
    summary_path = ROOT / "output/stage3/b3_vs_b2_comparison_summary.csv"
    with summary_path.open(encoding="utf-8-sig", newline="") as stream:
        summary = list(csv.DictReader(stream))
    j = read("output/stage3/b3_vs_b2_comparison_report.json")["b3_contrastive"]
    result["stage3_summary_vs_json"] = {
        k: {"csv_b3": next(r["B3_Contrastive"] for r in summary if r["Metric"] == label), "json_b3": j[k]}
        for k, label in [("accuracy", "Accuracy"), ("f1_score", "F1-Score"), ("mcc", "MCC")]
    }
    targets = {str(q["id"]): q for q in read("data/splits/reveal_dev_clean_100_ids.json")["sample_details"]}
    with (ROOT / "project_docs/reports/blind_review_reveal_sheet_hieu.csv").open(encoding="utf-8-sig", newline="") as stream:
        hieu = list(csv.DictReader(stream))
    with (ROOT / "project_docs/reports/blind_review_reveal_sheet_dung.csv").open(encoding="utf-8-sig", newline="") as stream:
        dung = list(csv.DictReader(stream))
    normalize_snippet = lambda s: re.sub(r"\s+", "", s.replace("\\n", "\n").split("/* ... [")[0])
    mismatches = []
    for r in hieu:
        q = targets[str(r["target_id"])]
        if not normalize_snippet(q["func"]).startswith(normalize_snippet(r["target_code_snippet"])):
            mismatches.append({"sample_idx": r["sample_idx"], "target_id": r["target_id"],
                               "sheet_start": r["target_code_snippet"].replace("\\n", "\n").splitlines()[0],
                               "source_start": q["func"].splitlines()[0]})
    result["reveal_review_target_identity"] = {
        "rows": len(hieu), "not_source_prefix_after_whitespace_normalization": len(mismatches),
        "both_sheets_share_target_snippets": len(hieu) == len(dung) and all(
            a["target_id"] == b["target_id"] and a["target_code_snippet"] == b["target_code_snippet"]
            for a, b in zip(hieu, dung)),
        "mismatch_examples": mismatches[:3],
        "caveat": "Non-prefix alone may reflect abridgement; different function examples need source inspection."
    }
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
