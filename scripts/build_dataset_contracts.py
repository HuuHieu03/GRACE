"""Build v2 function identity sidecars; preserve all historical datasets/runs."""
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from dataset_contract import make_identity, code_hash, stable_hash, validate_identities, attach_manifest
from scripts.audit_code_leakage import normalize_code_semantic


def load(path):
    if path.suffix == ".gz":
        return json.loads(gzip.decompress(path.read_bytes()))
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_code(row):
    return row.get("func") or row.get("functionSource") or row.get("code") or ""


def layout_hash(code):
    # Used only to classify existing physical line-layout differences.
    # Exact code hashes are retained separately; this is not a semantic proof.
    return code_hash(re.sub(r"[\r\n]+", "\n", code))


def build(dataset, root=ROOT):
    bank_path = root / f"data/processed/{dataset}_train_compact_cpg.json.gz"
    metadata_path = root / f"data/raw_c_files/{dataset}/train_metadata.json"
    split_path = root / f"data/splits/{dataset}_dev_clean_100_ids.json"
    pool, metadata, old_split = load(bank_path), load(metadata_path), load(split_path)
    lookup = defaultdict(list)
    for r in metadata:
        legacy = str(r["id"]) if dataset == "reveal" else Path(r["c_file_path"].replace("\\", "/")).name
        lookup[(legacy, layout_hash(source_code(r)), r["target"])].append(r)
    # Resolve only a unique full-code/label/source mapping, never dict[legacy_id].
    train = []
    for index, row in enumerate(pool):
        candidates = lookup.get((str(row["id"]), layout_hash(row["func"]), row["target"]), [])
        if len(candidates) != 1:
            raise ValueError(f"Ambiguous/missing raw metadata source at {dataset} train row {index}: {len(candidates)}")
        m = candidates[0]
        identity = make_identity(dataset, "train", m["c_file_path"], row["func"], row["target"], row["id"], index)
        identity["metadata_code_sha256"] = code_hash(source_code(m))
        train.append(identity)
    targets = [make_identity(dataset, "validation", r["c_file_path"], r["func"], r["target"], r["id"], i)
               for i, r in enumerate(old_split["sample_details"])]
    for group in [train, targets]:
        validate_identities(group)
    # Verify every code mapping against the original local .c file.
    def verify_file(pair):
        identity, sample = pair
        # make_identity already rejects absolute paths and traversal.
        path = root / identity["source_path"]
        file_code = path.read_text(encoding="utf-8", errors="strict")
        identity["source_file_code_sha256"] = code_hash(file_code)
        if identity["source_file_code_sha256"] == identity["code_sha256"]:
            identity["source_match"] = "EXACT_CANONICAL_TEXT"
        elif layout_hash(file_code) == layout_hash(sample["func"]):
            identity["source_match"] = "LINE_LAYOUT_VARIANT_NOT_SEMANTICALLY_VERIFIED"
        else:
            raise ValueError("Source .c code mismatch beyond line layout: " + identity["source_path"])
    print(f"Verifying {dataset}: {len(train)} train + {len(targets)} target source files...", flush=True)
    with ThreadPoolExecutor(max_workers=8) as executor:
        for _ in executor.map(verify_file, zip(train + targets, pool + old_split["sample_details"])):
            pass
    print(f"Source file verification completed: {dataset}", flush=True)
    exact, normalized = defaultdict(list), defaultdict(list)
    for r, identity in zip(pool, train):
        exact[identity["code_sha256"]].append(identity)
        normalized[normalize_code_semantic(r["func"])].append(identity)
    overlaps = []
    for r, identity in zip(old_split["sample_details"], targets):
        matches = normalized.get(normalize_code_semantic(r["func"]), [])
        identity["normalized_train_overlap"] = bool(matches)
        identity["eligibility"] = "QUARANTINED_CODE_OVERLAP" if matches else "DEVELOPMENT_ONLY_NEAR_CLONE_AUDIT_PENDING"
        if matches:
            overlaps.append({"query_uid": identity["function_uid"], "legacy_query_id": identity["legacy_id"],
                             "query_target": identity["target"],
                             "train_matches": [{"uid": m["function_uid"], "target": m["target"],
                                                "exact_code": m["code_sha256"] == identity["code_sha256"]} for m in matches]})
    inputs = {str(p.relative_to(root)).replace("\\", "/"): file_hash(p) for p in [bank_path, metadata_path, split_path]}
    manifests = {}
    for split, identities in [("train", train), ("validation", targets)]:
        manifests[split] = {"schema_version": 2, "dataset": dataset, "split": split, "inputs": inputs,
                            "function_identity": "source path + dataset + split + code hash; label excluded",
                            "ordered_identity_sha256": stable_hash(identities), "rows": identities,
                            "label_counts": dict(Counter(str(r["target"]) for r in identities)),
                            "source_file_verification": dict(Counter(r["source_match"] for r in identities)), "new_inference_run": False,
                            "ground_truth_verified": False, "near_clone_audit": "PENDING"}
    # Check that these sidecars can be applied losslessly without changing data/order.
    attach_manifest(pool, manifests["train"])
    attach_manifest(old_split["sample_details"], manifests["validation"])
    summary = {"dataset": dataset, "train_rows": len(train), "unique_function_uids": len({r['function_uid'] for r in train}),
               "legacy_unique_train_ids": len({r['legacy_id'] for r in train}),
               "actual_target_labels": manifests["validation"]["label_counts"],
               "historical_metadata_labels": {"1": old_split["vulnerable_count"], "0": old_split["safe_count"]},
               "overlaps": overlaps, "policy": "Keep all historical rows/labels; quarantine overlapping targets in future evaluation. No relabeling or replacement samples.",
               "source_verification": dict(Counter(r["source_match"] for r in train + targets)), "near_clone_audit": "PENDING",
               "dataset_revision": "local input SHA256 snapshots; upstream revision not independently verified"}
    return manifests, summary


def write_manifest_registry(out, report_dir):
    registry = []
    for path in sorted(out.glob("*.json")):
        manifest = load(path)
        registry.append({"path": path.relative_to(ROOT).as_posix(), "sha256": file_hash(path),
                         "bytes": path.stat().st_size, "rows": len(manifest["rows"]),
                         "ordered_identity_sha256": manifest["ordered_identity_sha256"],
                         "label_counts": manifest["label_counts"],
                         "metadata_layout_variants": sum(r.get("metadata_code_sha256", r["code_sha256"]) != r["code_sha256"]
                                                         for r in manifest["rows"])})
    (report_dir / "manifest_registry.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    out = ROOT / "data/manifests/function_uid_v2"
    report_dir = ROOT / "project_docs/reports/data_contract_v2_2026-10-22"
    # Build both datasets successfully before writing any manifest.
    built = {ds: build(ds) for ds in ["devign", "reveal"]}
    out.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for ds, (manifests, summary) in built.items():
        for split, manifest in manifests.items():
            (out / f"{ds}_{split}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summaries.append(summary)
    (report_dir / "audit.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_manifest_registry(out, report_dir)
    print(json.dumps([{k: v for k, v in s.items() if k != "overlaps"} for s in summaries], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
