"""
Test Script: Chạy thử mẫu thực tế trên dữ liệu Devign đã trích xuất đồ thị Joern
với mô hình LLM API (gpt-oss-20b và gemma-4-26B-A4B-it)
"""

import json
import time
import os
import sys
import io
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from prompt_engine import build_grace_prompt
from evaluator import LLMEvaluator, parse_llm_prediction

def main():
    dataset_path = "data/processed/devign_test_processed.json"
    print(f"[*] Nạp dữ liệu từ: {dataset_path}")
    
    with open(dataset_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)
    
    # Lấy 6 mẫu (3 an toàn 0, 3 có lỗ hổng 1)
    vuln_samples = [s for s in full_data if s.get("target") == 1][:3]
    safe_samples = [s for s in full_data if s.get("target") == 0][:3]
    test_samples = vuln_samples + safe_samples
    
    vuln_demo = {
        "func": "void process_packet(char *data, int len) {\n    char buffer[256];\n    strcpy(buffer, data); // No bounds check\n}",
        "target": 1,
        "nodes": [{"id": 0, "type": "AST_FUNC_DEF"}, {"id": 1, "type": "CALL_STRCPY"}],
        "edges": [{"source": 0, "target": 1, "type": "CDG"}]
    }
    safe_demo = {
        "func": "int validate_and_copy(char *src, int len) {\n    char dest[128];\n    if (len >= 128) return -1;\n    memcpy(dest, src, len);\n    return 0;\n}",
        "target": 0,
        "nodes": [{"id": 0, "type": "AST_FUNC_DEF"}, {"id": 1, "type": "IF_CHECK"}],
        "edges": [{"source": 0, "target": 1, "type": "CDG"}]
    }

    model_name = "Llama-3.3-70B-Instruct"
    print(f"\n[*] Khởi tạo LLM Evaluator với model: '{model_name}' (max_tokens=256)...")
    evaluator = LLMEvaluator(model_name=model_name, use_mock=False)
    
    print("\n" + "="*80)
    print(f"  KẾT QUẢ CHẠY THỰC TẾ TRÊN 6 MẪU DEVIGN (CPG GRAPH + IN-CONTEXT DEMO)")
    print("="*80)
    
    correct = 0
    total_time = 0
    
    for idx, s in enumerate(test_samples):
        s["example"] = vuln_demo if idx < 3 else safe_demo
        prompt = build_grace_prompt(s, include_demonstration=True)
        
        t0 = time.time()
        raw_response = evaluator.generate_response(prompt)
        elapsed = time.time() - t0
        total_time += elapsed
        
        pred_label, parse_method = parse_llm_prediction(raw_response)
        ground_truth = s.get("target", 0)
        is_correct = (ground_truth == pred_label)
        if is_correct:
            correct += 1
            
        status_icon = "✅ CHÍNH XÁC" if is_correct else "❌ LỆCH"
        target_name = "LỖ HỔNG (1)" if ground_truth == 1 else "AN TOÀN (0)"
        pred_name = "LỖ HỔNG (1)" if pred_label == 1 else "AN TOÀN (0)"
        
        func_preview = s.get("func", "").strip().split("\n")[0][:60]
        
        print(f"\n--- Mẫu #{idx+1} [ID: {s.get('id', idx)}] ---")
        print(f"  Mã nguồn: {func_preview}...")
        print(f"  Nodes AST/CPG: {len(s.get('nodes', []))} nút | Edges: {len(s.get('edges', []))} cạnh")
        print(f"  Ground Truth: {target_name} | AI Dự đoán: {pred_name} -> {status_icon}")
        print(f"  Phản hồi thô từ LLM: {repr(raw_response)}")
        print(f"  Thời gian phản hồi: {elapsed:.2f}s")
        
    print("\n" + "="*80)
    acc = (correct / len(test_samples)) * 100
    avg_latency = total_time / len(test_samples)
    print(f"📊 TỔNG KẾT: Độ chính xác = {correct}/{len(test_samples)} ({acc:.1f}%) | Latency trung bình = {avg_latency:.2f}s/mẫu")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
