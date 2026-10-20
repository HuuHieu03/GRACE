"""
GRACE Joern & Validation Dataset Packager for Kaggle Linux Cloud
Đóng gói công cụ Joern 0.2.5 và toàn bộ file .c + metadata của tập Validation:
- Devign validation: 2,732 mẫu
- ReVeal validation: 2,273 mẫu
Chuẩn bị thư mục và metadata để đẩy lên Kaggle Dataset (huuhieu3333/grace-joern-validation).
"""

import os
import io
import sys
import json
import shutil
import zipfile
import argparse
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).parent.parent.resolve()

JOERN_DIR = REPO_ROOT / "data" / "preproceed" / "joern" / "joern" / "joern"
DEVIGN_VAL_DIR = REPO_ROOT / "data" / "raw_c_files" / "devign" / "validation"
DEVIGN_VAL_META = REPO_ROOT / "data" / "raw_c_files" / "devign" / "validation_metadata.json"
REVEAL_VAL_DIR = REPO_ROOT / "data" / "raw_c_files" / "reveal" / "validation"
REVEAL_VAL_META = REPO_ROOT / "data" / "raw_c_files" / "reveal" / "validation_metadata.json"

DEFAULT_STAGING_DIR = REPO_ROOT / "data" / "kaggle_joern_validation_pkg"
DEFAULT_ZIP_PATH = REPO_ROOT / "data" / "grace_joern_validation_dataset.zip"


def create_dataset_metadata(target_dir: Path, dataset_slug: str = "huuhieu3333/grace-joern-validation"):
    """Tạo file dataset-metadata.json cho Kaggle Dataset."""
    metadata = {
        "title": "GRACE Joern 0.2.5 and Validation C Datasets",
        "id": dataset_slug,
        "licenses": [
            {
                "name": "CC0-1.0"
            }
        ],
        "description": "Joern 0.2.5 binaries and C source files for Devign & ReVeal validation splits."
    }
    meta_path = target_dir / "dataset-metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[✓] Đã tạo dataset-metadata.json tại: {meta_path}")


