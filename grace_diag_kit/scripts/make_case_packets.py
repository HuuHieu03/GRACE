"""Tạo gói ca chấm mù phân tầng theo bốn ô sửa/hỏng giữa mốc có giám sát (h) và LLM (g):
FN được sửa, FN bị tạo, FP được sửa, FP bị tạo — mỗi ô 15 ca (hoặc toàn bộ nếu ít hơn).

  python scripts/make_case_packets.py --records runs/final/devign/B2/42/records.jsonl \
      --anchor runs/anchor/anchor_scores.csv --tau 0.53 --code data/raw/devign_test.jsonl \
      --out packets/devign_B2 --per-cell 15 --seed 42

Mỗi ca xuất hai bản: packet_blind.csv (mã A/B tráo ngẫu nhiên, không có nhãn thật, không
có tên arm) để người chấm đọc, và answer_key.csv (giữ riêng) để hòa giải. Phiếu chấm có các
cột: thao tác nhạy cảm, biến liên quan, guard/nhánh thoát, dòng mã bằng chứng, đủ ngữ cảnh?,
nhãn benchmark đáng ngờ?, kết luận người chấm (0/1/không đủ ngữ cảnh).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

SHEET_COLS = ["case_id", "code", "verdict_A_or_B_hidden", "sensitive_operation", "variables", "guard_or_exit_branch",
              "evidence_lines", "enough_context(y/n)", "benchmark_label_suspicious(y/n)", "reviewer_label(0/1/na)", "notes"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--records", required=True, type=Path)
    ap.add_argument("--anchor", required=True, type=Path, help="anchor_scores.csv (SUP-LR, split test, seed 42)")
    ap.add_argument("--anchor-arm", default="SUP-LR")
    ap.add_argument("--tau", type=float, required=True)
    ap.add_argument("--code", required=True, type=Path, help="JSONL {id, func}")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--per-cell", type=int, default=15)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    code = {str(r["id"]): r["func"] for r in (json.loads(l) for l in open(a.code, encoding="utf-8") if l.strip())}
    llm = {str(r["id"]): r for r in (json.loads(l) for l in open(a.records, encoding="utf-8") if l.strip())}
    anchor = {}
    for r in csv.DictReader(open(a.anchor, encoding="utf-8")):
        if r["arm"] == a.anchor_arm and r["split"] == "test" and int(r["seed"]) == 42:
            anchor[r["id"]] = float(r["score"])
    cells = {"FN_repaired": [], "FN_created": [], "FP_repaired": [], "FP_created": []}
    for sid, r in llm.items():
        if sid not in anchor or not r["valid"] or r["label"] is None:
            continue
        y, h, g = int(r["label"]), int(anchor[sid] >= a.tau), int(r["pred_argmax"])
        if y == 1 and h == 0 and g == 1: cells["FN_repaired"].append(sid)
        elif y == 1 and h == 1 and g == 0: cells["FN_created"].append(sid)
        elif y == 0 and h == 1 and g == 0: cells["FP_repaired"].append(sid)
        elif y == 0 and h == 0 and g == 1: cells["FP_created"].append(sid)
    a.out.mkdir(parents=True, exist_ok=True)
    blind, key = [], []
    for cell, ids in cells.items():
        picked = rng.sample(ids, min(a.per_cell, len(ids)))
        for sid in picked:
            case_id = f"C{rng.randrange(10**6):06d}"
            blind.append({"case_id": case_id, "code": code.get(sid, "<missing code>")})
            key.append({"case_id": case_id, "id": sid, "cell": cell, "label": llm[sid]["label"],
                        "anchor_pred": int(anchor[sid] >= a.tau), "llm_pred": llm[sid]["pred_argmax"], "llm_s": llm[sid]["s"]})
    rng.shuffle(blind)
    with open(a.out / "packet_blind.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS); w.writeheader()
        for b in blind:
            w.writerow({**{c: "" for c in SHEET_COLS}, **b})
    with open(a.out / "answer_key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(key[0].keys()) if key else ["case_id"]); w.writeheader(); w.writerows(key)
    print({c: len(v) for c, v in cells.items()}, "->", len(blind), "ca trong gói; answer_key.csv giữ riêng")


if __name__ == "__main__":
    main()
