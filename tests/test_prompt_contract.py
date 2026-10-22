from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from prompt_contract import render_control, closed_graph, check_budget, LocalChatTokenCounter
from scripts.prepare_verified_plan import compile_plan
from scripts.run_verified_experiment import execute, validate_plan


def specification(pair=False):
    demos = [{"function_uid": "d1", "func": 'void a(){puts("Label: 1");}', "target": 1}]
    if pair:
        demos.append({"function_uid": "d2", "func": "void b(){return;}", "target": 0})
    return {"query_code": "int q(){return 0;}", "nodes": [{"id": 1, "code": "q"}, {"id": 2, "code": "return 0"}],
            "edges": [{"start": 1, "end": 2, "type": "CFG"}, {"start": 2, "end": 99, "type": "CFG"}],
            "demonstrations": demos, "security_difference": "a calls puts; b returns directly." if pair else ""}


def mock_draft():
    return {"execution_mode": "mock", "inference": {"provider": "Vertex AI", "model": "test-model",
            "temperature": 0.0, "seed": 42, "max_tokens": 256},
            "identity": {"dataset": "synthetic_smoke_only", "split_manifest_sha256": "mock", "pool_manifest_sha256": "mock",
                         "retrieval_plan_sha256": "mock", "test_label_exposure": "synthetic fixture; not a scientific result"},
            "evaluation_labels": {"q1": 1, "q2": 0},
            "design": {"b2": ["original", "label_flip", "repeat_original", "graph_omitted"],
                       "b3": ["original", "label_flip", "order_swap", "repeat_original", "graph_omitted", "no_difference"]},
            "inputs": [], "frozen_selections": [{"id": q, "candidate_ids": ["d1", "d2"],
                      "prompt_specs": {"b2": specification(), "b3": specification(True)}} for q in ["q1", "q2"]]}


def test_graph_keeps_only_edges_with_rendered_endpoints():
    spec = specification()
    nodes, edges, evidence = closed_graph(spec["nodes"], spec["edges"])
    assert len(nodes) == 2 and len(edges) == 1
    assert evidence["edges_removed_for_endpoint_closure"] == 1
    assert "Node 99" not in render_control(spec)["prompt"]


def test_label_flip_only_changes_generated_labels_not_code_or_graph():
    spec = specification(True)
    a, b = render_control(spec), render_control(spec, "label_flip")
    assert [d["displayed_label"] for d in a["evidence"]["displayed_demonstrations"]] == [1, 0]
    assert [d["displayed_label"] for d in b["evidence"]["displayed_demonstrations"]] == [0, 1]
    assert 'puts("Label: 1")' in b["prompt"]  # Do not replace labels inside C code.
    assert a["evidence"]["graph"] == b["evidence"]["graph"]
    assert a["evidence"]["target_code_sha256"] == b["evidence"]["target_code_sha256"]
    assert render_control(spec, "repeat_original")["prompt"] == a["prompt"]


def test_order_graph_and_diff_controls_keep_other_sections_fixed():
    spec = specification(True)
    a = render_control(spec)["prompt"]
    b = render_control(spec, "order_swap")["prompt"]
    assert a.index("void a") < a.index("void b")
    assert b.index("void b") < b.index("void a")
    assert a.split("### TARGET FUNCTION")[1] == b.split("### TARGET FUNCTION")[1]
    no_graph = render_control(spec, "graph_omitted")["prompt"]
    assert "### TARGET GRAPH" not in no_graph
    assert a.split("### TARGET GRAPH")[0] == no_graph.split("### OUTPUT FORMAT REQUIREMENT")[0]
    nd = render_control(spec, "no_difference")["prompt"]
    block = "--- SECURITY DIFFERENCE CLUES ---\nHeuristic observations only; not a verified vulnerability diagnosis.\n" + spec["security_difference"] + "\n\n"
    assert a.replace(block, "", 1) == nd