def package_dataset(
    output_dir: Path = DEFAULT_STAGING_DIR,
    zip_path: Path = DEFAULT_ZIP_PATH,
    create_zip: bool = True
) -> Path:
    """Đóng gói Joern và tập Validation vào thư mục chuẩn bị và file zip."""
    print("=" * 75)
    print("  GRACE KAGGLE DATASET PACKAGING: JOERN 0.2.5 + DEVIGN & REVEAL VALIDATION")
    print("=" * 75)

    if not JOERN_DIR.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục Joern tại: {JOERN_DIR}")
    if not DEVIGN_VAL_DIR.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục Devign validation tại: {DEVIGN_VAL_DIR}")
    if not REVEAL_VAL_DIR.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục ReVeal validation tại: {REVEAL_VAL_DIR}")

    if output_dir.exists():
        print(f"[*] Dọn dẹp thư mục staging cũ: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Sao chép Joern (loại bỏ file không cần thiết như docs, gremtest để tiết kiệm dung lượng)
    target_joern = output_dir / "joern"
    target_joern.mkdir(parents=True, exist_ok=True)
    print(f"[*] Đang sao chép công cụ Joern 0.2.5 sang: {target_joern}...")
    
    ignore_patterns = shutil.ignore_patterns(".git*", ".gradle*", "*.log", "docs", "gremtest", "eclipse")
    for item in os.listdir(JOERN_DIR):
        src_item = JOERN_DIR / item
        dst_item = target_joern / item
        if src_item.is_dir():
            if item not in [".git", ".gradle", "docs", "gremtest", "eclipse"]:
                shutil.copytree(src_item, dst_item, ignore=ignore_patterns, dirs_exist_ok=True)
        else:
            shutil.copy2(src_item, dst_item)

    # Đảm bảo quyền thực thi và line endings LF cho joern-parse
    joern_parse_script = target_joern / "joern-parse"
    if joern_parse_script.exists():
        try:
            with open(joern_parse_script, "rb") as f_jp:
                jp_bytes = f_jp.read().replace(b"\r\n", b"\n")
            with open(joern_parse_script, "wb") as f_jp:
                f_jp.write(jp_bytes)
            os.chmod(joern_parse_script, 0o755)
        except Exception:
            pass

    # 2. Sao chép Devign Validation (2,732 files .c + metadata)
    target_devign = output_dir / "devign_validation"
    target_devign.mkdir(parents=True, exist_ok=True)
    print(f"[*] Đang sao chép các file .c của Devign Validation...")
    devign_count = 0
    for f in os.listdir(DEVIGN_VAL_DIR):
        if f.endswith(".c"):
            shutil.copy2(DEVIGN_VAL_DIR / f, target_devign / f)
            devign_count += 1
    print(f"[✓] Đã sao chép {devign_count} file .c của Devign.")
    if DEVIGN_VAL_META.exists():
        # Chuẩn hóa c_file_path sang dấu gạch chéo xuôi '/' để tương thích tuyệt đối môi trường Linux
        with open(DEVIGN_VAL_META, "r", encoding="utf-8") as f_meta:
            dev_meta = json.load(f_meta)
        for item in dev_meta:
            if "c_file_path" in item:
                item["c_file_path"] = item["c_file_path"].replace("\\", "/")
        with open(target_devign / "validation_metadata.json", "w", encoding="utf-8") as f_meta:
            json.dump(dev_meta, f_meta, indent=2, ensure_ascii=False)
        print(f"[✓] Đã sao chép và chuẩn hóa Devign validation_metadata.json.")

    # 3. Sao chép ReVeal Validation (2,273 files .c + metadata)
    target_reveal = output_dir / "reveal_validation"
    target_reveal.mkdir(parents=True, exist_ok=True)
    print(f"[*] Đang sao chép các file .c của ReVeal Validation...")
    reveal_count = 0
    for f in os.listdir(REVEAL_VAL_DIR):
        if f.endswith(".c"):
            shutil.copy2(REVEAL_VAL_DIR / f, target_reveal / f)
            reveal_count += 1
    print(f"[✓] Đã sao chép {reveal_count} file .c của ReVeal.")
    if REVEAL_VAL_META.exists():
        with open(REVEAL_VAL_META, "r", encoding="utf-8") as f_meta:
            rev_meta = json.load(f_meta)
        for item in rev_meta:
            if "c_file_path" in item:
                item["c_file_path"] = item["c_file_path"].replace("\\", "/")
        with open(target_reveal / "validation_metadata.json", "w", encoding="utf-8") as f_meta:
            json.dump(rev_meta, f_meta, indent=2, ensure_ascii=False)
        print(f"[✓] Đã sao chép và chuẩn hóa ReVeal validation_metadata.json.")

    # 4. Tạo metadata cho Kaggle Dataset
    create_dataset_metadata(output_dir)

    # 5. Nén file zip nếu được yêu cầu
    if create_zip:
        print(f"\n[*] Đang nén toàn bộ gói thành file zip: {zip_path}...")
        if zip_path.exists():
            zip_path.unlink()
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(output_dir)
                    zipf.write(full_p, rel_p.as_posix())
        zip_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"[✓] File zip đã tạo thành công: {zip_path} ({zip_mb:.2f} MB)")

    print("\n" + "=" * 75)
    print(f"🎉 HOÀN TẤT ĐÓNG GÓI CHO KAGGLE!")
    print(f"    - Thư mục Staging: {output_dir}")
    print(f"    - Devign files: {devign_count} | ReVeal files: {reveal_count}")
    print(f"    - Lệnh upload lên Kaggle:")
    print(f"      kaggle datasets create -p \"{output_dir}\"")
    print("=" * 75)
    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Joern and validation datasets for Kaggle")
    parser.add_argument("--output_dir", type=str, default=str(DEFAULT_STAGING_DIR), help="Staging output directory")
    parser.add_argument("--zip_path", type=str, default=str(DEFAULT_ZIP_PATH), help="Path to create zip file")
    parser.add_argument("--no_zip", action="store_true", help="Do not create zip archive")
    args = parser.parse_args()

    out_d = Path(args.output_dir).resolve()
    zip_p = Path(args.zip_path).resolve()
    package_dataset(output_dir=out_d, zip_path=zip_p, create_zip=not args.no_zip)
