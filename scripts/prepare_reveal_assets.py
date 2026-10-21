"""
End-to-End Preparation for ReVeal Stage 3 Assets:
1. Embed C source code into data/splits/reveal_dev_clean_100_ids.json
2. Extract compact CPG from data/processed/reveal_train_processed.json (1.74 GB)
   into data/processed/reveal_train_compact_cpg.json.gz
"""

import sys
import io
import gzip
import json
import logging
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
src_dir = repo_root / "src"
for p in [str(repo_root), str(src_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.embed_code_in_dev_split import embed_code_into_split
from scripts.prepare_grace_train_assets import stream_extract_compact_cpg

log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[log_handler])
logger = logging.getLogger(__name__)

def main():
    # 1. Embed source code in dev splits
    print("\n" + "=" * 70)
    print("  STEP 1: EMBED C SOURCE CODE INTO REVEAL CLEAN DEV SPLIT (100 SAMPLES)")
    print("=" * 70)
    dev_split = repo_root / "data" / "splits" / "reveal_dev_clean_100_ids.json"
    embed_code_into_split(dev_split)

    # 2. Extract compact CPG for ReVeal Train
    print("\n" + "=" * 70)
    print("  STEP 2: EXTRACT COMPACT CPG FOR REVEAL TRAIN SET")
    print("=" * 70)
    raw_train = repo_root / "data" / "processed" / "reveal_train_processed.json"
    compact_out = repo_root / "data" / "processed" / "reveal_train_compact_cpg.json.gz"

    if not raw_train.exists():
        logger.error(f"[X] Source file not found: {raw_train}")
        sys.exit(1)

    count = stream_extract_compact_cpg(raw_train, compact_out, max_nodes=25, max_edges=25)
    print(f"\n[OK] Done! Extracted {count} samples into {compact_out}")

if __name__ == "__main__":
    main()
