"""
Security Signature Diagnostic Tool (STEP 6 trong Immediate Action Plan)

Nhiệm vụ:
1. Thống kê tỷ lệ rỗng (empty signature) trên tập mẫu:
   - % empty sink
   - % empty sanitizer
   - % empty vulnerability clues
   - % all memory flags false
2. Đo độ tương đồng SecSim trên các cặp ngẫu nhiên (Random Pairs SecSim):
   - Rút ngẫu nhiên N cặp target - demo từ train pool.
   - Tính mean, median, standard deviation, và phân bố SecSim.
   - Trả lời câu hỏi: SecSim có bị lạm phát (inflated) do hai tập rỗng Jaccard=1.0 và memory_ops trùng khớp mặc định hay không?
3. Kiểm thử 4 synthetic unit cases (Case A, B, C, D) theo thiết kế mục 6.3 Action Plan.
"""

import sys
import io
import math
import random
import statistics
from pathlib import Path
from typing import List, Dict, Any, Tuple

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from security_signature.extractor import extract_security_signature
from security_signature.similarity import compute_security_signature_similarity
from data_loader import generate_mock_dataset, standardize_sample


def test_synthetic_unit_cases():
    """Kiểm tra 4 ca code tổng hợp để thấy rõ extractor phân biệt được gì và chưa phân biệt được gì."""
    print("\n" + "=" * 75)
    print("  STEP 6.3: KIỂM THỬ 4 CA TỔNG HỢP SYNTHETIC UNIT CASES")
    print("=" * 75)

    case_a = "void copy(char *dst, char *src, int len) { if (len <= dst_size) { memcpy(dst, src, len); } }"
    case_b = "void copy(char *dst, char *src, int len) { if (retry > 0) { memcpy(dst, src, len); } }"
    case_c = "void copy(char *dst, char *src, int len) { memcpy(dst, src, len); if (len <= dst_size) { return; } }"
    case_d = "void handle(char *ptr, char *other) { if (other != NULL) { use(ptr); } }"

    sig_a = extract_security_signature(case_a)
    sig_b = extract_security_signature(case_b)
    sig_c = extract_security_signature(case_c)
    sig_d = extract_security_signature(case_d)

    print("[*] Case A (Correct Guard - len <= dst_size trước memcpy):")
    print(f"    - Sanitizers: {sig_a.sanitizer_types} | Clues: {sig_a.vulnerability_clues}")
    
    print("[*] Case B (Irrelevant Comparison - retry > 0 trước memcpy):")
    print(f"    - Sanitizers: {sig_b.sanitizer_types} | Clues: {sig_b.vulnerability_clues}")

    print("[*] Case C (Guard AFTER Sink - memcpy rồi mới if):")
    print(f"    - Sanitizers: {sig_c.sanitizer_types} | Clues: {sig_c.vulnerability_clues}")

    print("[*] Case D (Wrong Variable Null Check - other != NULL trước use(ptr)):")
    print(f"    - Sanitizers: {sig_d.sanitizer_types} | Clues: {sig_d.vulnerability_clues}")

    # So sánh độ tương đồng giữa Case A và Case B
    sim_ab, sub_ab = compute_security_signature_similarity(sig_a, sig_b)
    print(f"\n[!] SecSim(Case A, Case B) = {sim_ab} (Sub-scores: {sub_ab})")
    print("    -> Nhận định: Cả Case A và Case B đều có bounds_check vì regex chỉ tìm '<=' và '>',")
    print("       chưa phân tích data-flow liên kết giữa biến 'len' và tham số 'memcpy'.")


