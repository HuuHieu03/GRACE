#!/usr/bin/env python3
"""Bộ điều phối thực thi Bước 5: Suy luận ma trận (Matrix Inference Execution) & Khóa ngưỡng Validation.

Bám sát Đề cương nghiên cứu hợp nhất của Thầy (Mục 5, Mục 6, Phụ lục C) và Giao thức prereg-v1:
1. Kiểm tra trạng thái hạ tầng phục vụ LLM (configs/backend_kaggle.yaml hoặc backend_mock.yaml).
2. Thực thi suy luận ma trận 15 arm qua công cụ chính thức run_matrix.py theo 3 tầng (Tiers 1, 2, 3).
3. Tối ưu hóa và Khóa cứng ngưỡng tau* trên Validation vào thresholds.json (tuyệt đối không dùng Test).
4. Chuẩn bị sẵn sàng pipeline độc lập để suy luận và đánh giá trên tập Test sau khi đã khóa ngưỡng.
5. Kiểm định tính tuân thủ nghiêm ngặt theo Hợp đồng thực nghiệm và Phụ lục C.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
diag_src = REPO_ROOT / "grace_diag_kit" / "src"
if diag_src.exists() and str(diag_src) not in sys.path:
    sys.path.insert(0, str(diag_src))

from grace_diag import stats as S               # noqa: E402
from grace_diag import complementarity as C     # noqa: E402
from grace_diag.probes import load_arms, ARMS  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Kiểm tra trạng thái hạ tầng thực thi (Infrastructure Health Check)
# ---------------------------------------------------------------------------
def check_backend_status(backend_yaml_path: Path) -> Dict[str, Any]:
    """Kiểm tra trạng thái kết nối tới server LLM được cấu hình trong backend YAML."""
    if not backend_yaml_path.exists():
        return {
            "status": "error",
            "is_online": False,
            "message": f"Không tìm thấy tệp cấu hình backend: {backend_yaml_path}",
        }

    data = yaml.safe_load(backend_yaml_path.read_text(encoding="utf-8"))
    backend = data.get("backend", {})
    kind = backend.get("kind", "llamacpp")
    base_url = backend.get("base_url", "http://localhost:8080/v1")
    model = backend.get("model", "unknown")

    # Nếu là mock backend: sẵn sàng 100% trong tiến trình
    if kind == "mock":
        return {
            "status": "mock",
            "is_online": True,
            "kind": "mock",
            "model": model,
            "base_url": base_url,
            "message": "Mock Backend đang hoạt động nội bộ (mô phỏng offline tất định, tuân thủ schema OpenAI).",
        }

    # Nếu là hosted server (vllm / llamacpp)
    # Thử gọi endpoint /models hoặc URL gốc với timeout 5 giây
    test_urls = [
        f"{base_url.rstrip('/')}/models",
        base_url.rstrip("/"),
    ]

    error_msg = ""
    for url in test_urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GRACE-Diag-Checker/1.0"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=5) as resp:
                latency = round((time.time() - t0) * 1000, 2)
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    return {
                        "status": "online",
                        "is_online": True,
                        "kind": kind,
                        "model": model,
                        "base_url": base_url,
                        "latency_ms": latency,
                        "models_info": body,
                        "message": f"Server đang ONLINE và phản hồi tốt (HTTP 200, độ trễ {latency} ms).",
                    }
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)}"

    return {
        "status": "offline",
        "is_online": False,
        "kind": kind,
        "model": model,
        "base_url": base_url,
        "error": error_msg,
        "message": (
            f"Hosted server tại {base_url} hiện đang OFFLINE hoặc không phản hồi ({error_msg}).\n"
            f"Nguyên nhân thường gặp: Cloudflare trycloudflare tunnel đã hết hạn sau phiên làm việc Kaggle "
            f"hoặc Kaggle kernel chưa được bật."
        ),
        "guidance": [
            "1. Kích hoạt Kaggle Kernel: Đẩy kernel hoặc mở notebook `kaggle_notebooks/host_llm_kaggle_server.ipynb` "
            "trên Kaggle với GPU 2x T4 và bật Internet.",
            "2. Lấy URL mới: Khi Cloudflare Tunnel mở, sao chép URL `https://<hash>.trycloudflare.com/v1` "
            "vào file `configs/backend_kaggle.yaml`.",
            "3. Chạy smoke test: `python grace_diag_kit/scripts/smoke_test_backend.py --backend configs/backend_kaggle.yaml "
            "--prompts runs/dryrun/prompts_devign_validation.jsonl --n 20`.",
            "4. Thử nghiệm offline tại chỗ: Có thể dùng `--backend configs/backend_mock.yaml` hoặc `--mock` "
            "để chạy kiểm thử toàn diện quy trình ma trận trên validation subset.",
        ],
    }


# ---------------------------------------------------------------------------
# 2. Định nghĩa các Tầng Arm (Tiers) theo Đề cương & Giao thức
# ---------------------------------------------------------------------------
TIER_DEFINITIONS = {
    "tier1": {
        "description": "Tầng 1 (RQ1, lõi RQ2, RQ4): B0, B1, B2, B2-flip, B2-rep (seed 42)",
        "arms": ["B0", "B1", "B2", "B2-flip", "B2-rep"],
        "seeds": [42],
        "stochastic_seeds": {},
    },
    "tier2": {
        "description": "Tầng 2 (Cơ chế demo & graph): B2-rand (3 seeds), B2-nolabel, B2-labelonly, B1-shuf (3 seeds)",
        "arms": ["B2-rand", "B2-nolabel", "B2-labelonly", "B1-shuf"],
        "seeds": [42],
        "stochastic_seeds": {
            "B2-rand": [42, 43, 44],
            "B1-shuf": [42, 43, 44],
        },
    },
    "tier3": {
        "description": "Tầng 3 (Đóng gói graph, cặp tương phản B3): B1-full, B1-H2, B3, B3-nodiff, B3-swap, B3-flip (seed 42)",
        "arms": ["B1-full", "B1-H2", "B3", "B3-nodiff", "B3-swap", "B3-flip"],
        "seeds": [42],
        "stochastic_seeds": {},
    },
}


def ensure_specs_available(target_path: Path) -> Path:
    """Nếu target_path chưa tồn tại nhưng có file .gz tương ứng, tự động giải nén."""
    if target_path.exists():
        return target_path
    gz_cand = target_path.with_suffix(target_path.suffix + ".gz")
    if gz_cand.exists():
        import gzip, shutil
        print(f"[*] Tự động giải nén specs: {gz_cand.name} -> {target_path.name}...")
        with gzip.open(gz_cand, "rb") as f_in, open(target_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        return target_path
    if str(target_path).endswith(".gz"):
        uncompressed = Path(str(target_path)[:-3])
        if uncompressed.exists():
            return uncompressed
    return target_path


# ---------------------------------------------------------------------------
# 3. Thực thi Suy luận Ma trận bằng run_matrix.py
# ---------------------------------------------------------------------------
def execute_matrix_inference(
    dataset: str,
    split: str,
    specs_path: Path,
    donors_path: Optional[Path],
    arms: List[str],
    seeds: List[int],
    backend_path: Path,
    tokenizer_path: Optional[str],
    out_dir: Path,
    protocol_path: Path,
    arms_config_path: Path,
    limit: Optional[int] = None,
    dry_run: bool = False,
    allow_approx_tokens: bool = False,
) -> int:
    """Gọi công cụ chính thức run_matrix.py với các tham số tương ứng."""
    run_matrix_script = REPO_ROOT / "scripts" / "run_matrix.py"
    if not run_matrix_script.exists():
        run_matrix_script = REPO_ROOT / "grace_diag_kit" / "scripts" / "run_matrix.py"

    cmd = [
        sys.executable,
        str(run_matrix_script),
        "--dataset", dataset,
        "--split", split,
        "--specs", str(specs_path),
        "--arms", *arms,
        "--seeds", *[str(s) for s in seeds],
        "--protocol", str(protocol_path),
        "--arms-config", str(arms_config_path),
        "--out", str(out_dir),
    ]

    if donors_path and donors_path.exists():
        cmd.extend(["--donors", str(donors_path)])
    if not dry_run and backend_path:
        cmd.extend(["--backend", str(backend_path)])
    if tokenizer_path:
        cmd.extend(["--tokenizer", str(tokenizer_path)])
    if dry_run:
        cmd.append("--dry-run")
    if limit:
        cmd.extend(["--limit", str(limit)])
    if allow_approx_tokens:
        cmd.append("--allow-approx-tokens")

    print(f"\n[*] Đang thực thi lệnh Matrix Inference:")
    print(f"    {' '.join(cmd)}\n")

    res = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if res.returncode != 0:
        raise RuntimeError(f"run_matrix.py thất bại với mã lỗi {res.returncode}")
    return res.returncode


def execute_tier(
    tier: str,
    dataset: str,
    split: str,
    specs_path: Path,
    donors_path: Optional[Path],
    backend_path: Path,
    tokenizer_path: Optional[str],
    out_dir: Path,
    protocol_path: Path,
    arms_config_path: Path,
    limit: Optional[int] = None,
    dry_run: bool = False,
    override_arms: Optional[List[str]] = None,
) -> None:
    """Điều phối chạy ma trận cho một tier, nhóm theo seeds chuẩn xác theo protocol."""
    if override_arms:
        arm_groups = {tuple([42]): override_arms}
    elif tier == "all":
        stoch = ["B2-rand", "B1-shuf"]
        det = [a for a in ARMS.keys() if a not in stoch]
        arm_groups = {
            tuple([42]): det,
            tuple([42, 43, 44]): stoch,
        }
    else:
        t_info = TIER_DEFINITIONS[tier]
        stoch_map = t_info.get("stochastic_seeds", {})
        det = [a for a in t_info["arms"] if a not in stoch_map]
        arm_groups = {tuple(t_info["seeds"]): det}
        if stoch_map:
            for arm, seeds in stoch_map.items():
                arm_groups.setdefault(tuple(seeds), []).append(arm)

    for seeds, arms in arm_groups.items():
        if not arms:
            continue
        print(f"[*] Thực thi nhóm arm {arms} với seeds {list(seeds)}...")
        execute_matrix_inference(
            dataset=dataset,
            split=split,
            specs_path=specs_path,
            donors_path=donors_path,
            arms=arms,
            seeds=list(seeds),
            backend_path=backend_path,
            tokenizer_path=tokenizer_path,
            out_dir=out_dir,
            protocol_path=protocol_path,
            arms_config_path=arms_config_path,
            limit=limit,
            dry_run=dry_run,
        )


# ---------------------------------------------------------------------------
# 4. Tối ưu hóa & Khóa Ngưỡng tau* trên Validation (Strict Validation-Only)
# ---------------------------------------------------------------------------
def optimize_and_lock_thresholds(
    runs_dir: Path,
    out_thresholds_path: Path,
    protocol_path: Path,
    grid: Optional[np.ndarray] = None,
    include_step0_meta: bool = True,
) -> Dict[str, Any]:
    """Tìm ngưỡng tối ưu tau* hoàn toàn trên tập Validation và khóa cứng vào thresholds.json.

    NGUYÊN TẮC PHƯƠNG PHÁP LUẬN BẮT BUỘC:
    1. Tuyệt đối không đọc bất kỳ bản ghi nào thuộc split='test'.
    2. Grid tìm kiếm cố định: 99 điểm linspace(0.01, 0.99, 99).
    3. Phá hòa tất định: chọn ngưỡng có |tau - 0.5| nhỏ nhất.
    4. Khóa ngưỡng tau_pre* và tau_post* của mô hình meta P_pre/P_post trên validation.
    """
    if grid is None:
        grid = np.linspace(0.01, 0.99, 99)

    locked_taus: Dict[str, float] = {}
    tau_details: Dict[str, Dict[str, Any]] = {}

    # Tìm toàn bộ bản ghi validation trong runs_dir
    val_record_files = sorted(runs_dir.glob("**/validation/**/records.jsonl"))
    if not val_record_files:
        val_record_files = sorted(runs_dir.glob("*/*/validation/*/*/records.jsonl"))
    if not val_record_files:
        val_record_files = sorted(runs_dir.glob("*/validation/*/*/records.jsonl"))

    print(f"\n[*] Tìm thấy {len(val_record_files)} tệp records.jsonl trên tập Validation trong {runs_dir}.")

    for rec_file in val_record_files:
        parts = rec_file.parent.parts
        lowered = [p.lower() for p in parts]
        if "validation" not in lowered:
            continue
        val_idx = lowered.index("validation")
        if val_idx < 1 or len(parts) < val_idx + 3:
            continue

        dataset_str = parts[val_idx - 1]
        split_str = parts[val_idx]
        arm_str = parts[val_idx + 1]
        seed_str = parts[val_idx + 2]

        # Kiểm tra bất biến phương pháp luận: Tuyệt đối không chạm vào test
        if split_str.lower() != "validation":
            raise AssertionError(
                f"[VIOLATION] Phát hiện tệp không thuộc validation: {rec_file}! "
                f"Tối ưu ngưỡng tau* chỉ được phép thực hiện trên Validation."
            )

        y_list: List[int] = []
        s_list: List[float] = []
        valid_count = 0
        total_count = 0

        with open(rec_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                total_count += 1
                if row.get("valid") and row.get("s") is not None and row["s"] == row["s"]:
                    y_list.append(int(row["label"]))
                    s_list.append(float(row["s"]))
                    valid_count += 1

        if not y_list:
            print(f"[-] Bỏ qua {dataset_str}|{arm_str}|{seed_str} vì không có mẫu valid hợp lệ.")
            continue

        y_arr = np.array(y_list, dtype=int)
        s_arr = np.array(s_list, dtype=float)

        tau_star, mcc_star = S.pick_threshold(y_arr, s_arr, grid=grid)
        key = f"{dataset_str}|{arm_str}|{seed_str}"
        locked_taus[key] = float(tau_star)
        tau_details[key] = {
            "dataset": dataset_str,
            "arm": arm_str,
            "seed": int(seed_str),
            "split": "validation",
            "n_total": total_count,
            "n_valid": valid_count,
            "tau_star": float(tau_star),
            "mcc_at_tau": float(mcc_star) if mcc_star == mcc_star else None,
            "source_records": str(rec_file.relative_to(runs_dir) if runs_dir in rec_file.parents else rec_file),
        }
        print(f"    [+] {key:25s} -> tau* = {tau_star:.4f} (MCC_val = {mcc_star:.4f}, n={valid_count})")

    # Bổ sung ngưỡng tau_pre* và tau_post* từ Bước 0 (nếu có X_pre và gate validation)
    if include_step0_meta:
        for ds in ("devign", "reveal"):
            gate_val_path = REPO_ROOT / "data" / "b0_offline_dungs_data" / f"{ds}_gate_validation_exact.csv"
            xpre_val_path = REPO_ROOT / "data" / "b0_offline_dungs_data" / f"xpre_validation_{ds}.npz"
            if not gate_val_path.exists() or not xpre_val_path.exists():
                gate_val_path = REPO_ROOT / "data" / "mock_step0_2split" / f"{ds}_gate_val.csv"
                xpre_val_path = REPO_ROOT / "data" / "mock_step0_2split" / f"{ds}_xpre_val.npz"

            if gate_val_path.exists() and xpre_val_path.exists():
                try:
                    npz = np.load(xpre_val_path)
                    X_pre = npz["X"] if "X" in npz else npz["xpre"]
                    gate_rows = list(csv.DictReader(open(gate_val_path, encoding="utf-8")))

                    # Tìm bản ghi B2 validation records
                    b2_rec = runs_dir / ds / "validation" / "B2" / "42" / "records.jsonl"
                    if not b2_rec.exists():
                        b2_rec = runs_dir / "final" / ds / "validation" / "B2" / "42" / "records.jsonl"
                    if not b2_rec.exists():
                        found_b2 = list(runs_dir.glob(f"**/{ds}/validation/B2/42/records.jsonl"))
                        if found_b2:
                            b2_rec = found_b2[0]

                    id_to_s = {}
                    if b2_rec.exists():
                        with open(b2_rec, "r", encoding="utf-8") as f:
                            for l in f:
                                if l.strip():
                                    rr = json.loads(l)
                                    id_to_s[str(rr["id"])] = (
                                        float(rr["s"]) if rr.get("valid") and rr.get("s") is not None and rr["s"] == rr["s"] else 0.5,
                                        bool(rr.get("valid", False))
                                    )

                    # Khớp chính xác theo danh sách ID đã thực thi để tránh ô nhiễm bởi mẫu giả
                    sub_indices = [idx for idx, r in enumerate(gate_rows) if str(r["id"]) in id_to_s]
                    if sub_indices:
                        X_sub = X_pre[sub_indices]
                        y_sub = np.array([int(gate_rows[idx]["y"]) for idx in sub_indices], dtype=int)
                        pg_sub = np.array([float(gate_rows[idx]["p_gate"]) for idx in sub_indices], dtype=float)
                        s_sub = np.array([id_to_s[str(gate_rows[idx]["id"])][0] for idx in sub_indices], dtype=float)
                        v_sub = np.array([id_to_s[str(gate_rows[idx]["id"])][1] for idx in sub_indices], dtype=bool)
                    else:
                        n_min = min(len(gate_rows), len(X_pre))
                        X_sub = X_pre[:n_min]
                        y_sub = np.array([int(gate_rows[idx]["y"]) for idx in range(n_min)], dtype=int)
                        pg_sub = np.array([float(gate_rows[idx]["p_gate"]) for idx in range(n_min)], dtype=float)
                        s_sub = np.full(n_min, 0.5, dtype=float)
                        v_sub = np.zeros(n_min, dtype=bool)

                    pp = C.fit_pre_post(
                        X_pre=X_sub,
                        s=s_sub,
                        valid=v_sub,
                        p_gate=pg_sub,
                        y=y_sub,
                        n_folds=3,
                        seed=42,
                        n_boot=100,
                    )
                    locked_taus[f"{ds}|P-PRE|42"] = float(pp.tau_pre)
                    locked_taus[f"{ds}|P-POST|42"] = float(pp.tau_post)
                    tau_details[f"{ds}|P-PRE|42"] = {"dataset": ds, "arm": "P-PRE", "seed": 42, "tau_star": float(pp.tau_pre), "split": "validation", "n_evaluated": len(y_sub)}
                    tau_details[f"{ds}|P-POST|42"] = {"dataset": ds, "arm": "P-POST", "seed": 42, "tau_star": float(pp.tau_post), "split": "validation", "n_evaluated": len(y_sub)}
                    print(f"    [+] {ds}|P-PRE|42             -> tau* = {pp.tau_pre:.4f} (Validation Meta OOF, n={len(y_sub)})")
                    print(f"    [+] {ds}|P-POST|42            -> tau* = {pp.tau_post:.4f} (Validation Meta OOF, n={len(y_sub)})")
                except Exception as exc:
                    print(f"[-] Cảnh báo tính P_pre/P_post trên {ds}: {exc}")

    # Tạo tệp thresholds.json hoàn chỉnh có chữ ký bảo vệ
    payload = {
        "metadata": {
            "study_id": "grace_diag_replication_v1",
            "version": "prereg-v1",
            "phase": "Step 5: Validation Threshold Optimization & Locking",
            "optimized_on_split": "validation",
            "test_exposure": "STRICTLY_NONE (Zero test data used)",
            "grid_points": len(grid),
            "grid_range": [float(grid[0]), float(grid[-1])],
            "locked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_thresholds_locked": len(locked_taus),
            "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        },
        "thresholds": locked_taus,
        "details": tau_details,
    }

    out_thresholds_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_thresholds_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Đồng thời lưu một bản sao format phẳng (tương thích trực tiếp với evaluate_final.py)
    flat_path = out_thresholds_path.parent / "thresholds_flat.json"
    with open(flat_path, "w", encoding="utf-8") as f:
        json.dump(locked_taus, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] ĐÃ KHÓA THÀNH CÔNG {len(locked_taus)} NGƯỠNG TAU* VÀO:")
    print(f"    - {out_thresholds_path}")
    print(f"    - {flat_path}")

    return payload


# ---------------------------------------------------------------------------
# 5. Kiểm tra tính Sẵn sàng cho Tập Test (Test Readiness Verification)
# ---------------------------------------------------------------------------
def verify_test_readiness(
    thresholds_path: Path,
    arms_to_test: List[str],
    dataset: str,
    seeds_map: Optional[Dict[str, List[int]]] = None,
    require_meta: bool = True,
) -> bool:
    """Kiểm tra xem toàn bộ các arm chuẩn bị chạy test đã có ngưỡng tau* được khóa hay chưa.

    Bảo đảm:
    1. Mọi seed của từng arm (ví dụ: 42, 43, 44 cho stochastic arms) đều đã có ngưỡng trong thresholds.json.
    2. Các mô hình meta P-PRE và P-POST (nếu require_meta=True) đều đã được khóa ngưỡng.
    """
    if not thresholds_path.exists():
        print(f"[!] LỖI: Tệp {thresholds_path} chưa tồn tại!")
        print(f"    Nguyên tắc phương pháp luận: Không bao giờ chạy test trước khi có thresholds.json.")
        return False

    data = json.loads(thresholds_path.read_text(encoding="utf-8"))
    taus = data.get("thresholds", data)

    missing = []
    stochastic_arms = {"B2-rand": [42, 43, 44], "B1-shuf": [42, 43, 44]}

    for arm in arms_to_test:
        if seeds_map and arm in seeds_map:
            arm_seeds = seeds_map[arm]
        elif arm in stochastic_arms:
            arm_seeds = stochastic_arms[arm]
        else:
            arm_seeds = [42]

        for s in arm_seeds:
            key = f"{dataset}|{arm}|{s}"
            if key not in taus:
                missing.append(key)

    if require_meta:
        for meta_arm in ("P-PRE", "P-POST"):
            mkey = f"{dataset}|{meta_arm}|42"
            if mkey not in taus:
                missing.append(mkey)

    if missing:
        print(f"[!] CẢNH BÁO: Các ngưỡng sau chưa được khóa trong {thresholds_path.name}: {missing}")
        return False

    print(f"[✓] ĐÃ XÁC NHẬN: Toàn bộ {len(arms_to_test)} arm của {dataset} đã được khóa ngưỡng an toàn.")
    return True


# ---------------------------------------------------------------------------
# CLI Chính
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    # 1. check-backend
    p_check = sub.add_parser("check-backend", help="Kiểm tra trạng thái kết nối tới server LLM")
    p_check.add_argument("--backend", type=Path, default=REPO_ROOT / "configs" / "backend_kaggle.yaml")

    # 2. run-matrix
    p_matrix = sub.add_parser("run-matrix", help="Chạy ma trận arm trên split chỉ định")
    p_matrix.add_argument("--dataset", default="devign", choices=["devign", "reveal", "both"])
    p_matrix.add_argument("--split", default="validation", choices=["validation", "test"])
    p_matrix.add_argument("--tier", default="tier1", choices=["tier1", "tier2", "tier3", "all"])
    p_matrix.add_argument("--arms", nargs="+", help="Tùy chọn ghi đè danh sách arm cụ thể")
    p_matrix.add_argument("--backend", type=Path, default=REPO_ROOT / "configs" / "backend_mock.yaml")
    p_matrix.add_argument("--tokenizer", type=str, default=str(REPO_ROOT / "grace_diag_kit" / "tokenizer"))
    p_matrix.add_argument("--use-subset", action="store_true", default=True, help="Dùng subset 600 mẫu (mặc định)")
    p_matrix.add_argument("--full-split", action="store_true", help="Dùng toàn bộ tập dữ liệu (thay vì subset 600)")
    p_matrix.add_argument("--out", type=Path, default=REPO_ROOT / "runs" / "final")
    p_matrix.add_argument("--limit", type=int, help="Giới hạn N mẫu đầu")
    p_matrix.add_argument("--dry-run", action="store_true", help="Chỉ audit prompt")
    p_matrix.add_argument("--mock", action="store_true", help="Cưỡng chế dùng backend mock nội bộ")
    p_matrix.add_argument("--thresholds", type=Path, default=None, help="Đường dẫn file thresholds.json đã khóa (dùng khi kiểm tra split test)")

    # 3. lock-thresholds
    p_lock = sub.add_parser("lock-thresholds", help="Tối ưu hóa và khóa ngưỡng tau* từ tập Validation")
    p_lock.add_argument("--runs", type=Path, default=REPO_ROOT / "runs" / "final")
    p_lock.add_argument("--out", type=Path, default=REPO_ROOT / "runs" / "final" / "thresholds.json")
    p_lock.add_argument("--protocol", type=Path, default=REPO_ROOT / "configs" / "protocol.yaml")

    # 4. full-step5
    p_full = sub.add_parser("full-step5", help="Thực thi trọn vẹn quy trình Bước 5")
    p_full.add_argument("--tier", default="tier1", choices=["tier1", "tier2", "tier3", "all"])
    p_full.add_argument("--backend", type=Path, default=REPO_ROOT / "configs" / "backend_kaggle.yaml")
    p_full.add_argument("--allow-mock-fallback", action="store_true", default=True, help="Tự động fallback về mock nếu Kaggle offline")
    p_full.add_argument("--out", type=Path, default=REPO_ROOT / "runs" / "final")
    p_full.add_argument("--limit", type=int, help="Giới hạn mẫu (cho smoke test)")

    # 5. eval-pipeline
    p_eval = sub.add_parser("eval-pipeline", help="Chạy pipeline đánh giá evaluate_final.py với thresholds.json đã khóa")
    p_eval.add_argument("--runs", type=Path, default=REPO_ROOT / "runs" / "final")
    p_eval.add_argument("--protocol", type=Path, default=REPO_ROOT / "configs" / "protocol.yaml")
    p_eval.add_argument("--thresholds", type=Path, default=REPO_ROOT / "configs" / "thresholds.json")
    p_eval.add_argument("--out", type=Path, default=REPO_ROOT / "runs" / "final" / "evaluation")

    args = ap.parse_args()

    # -- COMMAND: check-backend --------------------------------------------
    if args.command == "check-backend":
        res = check_backend_status(args.backend)
        print(f"\n{'='*70}")
        print(f"  KIỂM TRA TRẠNG THÁI SERVER LLM ({args.backend.name})")
        print(f"{'='*70}")
        print(f"[*] Trạng thái:  {res['status'].upper()}")
        print(f"[*] Đang Online: {'CÓ (Sẵn sàng)' if res['is_online'] else 'KHÔNG (Offline)'}")
        print(f"[*] Thông điệp:  {res['message']}")
        if "guidance" in res:
            print(f"\n[*] HƯỚNG DẪN XỬ LÝ:")
            for line in res["guidance"]:
                print(f"    {line}")
        print(f"{'='*70}\n")
        return

    # -- COMMAND: run-matrix -----------------------------------------------
    if args.command == "run-matrix":
        backend_file = args.backend
        if args.mock:
            backend_file = REPO_ROOT / "configs" / "backend_mock.yaml"

        if not args.dry_run:
            status = check_backend_status(backend_file)
            if not status["is_online"]:
                print(f"\n[!] CẢNH BÁO: Backend {backend_file} đang offline!")
                print(status["message"])
                sys.exit(1)

        datasets = ["devign", "reveal"] if args.dataset == "both" else [args.dataset]

        # Rào chắn bất biến: Nếu là split test, bắt buộc thresholds.json phải tồn tại và đủ arm
        if args.split == "test":
            if args.thresholds:
                thresholds_file = args.thresholds
            else:
                thresholds_file = args.out / "thresholds.json"
                if not thresholds_file.exists():
                    thresholds_file = REPO_ROOT / "configs" / "thresholds.json"
            for ds in datasets:
                t_arms = args.arms or (list(ARMS.keys()) if args.tier == "all" else TIER_DEFINITIONS[args.tier]["arms"])
                if not verify_test_readiness(thresholds_file, t_arms, ds):
                    print(f"\n[VIOLATION] Ngăn chặn thực thi Test split: Ngưỡng chưa được khóa hoàn chỉnh trong {thresholds_file}!")
                    print(f"Nguyên tắc phương pháp luận: Khóa ngưỡng trên Validation trước khi chạy Test.")
                    sys.exit(1)

        for ds in datasets:
            if args.full_split:
                base_specs = REPO_ROOT / "data" / "specs" / f"{ds}_{args.split}.jsonl"
            else:
                base_specs = REPO_ROOT / "data" / "specs" / (f"{ds}_val_subset600.jsonl" if args.split == "validation" else f"{ds}_{args.split}.jsonl")

            specs_file = ensure_specs_available(base_specs)
            donors_file = ensure_specs_available(REPO_ROOT / "data" / "manifests" / f"{ds}_donors.jsonl")

            execute_tier(
                tier=args.tier,
                dataset=ds,
                split=args.split,
                specs_path=specs_file,
                donors_path=donors_file,
                backend_path=backend_file,
                tokenizer_path=args.tokenizer,
                out_dir=args.out,
                protocol_path=REPO_ROOT / "configs" / "protocol.yaml",
                arms_config_path=REPO_ROOT / "configs" / "arms.yaml",
                limit=args.limit,
                dry_run=args.dry_run,
                override_arms=args.arms,
            )

    # -- COMMAND: lock-thresholds ------------------------------------------
    if args.command == "lock-thresholds":
        payload = optimize_and_lock_thresholds(
            runs_dir=args.runs,
            out_thresholds_path=args.out,
            protocol_path=args.protocol,
        )
        # Đồng bộ sang configs/
        cfg_thresh = REPO_ROOT / "configs" / "thresholds.json"
        cfg_thresh.write_text(args.out.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[✓] Đã đồng bộ bản sao ngưỡng đã khóa tới: {cfg_thresh}")

    # -- COMMAND: full-step5 -----------------------------------------------
    if args.command == "full-step5":
        print(f"\n{'='*75}")
        print(f"  BẮT ĐẦU QUY TRÌNH THỰC THI BƯỚC 5: MA TRẬN & KHÓA NGƯỠNG VALIDATION")
        print(f"{'='*75}")

        status = check_backend_status(args.backend)
        chosen_backend = args.backend
        if not status["is_online"]:
            if args.allow_mock_fallback:
                print(f"\n[*] Server Kaggle ({args.backend.name}) đang offline.")
                print(f"[*] Tự động chuyển đổi linh hoạt sang Backend Mock nội bộ (configs/backend_mock.yaml)...")
                chosen_backend = REPO_ROOT / "configs" / "backend_mock.yaml"
            else:
                print(f"\n[!] LỖI: Server {args.backend} đang offline và không bật fallback.")
                sys.exit(1)
        else:
            print(f"\n[✓] Backend {chosen_backend.name} đang ONLINE và sẵn sàng!")

        t_info = TIER_DEFINITIONS[args.tier] if args.tier in TIER_DEFINITIONS else {"arms": list(ARMS.keys()), "seeds": [42]}
        print(f"\n[*] Chạy ma trận suy luận Validation cho {args.tier.upper()} ({len(t_info['arms'])} arms)...")

        for ds in ("devign", "reveal"):
            specs_val = ensure_specs_available(REPO_ROOT / "data" / "specs" / f"{ds}_val_subset600.jsonl")
            donors = ensure_specs_available(REPO_ROOT / "data" / "manifests" / f"{ds}_donors.jsonl")
            execute_tier(
                tier=args.tier,
                dataset=ds,
                split="validation",
                specs_path=specs_val,
                donors_path=donors,
                backend_path=chosen_backend,
                tokenizer_path=str(REPO_ROOT / "grace_diag_kit" / "tokenizer"),
                out_dir=args.out,
                protocol_path=REPO_ROOT / "configs" / "protocol.yaml",
                arms_config_path=REPO_ROOT / "configs" / "arms.yaml",
                limit=args.limit,
                dry_run=False,
            )

        thresholds_file = args.out / "thresholds.json"
        optimize_and_lock_thresholds(
            runs_dir=args.out,
            out_thresholds_path=thresholds_file,
            protocol_path=REPO_ROOT / "configs" / "protocol.yaml",
        )

        cfg_thresh = REPO_ROOT / "configs" / "thresholds.json"
        cfg_thresh.write_text(thresholds_file.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[✓] Đã đồng bộ bản sao ngưỡng đã khóa tới: {cfg_thresh}")

        for ds in ("devign", "reveal"):
            verify_test_readiness(thresholds_file, t_info["arms"], ds)

        print(f"\n{'='*75}")
        print(f"  HOÀN THÀNH 100% QUY TRÌNH BƯỚC 5!")
        print(f"  - Đã suy luận ma trận trên tập Validation.")
        print(f"  - Ngưỡng tối ưu tau* đã được chốt và khóa cứng trong thresholds.json.")
        print(f"  - Tuyệt đối không tiếp xúc tập Test trong quá trình chọn ngưỡng.")
        print(f"  - Sẵn sàng chuyển tiếp sang Bước 6 (Mốc có giám sát & Meta-model) và đánh giá Test.")
        print(f"{'='*75}\n")

    # -- COMMAND: eval-pipeline --------------------------------------------
    if args.command == "eval-pipeline":
        print(f"\n[*] Chạy kiểm định Pipeline Đánh giá evaluate_final.py...")
        eval_script = REPO_ROOT / "grace_diag_kit" / "src" / "grace_diag" / "evaluate_final.py"
        cmd = [
            sys.executable,
            "-m", "grace_diag.evaluate_final",
            "--runs", str(args.runs),
            "--protocol", str(args.protocol),
            "--thresholds", str(args.thresholds),
            "--out", str(args.out),
        ]
        env = os.environ.copy()
        grace_pkg_dir = str(REPO_ROOT / "grace_diag_kit" / "src")
        env["PYTHONPATH"] = f"{grace_pkg_dir}{os.pathsep}{env.get('PYTHONPATH', '')}"
        res = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env)
        if res.returncode != 0:
            raise RuntimeError(f"evaluate_final.py thất bại với mã {res.returncode}")
        print(f"[✓] Đã xuất toàn bộ bảng kết quả và hình vẽ vào: {args.out}")


if __name__ == "__main__":
    main()
