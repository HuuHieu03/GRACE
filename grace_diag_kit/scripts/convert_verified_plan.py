"""Chuyển một plan "verified protocol" (schema v2 của repo tái triển khai) thành specs.jsonl
cho run_matrix.py, gộp demo của arm b2 (1 demo) và b3 (2 demo + security_difference) theo id.

  python scripts/convert_verified_plan.py --plan output/plans/devign_validation_plan.json \
      --out data/specs/devign_validation.jsonl [--h2 data/h2/devign_validation_evidence.jsonl]

Nhãn lấy từ plan["evaluation_labels"] và chỉ được ghi ở trường `label` (run_matrix tách ra
trước khi dựng prompt). File --h2 (tùy chọn): {id, evidence_text} cho arm B1-H2.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--h2", type=Path)
    ap.add_argument("--group-field", default=None, help="tên trường nhóm trong prompt_spec nếu có (commit_id/project)")
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text(encoding="utf-8"))
    labels = plan["evaluation_labels"]
    h2 = {}
    if a.h2:
        for l in open(a.h2, encoding="utf-8"):
            if l.strip():
                r = json.loads(l); h2[str(r["id"])] = r["evidence_text"]
    merged = {}
    for item in plan["items"]:
        if item.get("condition", "original") != "original":
            continue
        sid = str(item["id"])
        spec = item["prompt_spec"]
        m = merged.setdefault(sid, {"id": sid, "query_code": spec["query_code"], "nodes": spec.get("nodes", []),
                                    "edges": spec.get("edges", []), "demonstrations": None, "demonstrations_pair": None,
                                    "security_difference": "", "label": int(labels[sid])})
        if a.group_field and spec.get(a.group_field) is not None:
            m["group"] = spec[a.group_field]
        demos = [{"function_uid": d["function_uid"], "func": d["func"], "target": int(d["target"])} for d in spec["demonstrations"]]
        if item["arm"].lower() in ("b2", "standard_1shot", "grace_baseline"):
            m["demonstrations"] = demos[:1]
        elif item["arm"].lower() in ("b3", "contrastive_icl", "contrastive_2shot"):
            if len(demos) != 2:
                raise ValueError(f"{sid}: arm b3 cần 2 demo")
            # thứ tự chuẩn: vulnerable trước, safe sau
            demos = sorted(demos, key=lambda d: -d["target"])
            m["demonstrations_pair"] = demos
            m["security_difference"] = spec.get("security_difference", "")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    n_b2 = n_b3 = 0
    with open(a.out, "w", encoding="utf-8") as f:
        for sid, m in merged.items():
            if m["demonstrations"] is None and m["demonstrations_pair"] is None:
                raise ValueError(f"{sid}: không có demo nào")
            if m["demonstrations"] is None:   # chỉ có b3: lấy demo vulnerable làm demo B2 (ghi rõ nguồn)
                m["demonstrations"] = [m["demonstrations_pair"][0]]
                m["b2_demo_source"] = "pair_vulnerable"
            if sid in h2:
                m["h2_evidence"] = h2[sid]
            n_b2 += 1; n_b3 += m["demonstrations_pair"] is not None
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"wrote {a.out}: {n_b2} target, {n_b3} có cặp B3, {len(h2)} có H2 evidence")


if __name__ == "__main__":
    main()
