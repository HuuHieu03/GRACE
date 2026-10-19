"""
GRACE Label-Flip Demonstration Sensitivity Test (Stage 2 - Step 2)
Tuân thủ Hợp đồng Đánh giá: evaluation_contract.yaml

Mục tiêu khoa học:
Đo lường định lượng xem LLM có thực sự hiểu ngữ nghĩa an ninh trong ví dụ mẫu (In-Context Demonstration)
hay chỉ đơn thuần sao chép nhãn bề mặt (Label bias / superficial pattern matching).

Thiết kế đối chứng 3 nhánh:
1. Condition A (Original Label chuẩn):
   Target Code + Graph + Top-1 Demo Code + Nhãn Chuẩn (y_demo)
2. Condition B (Flipped Label):
   Target Code + Graph + Top-1 Demo Code + Nhãn Đảo (1 - y_demo)
3. Condition C (Repeated Original):
   Cùng Prompt với Condition A, chạy lần 2 để đo Natural Model Variance

Đo lường định lượng:
- Flip Rate = N(Pred_A != Pred_B) / N_valid
- Natural Variance Rate = N(Pred_A != Pred_C) / N_valid
- Net Label Sensitivity = Flip Rate - Natural Variance Rate
- Phân rã: Correct -> Wrong (bị nhãn giả lừa) vs Wrong -> Correct (may mắn đoán đúng)
- Trivial Baselines & Full Metrics cho từng nhánh theo evaluation_contract.yaml
"""

