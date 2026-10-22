from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.generate_blind_review_sheets import generate_blind_sheets


def test_legacy_entrypoint_cannot_overwrite_review_artifacts(tmp_path):
    sentinel = tmp_path / "human_sheet.csv"
    sentinel.write_text("original human choices", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Legacy review generation is disabled"):
        generate_blind_sheets(output_hieu_path=sentinel)
    assert sentinel.read_text(encoding="utf-8") == "original human choices"