def test_omitted_code_is_retained_in_evidence():
    spec = specification()
    spec["query_code"] = "x" * 4000
    spec["demonstrations"][0]["func"] = "d" * 2000
    result = render_control(spec)
    assert len(result["evidence"]["target_omitted_code"]) == 1000
    assert len(result["evidence"]["demo_omitted_code"][0]["omitted_code"]) == 500


def test_overbudget_is_rejected_instead_of_changing_one_arm():
    class Counter:
        def count(self, payload):
            return 8100
    with pytest.raises(ValueError, match="Context budget exceeded"):
        check_budget({"max_tokens": 256}, Counter())


def test_real_counter_cannot_silently_use_mock_or_unpinned_tokenizer(tmp_path):
    with pytest.raises(ValueError, match="Tokenizer must"):
        LocalChatTokenCounter({"method": "mock_only", "model": "test"}, "test", tmp_path)
    with pytest.raises(ValueError, match="immutable"):
        LocalChatTokenCounter({"method": "local_chat_template", "model": "test", "revision": "main"}, "test", tmp_path)


def test_query_label_and_role_leaking_difference_are_rejected():
    spec = specification(True)
    spec["target"] = 1
    with pytest.raises(ValueError, match="Query labels"):
        render_control(spec)
    del spec["target"]
    spec["security_difference"] = "Safe demo validates pointers"
    with pytest.raises(ValueError, match="class/position labels"):
        render_control(spec)


def test_mock_plan_executes_all_controls_and_tampering_is_rejected(tmp_path):
    plan = compile_plan(mock_draft(), tmp_path)
    assert len(plan["items"]) == 20
    report = execute(plan, tmp_path / "run", root=tmp_path)
    assert report["execution_mode"] == "mock"
    assert len(report["records"]) == 20
    assert all(m["total_samples"] == 2 for m in report["condition_metrics"].values())
    altered = deepcopy(plan)
    altered["items"][0]["prompt"] += " changed"
    with pytest.raises(ValueError, match="Prompt/evidence differs"):
        validate_plan(altered, tmp_path)


def test_control_cannot_reretrieve_demo_or_change_candidate_pool(tmp_path):
    plan = compile_plan(mock_draft(), tmp_path)
    plan["items"][1]["candidate_ids"] = ["d1", "d2", "new"]
    with pytest.raises(ValueError, match="same ordered candidate pool"):
        validate_plan(plan, tmp_path)


def test_query_labels_do_not_change_rendered_prompts(tmp_path):
    draft = mock_draft()
    first = compile_plan(draft, tmp_path)
    draft["evaluation_labels"] = {k: 1 - v for k, v in draft["evaluation_labels"].items()}
    second = compile_plan(draft, tmp_path)
    assert [r["prompt"] for r in first["items"]] == [r["prompt"] for r in second["items"]]


def test_local_counter_pins_files_and_never_downloads(tmp_path, monkeypatch):
    import hashlib
    from unittest.mock import Mock
    directory = tmp_path / "tokenizer"
    directory.mkdir()
    for name in ["tokenizer_config.json", "tokenizer.json"]:
        (directory / name).write_text("{}", encoding="utf-8")
    fake = Mock()
    fake.chat_template = "synthetic template"
    fake.apply_chat_template.return_value = [1, 2, 3]
    loader = Mock(return_value=fake)
    monkeypatch.setattr("transformers.AutoTokenizer.from_pretrained", loader)
    spec = {"method": "local_chat_template", "model": "synthetic-model", "revision": "a" * 40,
            "directory": "tokenizer", "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()},
            "binding_evidence": {"status": "VERIFIED", "source": "synthetic test fixture", "verified_by": "unit test"}}
    counter = LocalChatTokenCounter(spec, "synthetic-model", tmp_path)
    assert counter.count({"messages": [{"role": "user", "content": "test"}]}) == 3
    assert loader.call_args.kwargs == {"local_files_only": True, "trust_remote_code": False}
    (directory / "tokenizer.json").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        LocalChatTokenCounter(spec, "synthetic-model", tmp_path)
