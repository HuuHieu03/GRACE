import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from grace_diag.probes import ARMS, DonorPool, render_arm, diff_blocks, assert_no_label_leak, split_blocks  # noqa: E402
from grace_diag.token_budget import TokenCounter  # noqa: E402


def make_graph(n, prefix="n"):
    nodes = [{"id": f"{prefix}{i}", "type": "CALL" if i % 3 else "IDENTIFIER", "code": f"x{i} = f(y{i})"} for i in range(n)]
    edges = [{"start": f"{prefix}{i}", "end": f"{prefix}{i+1}", "type": "CFG"} for i in range(n - 1)]
    return nodes, edges


@pytest.fixture
def spec():
    nodes, edges = make_graph(40)
    return {
        "id": "t1",
        "query_code": "int f(char *p){ char b[8]; strcpy(b, p); return 0; }\n" * 5,
        "nodes": nodes, "edges": edges,
        "demonstrations": [{"function_uid": "d1", "func": "void g(){ memcpy(a,b,n); }", "target": 1}],
        "demonstrations_pair": [{"function_uid": "d1", "func": "void g(){ memcpy(a,b,n); }", "target": 1},
                                 {"function_uid": "d2", "func": "void g(){ if(n<=sizeof a) memcpy(a,b,n); }", "target": 0}],
        "security_difference": "the second checks n against the buffer size before memcpy",
        "h2_evidence": "memcpy(a,b,n) <- n unchecked; guard: none",
    }


@pytest.fixture
def donors():
    rows = []
    for k in range(30):
        nodes, edges = make_graph(10 + k * 2, prefix=f"g{k}_")
        rows.append({"function_uid": f"tr{k}", "func": f"int h{k}(int a){{ return a*{k}; }}", "target": k % 2, "nodes": nodes, "edges": edges})
    return DonorPool(rows)


COUNTER = TokenCounter(None)


def test_every_arm_renders_and_no_leak(spec, donors):
    for arm in ARMS:
        r = render_arm(spec, arm, seed=42, counter=COUNTER, donors=donors)
        assert r.prompt.endswith("Answer (0 or 1):")
        assert_no_label_leak(r.prompt)
        assert r.evidence["tokens"]["total"] <= 8192
        blocks = split_blocks(r.prompt)
        assert blocks["code"].startswith("int f(")


def test_target_label_refused(spec):
    with pytest.raises(ValueError):
        render_arm({**spec, "target": 1}, "B2", counter=COUNTER)


@pytest.mark.parametrize("arm,base,expected", [
    ("B1", "B0", {"graph"}), ("B1-full", "B1", {"graph"}), ("B1-H2", "B1", {"graph"}), ("B1-shuf", "B1", {"graph"}),
    ("B2", "B1", {"demo"}), ("B2-rand", "B2", {"demo"}), ("B2-nolabel", "B2", {"demo"}), ("B2-labelonly", "B2", {"demo"}),
    ("B2-flip", "B2", {"demo"}), ("B2-rep", "B2", set()), ("B3", "B1", {"demo"}), ("B3-nodiff", "B3", {"demo"}),
    ("B3-swap", "B3", {"demo"}), ("B3-flip", "B3", {"demo"}),
])
def test_each_probe_changes_exactly_one_block(spec, donors, arm, base, expected):
    a = render_arm(spec, arm, seed=42, counter=COUNTER, donors=donors).prompt
    b = render_arm(spec, base, seed=42, counter=COUNTER, donors=donors).prompt
    assert set(diff_blocks(a, b)) == expected


def test_flip_and_order(spec, donors):
    b2 = render_arm(spec, "B2", counter=COUNTER).prompt
    flip = render_arm(spec, "B2-flip", counter=COUNTER).prompt
    assert "it is Vulnerable." in b2 and "it is Non-vulnerable." in flip
    b3 = split_blocks(render_arm(spec, "B3", counter=COUNTER).prompt)["demo"]
    swap = split_blocks(render_arm(spec, "B3-swap", counter=COUNTER).prompt)["demo"]
    assert b3.index("example is Vulnerable") < b3.index("example is Non-vulnerable")
    assert swap.index("example is Non-vulnerable") < swap.index("example is Vulnerable")
    assert "Key difference:" in b3 and "Key difference:" not in split_blocks(render_arm(spec, "B3-nodiff", counter=COUNTER).prompt)["demo"]
    # demo đứng sau graph (Hình 6), không đứng trước code
    assert b2.index("The node information") < b2.index("The following is an example")
    assert b2.index("int f(") < b2.index("The node information")


def test_shuffle_uses_other_graph_same_size(spec, donors):
    r = render_arm(spec, "B1-shuf", seed=42, counter=COUNTER, donors=donors)
    assert r.evidence["graph"]["donor_uid"].startswith("tr")
    assert 36 <= r.evidence["graph"]["donor_nodes"] <= 44
    r2 = render_arm(spec, "B1-shuf", seed=42, counter=COUNTER, donors=donors)
    assert r.prompt == r2.prompt                      # tất định theo (id, seed)
    r3 = render_arm(spec, "B1-shuf", seed=43, counter=COUNTER, donors=donors)
    assert r3.evidence["graph"]["donor_uid"] != r.evidence["graph"]["donor_uid"] or r3.prompt == r.prompt


def test_random_demo_excludes_retrieved(spec, donors):
    r = render_arm(spec, "B2-rand", seed=42, counter=COUNTER, donors=donors)
    assert r.evidence["demo"]["demos"][0]["function_uid"] != "d1"
    assert r.evidence["demo"]["demos"][0]["displayed_label"] == r.evidence["demo"]["demos"][0]["true_label"]


def test_budget_truncation_flags(spec):
    long_spec = {**spec, "query_code": "int f(){\n" + "  x = x + 1;\n" * 3000 + "}"}
    r = render_arm(long_spec, "B0", counter=COUNTER, budget={"target_code": 500, "total": 8192})
    assert r.evidence["truncated"]["code"] is True
    assert r.evidence["tokens"]["code"] <= 500
    assert "[TRUNCATED TARGET]" in r.prompt
