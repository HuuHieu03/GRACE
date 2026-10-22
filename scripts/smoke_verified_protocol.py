"""Persist a clearly synthetic protocol smoke test; no credentials or APIs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_verified_plan import compile_plan
from scripts.run_verified_experiment import execute


def synthetic_draft():
    demos = [{"function_uid": "synthetic-demo-1", "func": "void a(char *p) { puts(p); }", "target": 1},
             {"function_uid": "synthetic-demo-2", "func": "void b(char *p) { if(p) puts(p); }", "target": 0}]
    selections = []
    for uid in ["synthetic-query-1", "synthetic-query-2"]:
        common = {"query_code": "void q(char *p) { puts(p); }", "nodes": [{"id": 1, "code": "q"}, {"id": 2, "code": "puts(p)"}],
                  "edges": [{"start": 1, "end": 2, "type": "CFG"}, {"start": 2, "end": 99, "type": "CFG"}]}
        selections.append({"id": uid, "candidate_ids": [d["function_uid"] for d in demos], "prompt_specs": {
            "b2": {**common, "demonstrations": demos[:1]},
            "b3": {**common, "demonstrations": demos,
                   "security_difference": "b has an if(p) condition; guard effectiveness is not proven."}}})
    return {"execution_mode": "mock", "identity": {"dataset": "SYNTHETIC_NOT_BENCHMARK",
            "split_manifest_sha256": "synthetic-only", "pool_manifest_sha256": "synthetic-only",
            "retrieval_plan_sha256": "synthetic-only", "test_label_exposure": "Synthetic invented labels; not gold security labels."},
            "inference": {"model": "mock-no-external-model", "provider": "Vertex AI", "temperature": 0.0, "max_tokens": 256, "seed": 42},
            "inputs": [], "evaluation_labels": {"synthetic-query-1": 1, "synthetic-query-2": 0},
            "design": {"b2": ["original", "label_flip", "repeat_original", "graph_omitted"],
                       "b3": ["original", "label_flip", "order_swap", "repeat_original", "graph_omitted", "no_difference"]},
            "frozen_selections": selections}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output/stage4_verified/mock_protocol_smoke_v1")
    args = parser.parse_args()
    plan = compile_plan(synthetic_draft())
    report = execute(plan, args.output)
    summary = {"execution_mode": "mock", "conditions": len(report["records"]),
               "api_calls": sum(r["sdk_call_attempts"] for r in report["records"]),
               "purpose": "Infrastructure/controls test only; no model-quality or gold-label conclusion.",
               "identity_hash": report["identity_hash"], "plan_sha256": report["plan_sha256"],
               "artifacts": args.output.relative_to(ROOT).as_posix() if args.output.is_relative_to(ROOT) else str(args.output)}
    out = ROOT / "project_docs/reports/verified_protocol_2026-10-22"
    out.mkdir(parents=True, exist_ok=True)
    (out / "mock_smoke_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
