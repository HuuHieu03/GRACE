"""Kiểm tra toàn vẹn đầu vào (prompt integrity audit) trước khi gọi LLM.

Đọc các dòng {id, arm, seed, prompt, evidence} do run_matrix.py tạo ở chế độ --dry-run và xuất:
- audit_summary.json : theo arm — số prompt, tỷ lệ cắt code/graph/demo, demo rỗng, graph thiếu,
                       token trung bình/percentile, vượt ngân sách, rò rỉ nhãn target.
- audit_rows.csv     : một dòng/prompt với token từng phần và cờ.
- manual_sample.jsonl: 30 prompt/dataset chọn phân tầng theo tam phân vị độ dài × cờ cắt,
                       để hai người đọc bằng mắt (kiểm tính toàn vẹn, không phải chọn ví dụ đẹp).
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

LEAK_PATTERNS = [r"\bLabel\s*:", r"\bground[\s-]*truth\b", r"\bTARGET LABEL\b", r"\bthe target is (?:vulnerable|non-vulnerable)\b"]


def audit_rows(rows: Iterable[Dict]) -> Dict:
    per_arm = defaultdict(list)
    flat: List[Dict] = []
    for r in rows:
        ev = r["evidence"]
        prompt = r["prompt"]
        leak = any(re.search(p, prompt, re.I) for p in LEAK_PATTERNS)
        demo_tokens = ev["tokens"].get("demo", 0)
        demo_expected = ev["demo"].get("policy", "none") not in ("none", "labelonly")
        # demo bị cắt còn dưới 25% độ dài gốc coi như "rỗng về nội dung"
        demo_gutted = any(d.get("truncated") and d.get("tokens", 0) < 0.25 * max(1, d.get("original_tokens", 0))
                          for d in ev["demo"].get("demos", []))
        row = {
            "id": r["id"], "arm": r["arm"], "seed": r.get("seed", 42),
            "tokens_total": ev["tokens"]["total"], "tokens_code": ev["tokens"]["code"],
            "tokens_graph": ev["tokens"].get("graph", 0), "tokens_demo": demo_tokens,
            "code_truncated": ev["truncated"]["code"], "graph_truncated": ev["truncated"]["graph"],
            "demo_truncated": ev["truncated"]["demo"],
            "demo_empty": bool(demo_expected and (demo_tokens == 0 or demo_gutted)),
            "graph_missing": bool(ev["graph"].get("missing", False)),
            "rendered_nodes": ev["graph"].get("rendered_nodes", 0),
            "label_leak": leak, "approx_tokens": ev["tokens"].get("approx", False),
            "prompt_sha256": ev["prompt_sha256"],
        }
        flat.append(row)
        per_arm[r["arm"]].append(row)
    summary = {}
    for arm, items in per_arm.items():
        tot = np.array([i["tokens_total"] for i in items])
        summary[arm] = {
            "n": len(items),
            "tokens_mean": float(tot.mean()), "tokens_p50": float(np.percentile(tot, 50)), "tokens_p95": float(np.percentile(tot, 95)),
            "tokens_max": int(tot.max()),
            "rate_code_truncated": float(np.mean([i["code_truncated"] for i in items])),
            "rate_graph_truncated": float(np.mean([i["graph_truncated"] for i in items])),
            "rate_demo_truncated": float(np.mean([i["demo_truncated"] for i in items])),
            "rate_demo_empty": float(np.mean([i["demo_empty"] for i in items])),
            "rate_graph_missing": float(np.mean([i["graph_missing"] for i in items])),
            "n_label_leak": int(sum(i["label_leak"] for i in items)),
            "any_approx_tokens": bool(any(i["approx_tokens"] for i in items)),
        }
    return {"summary": summary, "rows": flat}


def stratified_manual_sample(flat: List[Dict], n: int = 30, seed: int = 42) -> List[Dict]:
    """Chọn n prompt theo tam phân vị độ dài × (có cắt / không cắt), đều nhau giữa các ô."""
    rng = np.random.default_rng(seed)
    tot = np.array([r["tokens_total"] for r in flat])
    if len(flat) == 0:
        return []
    q1, q2 = np.percentile(tot, [33.3, 66.7])
    cells = defaultdict(list)
    for r, t in zip(flat, tot):
        tert = 0 if t <= q1 else (1 if t <= q2 else 2)
        cut = bool(r["code_truncated"] or r["graph_truncated"] or r["demo_truncated"])
        cells[(tert, cut)].append(r)
    per_cell = max(1, n // max(1, len(cells)))
    picked = []
    for key in sorted(cells):
        items = cells[key]
        idx = rng.choice(len(items), size=min(per_cell, len(items)), replace=False)
        picked.extend({**items[i], "stratum": {"length_tertile": key[0], "truncated": key[1]}} for i in idx)
    return picked[:n]


def _main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prompts", required=True, help="JSONL từ run_matrix.py --dry-run")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--manual-n", type=int, default=30)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.prompts, encoding="utf-8") if l.strip()]
    res = audit_rows(rows)
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    json.dump(res["summary"], open(out / "audit_summary.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    with open(out / "audit_rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(res["rows"][0].keys()) if res["rows"] else ["id"])
        w.writeheader(); w.writerows(res["rows"])
    sample = stratified_manual_sample(res["rows"], a.manual_n)
    by_key = {(r["id"], r["arm"], r.get("seed", 42)): r["prompt"] for r in rows}
    with open(out / "manual_sample.jsonl", "w", encoding="utf-8") as f:
        for s in sample:
            f.write(json.dumps({**s, "prompt": by_key[(s["id"], s["arm"], s["seed"])]}, ensure_ascii=False) + "\n")
    bad = {arm: v for arm, v in res["summary"].items() if v["n_label_leak"] or v["any_approx_tokens"]}
    print(json.dumps(res["summary"], indent=2, ensure_ascii=False))
    if bad:
        raise SystemExit("DỪNG: có arm rò rỉ nhãn hoặc dùng token ước lượng: " + ", ".join(bad))


if __name__ == "__main__":
    _main()
