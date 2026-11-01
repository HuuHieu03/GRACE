#!/usr/bin/env python3
"""Công cụ tự động giám sát tiến độ Kaggle Kernel Version 10, tự động kéo kết quả về và thẩm định số liệu.

Tính năng:
- Kiểm tra trạng thái kernel định kỳ (`KernelWorkerStatus.RUNNING`, `QUEUED`, `COMPLETE`, `ERROR`).
- Tự động kéo kết quả về `data/kaggle_run_v10_output/` khi kernel hoàn tất.
- Giải nén `step5_results.zip` và kiểm tra toàn vẹn số liệu (kiểm chứng 0 ca lỗi HTTP 400).
- Xuất báo cáo tổng hợp Markdown và Bảng A, Bảng B.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


KERNEL_SLUG = "huuhieu3333/grace-host-llm-server"
DEFAULT_OUTPUT_DIR = Path("data/kaggle_run_v10_output")


def get_kernel_status(slug: str = KERNEL_SLUG) -> str:
    """Gọi Kaggle CLI để lấy trạng thái hiện tại của kernel."""
    try:
        res = subprocess.run(
            ["kaggle", "kernels", "status", slug],
            capture_output=True,
            text=True,
            check=True,
        )
        out = res.stdout.strip()
        for line in out.splitlines():
            if "status" in line.lower():
                return line.strip()
        return out
    except Exception as exc:
        return f"ERROR: {str(exc)}"


def pull_kernel_output(slug: str = KERNEL_SLUG, out_dir: Path = DEFAULT_OUTPUT_DIR) -> bool:
    """Kéo artifact và kết quả từ Kaggle về thư mục cục bộ."""
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Đang kéo artifact từ Kaggle ({slug}) về {out_dir}...")
    try:
        res = subprocess.run(
            ["kaggle", "kernels", "output", slug, "-p", str(out_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
        print(res.stdout)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[!] Lỗi khi kéo kết quả từ Kaggle: {exc.stderr}")
        return False


def verify_and_report_v10_results(out_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """Giải nén và kiểm định toàn diện số liệu của Version 10."""
    report: Dict[str, Any] = {
        "verified_at": datetime.now().isoformat(),
        "success": False,
        "zip_found": False,
        "invalid_count": 0,
        "total_records": 0,
        "arms_found": [],
        "table_A": [],
        "table_B": [],
    }

    zip_path = out_dir / "step5_results.zip"
    if zip_path.exists():
        report["zip_found"] = True
        extract_dir = out_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        print(f"[*] Đang giải nén {zip_path} -> {extract_dir}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

    # Quét records.jsonl
    search_base = out_dir / "extracted" if (out_dir / "extracted").exists() else out_dir
    record_files = list(search_base.rglob("records.jsonl"))
    print(f"[*] Tìm thấy {len(record_files)} tệp records.jsonl.")

    arm_stats = {}
    for rf in record_files:
        arm_name = rf.parent.parent.name
        split = rf.parent.parent.parent.name
        key = f"{split}/{arm_name}"
        total = 0
        valid = 0
        invalid = 0
        with open(rf, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                total += 1
                if row.get("valid") is True:
                    valid += 1
                else:
                    invalid += 1
        arm_stats[key] = {"total": total, "valid": valid, "invalid": invalid, "invalid_rate": (invalid / total) if total > 0 else 0.0}
        report["total_records"] += total
        report["invalid_count"] += invalid
        report["arms_found"].append(key)

    report["arm_stats"] = arm_stats

    # Đọc Bảng A và Bảng B nếu có
    tbl_a_candidates = list(search_base.rglob("table_A_metrics.csv"))
    if tbl_a_candidates:
        with open(tbl_a_candidates[0], "r", encoding="utf-8") as f:
            report["table_A"] = list(csv.DictReader(f))

    tbl_b_candidates = list(search_base.rglob("table_B_contrasts.csv"))
    if tbl_b_candidates:
        with open(tbl_b_candidates[0], "r", encoding="utf-8") as f:
            report["table_B"] = list(csv.DictReader(f))

    # Đánh giá thành công
    b2_invalid = arm_stats.get("test/B2", {}).get("invalid", 0)
    report["success"] = (report["total_records"] >= 5464 and b2_invalid == 0)

    # Xuất báo cáo Markdown
    report_md = out_dir / "v10_verification_report.md"
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# Báo cáo Thẩm định Thực nghiệm Version 10 Trên Kaggle GPU\n\n")
        f.write(f"- **Thời gian thẩm định**: `{report['verified_at']}`\n")
        f.write(f"- **Tổng số bản ghi thu thập**: {report['total_records']:,}\n")
        f.write(f"- **Tổng số ca lỗi invalid**: {report['invalid_count']} (Mục tiêu: 0 ca HTTP 400)\n")
        f.write(f"- **Trạng thái thẩm định**: {'🟢 THÀNH CÔNG VƯỢT TRỘI' if report['success'] else '⚠️ CẦN KIỂM TRA LẠI'}\n\n")
        f.write("## 1. Chi tiết Từng Nhánh (Arm)\n\n")
        f.write("| Phân nhánh | Tổng mẫu | Hợp lệ (Valid) | Không hợp lệ (Invalid) | Tỷ lệ lỗi |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: |\n")
        for k, v in arm_stats.items():
            f.write(f"| `{k}` | {v['total']:,} | {v['valid']:,} | {v['invalid']} | {v['invalid_rate']*100:.2f}% |\n")
        f.write("\n")

        if report["table_B"]:
            f.write("## 2. Kết quả Đối kháng Giả thuyết Nghiên cứu H1.1 (Bảng B)\n\n")
            f.write("| Đối kháng | Dataset | Chỉ số | Delta | 95% Bootstrap CI | Kết luận |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
            for r in report["table_B"]:
                if r.get("status") == "missing arm":
                    continue
                f.write(f"| {r.get('contrast')} | {r.get('dataset')} | {r.get('metric')} | {r.get('delta')} | [{r.get('ci_lo')}, {r.get('ci_hi')}] | {r.get('verdict_text', r.get('verdict'))} |\n")
            f.write("\n")

    print(f"\n[✓] Đã xuất báo cáo thẩm định: {report_md}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Tự động giám sát và kéo kết quả Kaggle Kernel Version 10.")
    parser.add_argument("--slug", default=KERNEL_SLUG, help="Kaggle kernel slug")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Thư mục xuất kết quả")
    parser.add_argument("--poll-interval", type=int, default=300, help="Chu kỳ kiểm tra trạng thái (giây)")
    parser.add_argument("--once", action="store_true", help="Chỉ kiểm tra 1 lần rồi thoát")
    args = parser.parse_args()

    print("=" * 70)
    print(f"  GIÁM SÁT KAGGLE KERNEL VERSION 10: {args.slug}")
    print("=" * 70)

    start_time = time.time()
    while True:
        status_line = get_kernel_status(args.slug)
        elapsed_min = (time.time() - start_time) / 60.0
        print(f"[{datetime.now().strftime('%H:%M:%S')} | +{elapsed_min:.1f}m] Trạng thái: {status_line}")

        if "COMPLETE" in status_line:
            print("\n🟢 KERNEL ĐÃ HOÀN TẤT THỰC THI (COMPLETE)! Đang tiến hành kéo kết quả...")
            success = pull_kernel_output(args.slug, args.out_dir)
            if success:
                verify_and_report_v10_results(args.out_dir)
            break
        elif "ERROR" in status_line or "CANCELLED" in status_line:
            print(f"\n[!] CẢNH BÁO: Kernel kết thúc với trạng thái lỗi: {status_line}")
            pull_kernel_output(args.slug, args.out_dir)
            sys.exit(1)

        if args.once:
            break

        print(f"[*] Đang chờ {args.poll_interval}s trước lần kiểm tra tiếp theo...")
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
