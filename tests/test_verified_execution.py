"""Exercise durable evidence and coverage with fake SDKs, never real APIs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from evaluator import LLMEvaluator
from experiment_tracking import RunJournal, JournalError, read_jsonl
from scripts.run_verified_experiment import execute, validate_plan


@pytest.fixture(autouse=True)
def isolate_journal_transport_tests(monkeypatch):
    # Payload rendering/tokenizers have their own integration tests. These
    # fixtures exercise the real dispatch branch with a fake SDK only.
    monkeypatch.setattr("scripts.run_verified_experiment.validate_payload_plan", lambda plan, root: None)


def plan_for(root):
    source = root / "input.json"
    source.write_text('{"fixture":true}', encoding="utf-8")
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    return {"schema_version": 2, "execution_mode": "real", "parser_policy": "strict_binary_v1",
            "inference": {"provider": "Vertex AI", "model": "publishers/qwen/models/test", "temperature": 0.0,
                          "max_tokens": 256, "seed": 17},
            "identity": {"dataset": "synthetic_test", "split_manifest_sha256": sha, "pool_manifest_sha256": sha,
                         "retrieval_plan_sha256": sha, "test_label_exposure": "synthetic fixture only"},
            "inputs": [{"path": "input.json", "sha256": sha}], "design": {"b2": ["original"]},
            "evaluation_labels": {"q1": 1, "q2": 0},
            "items": [{"id": q, "arm": "b2", "condition": "original", "prompt": "Check code " + q,
                       "demonstrations": [{"function_uid": "demo", "func": "void d(){}"}],
                       "candidate_ids": ["demo"], "target_code_sha256": sha} for q in ["q1", "q2"]]}


class Completion:
    def __init__(self, content, finish="stop"):
        self.id = "fake-response"
        self.usage = {"prompt_tokens": 30, "completion_tokens": 1, "total_tokens": 31}
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content, reasoning_content=None), finish_reason=finish)]

    def model_dump(self, mode="json"):
        return {"id": self.id, "usage": self.usage, "choices": [{"message": {"content": self.choices[0].message.content},
                                                                 "finish_reason": self.choices[0].finish_reason}]}


def engine_for(plan, handler):
    engine = LLMEvaluator.__new__(LLMEvaluator)
    engine.model_name = plan["inference"]["model"]
    engine.provider = "Vertex AI"
    engine.use_mock = False
    for k in ["seed", "temperature", "max_tokens"]:
        setattr(engine, k, plan["inference"][k])
    engine.trace_callback = None
    engine.last_generation_metadata = None
    engine.get_access_token = lambda: "SECRET_TEST_TOKEN_NEVER_STORE"
    engine.client = SimpleNamespace(max_retries=0, api_key=None,
                                    chat=SimpleNamespace(completions=SimpleNamespace(create=handler)))
    return engine


def test_payload_is_durable_before_call_and_raw_usage_finish_are_saved(tmp_path):
    plan = plan_for(tmp_path)
    folder = tmp_path / "run"
    calls = []

    def create(**payload):
        events = read_jsonl(folder / "events.jsonl")
        assert events[-1]["event"] == "sdk_request"
        assert events[-1]["payload"] == payload
        assert payload["seed"] == 17
        assert "evaluation_labels" not in payload
        calls.append(payload)
        return Completion(" 1 " if len(calls) == 1 else "Non-vulnerable")

    report = execute(plan, folder, engine_for(plan, create), root=tmp_path, sleep=lambda _: None)
    records = report["records"]
    assert records[0]["llm_raw_response"] == " 1 "
    assert records[0]["usage"]["total_tokens"] == 31
    assert records[0]["finish_reason"] == "stop"
    assert records[1]["prediction"] is None
    m = report["condition_metrics"]["b2/original"]
    assert (m["total_samples"], m["valid_samples"], m["invalid_samples"], m["invalid_rate"]) == (2, 1, 1, .5)
    assert "SECRET_TEST_TOKEN_NEVER_STORE" not in (folder / "events.jsonl").read_text(encoding="utf-8")


def test_exhausted_requests_stay_in_denominator_and_attempts_are_bounded(tmp_path):
    plan = plan_for(tmp_path)
    calls, waits = [], []

    def create(**payload):
        calls.append(payload)
        if len(calls) <= 5:
            raise TimeoutError("fake failure")
        return Completion("0")

    report = execute(plan, tmp_path / "run", engine_for(plan, create), root=tmp_path, sleep=waits.append)
    assert len(calls) == 6
    assert waits == [5, 10, 20, 40]
    invalid = report["records"][0]
    assert invalid["attempts"] == invalid["sdk_call_attempts"] == 5
    assert invalid["raw_response_available"] is False
    assert invalid["prediction"] is None
    assert report["condition_metrics"]["b2/original"]["total_samples"] == 2


def test_resume_completed_run_needs_no_client_or_more_calls(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return Completion("1")

    first = execute(plan, tmp_path / "run", engine_for(plan, create), root=tmp_path)
    def forbidden_client(**kwargs):
        raise AssertionError("Completed run must not initialize/authenticate a client")
    monkeypatch.setattr("scripts.run_verified_experiment.LLMEvaluator", forbidden_client)
    second = execute(plan, tmp_path / "run", root=tmp_path)
    assert len(calls) == 2
    assert first["condition_metrics"] == second["condition_metrics"]


def test_resume_changed_prompt_or_input_is_rejected(tmp_path):
    plan = plan_for(tmp_path)
    execute(plan, tmp_path / "run", engine_for(plan, lambda **_: Completion("1")), root=tmp_path)
    changed = deepcopy(plan)
    changed["items"][0]["prompt"] += " changed"
    with pytest.raises(JournalError, match="identity mismatch"):
        execute(changed, tmp_path / "run", root=tmp_path)
    (tmp_path / "input.json").write_text("changed file", encoding="utf-8")
    with pytest.raises(ValueError, match="Pinned input hash mismatch"):
        validate_plan(plan, tmp_path)


def test_persistence_failure_after_response_does_not_retry_paid_call(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = []
    append = RunJournal._append

    def fail_response(self, path, record):
        if record.get("event") == "sdk_response":
            raise JournalError("fake disk failure")
        return append(self, path, record)

    monkeypatch.setattr(RunJournal, "_append", fail_response)
    def create(**payload):
        calls.append(payload)
        return Completion("1")
    engine = engine_for(plan, create)
    with pytest.raises(JournalError, match="fake disk failure"):
        execute(plan, tmp_path / "run", engine, root=tmp_path)
    assert len(calls) == 1
    assert engine.trace_callback is None


def test_unfinished_or_corrupt_journals_are_not_silently_resumed(tmp_path):
    identity = {"plan": "frozen"}
    item = {"id": "q", "arm": "b2", "condition": "original"}
    journal = RunJournal(tmp_path / "pending", identity)
    journal.event(item, 1, {"event": "sdk_request", "payload": {}})
    with pytest.raises(JournalError, match="Unfinished request"):
        RunJournal(tmp_path / "pending", identity)
    corrupt = RunJournal(tmp_path / "corrupt", identity)
    corrupt.records_path.write_text('{"id":', encoding="utf-8")
    with pytest.raises(JournalError, match="Corrupt journal"):
        RunJournal(tmp_path / "corrupt", identity)


def test_every_target_needs_every_condition_and_labels_stay_outside_items(tmp_path):
    plan = plan_for(tmp_path)
    plan["design"]["b2"].append("repeat_original")
    with pytest.raises(ValueError, match="every declared arm/condition"):
        validate_plan(plan, tmp_path)
    plan = plan_for(tmp_path)
    plan["items"][0]["target"] = 1
    with pytest.raises(ValueError, match="outside inference items"):
        validate_plan(plan, tmp_path)


def test_length_finish_is_invalid_even_for_binary_content(tmp_path):
    plan = plan_for(tmp_path)
    report = execute(plan, tmp_path / "run", engine_for(plan, lambda **_: Completion("1", "length")), root=tmp_path)
    assert all(r["prediction"] is None and not r["is_valid"] for r in report["records"])
    assert report["condition_metrics"]["b2/original"]["invalid_rate"] == 1
