"""Execute a frozen prompt plan with durable per-condition evidence.

Default CLI validates only. --execute runs the explicitly declared real/mock
mode. Plan preparation and payload/context controls belong to the next step.
This runner performs no retrieval and never imports another run's baseline.
"""
from collections import defaultdict
import argparse
import hashlib
from importlib.metadata import version, PackageNotFoundError
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from dataset_contract import stable_hash
from evaluator import LLMEvaluator, parse_strict_binary
from experiment_tracking import RunJournal, JournalError, record_key, run_lock, verify_pinned_inputs
from metrics import compute_classification_metrics
from prompt_contract import validate_payload_plan

RETRY_POLICY = {"max_attempts": 5, "initial_backoff_seconds": 5, "max_backoff_seconds": 120,
                "sdk_max_retries": 0, "retry_on": ["api_error", "empty_final_content"],
                "exhausted_request": "invalid"}


def validate_plan(plan, root=ROOT):
    if plan.get("schema_version") != 2 or plan.get("execution_mode") not in ("real", "mock"):
        raise ValueError("An explicit v2 real/mock plan is required")
    inference = plan["inference"]
    required = {"dataset", "split_manifest_sha256", "pool_manifest_sha256", "retrieval_plan_sha256", "test_label_exposure"}
    if not required <= plan["identity"].keys() or not all(plan["identity"][k] is not None for k in required):
        raise ValueError("Incomplete dataset/split/retrieval identity or test exposure declaration")
    if inference["provider"] != "Vertex AI":
        raise ValueError("New real/mock protocol currently validates Vertex AI payloads only")
    if (not isinstance(inference["model"], str) or not inference["model"] or
            type(inference["max_tokens"]) is not int or inference["max_tokens"] <= 0 or
            type(inference["seed"]) is not int or type(inference["temperature"]) not in (int, float) or
            not math.isfinite(inference["temperature"]) or inference["temperature"] < 0):
        raise ValueError("Invalid inference configuration")
    if plan.get("parser_policy") != "strict_binary_v1":
        raise ValueError("New runs must declare strict_binary_v1 before execution")
    if plan.get("retry_policy", RETRY_POLICY) != RETRY_POLICY:
        raise ValueError("Declared retry policy differs from the implemented policy")
    labels = plan["evaluation_labels"]
    if not labels or any(type(v) is not int or v not in (0, 1) for v in labels.values()):
        raise ValueError("Evaluation labels must be complete binary labels")
    items = plan["items"]
    keys = [record_key(item) for item in items]
    if len(keys) != len(set(keys)) or {item["id"] for item in items} != set(labels):
        raise ValueError("Duplicate conditions, missing target IDs, or unexpected labels")
    expected = {(uid, arm, condition) for uid in labels for arm, conditions in plan["design"].items() for condition in conditions}
    if {(i["id"], i["arm"], i["condition"]) for i in items} != expected:
        raise ValueError("Each target must retain every declared arm/condition")
    for item in items:
        if not isinstance(item["prompt"], str) or not item["prompt"].strip():
            raise ValueError("Empty prompt")
        if "target" in item:
            raise ValueError("Ground truth must stay in evaluation_labels, outside inference items")
        if not {"demonstrations", "candidate_ids", "target_code_sha256"} <= item.keys():
            raise ValueError("Each request needs frozen target/demo/candidate evidence")
    if plan["execution_mode"] == "real" and not plan.get("inputs"):
        raise ValueError("Real runs require pinned local input artifacts")
    verify_pinned_inputs(root, plan.get("inputs", []))
    validate_payload_plan(plan, root)
    return stable_hash(plan)


