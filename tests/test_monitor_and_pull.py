"""Unit tests cho tiện ích giám sát và thẩm định kết quả Kaggle Version 10."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.monitor_and_pull_kaggle_v10 import (
    get_kernel_status,
    pull_kernel_output,
    verify_and_report_v10_results,
)


def test_get_kernel_status_mock():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout='huuhieu3333/grace-host-llm-server has status "KernelWorkerStatus.RUNNING"\n')
        status = get_kernel_status("huuhieu3333/grace-host-llm-server")
        assert "RUNNING" in status


def test_verify_and_report_v10_results_mock(tmp_path: Path):
    out_dir = tmp_path / "v10_output"
    extracted = out_dir / "extracted" / "runs" / "step5"
    b0_dir = extracted / "devign" / "test" / "B0" / "42"
    b2_dir = extracted / "devign" / "test" / "B2" / "42"
    b0_dir.mkdir(parents=True, exist_ok=True)
    b2_dir.mkdir(parents=True, exist_ok=True)

    # 10 records B0 valid
    with open(b0_dir / "records.jsonl", "w", encoding="utf-8") as f:
        for i in range(10):
            f.write(json.dumps({"id": f"devign_{i}", "valid": True, "s": 0.5}) + "\n")

    # 10 records B2 valid
    with open(b2_dir / "records.jsonl", "w", encoding="utf-8") as f:
        for i in range(10):
            f.write(json.dumps({"id": f"devign_{i}", "valid": True, "s": 0.8}) + "\n")

    # Bảng B
    eval_dir = extracted / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    with open(eval_dir / "table_B_contrasts.csv", "w", encoding="utf-8") as f:
        f.write("contrast,dataset,metric,delta,ci_lo,ci_hi,verdict\n")
        f.write("H1.1,devign,mcc,0.005,-0.02,0.03,inconclusive\n")

    res = verify_and_report_v10_results(out_dir)
    assert res["total_records"] == 20
    assert res["invalid_count"] == 0
    assert len(res["table_B"]) == 1
    assert (out_dir / "v10_verification_report.md").exists()
