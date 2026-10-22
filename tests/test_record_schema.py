import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from record_schema import normalize_records
from common_evaluator import load_records_from_file, audit_and_reparse, align_to_split


def test_real_stage2_adapter_reparses_each_condition_without_pooling():
    path = ROOT / "output/stage2/label_flip/label_flip_test_report.json"
    for name in ["original", "label_flip", "repeat_original"]:
        rows = load_records_from_file(path, condition=name, arm="b2")
        assert len(rows) == len({r["id"] for r in rows}) == 100
        report = audit_and_reparse(rows)
        assert report["label_changed_count"] == report["raw_unavailable_count"] == 0
        assert report["reparsed_count"] == 100


def test_stage3_missing_raw_does_not_get_fabricated_as_empty_response():
    path = ROOT / "output/stage3/b3_vs_b2_comparison_report.json"
    rows = load_records_from_file(path, arm="b3")
    report = audit_and_reparse(rows)
    assert report["raw_unavailable_count"] == 100
    assert report["reparsed_count"] == 0
    assert report["metrics_before"] == report["metrics_after"]
    assert report["label_changed_count"] == 0


def test_new_strict_policy_is_preserved_during_reparse():
    rows = normalize_records({"records": [{"id": "q", "target": 0, "prediction": None, "is_valid": False,
                                           "llm_raw_response": "Non-vulnerable", "parser_policy": "strict_binary_v1"}]})
    report = audit_and_reparse(rows)
    assert report["reparsed_records"][0]["prediction"] is None
    assert report["invalid_count"] == 1


def test_duplicates_and_missing_labels_cannot_silently_shrink_denominator():
    with pytest.raises(ValueError, match="Duplicate"):
        normalize_records([{"id": "q", "target": 1}, {"id": "q", "target": 1}])
    with pytest.raises(ValueError, match="Missing ground truth"):
        normalize_records([{"id": "q", "prediction": 0}])
    with pytest.raises(ValueError, match="aggregate metrics"):
        normalize_records({"accuracy": .9})


def test_csv_false_validity_and_empty_raw_are_distinct_from_missing_raw():
    row = normalize_records([{"id": "q", "target": "0", "prediction": "1", "is_valid": "false",
                              "llm_raw_response": ""}])[0]
    assert row["prediction"] is None
    assert row["raw_response_available"] is True


def test_split_alignment_never_uses_ambiguous_numeric_alias_or_drops_missing_ids():
    split = {"sample_details": [{"id": "id_7_label_True_p.c", "target": 1}]}
    with pytest.raises(ValueError, match="exactly"):
        align_to_split([{"id": "7", "target": 1}], split)
    with pytest.raises(ValueError, match="labels disagree"):
        align_to_split([{"id": "id_7_label_True_p.c", "target": 0}], split)
    with pytest.raises(ValueError, match="exactly"):
        align_to_split([], split)


def test_legacy_stage3_cannot_make_new_untracked_real_calls():
    from scripts.run_stage3_b3_vs_b2 import run_stage3_experiment
    with pytest.raises(RuntimeError, match="Legacy Stage3 real inference is retired"):
        run_stage3_experiment(Path("does-not-exist.json"), use_mock=False)
