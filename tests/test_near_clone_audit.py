"""Check candidate retrieval without assigning semantic or label truth."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.audit_near_clones import find_near_clones


def test_comment_and_whitespace_clone_with_conflicting_labels_is_flagged():
    code = "int f(int a, int b) { if (a < b) { a = a + 1; } return a + b; }"
    train = [{"id": "train-unique", "func": code, "target": 0}]
    query = [{"id": "query-unique", "func": "/* comment */\n" + code.replace(" ", "  "), "target": 1}]
    result = find_near_clones(train, query)
    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert hit["jaccard_token5"] == 1
    assert hit["label_conflict"] is True
    assert hit["exact_code"] is False
    assert hit["status"].startswith("REQUIRES_CODE_REVIEW")


def test_small_functions_are_explicitly_outside_scope():
    row = {"id": "small", "func": "void f(){}", "target": 0}
    result = find_near_clones([row], [row])
    assert result["small_queries_outside_scope"] == ["small"]
    assert result["small_train_rows_outside_scope"] == 1
    assert result["hits"] == []


def test_inverted_index_matches_brute_force_jaccard():
    from scripts.audit_near_clones import shingles
    base = "int f(int x) { if(x > 0) { x = x + 1; } return x * x + 2; }"
    train = [{"id": "a", "func": base, "target": 0},
             {"id": "b", "func": base.replace("+ 2", "+ 3"), "target": 1}]
    queries = [{"id": "q", "func": base, "target": 0}]
    threshold = .5
    actual = find_near_clones(train, queries, threshold)["hits"]
    a, _ = shingles(base)
    expected = []
    for row in train:
        b, _ = shingles(row["func"])
        score = len(a & b) / len(a | b)
        if score >= threshold:
            expected.append((row["id"], round(score, 6)))
    assert [(r["train_uid"], r["jaccard_token5"]) for r in actual] == expected
