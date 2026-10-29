#!/usr/bin/env python3
"""Script Adapter thực thi Bước 0: Phân tích chẩn đoán Offline (Offline Diagnostic Pipeline).

Hỗ trợ 2 chế độ đánh giá:
1. Chuẩn 2-Split (Phương pháp luận chuẩn của Thầy - Mục 15 trong đề cương & grace_diag.complementarity):
   - Validation split: Khớp meta-model OOF CV để xác định ngưỡng tối ưu tau_pre*, tau_post*;
     huấn luyện bộ định tuyến lợi ích (Benefit Router - Ridge).
   - Test split: Khóa mô hình và ngưỡng từ Validation, áp sang Test độc lập;
     tính toán ma trận Sửa/Hỏng, trần Oracle, Matched Meta-Model (95% Paired Bootstrap CI),
     kiểm định McNemar kèm hiệu chỉnh Holm, và Selective Routing Curves đầy đủ 4 chính sách.
2. Single-Split Fallback (Tương thích ngược):
   - Chạy OOF CV trên một split duy nhất kèm cảnh báo rò rỉ dữ liệu test nếu người dùng chỉ truyền --gate-csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np

# Đảm bảo import được grace_diag
try:
    import grace_diag
    from grace_diag import complementarity as C
    from grace_diag import stats as S
except ImportError:
    repo_root = Path(__file__).resolve().parents[1]
    diag_src = repo_root / "grace_diag_kit" / "src"
    if diag_src.exists():
        sys.path.insert(0, str(diag_src))
    import grace_diag
    from grace_diag import complementarity as C
    from grace_diag import stats as S


def parse_float_safe(val: Any, default: Optional[float] = None) -> Optional[float]:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return default
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "n/a", ""):
        return default
    try:
        f = float(s)
        return default if math.isnan(f) or math.isinf(f) else f
    except ValueError:
        return default


def sanitize_for_json(obj: Any) -> Any:
    """Chuyển đổi các kiểu dữ liệu numpy / float NaN thành đối tượng tương thích chuẩn JSON."""
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return sanitize_for_json(obj.tolist())
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, float)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


def load_gate_data(gate_csv_path: Path | str) -> Dict[str, Dict[str, Any]]:
    """Đọc file gate CSV. Hỗ trợ linh hoạt các tên cột phổ biến."""
    gate_csv_path = Path(gate_csv_path)
    if not gate_csv_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file Gate CSV: {gate_csv_path}")

    with open(gate_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = [c.strip() for c in reader.fieldnames or []]

        id_col = next((c for c in fieldnames if c.lower() in ("id", "record_id", "func_id", "function_uid", "example_id")), None)
        if not id_col:
            raise ValueError(f"File {gate_csv_path} thiếu cột 'id'. Các cột có sẵn: {fieldnames}")

        y_col = next((c for c in fieldnames if c.lower() in ("y", "target", "label", "ground_truth", "vuln")), None)
        if not y_col:
            raise ValueError(f"File {gate_csv_path} thiếu cột nhãn 'y'. Các cột có sẵn: {fieldnames}")

        p_col = next((c for c in fieldnames if c.lower() in ("p_gate", "p", "probability", "prob", "score_gate")), None)
        if not p_col:
            raise ValueError(f"File {gate_csv_path} thiếu cột xác suất 'p_gate'. Các cột có sẵn: {fieldnames}")

        grp_col = next((c for c in fieldnames if c.lower() in ("group", "project", "commit_id")), None)

        rows = {}
        for r in reader:
            sid = str(r[id_col]).strip()
            if not sid:
                continue
            y_val = int(round(float(r[y_col])))
            p_val = float(r[p_col])
            grp_val = str(r[grp_col]).strip() if grp_col and r.get(grp_col) else None
            rows[sid] = {
                "id": sid,
                "y": y_val,
                "p_gate": p_val,
                "group": grp_val,
            }
    return rows


def load_llm_predictions(llm_path: Path | str) -> Dict[str, Dict[str, Any]]:
    """Đọc kết quả dự đoán của LLM (hỗ trợ .jsonl, .json, .csv)."""
    llm_path = Path(llm_path)
    if not llm_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file LLM predictions: {llm_path}")

    records = {}

    def extract_record_fields(r: Dict[str, Any]) -> Tuple[str, Optional[float], bool, str]:
        sid = str(r.get("id") or r.get("custom_id") or r.get("record_id") or r.get("func_id") or "").strip()
        if not sid:
            return "", None, False, ""

        val_flag = r.get("valid")
        if val_flag is not None:
            if isinstance(val_flag, str):
                valid = val_flag.strip().lower() in ("1", "true", "yes")
            else:
                valid = bool(val_flag)
        else:
            valid = True

        raw_str = str(r.get("raw") or r.get("response") or r.get("prediction") or "")

        s_val = None
        if "s" in r and r["s"] is not None:
            s_val = parse_float_safe(r["s"])
        elif "s_llm" in r and r["s_llm"] is not None:
            s_val = parse_float_safe(r["s_llm"])

        if s_val is None:
            pred = r.get("pred_argmax")
            if pred is None:
                pred = r.get("prediction")
            if pred is not None:
                pred_str = str(pred).strip()
                if pred_str in ("1", "1.0", "vuln", "vulnerable"):
                    s_val = 1.0
                elif pred_str in ("0", "0.0", "safe", "non-vulnerable"):
                    s_val = 0.0
                else:
                    try:
                        s_val = float(pred_str)
                    except ValueError:
                        valid = False
                        s_val = 0.5
            else:
                valid = False
                s_val = 0.5

        if s_val is None:
            valid = False
            s_val = 0.5

        return sid, s_val, valid, raw_str

    if llm_path.suffix.lower() == ".csv":
        with open(llm_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                sid, s_val, valid, raw_str = extract_record_fields(r)
                if sid:
                    records[sid] = {"id": sid, "s_llm": s_val, "valid": valid, "raw": raw_str}
    else:
        with open(llm_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("[") and content.endswith("]"):
                items = json.loads(content)
                for r in items:
                    sid, s_val, valid, raw_str = extract_record_fields(r)
                    if sid:
                        records[sid] = {"id": sid, "s_llm": s_val, "valid": valid, "raw": raw_str}
            else:
                for line in content.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    sid, s_val, valid, raw_str = extract_record_fields(r)
                    if sid:
                        records[sid] = {"id": sid, "s_llm": s_val, "valid": valid, "raw": raw_str}

    return records


def build_canonical_table(
    gate_data: Dict[str, Dict[str, Any]],
    llm_data: Dict[str, Dict[str, Any]],
    xpre_path: Optional[Path] = None,
    split_name: str = "split",
) -> Tuple[List[str], np.ndarray, np.ndarray, np.ndarray, np.ndarray, Optional[List[str]], np.ndarray]:
    """Khớp nối dữ liệu theo ID thành các mảng canonical."""
    matched_ids = [sid for sid in gate_data if sid in llm_data]

    if not matched_ids:
        raise ValueError(
            f"Không tìm thấy mẫu nào trùng khớp ID giữa Gate ({len(gate_data)} mẫu) "
            f"và LLM ({len(llm_data)} mẫu) trong tập {split_name}!"
        )

    print(f"[*] Khớp nối thành công: {len(matched_ids)} / {len(gate_data)} mẫu từ Gate CSV ({split_name}).")
    if len(matched_ids) < len(gate_data):
        print(f"[!] Cảnh báo: Có {len(gate_data) - len(matched_ids)} mẫu trong Gate CSV thiếu kết quả LLM ({split_name}).")

    ids = matched_ids
    y = np.array([gate_data[i]["y"] for i in ids], dtype=int)
    p_gate = np.array([gate_data[i]["p_gate"] for i in ids], dtype=float)
    s_llm = np.array([llm_data[i]["s_llm"] for i in ids], dtype=float)
    valid = np.array([llm_data[i]["valid"] for i in ids], dtype=bool)

    groups = None
    if any(gate_data[i].get("group") is not None for i in ids):
        groups = [gate_data[i].get("group") or "default" for i in ids]

    # Xử lý X_pre
    if xpre_path and xpre_path.exists():
        npz = np.load(xpre_path)
        if "X" in npz:
            X_all = npz["X"]
        elif "features" in npz:
            X_all = npz["features"]
        else:
            X_all = npz[npz.files[0]]

        if "ids" in npz:
            xpre_ids = [str(x).strip() for x in npz["ids"]]
            id_to_idx = {xid: idx for idx, xid in enumerate(xpre_ids)}
            missing_xpre = [i for i in ids if i not in id_to_idx]
            if not missing_xpre:
                indices = [id_to_idx[i] for i in ids]
                X_pre = X_all[indices]
                print(f"[*] Đã nạp ma trận X_pre từ {xpre_path} (shape={X_pre.shape}) khớp theo cột 'ids'.")
            else:
                print(f"[!] Cảnh báo: {len(missing_xpre)} ID không có trong xpre NPZ; chuyển sang dùng logit(p_gate).")
                X_pre = C.logit(p_gate)[:, None]
        else:
            if len(X_all) == len(gate_data):
                gate_id_list = list(gate_data.keys())
                gate_idx_map = {gid: idx for idx, gid in enumerate(gate_id_list)}
                indices = [gate_idx_map[i] for i in ids]
                X_pre = X_all[indices]
                print(f"[*] Đã nạp ma trận X_pre từ {xpre_path} (shape={X_pre.shape}) theo thứ tự Gate CSV.")
            elif len(X_all) == len(ids):
                X_pre = X_all
                print(f"[*] Đã nạp ma trận X_pre từ {xpre_path} (shape={X_pre.shape}) đúng kích thước matched IDs.")
            else:
                print(f"[!] Kích thước X_pre ({len(X_all)}) không khớp số mẫu ({len(ids)}); dùng logit(p_gate).")
                X_pre = C.logit(p_gate)[:, None]
    else:
        print(f"[*] Không cung cấp X_pre ({split_name}); sử dụng logit(p_gate) làm đặc trưng nền duy nhất.")
        X_pre = C.logit(p_gate)[:, None]

    return ids, y, p_gate, s_llm, valid, groups, X_pre


def _export_canonical_csv(out_path: Path, ids: List[str], y: np.ndarray, p_gate: np.ndarray, s_llm: np.ndarray, valid: np.ndarray):
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "y", "p_gate", "s_llm", "valid"])
        for sid, yi, pi, si, vi in zip(ids, y, p_gate, s_llm, valid):
            writer.writerow([sid, yi, f"{pi:.6f}", f"{si:.6f}", int(vi)])
    print(f"[*] Đã lưu bảng canonical: {out_path}")


def run_offline_diagnostic_2split(
    gate_val_path: Path | str,
    gate_test_path: Path | str,
    llm_val_path: Path | str,
    llm_test_path: Path | str,
    xpre_val_path: Optional[Path | str] = None,
    xpre_test_path: Optional[Path | str] = None,
    dataset: str = "devign",
    tau: float = 0.5,
    output_dir: Path | str = Path("runs/step0"),
    seed: int = 42,
    n_boot: int = 1000,
    n_folds: int = 5,
    margin_mcc: float = 0.02,
) -> Tuple[Dict[str, Any], Path, Path]:
    """Thực thi chẩn đoán theo chuẩn 2-Split (Validation fit meta-model, Test áp mô hình độc lập)."""
    gate_val_path = Path(gate_val_path)
    gate_test_path = Path(gate_test_path)
    llm_val_path = Path(llm_val_path)
    llm_test_path = Path(llm_test_path)
    xpre_val_path = Path(xpre_val_path) if xpre_val_path else None
    xpre_test_path = Path(xpre_test_path) if xpre_test_path else None
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================")
    print(f"  KHỞI CHẠY BƯỚC 0: PHÂN TÍCH CHẨN ĐOÁN 2-SPLIT ({dataset.upper()})")
    print(f"=======================================================")
    print(f"  Validation Gate:  {gate_val_path}")
    print(f"  Validation LLM:   {llm_val_path}")
    print(f"  Validation X_pre: {xpre_val_path or 'None (fallback logit p_gate)'}")
    print(f"  Test Gate:        {gate_test_path}")
    print(f"  Test LLM:         {llm_test_path}")
    print(f"  Test X_pre:       {xpre_test_path or 'None (fallback logit p_gate)'}")
    print(f"  Ngưỡng Gate tau:  {tau}")
    print(f"  Bootstrap reps:   {n_boot}")
    print(f"  Folds CV (Val):   {n_folds}")
    print(f"  Seed:             {seed}")
    print(f"=======================================================\n")

    # 1. Đọc và khớp nối canonical cho cả hai split
    val_gate = load_gate_data(gate_val_path)
    val_llm = load_llm_predictions(llm_val_path)
    ids_v, y_v, p_gate_v, s_llm_v, valid_v, groups_v, X_pre_v = build_canonical_table(
        val_gate, val_llm, xpre_val_path, split_name="validation"
    )

    test_gate = load_gate_data(gate_test_path)
    test_llm = load_llm_predictions(llm_test_path)
    ids_t, y_t, p_gate_t, s_llm_t, valid_t, groups_t, X_pre_t = build_canonical_table(
        test_gate, test_llm, xpre_test_path, split_name="test"
    )

    # Xuất file canonical CSV cho cả 2 split
    canonical_val_path = output_dir / f"canonical_{dataset}_val.csv"
    canonical_test_path = output_dir / f"canonical_{dataset}_test.csv"
    _export_canonical_csv(canonical_val_path, ids_v, y_v, p_gate_v, s_llm_v, valid_v)
    _export_canonical_csv(canonical_test_path, ids_t, y_t, p_gate_t, s_llm_t, valid_t)
    # File alias canonical tổng cho tương thích
    canonical_alias_path = output_dir / f"canonical_{dataset}.csv"
    _export_canonical_csv(canonical_alias_path, ids_t, y_t, p_gate_t, s_llm_t, valid_t)

    # 2. Pha 1 (Validation): Fit meta-model OOF CV & chọn ngưỡng tối ưu tau_pre*, tau_post*
    print("[*] [Validation] Đang fit meta-model P_pre vs P_post (OOF CV) trên tập Validation...")
    pp_val = C.fit_pre_post(
        X_pre_v,
        s_llm_v,
        valid_v,
        p_gate_v,
        y_v,
        n_folds=n_folds,
        seed=seed,
        n_boot=min(n_boot, 1000),
        margin_mcc=margin_mcc,
        groups=groups_v,
    )
    tau_pre_opt = pp_val.tau_pre
    tau_post_opt = pp_val.tau_post
    print(f"[*] [Validation] Đã xác định ngưỡng tối ưu: tau_pre* = {tau_pre_opt:.4f}, tau_post* = {tau_post_opt:.4f}")

    # Huấn luyện Benefit Router trên Validation
    h_gate_v = (p_gate_v >= tau).astype(int)
    g_llm_v = (s_llm_v >= 0.5).astype(int)
    benefit_router = C.fit_benefit_router(X_pre_v, y_v, h_gate_v, g_llm_v, valid_v)
    print("[*] [Validation] Đã huấn luyện bộ định tuyến lợi ích (Benefit Router - Ridge) trên Validation.")

    # 3. Pha 2 (Test): Áp meta-model và ngưỡng đã khóa sang Test độc lập
    print("[*] [Test] Đang áp mô hình và ngưỡng tối ưu sang tập Test độc lập...")
    applied = C.apply_pre_post(
        X_pre_v,
        s_llm_v,
        valid_v,
        p_gate_v,
        y_v,
        X_pre_t,
        s_llm_t,
        valid_t,
        p_gate_t,
        seed=seed,
        tau_pre=tau_pre_opt,
        tau_post=tau_post_opt,
        n_folds=n_folds,
        groups=groups_v,
    )

    pred_pre_t = applied["pred_pre"]
    pred_post_t = applied["pred_post"]
    score_pre_t = applied["score_pre"]
    score_post_t = applied["score_post"]

    n_test = len(y_t)
    n_valid_t = int(valid_t.sum())
    n_invalid_t = n_test - n_valid_t
    n_vuln_t = int((y_t == 1).sum())
    n_safe_t = int((y_t == 0).sum())

    h_gate_t = (p_gate_t >= tau).astype(int)
    g_llm_t = (s_llm_t >= 0.5).astype(int)
    g_fallback_t = np.where(valid_t, g_llm_t, h_gate_t).astype(int)

    # Hiệu năng Standalone trên Test
    gate_metrics_t = S.thresholded_metrics(y_t, h_gate_t)
    gate_metrics_t["auroc"] = S.auroc(y_t, p_gate_t)
    gate_metrics_t["auprc"] = S.auprc(y_t, p_gate_t)

    llm_valid_metrics_t = (
        S.thresholded_metrics(y_t[valid_t], g_llm_t[valid_t]) if n_valid_t > 0 else {}
    )
    llm_fallback_metrics_t = S.thresholded_metrics(y_t, g_fallback_t)

    # Ma trận Sửa - Hỏng trên Test
    rh_matrix_t = C.repair_harm(y_t, h_gate_t, g_llm_t, valid_t)
    r_total_t = rh_matrix_t["total"]["repair"]
    h_total_t = rh_matrix_t["total"]["harm"]
    net_repair_t = r_total_t - h_total_t

    # Chuyên gia tham chiếu trên Test
    pos_rate_t = float(g_llm_t[valid_t].mean()) if n_valid_t > 0 else 0.5
    ref_experts_t = C.reference_experts(y_t, h_gate_t, positive_rate=pos_rate_t, n_random=20, seed=seed)

    # Trần lý thuyết Oracle trên Test
    oracle_base_t = C.oracle_ceiling(y_t, h_gate_t, g_llm_t, valid_t)
    y_oracle_t = np.where((h_gate_t == y_t) | (valid_t & (g_llm_t == y_t)), y_t, 1 - y_t).astype(int)
    oracle_metrics_t = {
        "accuracy": oracle_base_t["oracle_accuracy"],
        "f1": S.f1(y_t, y_oracle_t),
        "mcc": S.mcc(y_t, y_oracle_t),
        "balanced_accuracy": S.balanced_accuracy(y_t, y_oracle_t),
        "classifier_accuracy": oracle_base_t["classifier_accuracy"],
        "expert_accuracy_valid": oracle_base_t["expert_accuracy_valid"],
    }

    # Đánh giá Matched Meta-Model trên Test kèm Paired Bootstrap CI 95%
    print(f"[*] [Test] Đang tính Paired Bootstrap CI ({n_boot} reps) trên tập Test độc lập...")
    ci_delta_mcc_t = S.paired_bootstrap(y_t, pred_pre_t, pred_post_t, S.mcc, n_boot=n_boot, seed=seed, groups=groups_t)
    ci_delta_f1_t = S.paired_bootstrap(y_t, pred_pre_t, pred_post_t, S.f1, n_boot=n_boot, seed=seed, groups=groups_t)
    ci_delta_acc_t = S.paired_bootstrap(
        y_t, pred_pre_t, pred_post_t, lambda yt, pt: float((pt == yt).mean()), n_boot=n_boot, seed=seed, groups=groups_t
    )
    ci_delta_auroc_t = S.paired_bootstrap(y_t, score_pre_t, score_post_t, S.auroc, n_boot=n_boot, seed=seed, groups=groups_t)
    verdict_test = S.verdict(ci_delta_mcc_t, margin_mcc)

    metrics_pre_t = {**S.thresholded_metrics(y_t, pred_pre_t), "auroc": S.auroc(y_t, score_pre_t)}
    metrics_post_t = {**S.thresholded_metrics(y_t, pred_post_t), "auroc": S.auroc(y_t, score_post_t)}

    # Kiểm định McNemar kèm hiệu chỉnh Holm trên Test
    mcnemar_raw_t = {
        "P_pre_vs_P_post": S.mcnemar_test(y_t, pred_pre_t, pred_post_t),
        "Gate_vs_P_post": S.mcnemar_test(y_t, h_gate_t, pred_post_t),
        "Gate_vs_LLM_fallback": S.mcnemar_test(y_t, h_gate_t, g_fallback_t),
        "Gate_vs_P_pre": S.mcnemar_test(y_t, h_gate_t, pred_pre_t),
    }
    p_vals_dict_t = {k: v["p_value"] for k, v in mcnemar_raw_t.items()}
    p_vals_holm_t = S.holm(p_vals_dict_t)

    mcnemar_summary_t = {}
    for k in mcnemar_raw_t:
        mcnemar_summary_t[k] = {
            "b (A đúng, B sai)": mcnemar_raw_t[k]["b"],
            "c (A sai, B đúng)": mcnemar_raw_t[k]["c"],
            "p_value_raw": mcnemar_raw_t[k]["p_value"],
            "p_value_holm": p_vals_holm_t[k],
            "method": mcnemar_raw_t[k]["method"],
            "significant_at_05": bool(p_vals_holm_t[k] < 0.05),
        }

    # Định tuyến chọn lọc (Selective Routing Curves) trên Test với đầy đủ 4 chính sách
    benefit_scores_t = benefit_router.predict(X_pre_t)
    routing_results_t = C.routing_curves(
        y_t,
        h_gate_t,
        g_llm_t,
        valid_t,
        p_gate_t,
        tau,
        ids_t,
        budgets=(0.05, 0.10, 0.25, 0.50),
        benefit_scores=benefit_scores_t,
        seed=seed,
    )

    # Tổng hợp toàn bộ kết quả vào Dictionary
    report_dict: Dict[str, Any] = {
        "metadata": {
            "dataset": dataset,
            "evaluation_mode": "2_split",
            "n_samples": n_test,
            "n_samples_val": len(y_v),
            "n_samples_test": n_test,
            "n_vulnerable": n_vuln_t,
            "n_safe": n_safe_t,
            "vulnerability_rate": float(n_vuln_t / n_test) if n_test else 0.0,
            "n_valid_llm": n_valid_t,
            "n_invalid_llm": n_invalid_t,
            "tau_gate": tau,
            "seed": seed,
            "n_boot": n_boot,
            "n_folds": n_folds,
            "margin_mcc_delta": margin_mcc,
        },
        "verdict": {
            "delta_verdict": verdict_test,
            "verdict_description": S.VERDICTS.get(verdict_test, verdict_test),
            "delta_mcc": ci_delta_mcc_t.to_dict(),
            "delta_auroc": ci_delta_auroc_t.to_dict(),
            "delta_f1": ci_delta_f1_t.to_dict(),
            "delta_accuracy": ci_delta_acc_t.to_dict(),
        },
        "standalone_performance": {
            "gate": gate_metrics_t,
            "llm_valid_only": llm_valid_metrics_t,
            "llm_fallback": llm_fallback_metrics_t,
        },
        "repair_harm_matrix": rh_matrix_t,
        "net_repair": {
            "repair_total": r_total_t,
            "harm_total": h_total_t,
            "net_repair": net_repair_t,
            "repair_rate_gate_mistakes": float(r_total_t / max(1, (h_gate_t != y_t).sum())),
            "harm_rate_gate_correct": float(h_total_t / max(1, (h_gate_t == y_t).sum())),
        },
        "reference_experts": ref_experts_t,
        "oracle_ceiling": oracle_metrics_t,
        "matched_meta_model": {
            "tau_pre": tau_pre_opt,
            "tau_post": tau_post_opt,
            "metrics_pre": metrics_pre_t,
            "metrics_post": metrics_post_t,
            "evaluation_split": "test",
            "threshold_origin": "validation_oof",
            "validation_oof": {
                "metrics_pre": pp_val.metrics_pre,
                "metrics_post": pp_val.metrics_post,
                "delta_mcc": pp_val.delta_mcc.to_dict(),
                "delta_auroc": pp_val.delta_auroc.to_dict(),
                "verdict_mcc": pp_val.verdict_mcc,
            },
        },
        "mcnemar_tests": mcnemar_summary_t,
        "selective_routing_curves": routing_results_t,
    }

    # Xuất JSON
    report_json_path = output_dir / f"diagnostic_report_{dataset}.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(sanitize_for_json(report_dict), f, ensure_ascii=False, indent=2)
    print(f"[*] Đã xuất báo cáo JSON: {report_json_path}")

    # Xuất Markdown
    report_md_path = output_dir / f"diagnostic_summary_{dataset}.md"
    md_content = render_markdown_summary(report_dict)
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[*] Đã xuất tóm tắt Markdown: {report_md_path}")

    return report_dict, report_json_path, report_md_path


def run_offline_diagnostic_single_split(
    gate_csv_path: Path | str,
    llm_path: Path | str,
    xpre_path: Optional[Path | str],
    dataset: str,
    tau: float = 0.5,
    output_dir: Path | str = Path("runs/step0"),
    seed: int = 42,
    n_boot: int = 1000,
    n_folds: int = 5,
    margin_mcc: float = 0.02,
) -> Tuple[Dict[str, Any], Path, Path]:
    """Chế độ single-split tương thích ngược (kèm cảnh báo phương pháp luận)."""
    gate_csv_path = Path(gate_csv_path)
    llm_path = Path(llm_path)
    xpre_path = Path(xpre_path) if xpre_path else None
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "!" * 70)
    print("  [!] CẢNH BÁO PHƯƠNG PHÁP LUẬN (SINGLE-SPLIT FALLBACK):")
    print("  Đang chạy ở chế độ Single-Split (chỉ truyền --gate-csv).")
    print("  Ngưỡng và meta-model được fit và đánh giá OOF trên cùng một tập dữ liệu.")
    print("  Theo phương pháp luận chuẩn của Thầy (Mục 15 trong đề cương & grace_diag.complementarity),")
    print("  hãy sử dụng chuẩn 2-Split (--gate-val, --gate-test, --llm-val, --llm-test) để khóa ngưỡng")
    print("  trên Validation và kiểm định khách quan trên Test độc lập, tránh rò rỉ dữ liệu!")
    print("!" * 70 + "\n")

    print(f"\n=======================================================")
    print(f"  KHỞI CHẠY BƯỚC 0: PHÂN TÍCH CHẨN ĐOÁN OFFLINE ({dataset.upper()})")
    print(f"=======================================================")
    print(f"  Gate CSV:        {gate_csv_path}")
    print(f"  LLM Predictions: {llm_path}")
    print(f"  X_pre NPZ:       {xpre_path or 'None (fallback logit p_gate)'}")
    print(f"  Ngưỡng Gate tau: {tau}")
    print(f"  Bootstrap reps:  {n_boot}")
    print(f"  Seed:            {seed}")
    print(f"=======================================================\n")

    gate_data = load_gate_data(gate_csv_path)
    llm_data = load_llm_predictions(llm_path)
    ids, y, p_gate, s_llm, valid, groups, X_pre = build_canonical_table(
        gate_data, llm_data, xpre_path, split_name="single"
    )

    n_samples = len(y)
    n_valid = int(valid.sum())
    n_invalid = n_samples - n_valid
    n_vuln = int((y == 1).sum())
    n_safe = int((y == 0).sum())

    canonical_csv_path = output_dir / f"canonical_{dataset}.csv"
    _export_canonical_csv(canonical_csv_path, ids, y, p_gate, s_llm, valid)

    h_gate = (p_gate >= tau).astype(int)
    g_llm = (s_llm >= 0.5).astype(int)
    g_fallback = np.where(valid, g_llm, h_gate).astype(int)

    gate_metrics = S.thresholded_metrics(y, h_gate)
    gate_metrics["auroc"] = S.auroc(y, p_gate)
    gate_metrics["auprc"] = S.auprc(y, p_gate)

    llm_valid_metrics = (
        S.thresholded_metrics(y[valid], g_llm[valid]) if n_valid > 0 else {}
    )
    llm_fallback_metrics = S.thresholded_metrics(y, g_fallback)

    rh_matrix = C.repair_harm(y, h_gate, g_llm, valid)
    r_total = rh_matrix["total"]["repair"]
    h_total = rh_matrix["total"]["harm"]
    net_repair = r_total - h_total

    pos_rate = float(g_llm[valid].mean()) if n_valid > 0 else 0.5
    ref_experts = C.reference_experts(y, h_gate, positive_rate=pos_rate, n_random=20, seed=seed)

    oracle_base = C.oracle_ceiling(y, h_gate, g_llm, valid)
    y_oracle = np.where((h_gate == y) | (valid & (g_llm == y)), y, 1 - y).astype(int)
    oracle_metrics = {
        "accuracy": oracle_base["oracle_accuracy"],
        "f1": S.f1(y, y_oracle),
        "mcc": S.mcc(y, y_oracle),
        "balanced_accuracy": S.balanced_accuracy(y, y_oracle),
        "classifier_accuracy": oracle_base["classifier_accuracy"],
        "expert_accuracy_valid": oracle_base["expert_accuracy_valid"],
    }

    print("[*] Đang fit mô hình đối chứng P_pre vs P_post (OOF CV) & tính Paired Bootstrap CI...")
    pp_result = C.fit_pre_post(
        X_pre,
        s_llm,
        valid,
        p_gate,
        y,
        n_folds=n_folds,
        seed=seed,
        n_boot=n_boot,
        margin_mcc=margin_mcc,
        groups=groups,
    )

    pred_pre = (pp_result.oof_pre >= pp_result.tau_pre).astype(int)
    pred_post = (pp_result.oof_post >= pp_result.tau_post).astype(int)

    ci_delta_f1 = S.paired_bootstrap(y, pred_pre, pred_post, S.f1, n_boot=n_boot, seed=seed, groups=groups)
    ci_delta_acc = S.paired_bootstrap(
        y, pred_pre, pred_post, lambda yt, pt: float((pt == yt).mean()), n_boot=n_boot, seed=seed, groups=groups
    )

    mcnemar_raw = {
        "P_pre_vs_P_post": S.mcnemar_test(y, pred_pre, pred_post),
        "Gate_vs_P_post": S.mcnemar_test(y, h_gate, pred_post),
        "Gate_vs_LLM_fallback": S.mcnemar_test(y, h_gate, g_fallback),
        "Gate_vs_P_pre": S.mcnemar_test(y, h_gate, pred_pre),
    }
    p_vals_dict = {k: v["p_value"] for k, v in mcnemar_raw.items()}
    p_vals_holm = S.holm(p_vals_dict)

    mcnemar_summary = {}
    for k in mcnemar_raw:
        mcnemar_summary[k] = {
            "b (A đúng, B sai)": mcnemar_raw[k]["b"],
            "c (A sai, B đúng)": mcnemar_raw[k]["c"],
            "p_value_raw": mcnemar_raw[k]["p_value"],
            "p_value_holm": p_vals_holm[k],
            "method": mcnemar_raw[k]["method"],
            "significant_at_05": bool(p_vals_holm[k] < 0.05),
        }

    # Benefit router fitting trên single-split
    benefit_router = C.fit_benefit_router(X_pre, y, h_gate, g_llm, valid)
    benefit_scores = benefit_router.predict(X_pre)
    routing_results = C.routing_curves(
        y, h_gate, g_llm, valid, p_gate, tau, ids, budgets=(0.05, 0.10, 0.25, 0.50), benefit_scores=benefit_scores, seed=seed
    )

    report_dict: Dict[str, Any] = {
        "metadata": {
            "dataset": dataset,
            "evaluation_mode": "single_split_fallback",
            "n_samples": n_samples,
            "n_vulnerable": n_vuln,
            "n_safe": n_safe,
            "vulnerability_rate": float(n_vuln / n_samples) if n_samples else 0.0,
            "n_valid_llm": n_valid,
            "n_invalid_llm": n_invalid,
            "tau_gate": tau,
            "seed": seed,
            "n_boot": n_boot,
            "n_folds": n_folds,
            "margin_mcc_delta": margin_mcc,
        },
        "verdict": {
            "delta_verdict": pp_result.verdict_mcc,
            "verdict_description": S.VERDICTS.get(pp_result.verdict_mcc, pp_result.verdict_mcc),
            "delta_mcc": pp_result.delta_mcc.to_dict(),
            "delta_auroc": pp_result.delta_auroc.to_dict(),
            "delta_f1": ci_delta_f1.to_dict(),
            "delta_accuracy": ci_delta_acc.to_dict(),
        },
        "standalone_performance": {
            "gate": gate_metrics,
            "llm_valid_only": llm_valid_metrics,
            "llm_fallback": llm_fallback_metrics,
        },
        "repair_harm_matrix": rh_matrix,
        "net_repair": {
            "repair_total": r_total,
            "harm_total": h_total,
            "net_repair": net_repair,
            "repair_rate_gate_mistakes": float(r_total / max(1, (h_gate != y).sum())),
            "harm_rate_gate_correct": float(h_total / max(1, (h_gate == y).sum())),
        },
        "reference_experts": ref_experts,
        "oracle_ceiling": oracle_metrics,
        "matched_meta_model": {
            "tau_pre": pp_result.tau_pre,
            "tau_post": pp_result.tau_post,
            "metrics_pre": pp_result.metrics_pre,
            "metrics_post": pp_result.metrics_post,
            "evaluation_split": "oof_cross_validation",
            "threshold_origin": "oof_cross_validation",
        },
        "mcnemar_tests": mcnemar_summary,
        "selective_routing_curves": routing_results,
    }

    report_json_path = output_dir / f"diagnostic_report_{dataset}.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(sanitize_for_json(report_dict), f, ensure_ascii=False, indent=2)
    print(f"[*] Đã xuất báo cáo JSON: {report_json_path}")

    report_md_path = output_dir / f"diagnostic_summary_{dataset}.md"
    md_content = render_markdown_summary(report_dict)
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[*] Đã xuất tóm tắt Markdown: {report_md_path}")

    return report_dict, report_json_path, report_md_path


def run_offline_diagnostic(
    gate_csv_path: Optional[Path] = None,
    llm_path: Optional[Path] = None,
    xpre_path: Optional[Path] = None,
    dataset: str = "devign",
    tau: float = 0.5,
    output_dir: Path = Path("runs/step0"),
    seed: int = 42,
    n_boot: int = 1000,
    n_folds: int = 5,
    margin_mcc: float = 0.02,
    gate_val_path: Optional[Path] = None,
    gate_test_path: Optional[Path] = None,
    llm_val_path: Optional[Path] = None,
    llm_test_path: Optional[Path] = None,
    xpre_val_path: Optional[Path] = None,
    xpre_test_path: Optional[Path] = None,
) -> Tuple[Dict[str, Any], Path, Path]:
    """Hàm giao diện chính, tự động điều phối giữa chuẩn 2-Split và Single-Split Fallback."""
    if gate_val_path and gate_test_path:
        if not llm_val_path or not llm_test_path:
            raise ValueError("Chế độ 2-Split yêu cầu nạp đủ cả --llm-val và --llm-test!")
        return run_offline_diagnostic_2split(
            gate_val_path=gate_val_path,
            gate_test_path=gate_test_path,
            llm_val_path=llm_val_path,
            llm_test_path=llm_test_path,
            xpre_val_path=xpre_val_path,
            xpre_test_path=xpre_test_path,
            dataset=dataset,
            tau=tau,
            output_dir=output_dir,
            seed=seed,
            n_boot=n_boot,
            n_folds=n_folds,
            margin_mcc=margin_mcc,
        )
    elif gate_csv_path and llm_path:
        return run_offline_diagnostic_single_split(
            gate_csv_path=gate_csv_path,
            llm_path=llm_path,
            xpre_path=xpre_path,
            dataset=dataset,
            tau=tau,
            output_dir=output_dir,
            seed=seed,
            n_boot=n_boot,
            n_folds=n_folds,
            margin_mcc=margin_mcc,
        )
    else:
        raise ValueError(
            "Cần truyền bộ tham số chuẩn 2-Split (--gate-val, --gate-test, --llm-val, --llm-test) "
            "hoặc bộ tham số Single-Split (--gate-csv, --llm-predictions)!"
        )


def render_markdown_summary(d: Dict[str, Any]) -> str:
    """Sinh báo cáo tóm tắt Markdown theo đúng chuẩn Đề cương nghiên cứu để nộp Thầy."""
    meta = d["metadata"]
    vrd = d["verdict"]
    g_m = d["standalone_performance"]["gate"]
    l_m = d["standalone_performance"]["llm_fallback"]
    rh = d["repair_harm_matrix"]
    net_rh = d["net_repair"]
    ref = d["reference_experts"]
    ora = d["oracle_ceiling"]
    meta_m = d["matched_meta_model"]
    mcn = d["mcnemar_tests"]
    pos_rate = float(d["standalone_performance"].get("llm_valid_only", {}).get("positive_rate", 0.5) or 0.5)
    mode = meta.get("evaluation_mode", "single_split")

    def f_fmt(v: Any, digits: int = 4) -> str:
        if v is None:
            return "N/A"
        try:
            return f"{float(v):.{digits}f}"
        except (ValueError, TypeError):
            return str(v)

    def p_fmt(v: Any) -> str:
        if v is None:
            return "N/A"
        try:
            fv = float(v)
            if fv < 0.001:
                return "< 0.001"
            return f"{fv:.4f}"
        except (ValueError, TypeError):
            return str(v)

    v_code = vrd["delta_verdict"]
    v_badge = {
        "benefit": "🟢 **BENEFIT (CÓ BỔ SUNG THỰC SỰ ≥ δ)**",
        "no_meaningful_benefit": "🟡 **NO MEANINGFUL BENEFIT (KHÔNG ĐẠT NGƯỠNG HIỆU ỨNG δ)**",
        "harm": "🔴 **HARM (BẤT LỢI / GÂY HỎNG HƠN ĐƠN LẺ)**",
        "inconclusive": "⚪ **INCONCLUSIVE (CHƯA ĐỦ BẰNG CHỨNG THỐNG KÊ)**",
    }.get(v_code, v_code)

    mode_badge = (
        "🟢 **Chuẩn 2-Split Độc lập (Methodology Standard)** — Fit meta-model & chọn ngưỡng trên Validation; Đánh giá trên Test độc lập."
        if mode == "2_split"
        else "⚠️ **Single-Split Fallback** — Đánh giá OOF CV trên một split duy nhất (Dữ liệu đánh giá trùng tập fit)."
    )

    lines = [
        f"# BÁO CÁO CHẨN ĐOÁN OFFLINE BƯỚC 0 — ĐỀ TÀI GRACE",
        f"**Bộ dữ liệu**: `{meta['dataset'].upper()}` | **Quy chuẩn**: {mode_badge} | **Tài nguyên**: Offline (0 GPU)",
        "",
        "---",
        "",
        "## 1. Tóm tắt Kết luận Chẩn đoán (Executive Summary)",
        "",
        f"- **Đánh giá Thống kê ($\\delta$-Verdict)**: {v_badge}",
        f"- **Giải thích chi tiết**: {vrd['verdict_description']}",
        f"- **Tổng số mẫu kiểm thử**: **{meta['n_samples']}** (Lỗ hổng: {meta['n_vulnerable']} [{meta['vulnerability_rate']*100:.1f}%], An toàn: {meta['n_safe']})",
    ]

    if mode == "2_split":
        lines.append(f"- **Phân bổ mẫu**: Validation Split = **{meta.get('n_samples_val', 'N/A')}** mẫu | Test Split = **{meta.get('n_samples_test', 'N/A')}** mẫu")

    lines.extend([
        f"- **Tính hợp lệ phản hồi LLM**: {meta['n_valid_llm']} hợp lệ ({meta['n_valid_llm']/meta['n_samples']*100:.1f}%), {meta['n_invalid_llm']} lỗi format (được fallback đối xứng về Gate)",
        f"- **Chênh lệch $\\Delta$MCC ghép cặp**: **{f_fmt(vrd['delta_mcc']['delta'])}** (95% CI: [{f_fmt(vrd['delta_mcc']['lo'])}, {f_fmt(vrd['delta_mcc']['hi'])}])",
        f"- **Chênh lệch $\\Delta$F1 ghép cặp**: **{f_fmt(vrd['delta_f1']['delta'])}** (95% CI: [{f_fmt(vrd['delta_f1']['lo'])}, {f_fmt(vrd['delta_f1']['hi'])}])",
        f"- **Chênh lệch $\\Delta$AUROC**: **{f_fmt(vrd['delta_auroc']['delta'])}** (95% CI: [{f_fmt(vrd['delta_auroc']['lo'])}, {f_fmt(vrd['delta_auroc']['hi'])}])",
        "",
        "---",
        "",
        "## 2. Ma trận Sửa - Hỏng theo Nhãn Thực tế (Repair / Harm Matrix)",
        "",
        "> **Ý nghĩa**: Định lượng trực tiếp số lượng ca LLM Expert cứu chữa được lỗi của CodeT5 Gate ($R_y$) đối chiếu với số lượng ca LLM làm hỏng quyết định đúng ban đầu của Gate ($H_y$).",
        "",
        "| Phân nhóm Nhãn | Tổng số mẫu ($N$) | Ca Sửa ($R_y$) | Ca Hỏng ($H_y$) | Cả hai cùng Đúng | Cả hai cùng Sai | Hiệu quả Sửa Ròng ($R - H$) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        f"| **Safe ($y=0$)** | {rh['y=0']['n']} | {rh['y=0']['repair']} | {rh['y=0']['harm']} | {rh['y=0']['both_right']} | {rh['y=0']['both_wrong']} | **{rh['y=0']['repair'] - rh['y=0']['harm']}** |",
        f"| **Vulnerable ($y=1$)** | {rh['y=1']['n']} | {rh['y=1']['repair']} | {rh['y=1']['harm']} | {rh['y=1']['both_right']} | {rh['y=1']['both_wrong']} | **{rh['y=1']['repair'] - rh['y=1']['harm']}** |",
        f"| **Toàn bộ (Total)** | **{rh['total']['n']}** | **{rh['total']['repair']}** | **{rh['total']['harm']}** | **{rh['total']['both_right']}** | **{rh['total']['both_wrong']}** | **{net_rh['net_repair']}** |",
        "",
        f"- **Tỷ lệ sửa lỗi của Gate**: Đạt **{net_rh['repair_rate_gate_mistakes']*100:.2f}%** ({net_rh['repair_total']} / {rh['total']['repair'] + rh['total']['both_wrong']} ca Gate đoán sai).",
        f"- **Tỷ lệ làm hỏng quyết định đúng**: Ở mức **{net_rh['harm_rate_gate_correct']*100:.2f}%** ({net_rh['harm_total']} / {rh['total']['harm'] + rh['total']['both_right']} ca Gate đoán đúng).",
        "",
        "---",
        "",
        "## 3. Đối chứng với 3 Chuyên gia Tham chiếu (Reference Experts)",
        "",
        "> **Nguyên lý kiểm định của Thầy**: Một chuyên gia đoán ngẫu nhiên (lật đồng xu) cũng có thể 'sửa' được một lượng lớn lỗi của Gate do may rủi. LLM chỉ được coi là có tri thức khi số ca sửa ròng vượt trội rõ rệt mốc Random.",
        "",
        "| Chuyên gia / Mô hình | Số ca Sửa ($R$) | Số ca Hỏng ($H$) | Sửa Ròng ($R - H$) | Trần Oracle Accuracy |",
        "| :--- | :---: | :---: | :---: | :---: |",
        f"| **LLM Expert (Đề xuất)** | **{net_rh['repair_total']}** | **{net_rh['harm_total']}** | **{net_rh['net_repair']}** | **{f_fmt(ora['accuracy'])}** |",
    ])

    rand_key = next((k for k in ref if k.startswith("RANDOM")), None)
    if rand_key:
        r_info = ref[rand_key]
        r_net = r_info["repair_mean"] - r_info["harm_mean"]
        lines.append(
            f"| Random Expert (rate={pos_rate:.2f}) | {f_fmt(r_info['repair_mean'], 1)} [{f_fmt(r_info['repair_lo'], 1)}, {f_fmt(r_info['repair_hi'], 1)}] | {f_fmt(r_info['harm_mean'], 1)} [{f_fmt(r_info['harm_lo'], 1)}, {f_fmt(r_info['harm_hi'], 1)}] | {f_fmt(r_net, 1)} | {f_fmt(r_info['oracle_accuracy_mean'])} |"
        )
    if "ALL-0" in ref:
        a0 = ref["ALL-0"]
        lines.append(f"| Constant-0 (Luôn đoán An toàn) | {a0['repair']} | {a0['harm']} | {a0['repair'] - a0['harm']} | {f_fmt(a0['oracle_accuracy'])} |")
    if "ALL-1" in ref:
        a1 = ref["ALL-1"]
        lines.append(f"| Constant-1 (Luôn đoán Lỗ hổng) | {a1['repair']} | {a1['harm']} | {a1['repair'] - a1['harm']} | {f_fmt(a1['oracle_accuracy'])} |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Trần Lý thuyết Chẩn đoán (Oracle Ceiling Analysis)",
        "",
        "> **Định nghĩa**: Bộ chọn Oracle lý tưởng nếu biết trước nhãn thật để chọn bên đúng giữa Gate và LLM. Đây là giới hạn trên tuyệt đối không thể vượt qua của bất kỳ bộ kết hợp nào.",
        "",
        "| Cấu hình Đánh giá | Accuracy | F1-Score | MCC | Balanced Accuracy |",
        "| :--- | :---: | :---: | :---: | :---: |",
        f"| **CodeT5 Gate Standalone** (tau={meta['tau_gate']}) | {f_fmt(g_m.get('accuracy'))} | {f_fmt(g_m.get('f1'))} | {f_fmt(g_m.get('mcc'))} | {f_fmt(g_m.get('balanced_accuracy'))} |",
        f"| **LLM Standalone** (Fallback) | {f_fmt(l_m.get('accuracy'))} | {f_fmt(l_m.get('f1'))} | {f_fmt(l_m.get('mcc'))} | {f_fmt(l_m.get('balanced_accuracy'))} |",
        f"| **Trần Lý thuyết Oracle** | **{f_fmt(ora['accuracy'])}** | **{f_fmt(ora['f1'])}** | **{f_fmt(ora['mcc'])}** | **{f_fmt(ora['balanced_accuracy'])}** |",
        f"| *Dư địa tối đa tiềm năng (Oracle - Gate)* | *+{f_fmt(ora['accuracy'] - (g_m.get('accuracy') or 0))}* | *+{f_fmt(ora['f1'] - (g_m.get('f1') or 0))}* | *+{f_fmt(ora['mcc'] - (g_m.get('mcc') or 0))}* | *+{f_fmt(ora['balanced_accuracy'] - (g_m.get('balanced_accuracy') or 0))}* |",
        "",
        "---",
        "",
        "## 5. Mô hình Đối chứng Ghép cặp (Matched Meta-Model: $P_{pre}$ vs $P_{post}$)",
        "",
        f"> **Thiết kế kiểm định**: Cùng số fold ({meta['n_folds']}), cùng scaler, chỉ khác duy nhất 4 đặc trưng bổ sung từ LLM ($s, \\text{{valid}}, s \\times p, s - p$).",
    ])

    if mode == "2_split":
        lines.append(f"> **Quy chuẩn 2-Split**: Ngưỡng tối ưu $\\tau_{{pre}}^* = {f_fmt(meta_m['tau_pre'], 2)}$, $\\tau_{{post}}^* = {f_fmt(meta_m['tau_post'], 2)}$ được xác định hoàn toàn từ tập Validation và khóa chặt khi đánh giá tập Test.")

    lines.extend([
        "",
        "| Chỉ số Đánh giá | $P_{pre}$ (Gate + Đặc trưng nền) | $P_{post}$ (Thêm đặc trưng LLM) | Chênh lệch $\\Delta$ | 95% Bootstrap CI |",
        "| :--- | :---: | :---: | :---: | :---: |",
        f"| **MCC** | {f_fmt(meta_m['metrics_pre'].get('mcc'))} | {f_fmt(meta_m['metrics_post'].get('mcc'))} | **{f_fmt(vrd['delta_mcc']['delta'])}** | [{f_fmt(vrd['delta_mcc']['lo'])}, {f_fmt(vrd['delta_mcc']['hi'])}] |",
        f"| **F1-Score** | {f_fmt(meta_m['metrics_pre'].get('f1'))} | {f_fmt(meta_m['metrics_post'].get('f1'))} | **{f_fmt(vrd['delta_f1']['delta'])}** | [{f_fmt(vrd['delta_f1']['lo'])}, {f_fmt(vrd['delta_f1']['hi'])}] |",
        f"| **Accuracy** | {f_fmt(meta_m['metrics_pre'].get('accuracy'))} | {f_fmt(meta_m['metrics_post'].get('accuracy'))} | **{f_fmt(vrd['delta_accuracy']['delta'])}** | [{f_fmt(vrd['delta_accuracy']['lo'])}, {f_fmt(vrd['delta_accuracy']['hi'])}] |",
        f"| **Balanced Accuracy** | {f_fmt(meta_m['metrics_pre'].get('balanced_accuracy'))} | {f_fmt(meta_m['metrics_post'].get('balanced_accuracy'))} | {f_fmt((meta_m['metrics_post'].get('balanced_accuracy') or 0) - (meta_m['metrics_pre'].get('balanced_accuracy') or 0))} | — |",
        f"| **AUROC** | {f_fmt(meta_m['metrics_pre'].get('auroc'))} | {f_fmt(meta_m['metrics_post'].get('auroc'))} | **{f_fmt(vrd['delta_auroc']['delta'])}** | [{f_fmt(vrd['delta_auroc']['lo'])}, {f_fmt(vrd['delta_auroc']['hi'])}] |",
        f"| *Ngưỡng tối ưu $\\tau^*$* | *{f_fmt(meta_m['tau_pre'], 2)}* | *{f_fmt(meta_m['tau_post'], 2)}* | — | — |",
        "",
        "---",
        "",
        "## 6. Kiểm định McNemar & Hiệu chỉnh Holm (Family-wise Significance)",
        "",
        "| Cặp Mô hình So sánh | Số ca $A$ đúng / $B$ sai ($b$) | Số ca $A$ sai / $B$ đúng ($c$) | $p$-value (Raw) | $p$-value (Holm) | Ý nghĩa ($\\alpha=0.05$) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ])

    for pair_name, m_info in mcn.items():
        sig_str = "✅ Có ý nghĩa" if m_info["significant_at_05"] else "❌ Chưa có ý nghĩa"
        lines.append(
            f"| `{pair_name}` | {m_info['b (A đúng, B sai)']} | {m_info['c (A sai, B đúng)']} | {p_fmt(m_info['p_value_raw'])} | {p_fmt(m_info['p_value_holm'])} | {sig_str} |"
        )

    routing_rows = d.get("selective_routing_curves", [])
    if routing_rows:
        lines.extend([
            "",
            "---",
            "",
            "## 7. Phân tích Định tuyến theo Ngân sách Gọi LLM (Selective Routing Curves — RQ5b)",
            "",
            "> **Ý nghĩa**: Đánh giá hiệu năng đạt được khi chỉ gửi một tỷ lệ nhỏ ($q$) các hàm cần kiểm thử sang LLM qua 4 chính sách: `confidence` (gần biên), `benefit` (học máy Ridge), `oracle` (trần lý tưởng), và `random` (đối chứng ngẫu nhiên).",
            "",
            "| Chính sách (Policy) | Tỷ lệ gọi ($q$) | Số truy vấn | MCC | F1-Score | Balanced Accuracy | Số ca Sửa ($R$) | Số ca Hỏng ($H$) |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])
        for r in routing_rows:
            pol = r.get("policy", "")
            q_val = f"{r.get('q', 0.0)*100:.0f}%"
            queries = r.get("queries", "")
            mcc_v = f_fmt(r.get("mcc"))
            f1_v = f_fmt(r.get("f1"))
            ba_v = f_fmt(r.get("balanced_accuracy"))
            rep = r.get("repair", "—")
            hrm = r.get("harm", "—")
            lines.append(f"| `{pol}` | {q_val} | {queries} | {mcc_v} | {f1_v} | {ba_v} | {rep} | {hrm} |")

    lines.extend([
        "",
        "---",
        "",
        "## 8. Khuyến nghị Kỹ thuật cho Bước Tiếp theo",
        "",
        "1. **Bàn giao Dữ liệu**: Khi có kết quả chính thức từ CodeT5 và LLM, hãy chạy pipeline 2-Split với `--gate-val`, `--gate-test`, `--llm-val`, `--llm-test` để khóa ngưỡng tối ưu trên Validation và đánh giá trung thực trên Test.",
        "2. **Khóa Ngưỡng**: Giữ nguyên $\\tau = 0.5$ (hoặc $\\tau_{\\text{val}}$ cố định) cho toàn bộ so sánh, không thực hiện fine-tune lại trên tập Test nhằm tuân thủ quy chuẩn nghiên cứu.",
        "3. **Tích hợp Monorepo**: Sẵn sàng đón nhận bộ trích xuất CPG và đặc trưng 34 chiều vào thư mục `src/gate/` sau khi hoàn tất Bước 0.",
        "",
        "> *Báo cáo này được tự động kết xuất từ module `grace_diag` theo chuẩn đề tài nghiên cứu khoa học.*",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Thực thi Bước 0: Phân tích chẩn đoán Offline (Offline Diagnostic Runner)"
    )
    # Tham số chuẩn 2-Split
    parser.add_argument("--gate-val", type=Path, default=None, help="Đường dẫn file Gate CSV tập Validation")
    parser.add_argument("--gate-test", type=Path, default=None, help="Đường dẫn file Gate CSV tập Test")
    parser.add_argument("--llm-val", type=Path, default=None, help="Đường dẫn file dự đoán LLM tập Validation")
    parser.add_argument("--llm-test", type=Path, default=None, help="Đường dẫn file dự đoán LLM tập Test")
    parser.add_argument("--xpre-val", type=Path, default=None, help="Đường dẫn file đặc trưng nền NPZ tập Validation")
    parser.add_argument("--xpre-test", type=Path, default=None, help="Đường dẫn file đặc trưng nền NPZ tập Test")

    # Tham số tương thích ngược Single-Split
    parser.add_argument("--gate-csv", type=Path, default=None, help="[Fallback] Đường dẫn file Gate CSV (chế độ single-split)")
    parser.add_argument("--llm-predictions", type=Path, default=None, help="[Fallback] Đường dẫn file dự đoán LLM (chế độ single-split)")
    parser.add_argument("--xpre-npz", type=Path, default=None, help="[Fallback] Đường dẫn file đặc trưng nền NPZ (chế độ single-split)")

    # Tham số chung
    parser.add_argument("--dataset", type=str, default="devign", choices=["devign", "reveal"], help="Tên dataset")
    parser.add_argument("--tau", type=float, default=0.5, help="Ngưỡng phân loại của Gate (mặc định 0.5)")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/step0"), help="Thư mục xuất báo cáo")
    parser.add_argument("--seed", type=int, default=42, help="Random seed tái lập kết quả")
    parser.add_argument("--n-boot", type=int, default=1000, help="Số lượt Paired Bootstrap CI")
    parser.add_argument("--n-folds", type=int, default=5, help="Số fold cross-validation")
    parser.add_argument("--margin-mcc", type=float, default=0.02, help="Biên delta tối thiểu để kết luận có lợi ích")

    args = parser.parse_args()

    # Kiểm tra cờ tham số
    if args.gate_val and args.gate_test:
        if not args.llm_val or not args.llm_test:
            parser.error("Khi chạy chuẩn 2-Split (--gate-val, --gate-test), bắt buộc phải truyền cả --llm-val và --llm-test!")
        run_offline_diagnostic_2split(
            gate_val_path=args.gate_val,
            gate_test_path=args.gate_test,
            llm_val_path=args.llm_val,
            llm_test_path=args.llm_test,
            xpre_val_path=args.xpre_val,
            xpre_test_path=args.xpre_test,
            dataset=args.dataset,
            tau=args.tau,
            output_dir=args.output_dir,
            seed=args.seed,
            n_boot=args.n_boot,
            n_folds=args.n_folds,
            margin_mcc=args.margin_mcc,
        )
    elif args.gate_csv:
        if not args.llm_predictions:
            parser.error("Khi chạy chế độ Single-Split (--gate-csv), bắt buộc phải truyền --llm-predictions!")
        run_offline_diagnostic_single_split(
            gate_csv_path=args.gate_csv,
            llm_path=args.llm_predictions,
            xpre_path=args.xpre_npz,
            dataset=args.dataset,
            tau=args.tau,
            output_dir=args.output_dir,
            seed=args.seed,
            n_boot=args.n_boot,
            n_folds=args.n_folds,
            margin_mcc=args.margin_mcc,
        )
    else:
        parser.error(
            "Cần truyền bộ tham số chuẩn 2-Split (--gate-val, --gate-test, --llm-val, --llm-test) "
            "hoặc bộ tham số Single-Split (--gate-csv, --llm-predictions)!"
        )


if __name__ == "__main__":
    main()