import sys
import io
import os
import json
import time
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Thêm thư mục gốc và src vào sys.path
repo_root = Path(__file__).parent.parent.resolve()
src_dir = repo_root / "src"
for p in [str(repo_root), str(src_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import config
from prompt_engine import build_grace_prompt, format_graph_structure
from evaluator import parse_llm_prediction, LLMEvaluator
from metrics import compute_classification_metrics
from retrieval_engine import DemonstrationRetriever, CodeT5Embedder


class MockLabelFlipLLM:
    """
    Mock LLM cho chạy thử nghiệm nhanh offline / CPU.
    Mô phỏng mô hình ngôn ngữ có độ nhạy vừa phải với nhãn của ví dụ mẫu (In-Context Label Sensitivity):
    - Khi demo bị đảo nhãn, có một xác suất nhỏ (ví dụ ~15-20%) mô hình bị thiên lệch theo nhãn demo.
    - Có độ dao động tự nhiên nhỏ (natural variance ~3-5%) khi chạy cùng prompt nhiều lần.
    """
    def __init__(self, seed: int = 42, label_sensitivity_prob: float = 0.20, natural_variance_prob: float = 0.05):
        self.rng = random.Random(seed)
        self.label_sensitivity_prob = label_sensitivity_prob
        self.natural_variance_prob = natural_variance_prob

    def generate_response(self, prompt: str, run_iteration: int = 1) -> str:
        # Nhận diện đặc trưng an ninh từ code mục tiêu
        lower = prompt.lower()
        is_risky = any(k in lower for k in ["strcpy", "gets", "sprintf", "buffer", "overflow", "free", "leak", "vulnerab"])
        base_pred = 1 if is_risky else 0

        # Trích xuất nhãn demo từ prompt
        demo_is_vuln = "--- DEMONSTRATION GROUND TRUTH LABEL ---\nLabel: Vulnerable (1)" in prompt
        demo_is_safe = "--- DEMONSTRATION GROUND TRUTH LABEL ---\nLabel: Non-vulnerable (0)" in prompt

        effective_pred = base_pred

        # Mô phỏng ảnh hưởng từ nhãn demo
        if demo_is_vuln and not demo_is_safe:
            # Demo nhãn 1 có xu hướng kéo dự đoán về 1
            if self.rng.random() < self.label_sensitivity_prob:
                effective_pred = 1
        elif demo_is_safe and not demo_is_vuln:
            # Demo nhãn 0 có xu hướng kéo dự đoán về 0
            if self.rng.random() < self.label_sensitivity_prob:
                effective_pred = 0

        # Mô phỏng natural variance giữa các lần gọi lặp lại (iteration 2)
        if run_iteration > 1 and self.rng.random() < self.natural_variance_prob:
            effective_pred = 1 - effective_pred

        return str(effective_pred)


def load_canonical_dev_split(split_file: Path) -> List[Dict[str, Any]]:
    """Nạp danh sách mẫu từ file dev split json."""
    if not split_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file split tại: {split_file}")

    with open(split_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = []
    # Nếu file có sample_details, dùng trực tiếp
    if "sample_details" in data and isinstance(data["sample_details"], list):
        ds_name = data.get("dataset", "devign").lower()
        metadata_cache = None
        for item in data["sample_details"]:
            func_code = str(item.get("code") or item.get("func") or "")
            c_file_path = str(item.get("c_file_path", "")).replace("\\", "/")

            # 1. Nếu code bị trống, đọc từ file .c trên đĩa
            if not func_code and c_file_path:
                c_p = Path(c_file_path)
                if not c_p.is_absolute():
                    c_p = repo_root / c_p
                if c_p.exists():
                    try:
                        with open(c_p, "r", encoding="utf-8", errors="replace") as f_c:
                            func_code = f_c.read().strip()
                    except Exception:
                        pass

            # 2. Nếu vẫn trống, tra cứu từ validation_metadata.json
            if not func_code:
                if metadata_cache is None:
                    metadata_candidates = [
                        repo_root / "data" / "raw_c_files" / ds_name / "validation_metadata.json",
                        repo_root / "data" / "raw_c_files" / ds_name / "valid_metadata.json",
                    ]
                    metadata_cache = {}
                    for m_cand in metadata_candidates:
                        if m_cand.exists() and m_cand.stat().st_size > 10:
                            try:
                                with open(m_cand, "r", encoding="utf-8") as f_m:
                                    m_items = json.load(f_m)
                                for m_item in m_items:
                                    m_id = str(m_item.get("id", m_item.get("hash", "")))
                                    m_cpath = str(m_item.get("c_file_path", "")).replace("\\", "/")
                                    m_fname = Path(m_cpath).name if m_cpath else ""
                                    m_code = m_item.get("func") or m_item.get("functionSource") or m_item.get("code") or ""
                                    if m_id:
                                        metadata_cache[m_id] = m_code
                                    if m_fname:
                                        metadata_cache[m_fname] = m_code
                            except Exception:
                                pass
                            break
                item_id = str(item.get("id", ""))
                item_raw_id = str(item.get("raw_id", ""))
                func_code = metadata_cache.get(item_id) or metadata_cache.get(item_raw_id) or ""

            samples.append({
                "id": str(item.get("id")),
                "raw_id": str(item.get("raw_id", item.get("id"))),
                "target": int(item.get("target", 0)),
                "project": str(item.get("project", "unknown")),
                "c_file_path": c_file_path,
                "func": func_code,
                "nodes": item.get("nodes", []),
                "edges": item.get("edges", []),
            })

        # 3. Fallback nạp mã nguồn từ Hugging Face nếu môi trường chạy không có sẵn raw_c_files
        missing_indices = [idx for idx, s in enumerate(samples) if not s["func"]]
        if missing_indices:
            try:
                from datasets import load_dataset
                hf_name = config.hf_dataset_devign if ds_name == "devign" else (config.hf_dataset_bigvul if ds_name == "bigvul" else ds_name)
                hf_val = load_dataset(hf_name, split="validation")
                for idx in missing_indices:
                    raw_id = samples[idx].get("raw_id")
                    try:
                        int_id = int(raw_id)
                        if int_id < len(hf_val):
                            hf_item = hf_val[int_id]
                            code = hf_item.get("func") or hf_item.get("function") or hf_item.get("code") or ""
                            if code:
                                samples[idx]["func"] = code.strip()
                    except Exception:
                        pass
            except Exception:
                pass
    elif "sample_ids" in data:
        # Nếu chỉ có sample_ids, nạp từ raw_c_files hoặc processed
        ds_name = data.get("dataset", "devign").lower()
        id_set = set(str(sid) for sid in data["sample_ids"])
        
        candidates = [
            repo_root / "data" / "raw_c_files" / ds_name / "validation_metadata.json",
            repo_root / "data" / "raw_c_files" / ds_name / "valid_metadata.json",
            repo_root / "data" / "processed" / f"{ds_name}_test_processed.json",
        ]
        found_data = []
        for cand in candidates:
            if cand.exists():
                with open(cand, "r", encoding="utf-8") as f_cand:
                    found_data = json.load(f_cand)
                break
        
        for idx, item in enumerate(found_data):
            c_path = item.get("c_file_path", "")
            fname = Path(c_path).name if c_path else ""
            raw_id = str(item.get("id", item.get("hash", idx)))
            if fname in id_set or raw_id in id_set or str(idx) in id_set:
                samples.append({
                    "id": fname if fname else raw_id,
                    "raw_id": raw_id,
                    "target": int(item.get("target", item.get("label", 0))),
                    "project": str(item.get("project", "unknown")),
                    "c_file_path": c_path,
                    "func": item.get("func", item.get("functionSource", item.get("code", ""))),
                    "nodes": item.get("node", item.get("nodes", [])),
                    "edges": item.get("edge", item.get("edges", [])),
                })

    return samples


def load_train_retrieval_pool(dataset_name: str, max_train_samples: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Nạp kho ứng viên tìm kiếm (Retrieval Bank) từ tập huấn luyện (Train split).
    Tuân thủ Hợp đồng: keep_full_train_pool_when_running_subset = True.
    """
    ds_clean = dataset_name.lower()
    candidates = [
        repo_root / "data" / "raw_c_files" / ds_clean / "train_metadata.json",
        repo_root / "data" / "processed" / f"{ds_clean}_train_processed.json",
    ]
    raw_list = None
    for p in candidates:
        if p.exists() and p.stat().st_size > 10:
            file_size_mb = p.stat().st_size / (1024 * 1024)
            try:
                if file_size_mb > 500 or (max_train_samples is not None and max_train_samples < 5000):
                    # Đọc luồng nếu quá lớn
                    from data_loader import stream_json_array
                    raw_list = stream_json_array(p, max_items=max_train_samples)
                else:
                    with open(p, "r", encoding="utf-8") as f:
                        raw_list = json.load(f)
            except Exception as e:
                print(f"[!] Lỗi khi nạp file {p}: {e}")
                raw_list = None
            if raw_list:
                break

    if not raw_list:
        try:
            from data_loader import load_hf_dataset
            hf_ds_name = config.hf_dataset_devign if ds_clean == "devign" else (config.hf_dataset_bigvul if ds_clean == "bigvul" else ds_clean)
            print(f"[*] Đang nạp kho Train từ Hugging Face ({hf_ds_name})...")
            raw_list = load_hf_dataset(dataset_name=hf_ds_name, split="train", max_samples=max_train_samples)
        except Exception as e:
            print(f"[!] Không thể nạp tập Train từ Hugging Face: {e}. Sử dụng bộ dữ liệu mẫu giả lập cho Retriever.")
            from data_loader import generate_mock_dataset
            raw_list = generate_mock_dataset(num_samples=max(20, max_train_samples or 50))

    train_pool = []
    for idx, item in enumerate(raw_list):
        code = item.get("func") or item.get("functionSource") or item.get("code") or ""
        t = item.get("target", item.get("label", 0))
        target_int = 1 if (t is True or t == 1 or str(t).lower() in ("1", "true")) else 0
        train_pool.append({
            "id": str(item.get("id", item.get("hash", f"train_{idx}"))),
            "func": str(code),
            "target": target_int,
            "project": str(item.get("project", "unknown")),
            "nodes": item.get("node", item.get("nodes", [])),
            "edges": item.get("edge", item.get("edges", []))
        })
        if max_train_samples and len(train_pool) >= max_train_samples:
            break

    if not train_pool:
        print(f"[!] train_pool vẫn rỗng. Fallback sang mock dataset...")
        from data_loader import generate_mock_dataset
        raw_mock = generate_mock_dataset(num_samples=max(20, max_train_samples or 20))
        for idx, item in enumerate(raw_mock):
            code = item.get("func") or item.get("functionSource") or item.get("code") or ""
            t = item.get("target", item.get("label", 0))
            target_int = 1 if (t is True or t == 1 or str(t).lower() in ("1", "true")) else 0
            train_pool.append({
                "id": str(item.get("id", item.get("hash", f"train_{idx}"))),
                "func": str(code),
                "target": target_int,
                "project": str(item.get("project", "unknown")),
                "nodes": item.get("node", item.get("nodes", [])),
                "edges": item.get("edge", item.get("edges", []))
            })

    return train_pool


def build_condition_prompts(
    target_sample: Dict[str, Any],
    top1_demo: Dict[str, Any]
) -> Tuple[str, str, str, int, int]:
    """
    Xây dựng 3 điều kiện Prompt cho mẫu kiểm tra:
    - Condition A: Original GT demo label (y_demo)
    - Condition B: Flipped demo label (1 - y_demo)
    - Condition C: Repeated Original Prompt (giống hệt Prompt A)
    
    Tuân thủ chính sách cắt ngắn (Truncation Policy) trong evaluation_contract.yaml:
    - target_code <= 3000 chars
    - standard_demo <= 1500 chars
    - graph_nodes <= 25, graph_edges <= 25
    """
    y_demo = int(top1_demo.get("target", 0))
    y_demo_flipped = 1 - y_demo

    # Bản sao cho Condition A (Original)
    demo_a = dict(top1_demo)
    demo_a["target"] = y_demo
    sample_a = dict(target_sample)
    sample_a["example"] = demo_a

    prompt_a = build_grace_prompt(sample_a, include_demonstration=True)

    # Bản sao cho Condition B (Flipped)
    demo_b = dict(top1_demo)
    demo_b["target"] = y_demo_flipped
    sample_b = dict(target_sample)
    sample_b["example"] = demo_b

    prompt_b = build_grace_prompt(sample_b, include_demonstration=True)

    # Condition C giống hệt Prompt A
    prompt_c = prompt_a

    return prompt_a, prompt_b, prompt_c, y_demo, y_demo_flipped


def compute_label_flip_statistics(detailed_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính toán các chỉ số thống kê định lượng về độ nhạy đảo nhãn:
    - flip_rate = N(Pred_A != Pred_B) / N_valid
    - natural_variance = N(Pred_A != Pred_C) / N_valid
    - net_sensitivity = flip_rate - natural_variance
    - Phân rã:
      + correct_to_wrong (bị lừa bởi nhãn đảo)
      + wrong_to_correct (đoán trúng ngẫu nhiên)
      + stayed_correct (ổn định đúng)
      + stayed_wrong (ổn định sai)
    - Trivial baselines
    """
    valid_records = [
        r for r in detailed_records
        if r["pred_a"] is not None and r["pred_b"] is not None and r["pred_c"] is not None
    ]
    total_valid = len(valid_records)
    total_samples = len(detailed_records)

    if total_valid == 0:
        return {"error": "Không có mẫu nào có dự đoán hợp lệ ở cả 3 điều kiện!"}

    flips = 0
    natural_variances = 0

    correct_to_wrong = 0
    wrong_to_correct = 0
    stayed_correct = 0
    stayed_wrong = 0

    # Phân nhóm theo nhãn demo gốc
    vuln_demo_count = 0
    vuln_demo_flips = 0
    safe_demo_count = 0
    safe_demo_flips = 0

    y_true = []
    y_pred_a = []
    y_pred_b = []
    y_pred_c = []

    for r in valid_records:
        gt = r["target"]
        pa = r["pred_a"]
        pb = r["pred_b"]
        pc = r["pred_c"]
        y_demo = r["demo_gt"]

        y_true.append(gt)
        y_pred_a.append(pa)
        y_pred_b.append(pb)
        y_pred_c.append(pc)

        # 1. Flip Rate: Pred_A khác Pred_B
        if pa != pb:
            flips += 1
            if y_demo == 1:
                vuln_demo_flips += 1
            else:
                safe_demo_flips += 1

        # 2. Natural Variance: Pred_A khác Pred_C
        if pa != pc:
            natural_variances += 1

        # 3. Phân rã hành vi
        if pa == gt and pb != gt:
            correct_to_wrong += 1
        elif pa != gt and pb == gt:
            wrong_to_correct += 1
        elif pa == gt and pb == gt:
            stayed_correct += 1
        else:
            stayed_wrong += 1

        if y_demo == 1:
            vuln_demo_count += 1
        else:
            safe_demo_count += 1

    flip_rate = flips / total_valid
    natural_var_rate = natural_variances / total_valid
    net_sensitivity = flip_rate - natural_var_rate

    # Tính metrics phân loại cho từng điều kiện
    metrics_a = compute_classification_metrics(y_true, y_pred_a)
    metrics_b = compute_classification_metrics(y_true, y_pred_b)
    metrics_c = compute_classification_metrics(y_true, y_pred_c)

    # Trivial baselines theo hợp đồng
    all_vuln_preds = [1] * total_valid
    all_safe_preds = [0] * total_valid
    trivial_always_vuln = compute_classification_metrics(y_true, all_vuln_preds)
    trivial_always_safe = compute_classification_metrics(y_true, all_safe_preds)

    return {
        "total_samples": total_samples,
        "valid_samples": total_valid,
        "invalid_count": total_samples - total_valid,
        "invalid_rate": round((total_samples - total_valid) / total_samples, 4) if total_samples > 0 else 0.0,
        "quantitative_findings": {
            "flip_count": flips,
            "flip_rate": round(flip_rate, 4),
            "flip_rate_pct": round(flip_rate * 100, 2),
            "natural_variance_count": natural_variances,
            "natural_variance_rate": round(natural_var_rate, 4),
            "natural_variance_pct": round(natural_var_rate * 100, 2),
            "net_label_sensitivity": round(net_sensitivity, 4),
            "net_label_sensitivity_pct": round(net_sensitivity * 100, 2),
        },
        "behavioral_breakdown": {
            "correct_to_wrong": correct_to_wrong,
            "correct_to_wrong_pct": round(correct_to_wrong / total_valid * 100, 2),
            "wrong_to_correct": wrong_to_correct,
            "wrong_to_correct_pct": round(wrong_to_correct / total_valid * 100, 2),
            "stayed_correct": stayed_correct,
            "stayed_correct_pct": round(stayed_correct / total_valid * 100, 2),
            "stayed_wrong": stayed_wrong,
            "stayed_wrong_pct": round(stayed_wrong / total_valid * 100, 2),
        },
        "demo_label_breakdown": {
            "vuln_demo_count": vuln_demo_count,
            "vuln_demo_flips": vuln_demo_flips,
            "vuln_demo_flip_rate_pct": round((vuln_demo_flips / vuln_demo_count * 100) if vuln_demo_count > 0 else 0.0, 2),
            "safe_demo_count": safe_demo_count,
            "safe_demo_flips": safe_demo_flips,
            "safe_demo_flip_rate_pct": round((safe_demo_flips / safe_demo_count * 100) if safe_demo_count > 0 else 0.0, 2),
        },
        "condition_metrics": {
            "condition_a_original": metrics_a,
            "condition_b_flipped": metrics_b,
            "condition_c_repeated": metrics_c,
        },
        "trivial_baselines": {
            "always_predict_vulnerable": trivial_always_vuln,
            "always_predict_non_vulnerable": trivial_always_safe,
        }
    }


def print_label_flip_report(report: Dict[str, Any]):
    """In bảng báo cáo trực quan cho Thí nghiệm Đảo Nhãn."""
    qf = report["quantitative_findings"]
    bb = report["behavioral_breakdown"]
    db = report["demo_label_breakdown"]
    ma = report["condition_metrics"]["condition_a_original"]
    mb = report["condition_metrics"]["condition_b_flipped"]
    mc = report["condition_metrics"]["condition_c_repeated"]

    print("\n" + "=" * 80)
    print("  BÁO CÁO THÍ NGHIỆM ĐẢO NHÃN VÍ DỤ MẪU (LABEL-FLIP CONTROL TEST - STAGE 2.1)")
    print("  Tuân thủ Hợp đồng: evaluation_contract.yaml")
    print("=" * 80)
    print(f"[*] Quy mô kiểm thử: {report['total_samples']} mẫu | Hợp lệ: {report['valid_samples']} | Lỗi/Invalid: {report['invalid_count']} ({report['invalid_rate']*100:.1f}%)")
    print("-" * 80)
    print(f"[*] KẾT QUẢ ĐO LƯỜNG ĐỊNH LƯỢNG:")
    print(f"    1. Tỷ lệ Đảo Nhãn (Flip Rate):           {qf['flip_count']} / {report['valid_samples']} ({qf['flip_rate_pct']}%)")
    print(f"    2. Dao động Tự Nhiên (Natural Variance): {qf['natural_variance_count']} / {report['valid_samples']} ({qf['natural_variance_pct']}%)")
    print(f"    3. ĐỘ NHẠY NHÃN THỰC CHẤT (Net Sensitivity): {qf['net_label_sensitivity_pct']}% (Flip Rate - Natural Variance)")
    print("-" * 80)
    print(f"[*] PHÂN RÃ HÀNH VI MÔ HÌNH (BEHAVIORAL BREAKDOWN):")
    print(f"    - Bị nhãn giả đánh lừa (Correct -> Wrong): {bb['correct_to_wrong']} mẫu ({bb['correct_to_wrong_pct']}%)")
    print(f"    - May mắn đoán trúng (Wrong -> Correct):   {bb['wrong_to_correct']} mẫu ({bb['wrong_to_correct_pct']}%)")
    print(f"    - Kiên định đúng (Stayed Correct):         {bb['stayed_correct']} mẫu ({bb['stayed_correct_pct']}%)")
    print(f"    - Kiên định sai (Stayed Wrong):             {bb['stayed_wrong']} mẫu ({bb['stayed_wrong_pct']}%)")
    print("-" * 80)
    print(f"[*] PHÂN RÃ THEO LOẠI NHÃN DEMO GỐC:")
    print(f"    - Demo Vulnerable (1 -> 0): {db['vuln_demo_flips']} / {db['vuln_demo_count']} đảo ({db['vuln_demo_flip_rate_pct']}%)")
    print(f"    - Demo Safe (0 -> 1):       {db['safe_demo_flips']} / {db['safe_demo_count']} đảo ({db['safe_demo_flip_rate_pct']}%)")
    print("-" * 80)
    print(f"[*] SO SÁNH HIỆU NĂNG PHÂN LOẠI GIỮA CÁC ĐIỀU KIỆN:")
    print(f"{'Chỉ số':<22} | {'Condition A (Orig)':<18} | {'Condition B (Flip)':<18} | {'Condition C (Repeat)':<18}")
    print("-" * 80)
    for metric_key in ["accuracy", "precision", "recall", "f1_score", "mcc", "balanced_accuracy"]:
        val_a = ma.get(metric_key, "N/A")
        val_b = mb.get(metric_key, "N/A")
        val_c = mc.get(metric_key, "N/A")
        str_a = f"{val_a:.4f}" if isinstance(val_a, (int, float)) else str(val_a)
        str_b = f"{val_b:.4f}" if isinstance(val_b, (int, float)) else str(val_b)
        str_c = f"{val_c:.4f}" if isinstance(val_c, (int, float)) else str(val_c)
        print(f"{metric_key:<22} | {str_a:<18} | {str_b:<18} | {str_c:<18}")
    print("=" * 80 + "\n")


def call_model_with_contract_retry(
    engine: Any,
    prompt: str,
    use_mock: bool = False,
    run_iteration: int = 1,
    max_attempts: int = 5,
    min_backoff_sec: float = 5.0,
    max_backoff_sec: float = 120.0
) -> str:
    """
    Thực hiện gọi suy luận với chính sách Retry và Exponential Backoff tuân thủ evaluation_contract.yaml:
    - max_attempts = 5
    - exponential_backoff = 5s..120s
    - exhausted_request = invalid (trả về chuỗi rỗng để parser đánh dấu is_valid=False, pred=None).
    """
    if use_mock:
        return engine.generate_response(prompt, run_iteration=run_iteration)

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = engine.generate_response(prompt)
            if resp:
                return resp
            # Nếu phản hồi rỗng, chờ rồi thử lại
            time.sleep(min_backoff_sec)
        except Exception as e:
            last_error = e
            if attempt < max_attempts:
                sleep_time = min(min_backoff_sec * (2 ** (attempt - 1)), max_backoff_sec)
                print(f"[!] Lỗi gọi API LLM (lần {attempt}/{max_attempts}): {e}. Chờ {sleep_time:.1f}s trước khi thử lại...")
                time.sleep(sleep_time)
            else:
                print(f"[!] Đã kiệt sức sau {max_attempts} lần thử (Exhausted Request): {last_error}. Trả về invalid theo contract.")

    return ""


def run_experiment(
    dev_split_file: Path,
    dataset_name: str = "devign",
    output_path: Optional[Path] = None,
    max_samples: Optional[int] = None,
    max_train_samples: Optional[int] = None,
    use_mock: bool = False,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    seed: int = 42,
    train_samples: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Thực thi toàn bộ quy trình Thí nghiệm Đảo Nhãn."""
    print(f"\n[*] Bắt đầu Thí nghiệm Đảo Nhãn trên tập: {dev_split_file}")
    
    # 1. Nạp tập Dev sạch
    dev_samples = load_canonical_dev_split(dev_split_file)
    if max_samples is not None and max_samples < len(dev_samples):
        # Lấy subset cân bằng nếu max_samples nhỏ hơn
        dev_samples = dev_samples[:max_samples]
    print(f"[✓] Đã nạp {len(dev_samples)} mẫu mục tiêu từ dev split.")

    # 2. Nạp kho tìm kiếm huấn luyện và xây dựng Retriever
    if train_samples is not None:
        raw_train = list(train_samples)
        if max_train_samples and len(raw_train) > max_train_samples:
            raw_train = raw_train[:max_train_samples]
        train_pool = []
        for idx, item in enumerate(raw_train):
            code = item.get("func") or item.get("functionSource") or item.get("code") or ""
            t = item.get("target", item.get("label", 0))
            target_int = 1 if (t is True or t == 1 or str(t).lower() in ("1", "true")) else 0
            train_pool.append({
                "id": str(item.get("id", item.get("hash", f"train_{idx}"))),
                "func": str(code),
                "code": str(code),
                "target": target_int,
                "project": str(item.get("project", "unknown")),
                "nodes": item.get("node", item.get("nodes", [])),
                "edges": item.get("edge", item.get("edges", []))
            })
    else:
        train_pool = load_train_retrieval_pool(dataset_name, max_train_samples=max_train_samples)

    if not train_pool:
        print("[!] Kho train_pool rỗng. Tự động kích hoạt fallback generate_mock_dataset...")
        from data_loader import generate_mock_dataset
        mock_data = generate_mock_dataset(num_samples=max(20, max_train_samples or 20))
        train_pool = []
        for idx, item in enumerate(mock_data):
            code = item.get("func") or item.get("functionSource") or item.get("code") or ""
            t = item.get("target", item.get("label", 0))
            target_int = 1 if (t is True or t == 1 or str(t).lower() in ("1", "true")) else 0
            train_pool.append({
                "id": str(item.get("id", item.get("hash", f"train_{idx}"))),
                "func": str(code),
                "code": str(code),
                "target": target_int,
                "project": str(item.get("project", "unknown")),
                "nodes": item.get("node", item.get("nodes", [])),
                "edges": item.get("edge", item.get("edges", []))
            })

    print(f"[*] Khởi tạo DemonstrationRetriever với kho {len(train_pool)} mẫu Train...")
    embedder = CodeT5Embedder(use_fallback_default=True)
    retriever = DemonstrationRetriever(embedder=embedder)
    retriever.fit(train_pool)

    # 3. Khởi tạo LLM Engine
    if use_mock:
        print("[*] Khởi tạo Mock Label-Flip LLM Engine (chế độ kiểm thử CPU)...")
        effective_model = model_name or "mock_model"
        effective_provider = "Mock"
        engine = MockLabelFlipLLM(seed=seed)
    else:
        effective_model = model_name or config.vertex_model
        effective_provider = provider or ("Vertex AI" if ("publishers/" in effective_model or "qwen" in effective_model.lower()) else "FPT")
        print(f"[*] Khởi tạo LLMEvaluator với model {effective_model} (Provider: {effective_provider})...")
        engine = LLMEvaluator(model_name=effective_model, provider=effective_provider, use_mock=False)

    detailed_records = []
    print(f"[*] Bắt đầu suy luận 3 điều kiện cho {len(dev_samples)} mẫu...")

    for i, target in enumerate(dev_samples):
        # Bước 1: Trích xuất Top-1 Demo từ Top-50 ứng viên
        retrieval_res = retriever.retrieve(target, top_k=50)
        best_demo = retrieval_res["best_example"]
        if not best_demo:
            # Fallback nếu không tìm thấy
            best_demo = {"id": "mock_demo", "func": "void foo() {}", "target": 0}

        # Bước 2: Tạo Prompt cho 3 điều kiện
        prompt_a, prompt_b, prompt_c, y_demo, y_demo_flipped = build_condition_prompts(target, best_demo)

        # Bước 3: Thực thi 3 điều kiện với chính sách retry & exhausted_request của hợp đồng
        resp_a = call_model_with_contract_retry(engine, prompt_a, use_mock=use_mock, run_iteration=1)
        resp_b = call_model_with_contract_retry(engine, prompt_b, use_mock=use_mock, run_iteration=1)
        resp_c = call_model_with_contract_retry(engine, prompt_c, use_mock=use_mock, run_iteration=2)

        pred_a, desc_a, valid_a = parse_llm_prediction(resp_a)
        pred_b, desc_b, valid_b = parse_llm_prediction(resp_b)
        pred_c, desc_c, valid_c = parse_llm_prediction(resp_c)

        target_gt = target["target"]
        rec = {
            "index": i,
            "target_id": target["id"],
            "target": target_gt,
            "demo_id": best_demo.get("id"),
            "demo_gt": y_demo,
            "demo_flipped": y_demo_flipped,
            "retrieval_score": retrieval_res["best_hybrid_score"],
            "pred_a": pred_a,
            "valid_a": valid_a,
            "raw_resp_a": resp_a,
            "pred_b": pred_b,
            "valid_b": valid_b,
            "raw_resp_b": resp_b,
            "pred_c": pred_c,
            "valid_c": valid_c,
            "raw_resp_c": resp_c,
            "is_flipped": (pred_a != pred_b) if (valid_a and valid_b) else None,
            "is_variance": (pred_a != pred_c) if (valid_a and valid_c) else None,
        }
        detailed_records.append(rec)

    # 4. Thống kê & Tính toán chỉ số
    report_data = compute_label_flip_statistics(detailed_records)
    report_data["experiment_metadata"] = {
        "dataset": dataset_name,
        "dev_split_file": str(dev_split_file),
        "use_mock": use_mock,
        "model_name": effective_model,
        "provider": effective_provider,
        "seed": seed,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    report_data["detailed_samples"] = detailed_records

    print_label_flip_report(report_data)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"[✓] Đã xuất báo cáo chi tiết JSON tại: {output_path}")

    return report_data


def main():
    parser = argparse.ArgumentParser(description="GRACE Stage 2 Label-Flip Sensitivity Test")
    parser.add_argument("--dev_split", type=str, default="data/splits/devign_dev_clean_100_ids.json", help="Đường dẫn file clean dev split IDs")
    parser.add_argument("--dataset", type=str, default="devign", choices=["devign", "reveal"], help="Tên bộ dữ liệu")
    parser.add_argument("--output", type=str, default="output/label_flip_test_report.json", help="Đường dẫn lưu file JSON báo cáo")
    parser.add_argument("--max_samples", type=int, default=None, help="Số lượng mẫu dev cần test (mặc định toàn bộ)")
    parser.add_argument("--max_train_samples", type=int, default=None, help="Giới hạn số mẫu train nạp vào retriever (nếu cần test nhanh)")
    parser.add_argument("--use_mock", action="store_true", help="Chạy chế độ mock offline trên CPU không cần API key")
    parser.add_argument("--model", type=str, default=None, help="Tên mô hình LLM (mặc định lấy theo config.vertex_model)")
    parser.add_argument("--provider", type=str, default=None, help="Provider LLM: 'Vertex AI' hoặc 'FPT'")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (mặc định 42)")
    args = parser.parse_args()

    split_file = Path(args.dev_split)
    output_file = Path(args.output)

    run_experiment(
        dev_split_file=split_file,
        dataset_name=args.dataset,
        output_path=output_file,
        max_samples=args.max_samples,
        max_train_samples=args.max_train_samples,
        use_mock=args.use_mock,
        model_name=args.model,
        provider=args.provider,
        seed=args.seed
    )


if __name__ == "__main__":
    main()
