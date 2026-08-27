"""
Script tự động đóng gói dự án GRACE chuẩn sạch để tải lên Kaggle Dataset.
Tự động loại bỏ các thư mục rác/thô: .git, .env, raw_c_files (50.000 file .c), __pycache__,...
Chỉ giữ lại mã nguồn thực thi và thư mục data/processed/ (đã trích xuất xong đồ thị Joern).
"""

import os
import zipfile
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_ZIP = BASE_DIR / "grace_kaggle_clean_package.zip"

INCLUDE_FILES = [
    "config.py",
    "data_loader.py",
    "retrieval_engine.py",
    "retrieval_security_engine.py",
    "contrastive_selector.py",
    "prompt_engine.py",
    "evaluator.py",
    "metrics.py",
    "run_pipeline.py",
    "requirements.txt",
    "build_kaggle_contrastive_notebook.py",
    "GRACE_Kaggle_Reproduce.ipynb",
    "GRACE_Stage5_Contrastive_Retrieval.ipynb"
]

INCLUDE_DIRS = [
    "security_signature",
    "tests"
]

EXCLUDE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "raw_c_files",
    "preproceed",
    "joern",
    ".system_generated"
}

def create_kaggle_package():
    print("="*75)
    print("  ĐÓNG GÓI BỘ MÃ NGUỒN CHUẨN SẠCH CHO KAGGLE DATASET")
    print("="*75)
    print(f"[*] Thư mục gốc: {BASE_DIR}")
    print(f"[*] File zip đầu ra: {OUTPUT_ZIP.name}\n")
    
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
        
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        # 1. Đóng gói các file mã nguồn cốt lõi
        for fname in INCLUDE_FILES:
            fpath = BASE_DIR / fname
            if fpath.exists():
                arcname = f"GRACE/{fname}"
                zipf.write(fpath, arcname)
                print(f"  [+] Đã thêm mã nguồn: {fname}")

        # 2. Đóng gói các thư mục mã nguồn (security_signature, tests)
        for dname in INCLUDE_DIRS:
            dpath = BASE_DIR / dname
            if dpath.exists():
                print(f"\n[*] Đang thêm thư mục mã nguồn ({dname}/)...")
                for root, _, files in os.walk(dpath):
                    for file in files:
                        if not file.endswith(".pyc") and "__pycache__" not in root:
                            full_p = Path(root) / file
                            rel_p = full_p.relative_to(BASE_DIR)
                            arcname = f"GRACE/{rel_p.as_posix()}"
                            zipf.write(full_p, arcname)
                            print(f"  [+] Đã thêm: {rel_p}")
                
        # 3. Đóng gói thư mục data/processed/ (chứa đồ thị CPG đã trích xuất)
        processed_dir = BASE_DIR / "data" / "processed"
        if processed_dir.exists():
            print(f"\n[*] Đang thêm thư mục dữ liệu đồ thị CPG (data/processed/)...")
            for fpath in processed_dir.glob("*.json"):
                arcname = f"GRACE/data/processed/{fpath.name}"
                file_mb = fpath.stat().st_size / (1024 * 1024)
                print(f"  [+] Đã nén: {fpath.name} ({file_mb:.1f} MB)")
                zipf.write(fpath, arcname)
                
    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print("\n" + "="*75)
    print(f"🎉 HOÀN TẤT ĐÓNG GÓI! File zip sẵn sàng: {OUTPUT_ZIP} ({zip_size_mb:.1f} MB)")
    print("="*75 + "\n")

if __name__ == "__main__":
    create_kaggle_package()
