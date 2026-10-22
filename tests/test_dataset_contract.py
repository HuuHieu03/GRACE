"""Function identity must survive legacy collisions and reject stale reuse."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dataset_contract import make_identity, stable_hash, attach_manifest, validate_identities


def make_manifest(samples):
    identities = [make_identity("reveal", "train", f"data/raw/train/row_{i}.c", s["func"], s["target"], s["id"], i)
                  for i, s in enumerate(samples)]
    return {"rows": identities, "ordered_identity_sha256": stable_hash(identities)}


def test_legacy_collision_does_not_collapse_different_functions():
    samples = [{"id": "legacy", "func": "int a(){return 0;}", "target": 0},
               {"id": "legacy", "func": "int b(){return 1;}", "target": 1}]
    attached = attach_manifest(samples, make_manifest(samples))
    assert attached[0]["id"] != attached[1]["id"]
    assert [s["func"] for s in attached] == [s["func"] for s in samples]
    assert [s["target"] for s in attached] == [0, 1]
    assert all(s["id"] == "legacy" for s in samples)


def test_labels_do_not_determine_uid_but_label_changes_invalidate_reuse():
    a = make_identity("d", "train", "data/a.c", "void a(){}", 0, "legacy", 0)
    b = make_identity("d", "train", "data/a.c", "void a(){}", 1, "legacy", 0)
    assert a["function_uid"] == b["function_uid"]
    samples = [{"id": "x", "func": "void a(){}", "target": 0}]
    manifest = make_manifest(samples)
    with pytest.raises(ValueError, match="label mismatch"):
        attach_manifest([{**samples[0], "target": 1}], manifest)


def test_changed_code_or_row_order_rejects_cache_identity():
    samples = [{"id": "same", "func": "void a(){}", "target": 0},
               {"id": "same", "func": "void b(){}", "target": 0}]
    manifest = make_manifest(samples)
    with pytest.raises(ValueError, match="mismatch at row"):
        attach_manifest(samples[::-1], manifest)
    with pytest.raises(ValueError, match="mismatch at row"):
        attach_manifest([{**samples[0], "func": "void changed(){}"}, samples[1]], manifest)


def test_duplicate_source_or_tampered_manifest_is_rejected():
    row = make_identity("d", "train", "data/a.c", "void a(){}", 0, "legacy", 0)
    with pytest.raises(ValueError, match="Duplicate"):
        validate_identities([row, row])
    samples = [{"id": "x", "func": "void a(){}", "target": 0}]
    manifest = make_manifest(samples)
    altered = deepcopy(manifest)
    altered["rows"][0]["target"] = 1
    with pytest.raises(ValueError, match="manifest hash mismatch"):
        attach_manifest(samples, altered)


@pytest.mark.parametrize("label", [None, "0", 2, -1, False])
def test_unknown_or_implicit_labels_cannot_default_safe(label):
    with pytest.raises(ValueError, match="Label must"):
        make_identity("d", "train", "data/a.c", "void a(){}", label, "x", 0)


@pytest.mark.parametrize("path", ["../outside.c", "C:/absolute.c", "/absolute.c"])
def test_source_identity_must_stay_workspace_relative(path):
    with pytest.raises(ValueError, match="workspace-relative"):
        make_identity("d", "train", path, "void a(){}", 0, "x", 0)
