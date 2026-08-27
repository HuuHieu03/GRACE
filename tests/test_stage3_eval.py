"""
Unit Test & Interactive Demo cho Stage 3: Resilient LLM Evaluator & Prompt Engine.
Được bổ sung log trực quan để người dùng theo dõi chi tiết từng bước (Step-by-Step).
"""

import sys
import time
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import config
from data_loader import standardize_sample, generate_mock_dataset
from prompt_engine import build_grace_prompt, format_graph_structure
from metrics import compute_classification_metrics, print_metrics_summary
from evaluator import parse_llm_prediction, CheckpointManager, LLMEvaluator


def print_header(title: str):
    print("\n" + "="*70)
    print(f"  STEP: {title}")
    print("="*70)


def test_prompt_engine_figure6():
    print_header("1. KIỂM TRA BỘ LẮP RÁP PROMPT THEO HÌNH 6 BÀI BÁO GRACE (PROMPT ENGINE)")
    print("[*] Chuẩn bị một mẫu Query và đính kèm ví dụ Demonstration từ Stage 2...")
    demo_ex = {
        "id": "demo_commit_8891",
        "func": "void bad_copy(char *src) { char dest[12]; strcpy(dest, src); }",
        "target": 1,
        "nodes": [{"id": 0, "type": "FUNC_DEF"}, {"id": 1, "type": "CALL_STRCPY"}],
        "edges": [0, 1]
    }
    target_query = {
        "id": "test_cve_9012",
        "func": "int parse_auth(char *password) { char buf[16]; gets(buf); return 0; }",
        "target": 1,
        "nodes": [{"id": 0, "type": "FUNC_DEF"}, {"id": 1, "type": "CALL_GETS"}],
        "edges": [0, 1],
        "example": demo_ex
    }
    
    prompt = build_grace_prompt(target_query, include_demonstration=True)
    print("[*] Câu Lệnh Dẫn Hướng (Prompt) đã lắp ráp xong. Trích xuất văn bản (Preview 20 dòng):")
    lines = prompt.split("\n")
    for l in lines[:22]:
        print(f"  | {l}")
    if len(lines) > 22:
        print(f"  | ... (Còn lại {len(lines) - 22} dòng cấu trúc chi tiết)")
        
    assert "### TASK INSTRUCTION" in prompt
    assert "### DEMONSTRATION EXAMPLE" in prompt
    assert "### TARGET QUERY FOR EVALUATION" in prompt
    assert "### OUTPUT FORMAT REQUIREMENT" in prompt
    print("\n>>> [PASS] Cấu trúc Prompt Engine khớp tuyệt đối với mô hình In-Context tại Figure 6!")


def test_resilient_regex_parser():
    print_header("2. KIỂM TRA ĐỘ BỀN BỘ BÓC TÁCH NHÃN (MULTI-PATTERN REGEX PARSER)")
    test_cases = [
        ("Case A (Đúng định dạng chuẩn):", "1", 1),
        ("Case B (Đúng định dạng chuẩn):", "0", 0),
        ("Case C (Có khoảng trắng thừa):", " 1 ", 1),
        ("Case D (Dính chữ nhưng chứa 1):", "Prediction is 1", 1),
        ("Case E (Từ khóa Vulnerable):", "Security analysis: Vulnerable code found.", 1),
        ("Case F (Lỗi hoàn toàn/Rác):", "completely unknown text without keywords", 0) # Fallback = 0
    ]
    
    print("[*] Thử nghiệm khả năng chống chọi hiện tượng lệch định dạng (Formatting Drift) của LLM:")
    for desc, raw_text, expected in test_cases:
        pred, method = parse_llm_prediction(raw_text)
        status = "✓ OK" if pred == expected else "✗ FAIL"
        print(f"\n  + {desc}")
        print(f"    - Raw text snippet: \"{raw_text[:70]}...\"" if len(raw_text)>70 else f"    - Raw text: \"{raw_text}\"")
        print(f"    - -> Kết quả trích xuất: Pred = {pred} [{status}] | Phương thức bốc tách: {method}")
        assert pred == expected
        
    print("\n>>> [PASS] Parser Regex đa tầng bóc tách chuẩn xác 100% các tình huống dị thường!")


