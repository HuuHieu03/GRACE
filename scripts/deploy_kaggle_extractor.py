"""
Deploy GRACE Joern Extractor to Kaggle
Script tự động đẩy Dataset và Notebook trích xuất đồ thị lên Kaggle Linux Cloud:
1. Đóng gói hoặc xác nhận dataset (huuhieu3333/grace-joern-validation).
2. Đẩy dataset lên Kaggle qua Kaggle CLI: kaggle datasets create / version.
3. Đẩy kernel lên Kaggle: kaggle kernels push -p kaggle_notebooks/extract_graphs.
4. Theo dõi tiến độ chạy kernel: kaggle kernels status huuhieu3333/grace-joern-val-extractor.
"""

import io
import sys
import time
import argparse
import subprocess
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).parent.parent.resolve()
PKG_DIR = REPO_ROOT / "data" / "kaggle_joern_validation_pkg"
KERNEL_DIR = REPO_ROOT / "kaggle_notebooks" / "extract_graphs"
KERNEL_SLUG = "huuhieu3333/grace-joern-val-extractor"
DATASET_SLUG = "huuhieu3333/grace-joern-validation"


def run_cmd(cmd_list, check=True):
    """Chạy lệnh shell và hiển thị đầu ra."""
    cmd_str = " ".join(cmd_list)
    print(f"\n[*] Đang thực thi: {cmd_str}")
    proc = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(f"[stderr]: {proc.stderr}")
    if check and proc.returncode != 0:
        raise RuntimeError(f"Lệnh thất bại (Exit code {proc.returncode}): {cmd_str}")
    return proc


def deploy_dataset(skip_package=False):
    """Đóng gói và đẩy dataset lên Kaggle."""
    print("=" * 75)
    print("  BƯỚC 1: ĐẨY DATASET JOERN & VALIDATION LÊN KAGGLE")
    print("=" * 75)

    if not skip_package or not PKG_DIR.exists():
        from scripts.package_joern_validation import package_dataset
        package_dataset(output_dir=PKG_DIR, create_zip=False)

    # Kiểm tra dataset đã tồn tại chưa qua lệnh `kaggle datasets files`
    check_proc = run_cmd(["kaggle", "datasets", "files", DATASET_SLUG], check=False)
    if check_proc.returncode == 0:
        print(f"[*] Dataset {DATASET_SLUG} đã tồn tại. Đang cập nhật phiên bản mới...")
        run_cmd(["kaggle", "datasets", "version", "-p", str(PKG_DIR), "-m", "Cập nhật Joern 0.2.5 và Validation data", "-r", "zip"])
    else:
        print(f"[*] Đang tạo mới dataset {DATASET_SLUG}...")
        run_cmd(["kaggle", "datasets", "create", "-p", str(PKG_DIR), "-r", "zip"])

    print(f"[✓] Dataset {DATASET_SLUG} đã được đẩy thành công lên Kaggle!")


def deploy_kernel():
    """Đẩy kernel lên Kaggle và theo dõi trạng thái."""
    print("\n" + "=" * 75)
    print("  BƯỚC 2: ĐẨY VÀ KÍCH HOẠT KERNEL TRÍCH XUẤT ĐỒ THỊ TRÊN KAGGLE")
    print("=" * 75)

    if not (KERNEL_DIR / "kernel-metadata.json").exists():
        raise FileNotFoundError(f"Thiếu kernel-metadata.json tại: {KERNEL_DIR}")

    run_cmd(["kaggle", "kernels", "push", "-p", str(KERNEL_DIR)])
    print(f"[✓] Đã đẩy thành công Kernel: {KERNEL_SLUG}")


def monitor_kernel(poll_interval=30, timeout_mins=60):
    """Theo dõi tiến độ chạy của kernel."""
    print("\n" + "=" * 75)
    print(f"  BƯỚC 3: THEO DÕI TRẠNG THÁI KERNEL ({KERNEL_SLUG})")
    print("=" * 75)

    start_time = time.time()
    max_sec = timeout_mins * 60

    while True:
        elapsed = time.time() - start_time
        proc = run_cmd(["kaggle", "kernels", "status", KERNEL_SLUG], check=False)
        output = proc.stdout.lower()

        if "complete" in output:
            print(f"\n🎉 [COMPLETE] Kernel {KERNEL_SLUG} đã chạy hoàn tất thành công trong {elapsed/60:.1f} phút!")
            break
        elif "error" in output or "failed" in output:
            print(f"\n❌ [ERROR] Kernel gặp sự cố: {proc.stdout}")
            sys.exit(1)
        elif "cancel" in output:
            print(f"\n[!] Kernel đã bị hủy.")
            sys.exit(1)
        elif elapsed > max_sec:
            print(f"\n[Warning] Hết thời gian chờ {timeout_mins} phút. Kernel vẫn đang chạy ngầm.")
            break

        print(f"[*] Trạng thái: {proc.stdout.strip()} (Đã trôi qua {elapsed/60:.1f}m)... Tiếp tục chờ {poll_interval}s.")
        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Deploy GRACE Joern extractor to Kaggle")
    parser.add_argument("--skip_dataset", action="store_true", help="Bỏ qua bước upload dataset")
    parser.add_argument("--skip_package", action="store_true", help="Không đóng gói lại thư mục staging nếu đã có")
    parser.add_argument("--no_monitor", action="store_true", help="Không chờ theo dõi tiến trình kernel")
    parser.add_argument("--poll_interval", type=int, default=30, help="Khoảng thời gian polling trạng thái (giây)")
    args = parser.parse_args()

    if not args.skip_dataset:
        deploy_dataset(skip_package=args.skip_package)

    deploy_kernel()

    if not args.no_monitor:
        monitor_kernel(poll_interval=args.poll_interval)

    print("\n[✓] Hoàn thành quy trình triển khai! Để kéo kết quả về máy, chạy:")
    print("    python scripts/pull_kaggle_graphs.py")


if __name__ == "__main__":
    main()
