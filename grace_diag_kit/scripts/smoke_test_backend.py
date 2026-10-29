"""Smoke test server LLM: 20 prompt chạy hai lần; kiểm tra token 0/1 trong top-k logprob,
độ lặp lại giữa hai lần và thông lượng. Chạy TRƯỚC khi đăng ký trước.

  python scripts/smoke_test_backend.py --backend configs/backend_vllm.yaml \
      --prompts runs/dryrun/prompts_devign_validation.jsonl --n 20

Tiêu chí đạt: >= 99% prompt có token 0 hoặc 1 trong top-k; >= 98% trùng nhãn giữa hai lần.
Nếu không đạt tiêu chí thứ nhất: bật guided_choice trong backend yaml rồi chạy lại.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from grace_diag.llm_backend import FirstTokenScorer, load_backend_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", required=True, type=Path)
    ap.add_argument("--prompts", required=True, type=Path, help="JSONL có trường prompt (từ run_matrix --dry-run)")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--out", type=Path, default=ROOT / "runs" / "smoke_test.json")
    a = ap.parse_args()
    cfg = load_backend_config(a.backend)
    scorer = FirstTokenScorer(cfg, cache_dir=None)
    rows = [json.loads(l) for l in open(a.prompts, encoding="utf-8") if l.strip()][: a.n]
    results = []
    t0 = time.time()
    for r in rows:
        first = scorer.score(r["prompt"], use_cache=False)
        second = scorer.score(r["prompt"], use_cache=False)
        results.append({"id": r["id"], "arm": r["arm"], "valid": first.valid, "pred1": first.pred_argmax, "pred2": second.pred_argmax,
                        "s1": first.s, "s2": second.s, "top1": first.top, "raw1": first.raw, "error": first.error or second.error,
                        "latency_s": first.latency_s})
    elapsed = time.time() - t0
    n = len(results)
    valid_rate = sum(x["valid"] for x in results) / max(1, n)
    agree = sum(1 for x in results if x["pred1"] is not None and x["pred1"] == x["pred2"]) / max(1, n)
    max_s_gap = max((abs(x["s1"] - x["s2"]) for x in results if x["s1"] == x["s1"] and x["s2"] == x["s2"]), default=0.0)
    summary = {"backend": cfg.inference_identity(), "n": n, "valid_rate": valid_rate, "repeat_agreement": agree,
               "max_abs_s_gap": max_s_gap, "prompts_per_second": (2 * n) / elapsed if elapsed else None,
               "errors": [x["error"] for x in results if x["error"]],
               "pass": valid_rate >= 0.99 and agree >= 0.98 and not any(x["error"] for x in results)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"summary": summary, "rows": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["pass"]:
        print("CHƯA ĐẠT: xem rows trong", a.out, "- cân nhắc bật guided_choice hoặc kiểm tra server trả logprobs")
        sys.exit(1)


if __name__ == "__main__":
    main()
