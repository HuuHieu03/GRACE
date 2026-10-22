"""Function-level identities for versioned data manifests.

Legacy hashes are descriptive fields, never unique lookup keys. Labels are
excluded from identities so a label edit is detectable without changing UID.
"""
import hashlib
import json
from pathlib import PurePosixPath


def code_hash(code):
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Function code must be a nonempty string")
    canonical = code.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def stable_hash(value):
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_identity(dataset, split, source_path, code, label, legacy_id, source_row):
    if type(label) is not int or label not in (0, 1):
        raise ValueError("Label must be an integer 0 or 1; missing/unknown labels cannot default safe")
    path = PurePosixPath(str(source_path).replace("\\", "/"))
    if not dataset or not split or path.is_absolute() or ".." in path.parts or ":" in str(path) or str(path) in (".", ""):
        raise ValueError("Dataset/split and a workspace-relative source path are required")
    chash = code_hash(code)
    identity = {"schema": "function_uid_v2", "dataset": dataset, "split": split,
                "source_path": str(path), "code_sha256": chash}
    return {"function_uid": f"{dataset}:{split}:" + stable_hash(identity),
            "dataset": dataset, "split": split, "source_path": str(path), "code_sha256": chash,
            "target": label, "legacy_id": str(legacy_id), "legacy_row": source_row}


def validate_identities(rows):
    uids = [r["function_uid"] for r in rows]
    paths = [r["source_path"] for r in rows]
    if len(uids) != len(set(uids)) or len(paths) != len(set(paths)):
        raise ValueError("Duplicate function UID or source file in manifest")
    for r in rows:
        if type(r["target"]) is not int or r["target"] not in (0, 1):
            raise ValueError("Invalid manifest label")
        expected = f"{r['dataset']}:{r['split']}:" + stable_hash({
            "schema": "function_uid_v2", "dataset": r["dataset"], "split": r["split"],
            "source_path": r["source_path"], "code_sha256": r["code_sha256"]})
        if r["function_uid"] != expected:
            raise ValueError("Function UID does not match its identity fields")


def attach_manifest(rows, manifest):
    """Return new rows; require exact order/code/label alignment before reuse.

    Does not edit the original pool or permit a legacy-ID-only fallback.
    """
    identities = manifest["rows"]
    validate_identities(identities)
    if manifest.get("ordered_identity_sha256") != stable_hash(identities):
        raise ValueError("Ordered manifest hash mismatch")
    if len(rows) != len(identities):
        raise ValueError("Manifest and dataset row counts differ")
    result = []
    for index, (sample, identity) in enumerate(zip(rows, identities)):
        if (identity["legacy_row"] != index or str(sample["id"]) != identity["legacy_id"] or
                code_hash(sample["func"]) != identity["code_sha256"] or
                sample["target"] != identity["target"]):
            raise ValueError(f"Dataset identity/order/code/label mismatch at row {index}")
        result.append({**sample, "id": identity["function_uid"], "legacy_id": identity["legacy_id"],
                       "code_sha256": identity["code_sha256"], "c_file_path": identity["source_path"]})
    return result