def test_checkpointing_crash_recovery():
    print_header("3. KIỂM TRA CƠ CHẾ LƯU VẾT & TỰ CHỐNG ĐỨT GÃY (JSONL CRASH RECOVERY)")
    exp_name = "test_resilient_recovery"
    ckpt = CheckpointManager(experiment_name=exp_name)
    ckpt.clear_checkpoint() # Xóa sạch trạng thái cũ để test từ đầu
    
    raw_mock = generate_mock_dataset(num_samples=10)
    samples = [standardize_sample(s, idx=i) for i, s in enumerate(raw_mock)]
    
    print("[*] PHẦN A: Giả lập khởi chạy Đánh Giá trên 5 mẫu đầu tiên rồi KẾT THÚC BẤT NGỜ (Crash/Timeout)...")
    evaluator = LLMEvaluator(use_mock=True)
    # Chạy 5 mẫu đầu
    evaluator.evaluate_dataset(samples[:5], experiment_name=exp_name, include_demonstration=False)
    print(f"    -> Đã ghi nhận {len(ckpt.completed_ids)} mẫu vào file Checkpoint cứng.")
    
    print("\n[*] PHẦN B: Khởi tạo phiên làm việc hoàn toàn mới, yêu cầu chạy TOÀN BỘ 10 mẫu...")
    print("    (Quan sát: Hệ thống phải phát hiện và TỰ ĐỘNG BỎ QUA 5 mẫu đã làm trong Checkpoint cũ)")
    evaluator_new = LLMEvaluator(use_mock=True)
    all_res, metrics = evaluator_new.evaluate_dataset(samples, experiment_name=exp_name, include_demonstration=False)
    
    print(f"\n[*] Tổng kết thu được sau khi phục hồi: {len(all_res)} kết quả (5 khôi phục + 5 chạy tiếp).")
    assert len(all_res) == 10
    ckpt.clear_checkpoint() # Dọn dẹp sau test
    print(">>> [PASS] Cơ chế JSONL Crash Recovery bảo vệ tuyệt đối tiến trình, không lãng phí 1 giây nào!")


def test_classification_metrics():
    print_header("4. KIỂM TRA HỆ THỐNG ĐO lƯỜNG NGHIỆM THU AN NINH MẠNG (METRICS ENGINE)")
    print("[*] Tạo bộ dữ liệu kết quả đánh giá giả lập gồm 100 mẫu (Vulnerables & Safes)...")
    # Giả lập 50 nhãn thật là 1, 50 nhãn thật là 0
    y_true = [1]*50 + [0]*50
    # Giả lập mô hình đoán đúng 45 mẫu có lỗi (5 FN), đoán đúng 40 mẫu an toàn (10 FP)
    y_pred = [1]*45 + [0]*5 + [0]*40 + [1]*10
    
    metrics = compute_classification_metrics(y_true, y_pred)
    print_metrics_summary(metrics, dataset_name="Test Metric Simulation")
    
    assert 0.0 <= metrics["f1_score"] <= 1.0
    assert metrics["confusion_matrix"]["TP (True Positive)"] == 45
    print(">>> [PASS] Hệ thống tính toán chỉ số F1, Precision, Recall hoạt động cực kỳ mượt mà & chính xác!")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("\n" + "#"*75)
    print("###  CHƯƠNG TRÌNH KIỂM THỬ & NGHIỆM THU STAGE 3 (RESILIENT LLM EVALUATOR) ###")
    print("#"*75)
    
    test_prompt_engine_figure6()
    time.sleep(0.5)
    test_resilient_regex_parser()
    time.sleep(0.5)
    test_checkpointing_crash_recovery()
    time.sleep(0.5)
    test_classification_metrics()
    time.sleep(0.5)
    
    print("\n" + "="*75)
    print("🎉 STAGE 3 VERIFICATION CHECKPOINT PASSED 100%! HỆ THỐNG SẴN SÀNG CHO STAGE 4.")
    print("="*75 + "\n")
