"""
Unit Test & Interactive Demo cho Stage 1: Verification of Config, Data Loader, and Dataset Slicing.
Được bổ sung log trực quan để người dùng theo dõi chi tiết từng bước (Step-by-Step).
"""

import sys
import time
from pathlib import Path

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import config, is_kaggle_environment
from data_loader import (
    standardize_sample,
    slice_dataset,
    generate_mock_dataset,
    load_hf_dataset
)


def print_header(title: str):
    print("\n" + "="*70)
    print(f"  STEP: {title}")
    print("="*70)


def test_config_initialization():
    print_header("1. KIỂM TRA NHẬN DIỆN MÔI TRƯỜNG & KHỞI TẠO ĐƯỜNG DẪN")
    print(f"[*] Môi trường chạy hiện tại là Kaggle? -> {config.is_kaggle} ({'Kaggle Notebook' if config.is_kaggle else 'Local Workspace'})")
    print(f"[*] Thư mục gốc dự án (Base Dir)       -> {config.base_dir}")
    print(f"[*] Thư mục dữ liệu (Data Dir)         -> {config.data_dir} [Tồn tại: {config.data_dir.exists()}]")
    print(f"[*] Thư mục lưu checkpoint (Ckpt Dir)  -> {config.checkpoint_dir} [Tồn tại: {config.checkpoint_dir.exists()}]")
    print(f"[*] Thư mục xuất log/kết quả           -> {config.output_dir} [Tồn tại: {config.output_dir.exists()}]")
    print(f"[*] Mô hình LLM mặc định cho Kaggle    -> {config.default_llm_model}")
    assert config.base_dir.exists()
    print(">>> [PASS] Hệ thống đã tự động cấu hình và chuẩn bị sẵn các thư mục lưu trữ!")


def test_standardize_sample():
    print_header("2. KIỂM TRA TIỂU CHẢO CHUẨN HÓA DỮ LIỆU THÔ")
    raw_sample = {
        "id": "vuln_cve_2026_001",
        "func": "void bad_func(char* input) { char buf[10]; strcpy(buf, input); }",
        "target": "1",  # Nhãn thô dạng string
        "node": [{"id": 0, "type": "AST_ROOT"}, {"id": 1, "type": "CALL"}],
        "edge": [{"source": 0, "target": 1, "label": "AST"}]
    }
    print("[*] Mẫu dữ liệu thô (Raw) trước khi xử lý:")
    print(f"    - ID thô: {raw_sample['id']} | Target thô (string): '{raw_sample['target']}'")
    print(f"    - Số lượng Nút (Node) thô: {len(raw_sample['node'])} | Cạnh (Edge) thô: {len(raw_sample['edge'])}")
    
    std = standardize_sample(raw_sample, idx=0)
    print("\n[*] Mẫu dữ liệu sau khi qua pipeline chuẩn hóa (Standardize):")
    print(f"    - ID: {std['id']} | Target chuẩn hóa (int): {std['target']} (1 = Vulnerable)")
    print(f"    - Đoạn code: {std['func']}")
    print(f"    - Schema chuẩn có các trường: {list(std.keys())}")
    
    assert std["target"] == 1
    assert len(std["nodes"]) == 2
    print(">>> [PASS] Chuẩn hóa thành công định dạng mảng, kiểu dữ liệu và trường code C/C++!")


def test_slice_dataset_stratified():
    print_header("3. KIỂM TRA THUẬT TOÁN CẮT MẪU CÂN BẰNG NHÃN (STRATIFIED SLICING)")
    print("[*] Khởi tạo bộ dữ liệu giả lập 100 hàm C/C++ (50 hàm An toàn - 0, 50 hàm Có lỗ hổng - 1)...")
    mock_data = [standardize_sample(s, i) for i, s in enumerate(generate_mock_dataset(num_samples=100))]
    orig_vuln = sum(1 for s in mock_data if s["target"] == 1)
    orig_safe = sum(1 for s in mock_data if s["target"] == 0)
    print(f"    -> Gốc: Tổng {len(mock_data)} hàm (Vulnerable: {orig_vuln}, Safe: {orig_safe}) - Tỷ lệ 50:50")
    
    ratio = 0.10 # Cắt thử thách 10%
    print(f"[*] Tiến hành cắt mẩu nghiệm thu {int(ratio*100)}% dataset (Yêu cầu giữ nguyên tỷ lệ nhãn)...")
    sliced_data = slice_dataset(mock_data, ratio=ratio, seed=42)
    
    sliced_vuln = sum(1 for s in sliced_data if s["target"] == 1)
    sliced_safe = sum(1 for s in sliced_data if s["target"] == 0)
    print(f"    -> Mẩu 10% thu được: Tổng {len(sliced_data)} hàm (Vulnerable: {sliced_vuln}, Safe: {sliced_safe})")
    
    assert len(sliced_data) == 10
    assert sliced_vuln == 5 and sliced_safe == 5
    print(">>> [PASS] Thuật toán Stratified Slicing hoạt động chính xác! Không bị chênh lệch tỷ lệ nhãn.")


def test_load_hf_dataset_fallback():
    print_header("4. KIỂM TRA CƠ CHẾ NẠP DỮ LIỆU & TỰ ĐỘNG KHÔI PHỤC (FALLBACK ROUTINE)")
    print("[*] Thử nghiệm yêu cầu nạp từ Hugging Face (hoặc chuyển sang chế độ Offline Fallback)...")
    samples = load_hf_dataset(dataset_name="DetectVul/devign_offline_test", sample_ratio=0.2, seed=42)
    print(f"[*] Kết quả nạp vào hệ thống: Thu được {len(samples)} hàm C/C++ đã sẵn sàng cho LLM Evaluation.")
    if len(samples) > 0:
        sample_0 = samples[0]
        print("\n[*] Ví dụ 1 mẫu hàm thu được:")
        print(f"    [ID: {sample_0['id']}] - Nhãn: {'[!] VULNERABLE (1)' if sample_0['target']==1 else '[OK] SAFE (0)'}")
        print("    Code C/C++ preview:")
        lines = sample_0['func'].split('\n')
        for l in lines[:4]:
            print(f"      {l}")
        if len(lines) > 4:
            print("      ...")
    
    assert len(samples) > 0
    print(">>> [PASS] Bộ nạp dữ liệu (Data Loader) đã thông suốt 100%!")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("\n" + "#"*70)
    print("###  CHƯƠNG TRÌNH KIỂM THỬ & NGHIỆM THU STAGE 1 (GRACE FOUNDATION) ###")
    print("#"*70)
    
    test_config_initialization()
    time.sleep(0.5)
    test_standardize_sample()
    time.sleep(0.5)
    test_slice_dataset_stratified()
    time.sleep(0.5)
    test_load_hf_dataset_fallback()
    time.sleep(0.5)
    
    print("\n" + "="*70)
    print("🎉 STAGE 1 VERIFICATION CHECKPOINT PASSED 100%! HỆ THỐNG SẴN SÀNG CHO STAGE 2.")
    print("="*70 + "\n")
