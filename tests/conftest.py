import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.resolve()
src_dir = root_dir / "src"

for p in [str(src_dir), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)