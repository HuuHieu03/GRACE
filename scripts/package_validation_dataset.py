"""
Package Validation Dataset for Kaggle Deployment
Khao sat cau truc folder 'validation' va dong goi len Kaggle Dataset:
Dataset Slug: huuhieu3333/grace-h2-vertex-validation
"""

import os
import io
import sys
import json
import shutil
import zipfile
import argparse
from pathlib import Path

# Force UTF-8 on Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_VALIDATION_SOURCES = [
    Path(r"D:\tai lieu hoc tap\Đề tài nghiên cứu khoa học\papers source code\SHARE_H2_VERTEX_DEEPSEEK_V41_CONTEXT8192_20261022\validation"),
    Path(r"D:/tai lieu hoc tap/Đề tài nghiên cứu khoa học/papers source code/SHARE_H2_VERTEX_DEEPSEEK_V41_CONTEXT8192_20261022/validation"),
    REPO_ROOT / "validation",
    REPO_ROOT / "data" / "validation",
    Path(r"D:\tai lieu hoc tap\Đề tài nghiên cứu khoa học\papers source code\SHARE_H2_VERTEX_DEEPSEEK_V41_CONTEXT8192_20261022"),
]

DEFAULT_STAGING_DIR = REPO_ROOT / "kaggle_notebooks" / "h2_vertex_validation" / "dataset_staging"
DEFAULT_ZIP_PATH = REPO_ROOT / "kaggle_notebooks" / "h2_vertex_validation" / "validation_data.zip"
DATASET_SLUG = "huuhieu3333/grace-h2-vertex-validation"


def find_validation_source(custom_path: str = None) -> Path:
    """Xac dinh thu muc nguon cua validation dataset."""
    if custom_path:
        p = Path(custom_path).resolve()
        if p.exists() and p.is_dir():
            return p
        raise FileNotFoundError(f"Custom validation path not found: {p}")

    for candidate in DEFAULT_VALIDATION_SOURCES:
        if candidate.exists() and candidate.is_dir():
            return candidate

    return None


def create_dataset_metadata(target_dir: Path, dataset_slug: str = DATASET_SLUG):
    """Tao file dataset-metadata.json cho Kaggle."""
    metadata = {
        "title": "GRACE H2 Vertex Validation Dataset",
        "id": dataset_slug,
        "licenses": [
            {
                "name": "CC0-1.0"
            }
        ],
        "description": "Validation prompts, manifests, runner, and configs for GRACE H2 Vertex AI DeepSeek-V4.1-Flash evaluation."
    }
    meta_path = target_dir / "dataset-metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[✓] Da tao dataset-metadata.json tai: {meta_path}")


def package_validation_dataset(
    source_dir: Path,
    staging_dir: Path = DEFAULT_STAGING_DIR,
    zip_path: Path = DEFAULT_ZIP_PATH,
    create_zip: bool = True
) -> Path:
    """Sao chep va dong goi toan bo tai nguyen validation vao thu muc staging va file zip."""
    print("=" * 75)
    print("  GRACE H2: PACKAGING VALIDATION DATASET FOR KAGGLE")
    print("=" * 75)
    print(f"[*] Thu muc nguon: {source_dir}")
    print(f"[*] Thu muc staging: {staging_dir}")

    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    # 1. Quet va sao chep cac file quan trong tu source_dir
    items = list(source_dir.iterdir())
    print(f"[*] Tim thay {len(items)} muc trong thu muc validation:")
    for item in items:
        rel_name = item.name
        dst = staging_dir / rel_name
        if item.is_dir():
            print(f"  -> Sao chep thu muc: {rel_name}/")
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            print(f"  -> Sao chep file: {rel_name} ({item.stat().st_size / 1024:.1f} KB)")
            shutil.copy2(item, dst)

    # 2. Bo sung cac file ho tro neu co o parent folder (nhu runner.py, request_config.json)
    supplementary = ["runner.py", "request_config.json", "manifest.json"]
    for supp_name in supplementary:
        supp_dst = staging_dir / supp_name
        if not supp_dst.exists():
            supp_src = source_dir.parent / supp_name
            if supp_src.exists():
                print(f"  -> Bo sung tu parent: {supp_name} ({supp_src.stat().st_size / 1024:.1f} KB)")
                shutil.copy2(supp_src, supp_dst)

    # 3. Bo sung evaluation_contract.yaml tu repo
    eval_contract = REPO_ROOT / "evaluation_contract.yaml"
    if eval_contract.exists() and not (staging_dir / "evaluation_contract.yaml").exists():
        shutil.copy2(eval_contract, staging_dir / "evaluation_contract.yaml")
        print(f"  -> Bo sung evaluation_contract.yaml tu repository root")

    # 4. Tao dataset-metadata.json
    create_dataset_metadata(staging_dir)

    # 5. Nen zip neu can
    if create_zip:
        print(f"\n[*] Dang nen thu muc staging vao: {zip_path}...")
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if zip_path.exists():
            zip_path.unlink()
            
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(staging_dir):
                for f in files:
                    p = Path(root) / f
                    zf.write(p, p.relative_to(staging_dir).as_posix())
                    
        zip_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"✓ Da tao file zip thanh cong: {zip_path} ({zip_mb:.2f} MB)")

    print("\n" + "=" * 75)
    print("🎉 HOAN TAT DONG GOI VALIDATION DATASET!")
    print(f"    - Staging Dir: {staging_dir}")
    print(f"    - Zip File:    {zip_path}")
    print(f"    - Lenh upload len Kaggle qua CLI:")
    print(f"      kaggle datasets create -p \"{staging_dir}\" -r zip")
    print("=" * 75)
    return staging_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package validation dataset for Kaggle")
    parser.add_argument("--source", type=str, default=None, help="Path to source validation directory")
    parser.add_argument("--staging", type=str, default=str(DEFAULT_STAGING_DIR), help="Staging output directory")
    parser.add_argument("--zip_path", type=str, default=str(DEFAULT_ZIP_PATH), help="Path for output zip file")
    parser.add_argument("--no_zip", action="store_true", help="Do not create zip archive")
    args = parser.parse_args()

    src = find_validation_source(args.source)
    if not src:
        print("[!] ERROR: Khong tim thay thu muc validation!")
        print("    Vui long kiem tra lai duong dan hoac truyen tham so --source <path>")
        sys.exit(1)

    package_validation_dataset(
        source_dir=src,
        staging_dir=Path(args.staging).resolve(),
        zip_path=Path(args.zip_path).resolve(),
        create_zip=not args.no_zip
    )
