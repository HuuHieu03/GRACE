"""Inventory review inputs by actual run; never substitute B2 or fill votes."""
from collections import defaultdict
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from dataset_contract import attach_manifest, code_hash


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def inventory(root=ROOT):
    availability_path = root / "project_docs/reports/verified_review_inputs_2026-10-22/historical_availability.json"
    confirmed = load(availability_path) if availability_path.exists() else None
    results = []
    for dataset, stem, run in [("devign", "b3_vs_b2_comparison_report", "Ver03"),
                               ("reveal", "reveal_b3_vs_b2_comparison_report", "Ver04")]:
        manifest_dir = root / "data/manifests/function_uid_v2"
        train = json.loads(gzip.decompress((root / f"data/processed/{dataset}_train_compact_cpg.json.gz").read_bytes()))
        train = attach_manifest(train, load(manifest_dir / f"{dataset}_train.json"))
        target_rows = load(root / f"data/splits/{dataset}_dev_clean_100_ids.json")["sample_details"]
        targets = attach_manifest(target_rows, load(manifest_dir / f"{dataset}_validation.json"))
        target_map = {s["legacy_id"]: s for s in targets}
        by_full_identity = defaultdict(list)
        for row in train:
            by_full_identity[(row["legacy_id"], code_hash(row["func"]), row["target"])].append(row)
        report_path = root / "output/stage3" / (stem + ".json")
        report = load(report_path)
        if report["metadata"]["dataset"] != dataset:
            raise ValueError("Run dataset mismatch")
        b3_records = report["detailed_records_b3"]
        if len({r["target_id"] for r in b3_records}) != len(targets):
            raise ValueError("Missing/duplicate B3 targets")
        private = []
        for r in b3_records:
            target = target_map[str(r["target_id"])]
            if target["target"] != r["target"]:
                raise ValueError("Target label/source mismatch")
            pair_uids = []
            # Both demos retained. Target label is not used to choose either.
            for member in ["vulnerable", "safe"]:
                demo = r["contrastive_pair"][member]
                found = by_full_identity[(str(demo["id"]), code_hash(demo["func"]), demo["target"])]
                if len(found) != 1:
                    raise ValueError("B3 demo identity missing/ambiguous")
                pair_uids.append(found[0]["id"])
            private.append({"target_uid": target["id"], "target_code_sha256": target["code_sha256"],
                            "b3_demo_uids": pair_uids, "b2_demo_uid": None})
        # A future source adapter must validate actual B2 records and same-run
        # manifest. An aggregate report or Stage2 result is not a replacement.
        results.append({"dataset": dataset, "run": run, "source_report": report_path.relative_to(root).as_posix(),
                        "status": "BLOCKED_MISSING_ACTUAL_B2_RECORDS", "targets_verified": len(private),
                        "b3_pair_members_verified": len(private) * 2, "actual_b2_records_available": False,
                        "reviewer_packet_generated": False, "human_votes_generated": False,
                        "required_input": "Actual per-target B2 demo selection from this run, with function code/hash or unique source mapping and matching run/pool manifest.",
                        "prohibited_substitution": "Stage2 baseline or opposite-label member of B3 pair",
                        "private_identity_map": private})
    if confirmed and confirmed.get("confirmed_by") == "user":
        unavailable = {(r["dataset"], r["run"]) for r in confirmed["runs"]
                       if all(r.get(k) == "UNAVAILABLE_CONFIRMED" for k in
                              ["b2_per_id_prediction", "b2_raw_response", "b2_actual_prompt"])}
        for item in results:
            if (item["dataset"], item["run"]) in unavailable:
                item["status"] = "HISTORICAL_INPUTS_UNAVAILABLE_CONFIRMED_NEW_RUN_REQUIRED"
    status = ("HISTORICAL_INPUTS_UNAVAILABLE_CONFIRMED_NEW_RUN_REQUIRED"
              if all(r["status"].startswith("HISTORICAL_INPUTS_UNAVAILABLE") for r in results)
              else "BLOCKED_MISSING_ACTUAL_B2_RECORDS")
    return {"status": status, "datasets": results,
            "independent_human_review": "NOT_ESTABLISHED; needs two actual separate reviewers after valid packets exist"}


if __name__ == "__main__":
    result = inventory()
    folder = ROOT / "project_docs/reports/verified_review_inputs_2026-10-22"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "input_inventory_private.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
