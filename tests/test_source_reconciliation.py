"""Reject provenance and identity errors before publishing a metrics table."""
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.reconcile_experiment_sources import build_registry, validate_records


@pytest.fixture
def artifact_root(tmp_path):
    registry = build_registry(ROOT)
    for relative in registry["sources"]:
        dst = tmp_path / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, dst)
    return tmp_path


def test_registry_excludes_conflicting_summary_and_marks_missing_b2():
    registry = build_registry(ROOT)
    excluded = [t for t in registry["historical_tables"] if t["status"] == "EXCLUDED_CONFLICT"]
    assert [t["path"] for t in excluded] == ["output/stage3/b3_vs_b2_comparison_summary.csv"]
    assert any(x["metric"] == "mcc" for x in excluded[0]["mismatches"])
    for r in registry["runs"]:
        if r["run_id"].startswith("stage3"):
            assert r["raw_response"] == "unavailable_in_export"
            assert r["paired_b2_statistics_support"].startswith("reported_only")


def test_changed_archive_is_not_silently_accepted(artifact_root):
    p = artifact_root / "kaggle_notebooks/stage3_b3_vs_b2/downloaded_runs/Ver03_B3_vs_B2_Comparison/b3_vs_b2_comparison_report.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["detailed_records_b3"][0]["pred_a"] ^= 1
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Working/archive JSON diverged"):
        build_registry(artifact_root)


def test_matching_archives_with_wrong_metrics_are_rejected(artifact_root):
    paths = [artifact_root / "output/stage3/b3_vs_b2_comparison_report.json",
             artifact_root / "kaggle_notebooks/stage3_b3_vs_b2/downloaded_runs/Ver03_B3_vs_B2_Comparison/b3_vs_b2_comparison_report.json"]
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        data["b3_contrastive"]["mcc"] = 0.9
        p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Recomputed metric mismatch"):
        build_registry(artifact_root)


def test_records_cannot_drop_invalid_or_change_ground_truth():
    row = {"target_id": "a", "target": 1, "pred_a": None, "valid_a": False,
           "pred_b": 0, "valid_b": True, "pred_c": 1, "valid_c": True}
    validate_records([row], {"a": 1})
    with pytest.raises(ValueError, match="entire declared target split"):
        validate_records([row], {"a": 1, "b": 0})
    with pytest.raises(ValueError, match="Ground truth mismatch"):
        validate_records([row], {"a": 0})
    with pytest.raises(ValueError, match="Duplicate"):
        validate_records([row, row], {"a": 1})


def test_validity_flag_must_agree_with_prediction():
    row = {"target_id": "a", "target": 1, "pred_a": 0, "valid_a": False}
    with pytest.raises(ValueError, match="validity contract"):
        validate_records([row], {"a": 1})
