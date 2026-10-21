"""
Embed C source code directly into sample_details of clean dev split JSONs.
Bảo đảm tính độc lập hoàn toàn cho Kaggle runtime: không cần thư mục raw_c_files hay Hugging Face API.
"""

import sys
import io
import json
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr.encoding != "utf-8":
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

repo_root = Path(__file__).parent.parent.resolve()

def embed_code_into_split(split_file: Path) -> int:
    if not split_file.exists():
        print(f"[!] File does not exist: {split_file}")
        return 0

    with open(split_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    sample_details = data.get("sample_details", [])
    updated = 0

    for item in sample_details:
        if item.get("func") and len(str(item["func"]).strip()) > 0:
            continue
        c_path_str = str(item.get("c_file_path", "")).replace("\\", "/")
        if not c_path_str:
            continue
        c_path = Path(c_path_str)
        if not c_path.is_absolute():
            c_path = repo_root / c_path

        if c_path.exists():
            with open(c_path, "r", encoding="utf-8", errors="replace") as f_c:
                code_text = f_c.read().strip()
                item["func"] = code_text
                updated += 1
        else:
            print(f"[!] C file not found: {c_path}")

    with open(split_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Updated C source code for {updated}/{len(sample_details)} samples in {split_file.name}")
    return updated

if __name__ == "__main__":
    for ds in ["reveal", "devign"]:
        split_p = repo_root / "data" / "splits" / f"{ds}_dev_clean_100_ids.json"
        embed_code_into_split(split_p)
