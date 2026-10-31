"""Chạy ma trận arm × seed trên một split, có journal/resume và cache theo prompt.

Ví dụ:
  # chỉ dựng prompt để audit (không gọi LLM)
  python scripts/run_matrix.py --dataset devign --split validation \
      --specs data/specs/devign_validation.jsonl --donors data/donors/devign_train.jsonl \
      --arms B0 B1 B2 B2-flip B2-rep --dry-run --out runs/dryrun

  # chạy thật
  python scripts/run_matrix.py --dataset devign --split test --specs ... --donors ... \
      --arms B0 B1 B2 B2-flip B2-rep --seeds 42 --backend configs/backend_vllm.yaml \
      --protocol configs/protocol.yaml --out runs/final

Mỗi dòng specs: {id, query_code, nodes, edges, demonstrations, security_difference, h2_evidence, label[, group]}
`label` được tách ra trước khi dựng prompt và chỉ ghi vào bản ghi kết quả.
Đầu ra: <out>/<dataset>/<split>/<arm>/<seed>/records.jsonl (schema B.2) + manifest.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent if (ROOT.parent / "configs").exists() else ROOT
sys.path.insert(0, str(ROOT / "src"))

from grace_diag.probes import ARMS, DonorPool, render_arm, load_arms   # noqa: E402
from grace_diag.token_budget import TokenCounter                      # noqa: E402


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def append_jsonl(path: Path, row: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush(); os.fsync(f.fileno())


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--split", required=True, choices=["validation", "test"])
    ap.add_argument("--specs", required=True, type=Path)
    ap.add_argument("--donors", type=Path, help="JSONL hàm train (đã khử trùng) cho B2-rand/B1-shuf")
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--arms-config", type=Path, default=REPO_ROOT / "configs" / "arms.yaml" if (REPO_ROOT / "configs" / "arms.yaml").exists() else ROOT / "configs" / "arms.yaml")
    ap.add_argument("--seeds", nargs="+", type=int, default=[42])
    ap.add_argument("--protocol", type=Path, default=REPO_ROOT / "configs" / "protocol.yaml" if (REPO_ROOT / "configs" / "protocol.yaml").exists() else ROOT / "configs" / "protocol.yaml")
    ap.add_argument("--backend", type=Path, help="configs/backend_vllm.yaml, backend_llamacpp.yaml, backend_kaggle.yaml hoặc backend_mock.yaml")
    ap.add_argument("--tokenizer", help="model/thư mục tokenizer; mặc định lấy từ local grace_diag_kit/tokenizer nếu có")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true", help="chỉ dựng prompt, ghi prompts.jsonl để audit")
    ap.add_argument("--limit", type=int, help="chỉ chạy N target đầu (smoke test)")
    ap.add_argument("--allow-approx-tokens", action="store_true", help="CHỈ cho thử nghiệm với server giả: cho phép đếm token ước lượng")
    a = ap.parse_args()

    import yaml
    proto = yaml.safe_load(a.protocol.read_text(encoding="utf-8"))
    budget = proto["token_budget"]
    prefix = proto.get("graph_prefix", {"nodes": 25, "edges": 25})
    arms_cfg = load_arms(a.arms_config) if a.arms_config.exists() else ARMS
    unknown = [x for x in a.arms if x not in arms_cfg]
    if unknown:
        raise SystemExit("Arm không có trong arms.yaml: " + ", ".join(unknown))

    backend_cfg = None
    scorer = None
    if not a.dry_run:
        from grace_diag.llm_backend import FirstTokenScorer, load_backend_config
        if not a.backend:
            raise SystemExit("Chạy thật bắt buộc phải có --backend (ví dụ: configs/backend_kaggle.yaml hoặc configs/backend_mock.yaml)")
        backend_cfg = load_backend_config(a.backend)
        scorer = FirstTokenScorer(backend_cfg, cache_dir=a.out / "_cache")

    default_tok = ROOT / "tokenizer"
    if not default_tok.exists() and (REPO_ROOT / "grace_diag_kit" / "tokenizer").exists():
        default_tok = REPO_ROOT / "grace_diag_kit" / "tokenizer"
    tok_name = a.tokenizer or (str(default_tok) if default_tok.exists() else None)
    if not tok_name and backend_cfg and not a.allow_approx_tokens:
        tok_name = backend_cfg.model

    counter = TokenCounter(tok_name)
    if counter.approx and not a.dry_run and not a.allow_approx_tokens:
        raise SystemExit("Lượt chạy thật phải có tokenizer của model (--tokenizer)")

    specs = read_jsonl(a.specs)
    if a.limit:
        specs = specs[: a.limit]
    needs_donors = any(arms_cfg[arm].get("demo") == "random" or arms_cfg[arm].get("graph") == "shuffle" for arm in a.arms)
    donors = DonorPool(read_jsonl(a.donors)) if (a.donors and needs_donors) else None

    a.out.mkdir(parents=True, exist_ok=True)
    dry_path = a.out / f"prompts_{a.dataset}_{a.split}.jsonl"
    t_start = time.time()
    n_done = 0
    for arm in a.arms:
        for seed in a.seeds:
            run_dir = a.out / a.dataset / a.split / arm / str(seed)
            run_dir.mkdir(parents=True, exist_ok=True)
            rec_path = run_dir / "records.jsonl"
            done = {str(r["id"]) for r in read_jsonl(rec_path)} if rec_path.exists() else set()
            manifest = {"dataset": a.dataset, "split": a.split, "arm": arm, "arm_config": arms_cfg[arm], "seed": seed,
                        "protocol_sha256": hashlib.sha256(a.protocol.read_bytes()).hexdigest(),
                        "specs_sha256": hashlib.sha256(a.specs.read_bytes()).hexdigest(),
                        "backend": backend_cfg.inference_identity() if backend_cfg else "dry-run",
                        "tokenizer": tok_name, "python": platform.python_version(), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            mpath = run_dir / "manifest.json"
            if mpath.exists():
                old = json.loads(mpath.read_text(encoding="utf-8"))
                for k in ("arm_config", "protocol_sha256", "specs_sha256", "backend", "tokenizer"):
                    if old.get(k) != manifest[k]:
                        raise SystemExit(f"Run {run_dir} đã tồn tại với {k} khác; dùng thư mục --out mới")
            else:
                mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            for spec in specs:
                sid = str(spec["id"])
                if sid in done:
                    continue
                label = spec.get("label")
                group = spec.get("group")
                clean = {k: v for k, v in spec.items() if k not in ("label", "target", "group")}
                rendered = render_arm(clean, arm, seed=seed, counter=counter, donors=donors, budget=budget, graph_prefix=prefix, arms=arms_cfg)
                if a.dry_run:
                    append_jsonl(dry_path, {"id": sid, "arm": arm, "seed": seed, "prompt": rendered.prompt, "evidence": rendered.evidence})
                    continue
                res = scorer.score(rendered.prompt, seed=seed)
                row = {"id": sid, "dataset": a.dataset, "split": a.split, "arm": arm, "seed": seed,
                       "prompt_sha256": rendered.evidence["prompt_sha256"],
                       "demo_ids": [d["function_uid"] for d in rendered.evidence["demo"].get("demos", [])],
                       "tokens_code": rendered.evidence["tokens"]["code"], "tokens_graph": rendered.evidence["tokens"]["graph"],
                       "tokens_demo": rendered.evidence["tokens"]["demo"], "tokens_total": rendered.evidence["tokens"]["total"],
                       "truncated": rendered.evidence["truncated"], "tokens_approx": counter.approx, "raw": res.raw, "top5": res.top,
                       "s": None if res.s != res.s else res.s, "p0": res.p0, "p1": res.p1,
                       "pred_argmax": res.pred_argmax, "valid": res.valid, "error": res.error,
                       "label": label, "group": group, "model": backend_cfg.model, "backend_kind": backend_cfg.kind,
                       "usage": res.usage, "latency_s": res.latency_s, "cached": res.cached,
                       "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                append_jsonl(rec_path, row)
                n_done += 1
                if n_done % 100 == 0:
                    rate = n_done / max(1e-9, time.time() - t_start)
                    print(f"[{arm}/{seed}] {n_done} request, {rate:.2f}/s", flush=True)
    if a.dry_run:
        print("Prompt đã ghi vào", dry_path, "— chạy prompt_audit.py trước khi gọi LLM")
    else:
        print("Xong", n_done, "request mới trong", round(time.time() - t_start, 1), "giây")


if __name__ == "__main__":
    main()
