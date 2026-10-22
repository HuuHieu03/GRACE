"""Read-only audit of archived experiment evidence; never calls an LLM.

Run: python scripts/audit_report_readiness.py
Output is printed as JSON; redirect it to retain an audit snapshot.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from evaluator import parse_llm_prediction
from metrics import compute_classification_metrics
from scripts.fill_dung_review_sheet import analyze_pair


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit():
    result = {"scope": "local archived records and current source; no API calls"}
    runs = {}
    for filename in ["b3_vs_b2_comparison_report.json", "reveal_b3_vs_b2_comparison_report.json",
                     "ablation_nodiff_comparison_report.json"]:
        data = read("output/stage3/" + filename)
        records = data["detailed_records_b3"]
        metrics = compute_classification_metrics([r["target"] for r in records],
                                                [r["pred_a"] for r in records])
        split = read("data/splits/" + data["metadata"]["dataset"] + "_dev_clean_100_ids.json")
        labels = {str(s["id"]): s["target"] for s in split["sample_details"]}
        runs[filename] = {
            "records": len(records), "unique_ids": len({r["target_id"] for r in records}),
            "all_ids_and_labels_match_split": all(labels.get(str(r["target_id"])) == r["target"] for r in records),
            "recomputed_b3_metrics_match": metrics == data["b3_contrastive"],
            "invalid_a": sum(not r["valid_a"] for r in records),
            "raw_response_or_prompt_keys": [k for k in records[0] if "raw" in k or "prompt" in k],
            "paired_ci": data["paired_bootstrap_95_ci"],
            "b3_metrics": metrics,
            "fallback": data["selector_fallback_telemetry"],
        }
    result["stage3"] = runs
    full = read("output/stage3/b3_vs_b2_comparison_report.json")["detailed_records_b3"]
    nd = read("output/stage3/ablation_nodiff_comparison_report.json")
    nd_map = {r["target_id"]: r for r in nd["detailed_records_b3"]}
    result["ablation"] = {
        "same_demo_bodies_and_ids": sum(
            all(r["contrastive_pair"][k] == nd_map[r["target_id"]]["contrastive_pair"][k]
                for k in ["vulnerable", "safe"]) for r in full),
        "full_vs_nodiff_ci": nd["paired_bootstrap_full_vs_nodiff"],
    }
    graph = {}
    for ds in ["devign", "reveal"]:
        samples = read(f"data/splits/{ds}_dev_clean_100_ids.json")["sample_details"]
        dangling = 0
        for s in samples:
            ids = {str(n["id"]) for n in s["nodes"][:25]}
            dangling += any(str(e.get("start", e.get("source"))) not in ids or
                            str(e.get("end", e.get("target"))) not in ids for e in s["edges"][:25])
        graph[ds] = {"samples": len(samples), "empty_code": sum(not s["func"] for s in samples),
                     "queries_with_edge_endpoint_outside_rendered_nodes": dangling}
    result["current_renderer_graph_prefix_audit"] = graph
    rows = list(csv.DictReader((ROOT / "project_docs/reports/blind_review_sheet_dung.csv").open(encoding="utf-8-sig")))
    matches = 0
    fields = ["sink_match_A", "variable_match_A", "guard_match_A", "sink_match_B", "variable_match_B", "guard_match_B"]
    for r in rows:
        a = analyze_pair(r["target_code_snippet"], r["demo_A_snippet"])
        b = analyze_pair(r["target_code_snippet"], r["demo_B_snippet"])
        delta = a[3] - b[3]
        choice = ("Equal" if a[3] >= 3 and b[3] >= 3 else "Neither") if abs(delta) < .6 else ("A" if delta > 0 else "B")
        matches += choice == r["better_demo (A/B/Equal/Neither)"] and all(str(x) == r[k] for x, k in zip(a[:3] + b[:3], fields))
    result["dung_sheet"] = {"rows": len(rows), "exact_heuristic_choice_and_all_six_rubric_matches": matches,
                            "caveat": "Match is evidence of heuristic compatibility, not proof of who executed the script."}
    result["old_review_label_conditioning"] = {}
    for ds, filename in [("devign", "blind_review_answer_key.json"), ("reveal", "blind_review_reveal_answer_key.json")]:
        keys = read("project_docs/reports/" + filename)["answer_key"]
        result["old_review_label_conditioning"][ds] = {
            "rows": len(keys),
            "security_demo_same_label_as_target": sum(k["security_aware_demo_label"] == k["target_label"] for k in keys),
            "baseline_demo_opposite_label_to_target": sum(k["baseline_demo_label"] != k["target_label"] for k in keys),
        }
    result["parser_probes"] = {s: parse_llm_prediction(s) for s in
                               ["0", "1", "Vulnerable", "Non-vulnerable", "", "cannot determine\n1",
                                "0\n1", "There are 0 vulnerabilities", "Non-vulnerable (1)"]}
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
