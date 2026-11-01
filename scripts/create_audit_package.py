#!/usr/bin/env python3
"""
Create a clean, audit-ready ZIP archive for the GRACE research project.
Excludes redundant files (git objects, caches, massive raw dumps, sensitive keys)
while preserving ALL teacher documents, source code, configs, tests, specs, and final results.
"""

import os
import sys
import zipfile
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_ZIP = os.path.join(PROJECT_ROOT, "audit_package_grace.zip")

# Directories to include (scanned recursively)
INCLUDE_DIRS = [
    "00_Reports_and_Docs",
    "project_docs",
    "src",
    "grace_diag_kit",
    "scripts",
    "configs",
    "tests",
    "kaggle_notebooks",
    "01_Reproduce_Notebooks",
    "02_Baseline_Code_Author",
    "data/b0_offline_dungs_data",
    "data/manifests",
    "data/specs",
    "runs/step0_real_devign",
    "runs/step0_real_reveal",
    "runs/final",
    "output",
    "figs"
]

# Root files to include
ROOT_FILES = [
    "AUDIT_README.md",
    "preregistration.md",
    "PROGRESS.md",
    "CHANGES_AFTER_PREREG.md",
    "README.md",
    "run.py",
    "requirements.txt",
    "pytest.ini",
    "evaluation_contract.yaml"
]

# Exact relative paths to exclude (normalized with forward slashes)
EXCLUDE_EXACT = {
    # 473MB old raw runs zip from teammate Dung (offline data already in data/b0_offline_dungs_data)
    "00_Reports_and_Docs/requested_data_bundle_20261029_FINAL.zip",
    # 310MB baseline raw author zip (scripts retained in author_original_scripts/ and baseline_code_text/)
    "02_Baseline_Code_Author/GRACE_source_code_baseline.zip",
    # Large uncompressed donor jsonls (compressed .jsonl.gz are included)
    "data/manifests/devign_donors.jsonl",
    "data/manifests/devign_donor_clean.jsonl",
    "data/manifests/reveal_donors.jsonl",
    "data/manifests/reveal_donor_clean.jsonl",
    # Large uncompressed specs (compressed .jsonl.gz are included)
    "data/specs/devign_test.jsonl",
    "data/specs/devign_validation.jsonl",
    "data/specs/devign_validation_subset600.jsonl",
    "data/specs/devign_val_subset600.jsonl",
    "data/specs/reveal_test.jsonl",
    "data/specs/reveal_validation.jsonl",
    "data/specs/reveal_validation_subset600.jsonl",
    "data/specs/reveal_val_subset600.jsonl"
}

def is_excluded(rel_path: str) -> bool:
    norm = rel_path.replace(os.sep, "/")
    
    # Exact match
    if norm in EXCLUDE_EXACT:
        return True
        
    # Exclude sensitive environment / credentials
    basename = os.path.basename(norm)
    if basename in [".env", ".gcp_key.json", "id_ed25519", "id_rsa"]:
        return True
        
    # Exclude git objects
    if "/.git/" in norm or norm.startswith(".git/") or norm.endswith("/.git"):
        return True
        
    # Exclude caches and build artifacts
    if "/_cache/" in norm or norm.endswith("/_cache"):
        return True
    if "/__pycache__/" in norm or norm.endswith("/__pycache__") or norm.endswith(".pyc"):
        return True
    if "/.pytest_cache/" in norm or norm.endswith(".pytest_cache"):
        return True
        
    # Exclude log directories and scratch debugging files
    if norm.startswith("log/") or norm.startswith("scratch/"):
        return True
    if "/.ipynb_checkpoints/" in norm:
        return True
        
    return False

def build_audit_package():
    os.chdir(PROJECT_ROOT)
    print(f"Creating audit package at: {OUTPUT_ZIP}")
    start_time = time.time()
    
    selected_files = []
    
    # Add root files
    for rf in ROOT_FILES:
        if os.path.exists(rf):
            selected_files.append(rf)
        else:
            print(f"Warning: Root file {rf} does not exist.")
            
    # Add directory contents
    for d in INCLUDE_DIRS:
        if not os.path.exists(d):
            print(f"Notice: Directory {d} does not exist, skipping.")
            continue
        for root, dirs, files in os.walk(d):
            for f in files:
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, PROJECT_ROOT)
                if not is_excluded(rel):
                    selected_files.append(rel)
                    
    print(f"Total selected files: {len(selected_files)}")
    
    # Write ZIP archive
    total_uncompressed = 0
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for idx, rel in enumerate(selected_files, 1):
            fp = os.path.join(PROJECT_ROOT, rel)
            arcname = rel.replace(os.sep, "/")
            zf.write(fp, arcname=arcname)
            total_uncompressed += os.path.getsize(fp)
            if idx % 100 == 0 or idx == len(selected_files):
                print(f"  Processed {idx}/{len(selected_files)} files...")
                
    elapsed = time.time() - start_time
    zip_size = os.path.getsize(OUTPUT_ZIP)
    
    print("\n" + "="*60)
    print("AUDIT PACKAGE GENERATION COMPLETED SUCCESSFULLY")
    print(f"Archive path: {OUTPUT_ZIP}")
    print(f"Files packaged: {len(selected_files)}")
    print(f"Uncompressed size: {total_uncompressed / (1024*1024):.2f} MB")
    print(f"Compressed size:   {zip_size / (1024*1024):.2f} MB")
    print(f"Compression ratio: {zip_size / total_uncompressed * 100:.1f}%")
    print(f"Time taken:        {elapsed:.2f} seconds")
    print("="*60)

if __name__ == "__main__":
    build_audit_package()
