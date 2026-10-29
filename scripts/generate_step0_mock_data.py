#!/usr/bin/env python3
"""Script sinh dữ liệu giả lập (Mock Data) phục vụ kiểm thử Offline Diagnostic Bước 0.

Sinh các file đồng bộ theo id theo chuẩn 2-Split (Validation và Test) cho Devign và ReVeal:
1. <dataset>_gate_val.csv, <dataset>_gate_test.csv: id, y, p_gate
2. <dataset>_llm_val.jsonl, <dataset>_llm_test.jsonl: id, s, pred_argmax, prediction, valid, raw
3. <dataset>_xpre_val.npz, <dataset>_xpre_test.npz: X (Nx34 float matrix), ids (N strings)
Đồng thời tạo file single-split (<dataset>_gate.csv, <dataset>_llm.jsonl, <dataset>_xpre.npz) để tương thích ngược.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np


def _generate_single_split(
    output_dir: Path,
    dataset: str,
    split_suffix: str,
    n_samples: int,
    seed: int,
    p_vuln: float = 0.45,
    invalid_rate: float = 0.04,
) -> Dict[str, Path]:
    """Sinh dữ liệu cho một split cụ thể."""
    rng = np.random.default_rng(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{dataset}_{split_suffix}" if split_suffix else dataset
    ids = [f"mock_{prefix}_{i:04d}" for i in range(1, n_samples + 1)]

    # 1. Ground truth y: 0 (safe) hoặc 1 (vulnerable)
    y = (rng.random(n_samples) < p_vuln).astype(int)

    # 2. Gate probabilities (CodeT5 gate mock)
    # Tương quan với y, mô phỏng gate có độ chính xác ~75%
    logit_gate = rng.normal(loc=1.2 * (2 * y - 1), scale=0.9, size=n_samples)
    p_gate = 1.0 / (1.0 + np.exp(-logit_gate))
    p_gate = np.clip(p_gate, 0.005, 0.995)

    # 3. LLM expert predictions (mô phỏng nhánh B2)
    # LLM có tương quan với y, sửa một số ca gate sai, nhưng cũng có thể làm hỏng vài ca gate đúng
    logit_llm = rng.normal(loc=1.4 * (2 * y - 1), scale=1.0, size=n_samples)
    s_llm = 1.0 / (1.0 + np.exp(-logit_llm))
    s_llm = np.clip(s_llm, 0.01, 0.99)

    # Mô phỏng một vài ca invalid (ví dụ không parse được binary)
    valid_flags = rng.random(n_samples) >= invalid_rate
    if invalid_rate > 0 and valid_flags.all():
        valid_flags[rng.integers(0, n_samples)] = False

    # 4. Ghi gate CSV
    suffix_tag = f"_{split_suffix}" if split_suffix else ""
    gate_csv_path = output_dir / f"{dataset}_gate{suffix_tag}.csv"
    with open(gate_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "y", "p_gate"])
        for sid, yi, pi in zip(ids, y, p_gate):
            writer.writerow([sid, yi, f"{pi:.6f}"])

    # 5. Ghi LLM predictions JSONL
    llm_jsonl_path = output_dir / f"{dataset}_llm{suffix_tag}.jsonl"
    with open(llm_jsonl_path, "w", encoding="utf-8") as f:
        for sid, yi, si, val in zip(ids, y, s_llm, valid_flags):
            pred_int = int(si >= 0.5) if val else -1
            record = {
                "id": sid,
                "dataset": dataset,
                "split": split_suffix or "default",
                "arm": "B2",
                "seed": seed,
                "s": float(si) if val else None,
                "pred_argmax": pred_int,
                "prediction": str(pred_int) if val else "PARSE_ERROR",
                "valid": bool(val),
                "raw": str(pred_int) if val else "Invalid response format",
                "label": int(yi),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 6. Ghi xpre NPZ (34 đặc trưng nền như trong H3-B: 5 view scores, code metrics, v.v.)
    X_pre = rng.normal(loc=0.0, scale=1.0, size=(n_samples, 34))
    X_pre[:, 0] = logit_gate
    X_pre[:, 1] += 0.5 * (2 * y - 1)
    X_pre[:, 2] += 0.3 * (2 * y - 1)

    xpre_npz_path = output_dir / f"{dataset}_xpre{suffix_tag}.npz"
    np.savez(xpre_npz_path, X=X_pre.astype(np.float32), ids=np.array(ids))

    return {
        "gate_csv": gate_csv_path,
        "llm_jsonl": llm_jsonl_path,
        "xpre_npz": xpre_npz_path,
    }


def generate_mock_step0_data(
    output_dir: Path,
    n_samples: int = 100,
    dataset: str = "devign",
    seed: int = 42,
    p_vuln: float = 0.45,
    invalid_rate: float = 0.04,
    generate_2split: bool = True,
    n_val: Optional[int] = None,
    n_test: Optional[int] = None,
) -> Dict[str, Path]:
    """Sinh mock data cho một dataset, bao gồm cả 2-split (val, test) và single-split."""
    val_count = n_val if n_val is not None else n_samples
    test_count = n_test if n_test is not None else n_samples

    result: Dict[str, Path] = {}

    if generate_2split:
        val_files = _generate_single_split(
            output_dir=output_dir,
            dataset=dataset,
            split_suffix="val",
            n_samples=val_count,
            seed=seed,
            p_vuln=p_vuln,
            invalid_rate=invalid_rate,
        )
        test_files = _generate_single_split(
            output_dir=output_dir,
            dataset=dataset,
            split_suffix="test",
            n_samples=test_count,
            seed=seed + 1000,
            p_vuln=p_vuln,
            invalid_rate=invalid_rate,
        )
        result["gate_val"] = val_files["gate_csv"]
        result["llm_val"] = val_files["llm_jsonl"]
        result["xpre_val"] = val_files["xpre_npz"]
        result["gate_test"] = test_files["gate_csv"]
        result["llm_test"] = test_files["llm_jsonl"]
        result["xpre_test"] = test_files["xpre_npz"]

    # Single-split file phục vụ kiểm thử đơn giản hoặc backward compatibility
    single_files = _generate_single_split(
        output_dir=output_dir,
        dataset=dataset,
        split_suffix="",
        n_samples=n_samples,
        seed=seed,
        p_vuln=p_vuln,
        invalid_rate=invalid_rate,
    )
    result["gate_csv"] = single_files["gate_csv"]
    result["llm_jsonl"] = single_files["llm_jsonl"]
    result["xpre_npz"] = single_files["xpre_npz"]

    print(f"[OK] Đã sinh mock data cho '{dataset}' tại {output_dir}:")
    if generate_2split:
        print(f"  - Validation (N={val_count}):")
        print(f"      Gate: {result['gate_val'].name}")
        print(f"      LLM:  {result['llm_val'].name}")
        print(f"      Xpre: {result['xpre_val'].name}")
        print(f"  - Test (N={test_count}):")
        print(f"      Gate: {result['gate_test'].name}")
        print(f"      LLM:  {result['llm_test'].name}")
        print(f"      Xpre: {result['xpre_test'].name}")
    print(f"  - Single-split (N={n_samples}): {result['gate_csv'].name}, {result['llm_jsonl'].name}, {result['xpre_npz'].name}")

    return result


def generate_all_step0_mock_data(
    output_dir: Path,
    n_val: int = 100,
    n_test: int = 100,
    seed: int = 42,
    invalid_rate: float = 0.04,
) -> Dict[str, Dict[str, Path]]:
    """Sinh toàn bộ mock data cho cả Devign và ReVeal (chuẩn 2-split: 100 val, 100 test)."""
    datasets = ["devign", "reveal"]
    all_results: Dict[str, Dict[str, Path]] = {}
    for i, ds in enumerate(datasets):
        ds_seed = seed + i * 2000
        all_results[ds] = generate_mock_step0_data(
            output_dir=output_dir,
            n_samples=n_test,
            dataset=ds,
            seed=ds_seed,
            invalid_rate=invalid_rate,
            generate_2split=True,
            n_val=n_val,
            n_test=n_test,
        )
    return all_results


def main():
    parser = argparse.ArgumentParser(description="Tạo mock data 2-split cho bước 0 offline diagnostic")
    parser.add_argument("--output-dir", type=Path, default=Path("data/mock_step0"))
    parser.add_argument("--dataset", type=str, default="all", choices=["all", "devign", "reveal"])
    parser.add_argument("--n-val", type=int, default=100, help="Số mẫu tập validation (mặc định 100)")
    parser.add_argument("--n-test", type=int, default=100, help="Số mẫu tập test (mặc định 100)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--p-vuln", type=float, default=0.45)
    parser.add_argument("--invalid-rate", type=float, default=0.04)
    args = parser.parse_args()

    if args.dataset == "all":
        generate_all_step0_mock_data(
            output_dir=args.output_dir,
            n_val=args.n_val,
            n_test=args.n_test,
            seed=args.seed,
            invalid_rate=args.invalid_rate,
        )
    else:
        generate_mock_step0_data(
            output_dir=args.output_dir,
            n_samples=args.n_test,
            dataset=args.dataset,
            seed=args.seed,
            p_vuln=args.p_vuln,
            invalid_rate=args.invalid_rate,
            generate_2split=True,
            n_val=args.n_val,
            n_test=args.n_test,
        )


if __name__ == "__main__":
    main()