def analyze_dataset_signatures(samples: List[Dict[str, Any]], num_pairs: int = 500) -> Dict[str, Any]:
    """Phân tích phân phối chữ ký an ninh và đo SecSim cặp ngẫu nhiên."""
    total = len(samples)
    if total == 0:
        return {}

    signatures = []
    empty_sinks = 0
    empty_sanitizers = 0
    empty_clues = 0
    all_mem_false = 0

    for s in samples:
        code = s.get("func", "")
        nodes = s.get("nodes", [])
        edges = s.get("edges", [])
        sig = extract_security_signature(code, nodes, edges)
        signatures.append(sig)

        if not sig.sinks:
            empty_sinks += 1
        if not sig.sanitizer_types:
            empty_sanitizers += 1
        if not sig.vulnerability_clues:
            empty_clues += 1
        
        m = sig.memory_ops
        if not (m.has_pointer_deref or m.has_array_indexing or m.has_dynamic_alloc or m.has_explicit_free or m.has_pointer_arithmetic):
            all_mem_false += 1

    rate_empty_sinks = empty_sinks / float(total)
    rate_empty_sans = empty_sanitizers / float(total)
    rate_empty_clues = empty_clues / float(total)
    rate_all_mem_false = all_mem_false / float(total)

    # Đo độ tương đồng SecSim trên các cặp ngẫu nhiên
    random_scores = []
    random.seed(42)
    n_trials = min(num_pairs, total * (total - 1) // 2) if total > 1 else 0
    for _ in range(n_trials):
        i, j = random.sample(range(total), 2)
        score, _ = compute_security_signature_similarity(signatures[i], signatures[j])
        random_scores.append(score)

    mean_secsim = statistics.mean(random_scores) if random_scores else 0.0
    median_secsim = statistics.median(random_scores) if random_scores else 0.0
    stdev_secsim = statistics.stdev(random_scores) if len(random_scores) > 1 else 0.0

    # Phân bố tần suất theo khoảng [0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0]
    hist = {"[0.0, 0.2)": 0, "[0.2, 0.4)": 0, "[0.4, 0.6)": 0, "[0.6, 0.8)": 0, "[0.8, 1.0]": 0}
    for sc in random_scores:
        if sc < 0.2:
            hist["[0.0, 0.2)"] += 1
        elif sc < 0.4:
            hist["[0.2, 0.4)"] += 1
        elif sc < 0.6:
            hist["[0.4, 0.6)"] += 1
        elif sc < 0.8:
            hist["[0.6, 0.8)"] += 1
        else:
            hist["[0.8, 1.0]"] += 1

    return {
        "total_samples": total,
        "empty_sink_rate": round(rate_empty_sinks, 4),
        "empty_sanitizer_rate": round(rate_empty_sans, 4),
        "empty_clue_rate": round(rate_empty_clues, 4),
        "all_memory_flags_false_rate": round(rate_all_mem_false, 4),
        "random_pairs_mean_secsim": round(mean_secsim, 4),
        "random_pairs_median_secsim": round(median_secsim, 4),
        "random_pairs_stdev_secsim": round(stdev_secsim, 4),
        "distribution_histogram": hist
    }


def main():
    test_synthetic_unit_cases()

    print("\n" + "=" * 75)
    print("  STEP 6.1 & 6.2: THỐNG KÊ EMPTY SIGNATURE & RANDOM PAIR SECSIM")
    print("=" * 75)
    print("[*] Đang chạy kiểm toán trên tập mẫu chuẩn hóa (50 mẫu mock demo)...")
    mock_data = generate_mock_dataset(num_samples=50)
    samples = [standardize_sample(s, idx=i) for i, s in enumerate(mock_data)]
    
    stats = analyze_dataset_signatures(samples, num_pairs=300)
    print(f"[*] Tổng số mẫu kiểm toán: {stats['total_samples']}")
    print(f"    - Tỷ lệ Empty Sinks:           {stats['empty_sink_rate']:.2%}")
    print(f"    - Tỷ lệ Empty Sanitizers:      {stats['empty_sanitizer_rate']:.2%}")
    print(f"    - Tỷ lệ Empty Clues:           {stats['empty_clue_rate']:.2%}")
    print(f"    - Tỷ lệ All Memory Flags False: {stats['all_memory_flags_false_rate']:.2%}")
    print(f"\n[*] Điểm tương đồng SecSim trên cặp ngẫu nhiên (Random Pairs Baseline):")
    print(f"    - Mean SecSim:   {stats['random_pairs_mean_secsim']}")
    print(f"    - Median SecSim: {stats['random_pairs_median_secsim']}")
    print(f"    - Stdev SecSim:  {stats['random_pairs_stdev_secsim']}")
    print(f"    - Phân bố: {stats['distribution_histogram']}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