def execute(plan, folder, engine=None, root=ROOT, sleep=time.sleep):
    plan_hash = validate_plan(plan, root)
    inference = plan["inference"]
    is_mock = plan["execution_mode"] == "mock"
    source_paths = [ROOT / "src" / name for name in ["evaluator.py", "experiment_tracking.py", "metrics.py",
                                                    "dataset_contract.py", "record_schema.py", "prompt_contract.py",
                                                    "prompt_engine.py"]] + [Path(__file__)]
    try:
        sdk_version = version("openai")
    except PackageNotFoundError:
        sdk_version = "not_installed"
    try:
        git_commit = subprocess.check_output(["git", "-c", "safe.directory=" + ROOT.as_posix(), "rev-parse", "HEAD"],
                                             cwd=ROOT, stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        git_commit = "unavailable"
    identity = {"plan": plan, "plan_sha256": plan_hash,
                "execution_policy": RETRY_POLICY, "openai_sdk_version": sdk_version,
                "git_commit": git_commit, "python_version": sys.version,
                "runner_source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}}
    with run_lock(folder):
        journal = RunJournal(folder, identity)
        pending = any(record_key(item) not in journal.records for item in plan["items"])
        if engine is None and pending:
            engine = LLMEvaluator(model_name=inference["model"], provider=inference["provider"],
                                  temperature=inference["temperature"], max_tokens=inference["max_tokens"],
                                  seed=inference["seed"], use_mock=is_mock)
        if engine is not None and (engine.use_mock != is_mock or engine.model_name != inference["model"] or engine.provider != inference["provider"]):
            raise ValueError("Engine mode/model/provider disagrees with frozen plan")
        for field in ["temperature", "max_tokens", "seed"]:
            if engine is not None and getattr(engine, field) != inference[field]:
                raise ValueError("Engine inference parameters disagree with plan: " + field)
        if engine is not None and not is_mock and getattr(engine.client, "max_retries", None) != 0:
            raise ValueError("SDK retries must be disabled; the journal owns all attempts")
        for item in plan["items"]:
            key = record_key(item)
            if key in journal.records:
                continue
            raw, attempts, sdk_calls = "", 0, 0
            metadata = {}
            for attempt in range(1, 6):
                attempts = attempt
                # Events are persisted before SDK dispatch; no credentials included.
                journal.event(item, attempt, {"event": "attempt_start"})
                def trace(event, i=item, a=attempt):
                    nonlocal sdk_calls
                    journal.event(i, a, event)
                    if event["event"] == "sdk_request":
                        sdk_calls += 1
                engine.trace_callback = trace
                try:
                    returned = engine.generate_response(item["prompt"])
                    metadata = engine.last_generation_metadata or {}
                    raw = metadata.get("raw_content", returned)
                    if not isinstance(raw, str):
                        raw = ""
                    if raw.strip():
                        break
                except JournalError:
                    raise  # Never retry after loss of durable evidence.
                except Exception as exc:
                    journal.event(item, attempt, {"event": "request_error", "error_type": type(exc).__name__,
                                                   "status_code": getattr(exc, "status_code", None)})
                    raw, metadata = "", {}
                finally:
                    engine.trace_callback = None
                if attempt < 5:
                    sleep(min(5 * 2 ** (attempt - 1), 120))
            finish = metadata.get("finish_reason")
            prediction, method, valid = parse_strict_binary(raw, finish)
            journal.save({"id": item["id"], "arm": item["arm"], "condition": item["condition"],
                          "target": plan["evaluation_labels"][item["id"]], "prediction": prediction,
                          "is_valid": valid, "parse_method": method, "parser_policy": "strict_binary_v1",
                          "llm_raw_response": raw, "raw_response_available": "raw_content" in metadata, "attempts": attempts,
                          "sdk_call_attempts": sdk_calls,
                          "payload_provenance": "actual_sdk_call_arguments" if sdk_calls else ("mock_only" if is_mock else "planned_not_dispatched"),
                          "request_payload": engine.build_request_payload(item["prompt"]),
                          "prompt_sha256": hashlib.sha256(item["prompt"].encode("utf-8")).hexdigest(),
                          "finish_reason": finish, "usage": metadata.get("usage"),
                          "demonstrations": item["demonstrations"], "candidate_ids": item["candidate_ids"],
                          "target_code_sha256": item["target_code_sha256"], "execution_mode": plan["execution_mode"]})
        if engine is not None:
            engine.trace_callback = None
        records = list(journal.records.values())
        if {record_key(r) for r in records} != {record_key(i) for i in plan["items"]}:
            raise JournalError("Completed record set differs from the frozen plan")
        groups = defaultdict(list)
        for r in records:
            if r["target"] != plan["evaluation_labels"][r["id"]]:
                raise JournalError("Stored evaluation label mismatch")
            groups[r["arm"] + "/" + r["condition"]].append(r)
        metrics = {name: compute_classification_metrics([r["target"] for r in rows],
                                                       [r["prediction"] for r in rows]) for name, rows in groups.items()}
        report = {"schema_version": 2, "execution_mode": plan["execution_mode"],
                  "scientific_improvement_claim": "NOT_ESTABLISHED", "identity_hash": journal.identity_hash,
                  "plan_sha256": plan_hash, "condition_metrics": metrics, "records": records}
        temporary = Path(folder) / "report.json.tmp"
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(Path(folder) / "report.json")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    fingerprint = validate_plan(plan)
    if not args.execute:
        print(f"VALIDATED_ONLY: {fingerprint}; {len(plan['items'])} requests planned; no API calls")
        return
    if args.output is None:
        parser.error("--output must identify a new run directory")
    report = execute(plan, args.output)
    print(f"Completed {len(report['records'])} conditions in {report['execution_mode']} mode")


if __name__ == "__main__":
    main()
