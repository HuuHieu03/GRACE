"""Compile frozen selections into a checked plan; never call an LLM."""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from evaluator import make_request_payload
from prompt_contract import render_control, check_budget, MockTokenCounter, LocalChatTokenCounter
from scripts.run_verified_experiment import validate_plan


def compile_plan(draft, root=ROOT):
    plan = deepcopy(draft)
    selections = plan.pop("frozen_selections")
    plan["schema_version"] = 2
    plan["parser_policy"] = "strict_binary_v1"
    plan.setdefault("payload_contract", {})["version"] = "prompt_contract_v1"
    counter = (LocalChatTokenCounter(plan["payload_contract"]["tokenizer"], plan["inference"]["model"], root)
               if plan["execution_mode"] == "real" else MockTokenCounter())
    items = []
    for selection in selections:
        for arm, conditions in plan["design"].items():
            spec = selection["prompt_specs"][arm]
            for condition in conditions:
                rendered = render_control(spec, condition)
                payload = make_request_payload(plan["inference"], rendered["prompt"])
                items.append({"id": selection["id"], "arm": arm, "condition": condition,
                              "prompt": rendered["prompt"], "prompt_spec": deepcopy(spec),
                              "prompt_evidence": rendered["evidence"],
                              "target_code_sha256": rendered["evidence"]["target_code_sha256"],
                              "demonstrations": deepcopy(spec["demonstrations"]),
                              "candidate_ids": list(selection["candidate_ids"]),
                              "token_budget": check_budget(payload, counter)})
    plan["items"] = items
    validate_plan(plan, root)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = compile_plan(json.loads(args.draft.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(plan, stream, ensure_ascii=False, indent=2)
    print(f"Prepared {len(plan['items'])} conditions; no API calls")


if __name__ == "__main__":
    main()
