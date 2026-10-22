"""Offline lexical near-clone audit against the full train pool.

Exact token-5-gram set Jaccard is computed for all potentially matching pairs
using a query-shingle inverted index. This does not establish semantic
equivalence, validate labels, or detect every renamed/control-flow clone.
"""
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from dataset_contract import attach_manifest, code_hash
from scripts.audit_code_leakage import strip_c_comments

TOKEN = re.compile(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_]\w*|\d+(?:\.\d+)?|==|!=|<=|>=|->|\+\+|--|&&|\|\||[^\s]''')


def shingles(code, size=5):
    tokens = TOKEN.findall(strip_c_comments(code))
    return {tuple(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}, len(tokens)


def find_near_clones(train, queries, threshold=0.8, min_tokens=20):
    if not 0 < threshold <= 1:
        raise ValueError("Jaccard threshold must be in (0, 1]")
    index = defaultdict(list)
    qsets, small = [], []
    for i, row in enumerate(queries):
        ss, token_count = shingles(row["func"])
        qsets.append(ss)
        if token_count < min_tokens:
            small.append(row["id"])
        else:
            for shingle in ss:
                index[shingle].append(i)
    hits = []
    small_train = 0
    for train_index, row in enumerate(train):
        ss, token_count = shingles(row["func"])
        if token_count < min_tokens:
            small_train += 1
            continue
        shared = Counter(q for shingle in ss for q in index.get(shingle, ()))
        for q, count in shared.items():
            union = len(ss) + len(qsets[q]) - count
            score = count / union if union else 0
            if score >= threshold:
                query = queries[q]
                hits.append({"query_uid": query["id"], "query_row": q, "train_uid": row["id"],
                             "train_row": train_index, "jaccard_token5": round(score, 6),
                             "query_target": query["target"], "train_target": row["target"],
                             "exact_code": code_hash(query["func"]) == code_hash(row["func"]),
                             "label_conflict": query["target"] != row["target"],
                             "status": "REQUIRES_CODE_REVIEW_NOT_AUTOMATIC_RELABEL"})
    return {"threshold": threshold, "shingle_tokens": 5, "min_tokens": min_tokens,
            "train_rows": len(train), "query_rows": len(queries), "small_queries_outside_scope": small,
            "small_train_rows_outside_scope": small_train, "hits": hits,
            "queries_with_hits": len({h['query_uid'] for h in hits}),
            "scope": "Lexical token-5-gram set Jaccard, full train; not semantic or comprehensive clone detection."}


def main():
    folder = ROOT / "project_docs/reports/data_contract_v2_2026-10-22"
    results = {}
    for dataset in ["devign", "reveal"]:
        train = json.loads(gzip.decompress((ROOT / f"data/processed/{dataset}_train_compact_cpg.json.gz").read_bytes()))
        queries = json.loads((ROOT / f"data/splits/{dataset}_dev_clean_100_ids.json").read_text(encoding="utf-8"))["sample_details"]
        manifest_dir = ROOT / "data/manifests/function_uid_v2"
        train_manifest = json.loads((manifest_dir / f"{dataset}_train.json").read_text(encoding="utf-8"))
        query_manifest = json.loads((manifest_dir / f"{dataset}_validation.json").read_text(encoding="utf-8"))
        train = attach_manifest(train, train_manifest)
        queries = attach_manifest(queries, query_manifest)
        results[dataset] = find_near_clones(train, queries)
        results[dataset]["ordered_manifest_hashes"] = {
            "train": train_manifest["ordered_identity_sha256"], "validation": query_manifest["ordered_identity_sha256"]}
        print(f"{dataset}: {len(results[dataset]['hits'])} lexical candidate pairs; {results[dataset]['queries_with_hits']} queries", flush=True)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "near_clone_audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
