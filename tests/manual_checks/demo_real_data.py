"""
Demo Nạp Dữ Liệu THẬT (Real Dataset) từ Hugging Face
Script này tải dữ liệu thực tế từ 'DetectVul/devign' trên Hugging Face để cho thấy pipeline xử lý code thật.
"""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from data_loader import load_hf_dataset

print("\n" + "="*70)
print("  DEMO NẠP DỮ LIỆU THỰC TẾ TỪ HUGGING FACE (DetectVul/devign)")
print("="*70)

print("\n[*] Đang kết nối tới Hugging Face Hub để tải dataset 'DetectVul/devign'...")
print("[*] Áp dụng Stratified Slicing trích xuất 1% dữ liệu thực tế...")

# Tải 1% dữ liệu thật từ Hugging Face
real_samples = load_hf_dataset(
    dataset_name="DetectVul/devign", 
    split="test", 
    sample_ratio=0.01, 
    seed=42
)

print(f"\n[✓] THÀNH CÔNG! Đã tải và chuẩn hóa {len(real_samples)} hàm C/C++ thực tế từ dự án FFmpeg/QEMU.\n")

print("-" * 70)
print("HIỂN THỊ MỘT SỐ MẪU HÀM C/C++ THỰC TẾ TRONG DATASET:")
print("-" * 70)

for idx, sample in enumerate(real_samples[:3]):
    status_str = "[!] CÓ LỖ HỔNG (Vulnerable - 1)" if sample["target"] == 1 else "[✓] AN TOÀN (Safe - 0)"
    print(f"\n--- [Mẫu Real #{idx+1}] ID: {sample['id']} | Trạng thái: {status_str} ---")
    lines = sample["func"].split("\n")
    print("Mã nguồn C/C++ (Trích 6 dòng đầu):")
    for line in lines[:6]:
        print(f"  {line}")
    if len(lines) > 6:
        print(f"  ... (Còn {len(lines)-6} dòng mã nguồn)")

print("\n" + "="*70)
print("DEMO HOÀN TẤT: Dữ liệu thật đã sẵn sàng đưa vào mô hình LLM!")
print("="*70 + "\n")
