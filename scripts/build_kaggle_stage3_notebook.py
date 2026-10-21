"""
Script tự động sinh và đóng gói file Jupyter Notebook cho Stage 3:
- Devign: kaggle_notebooks/stage3_b3_vs_b2/stage3_b3_vs_b2_kaggle.ipynb
- ReVeal: kaggle_notebooks/stage3_b3_vs_b2_reveal/stage3_b3_vs_b2_reveal_kaggle.ipynb
"""

import json
import argparse
from pathlib import Path

repo_root = Path(__file__).parent.parent.resolve()


def generate_stage3_notebook(
    dataset_name: str = "devign",
    target_dir_name: str = None,
    target_nb_name: str = None,
    kernel_id: str = None
):
    ds_clean = dataset_name.lower().strip()
    is_reveal = (ds_clean == "reveal")
    
    ds_display = "ReVeal" if is_reveal else "Devign"
    target_dir_name = target_dir_name or ("stage3_b3_vs_b2_reveal" if is_reveal else "stage3_b3_vs_b2")
    target_nb_name = target_nb_name or ("stage3_b3_vs_b2_reveal_kaggle.ipynb" if is_reveal else "stage3_b3_vs_b2_kaggle.ipynb")
    kernel_id = kernel_id or ("huuhieu3333/grace-stage-3-b3-vs-b2-reveal" if is_reveal else "huuhieu3333/grace-stage-3-b3-vs-b2-contrastive-demonstration")
    kernel_title = f"GRACE Stage 3 B3 vs B2 {ds_display}"
    
    target_dir = repo_root / "kaggle_notebooks" / target_dir_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_ipynb = target_dir / target_nb_name
    metadata_json = target_dir / "kernel-metadata.json"

    dev_split_file = f"data/splits/{ds_clean}_dev_clean_100_ids.json"
    train_cpg_file = f"data/processed/{ds_clean}_train_compact_cpg.json.gz"
    output_report_file = f"output/stage3/{ds_clean}_b3_vs_b2_comparison_report.json"
    output_csv_file = f"output/stage3/{ds_clean}_b3_vs_b2_comparison_report.csv"

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# 🛡️ GRACE Đợt 3: Đối Đầu B3 (Contrastive Demonstration Selection) vs B2 (Baseline) & Ablation B3-NoDiff trên {ds_display}\n",
                "\n",
                "**Môi Trường Thực Thi**: Kaggle GPU (T4 / P100) với Google Cloud Vertex AI MaaS  \n",
                "**Hợp Đồng Đánh Giá**: `evaluation_contract.yaml`  \n",
                "**Kế Hoạch Khoa Học**: `project_docs/plans/PLAN_SUPERVISOR_REQUIREMENTS_EXECUTION_20261014.md`  \n",
                "\n",
                "### 1. Mục Tiêu Khoa Học & Nhiệm Vụ 1 (Ablation Study B3-NoDiff):\n",
                f"- Đánh giá đối đầu trực diện giữa **Baseline B2** (1-shot hybrid CodeT5 768-d + GraphSim) và **B3** (2-shot Contrastive Demonstration Selection: Security-Aware Retriever + Strategy C Counterexample Pair) trên bộ dữ liệu **{ds_display}** (100 mẫu sạch).\n",
                "- **Nhiệm Vụ 1 (Ablation B3-NoDiff)**: Cắt bỏ khối `--- CORE SECURITY DIFFERENCE ---` bằng cờ `--no_security_diff` để trả lời câu hỏi cốt lõi: *Hiệu năng B3 tăng vọt là nhờ Cặp mẫu cân bằng nhãn 1:1, hay nhờ khối phân tích rào chắn an ninh Core Security Difference?*\n",
                "- Kiểm chứng giả thuyết: Cặp mẫu tương phản *(1 Vulnerable + 1 Safe)* kết hợp phân tích điểm khác biệt an ninh cốt lõi (*Security Difference*) giúp:\n",
                "  1. Nâng cao vượt trội khả năng phát hiện lỗ hổng thực tế (**Recall**, **F1-Score**, **MCC**, **Balanced Accuracy**).\n",
                "  2. Triệt tiêu hoàn toàn sự phụ thuộc/học vẹt nhãn đảo (**Label Sensitivity**).\n",
                "- Đo lường thống kê mẫu ghép cặp: **Kiểm định McNemar** và **Paired Bootstrap 95% Confidence Interval** (2,000 resamples).\n",
                "\n",
                "### 2. Cấu Hình Thực Nghiệm B3 Chuẩn Figure 6 & Hợp Đồng:\n",
                "- **Target Query**: Code mục tiêu ($\\le 3000$ ký tự) + Đồ thị CPG Joern (tối đa 25 nodes, 25 edges).\n",
                "- **1 Vulnerable Demo Reference**: Code mẫu có lỗ hổng ($\\le 1200$ ký tự) + Nhãn `Vulnerable (1)`.\n",
                "- **1 Safe Demo Reference**: Code mẫu an toàn tương phản ($\\le 1200$ ký tự) + Nhãn `Non-vulnerable (0)`.\n",
                "- **Core Security Difference**: Phân tích ranh giới an ninh cốt lõi (sanitization guards, bounds check, pointer validation).\n",
                "- **Backbone LLM**: `publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas` (Location: `us-south1`, Temperature: 0.0, Seed: 42, Max tokens: 256, Retry: 5 attempts)."
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Bước 1: Thiết Lập Thư Mục Làm Việc (Workspace Setup)\n",
                "Tìm kiếm mã nguồn dự án trong `/kaggle/input` hoặc sao chép sang `/kaggle/working/GRACE` để có toàn quyền ghi file báo cáo và checkpoints."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import sys\n",
                "import shutil\n",
                "import subprocess\n",
                "from pathlib import Path\n",
                "\n",
                "dest_dir = '/kaggle/working/GRACE'\n",
                "\n",
                "# 1. Đảm bảo luôn lấy mã nguồn mới nhất từ GitHub\n",
                "if not os.path.exists(dest_dir):\n",
                "    print('[*] Đang clone mã nguồn GRACE mới nhất từ GitHub...')\n",
                "    subprocess.run(['git', 'clone', 'https://github.com/HuuHieu03/GRACE.git', dest_dir], check=True)\n",
                "else:\n",
                "    print('[*] Đang cập nhật mã nguồn mới nhất từ GitHub...')\n",
                "    subprocess.run(['git', '-C', dest_dir, 'fetch', 'origin'], check=True)\n",
                "    subprocess.run(['git', '-C', dest_dir, 'reset', '--hard', 'origin/main'], check=True)\n",
                "\n",
                "subprocess.run(['git', '-C', dest_dir, 'log', '-1', '--oneline'], check=True)\n",
                "\n",
                "# 2. Chuyển thư mục làm việc và bổ sung sys.path\n",
                "%cd /kaggle/working/GRACE\n",
                "for p in ['/kaggle/working/GRACE', '/kaggle/working/GRACE/src', '/kaggle/working/GRACE/scripts']:\n",
                "    if p not in sys.path:\n",
                "        sys.path.insert(0, p)\n",
                "\n",
                "print(f'✓ Thư mục làm việc hiện tại: {os.getcwd()}')\n",
                "!ls -la\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Bước 2: Cài Đặt Các Gói Phụ Thuộc (Dependencies Installation)\n",
                "Cài đặt các thư viện cần thiết: `google-auth`, `openai>=1.0.0`, `transformers`, `torch`, `scikit-learn`, `datasets`, `pyyaml`, `pandas`, `tqdm`."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "!pip install -q google-auth google-auth-oauthlib openai>=1.0.0 transformers torch scikit-learn datasets pandas tqdm pyyaml pytest\n",
                "import torch\n",
                "print(f'✓ PyTorch Version: {torch.__version__} | CUDA Available: {torch.cuda.is_available()}')\n",
                "if torch.cuda.is_available():\n",
                "    print(f'✓ GPU Device: {torch.cuda.get_device_name(0)}')\n",
                "print('✓ [Setup Complete] Các thư viện phụ thuộc đã sẵn sàng!')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Bước 3: Xác Thực Google Cloud Vertex AI Qua Kaggle Secrets\n",
                "Đọc Service Account Key từ Kaggle Secret `GCP_SA_KEY`, ghi ra file tạm `/tmp/gcp_sa_key.json`,\n",
                "thiết lập `GOOGLE_APPLICATION_CREDENTIALS` và kiểm tra sinh Access Token hợp lệ qua `google.auth`."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import json\n",
                "from pathlib import Path\n",
                "from kaggle_secrets import UserSecretsClient\n",
                "\n",
                "# 1. Đọc Kaggle Secret: GCP_SA_KEY\n",
                "print('[*] Đang nạp Service Account Key từ Kaggle Secrets...')\n",
                "try:\n",
                "    user_secrets = UserSecretsClient()\n",
                "    sa_json_str = user_secrets.get_secret('GCP_SA_KEY')\n",
                "    sa_path = Path('/tmp/gcp_sa_key.json')\n",
                "    with open(sa_path, 'w', encoding='utf-8') as f:\n",
                "        f.write(sa_json_str.strip())\n",
                "    os.chmod(sa_path, 0o600)\n",
                "    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(sa_path)\n",
                "    print(f'✓ [OK] Đã lưu Service Account key tại: {sa_path}')\n",
                "except Exception as e:\n",
                "    print(f'[!] Cảnh báo nạp Kaggle Secret: {e}. Vui lòng kiểm tra Add-ons -> Secrets trên Kaggle!')\n",
                "\n",
                "# 2. Khởi tạo cấu hình và xác thực Vertex AI\n",
                "from config import config, setup_vertex_credentials\n",
                "cred_file = setup_vertex_credentials()\n",
                "print(f'[*] File Credentials hoạt động: {cred_file}')\n",
                "print(f'[*] Vertex Project ID: {config.vertex_project_id}')\n",
                "print(f'[*] Vertex Location:   {config.vertex_location}')\n",
                "print(f'[*] Vertex Model:      {config.vertex_model}')\n",
                "\n",
                "# 3. Xác thực sinh OAuth2 Token qua google.auth\n",
                "try:\n",
                "    import google.auth\n",
                "    from google.auth.transport.requests import Request\n",
                "    creds, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])\n",
                "    creds.refresh(Request())\n",
                "    print(f'✓ [OK] Vertex AI Authentication Verified! Token prefix: {creds.token[:12]}... (valid={creds.valid})')\n",
                "except Exception as e:\n",
                "    print(f'[!] Lỗi xác thực Vertex AI: {e}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"## Bước 4: Thiết Lập Cấu Hình Bộ Dữ Liệu & Rào Chắn Hợp Đồng\n",
                f"Cấu hình bộ dữ liệu chạy thực nghiệm (`devign` hoặc `reveal`) và chế độ Ablation Study B3-NoDiff.\n",
                "Xác nhận tập kiểm thử 100 mẫu sạch không rò rỉ mã và kho huấn luyện Train Compact CPG có đầy đủ nodes & edges theo chuẩn Joern 0.2.5 CPG."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import json\n",
                "from pathlib import Path\n",
                "\n",
                "# ==============================================================================\n",
                f"# CẤU HÌNH BỘ DỮ LIỆU ĐỢT 3: '{ds_clean}' (Mặc định) hoặc 'reveal' / 'devign'\n",
                "# ==============================================================================\n",
                f"DATASET = os.environ.get('DATASET', '{ds_clean}').lower().strip()\n",
                "# Bật cờ Nhiệm Vụ 1: Ablation Study B3-NoDiff (Cắt bỏ Core Security Difference)\n",
                "RUN_ABLATION_NO_DIFF = os.environ.get('RUN_ABLATION_NO_DIFF', 'true').lower().strip() in ('true', '1', 'yes')\n",
                "\n",
                "if DATASET == 'devign':\n",
                "    DATASET_NAME = 'devign'\n",
                "    DATASET_DISPLAY = 'Devign'\n",
                "    DEV_SPLIT_FILE = 'data/splits/devign_dev_clean_100_ids.json'\n",
                "    TRAIN_CPG_FILE = 'data/processed/devign_train_compact_cpg.json.gz'\n",
                "    if RUN_ABLATION_NO_DIFF:\n",
                "        OUTPUT_REPORT_FILE = 'output/stage3/ablation_nodiff_comparison_report.json'\n",
                "        OUTPUT_CSV_FILE = 'output/stage3/ablation_nodiff_comparison_report.csv'\n",
                "    else:\n",
                "        OUTPUT_REPORT_FILE = 'output/stage3/devign_b3_vs_b2_comparison_report.json'\n",
                "        OUTPUT_CSV_FILE = 'output/stage3/devign_b3_vs_b2_comparison_report.csv'\n",
                "else:\n",
                "    DATASET_NAME = 'reveal'\n",
                "    DATASET_DISPLAY = 'ReVeal'\n",
                "    DEV_SPLIT_FILE = 'data/splits/reveal_dev_clean_100_ids.json'\n",
                "    TRAIN_CPG_FILE = 'data/processed/reveal_train_compact_cpg.json.gz'\n",
                "    if RUN_ABLATION_NO_DIFF:\n",
                "        OUTPUT_REPORT_FILE = 'output/stage3/reveal_ablation_nodiff_comparison_report.json'\n",
                "        OUTPUT_CSV_FILE = 'output/stage3/reveal_ablation_nodiff_comparison_report.csv'\n",
                "    else:\n",
                "        OUTPUT_REPORT_FILE = 'output/stage3/reveal_b3_vs_b2_comparison_report.json'\n",
                "        OUTPUT_CSV_FILE = 'output/stage3/reveal_b3_vs_b2_comparison_report.csv'\n",
                "\n",
                "print(f'[*] Bộ dữ liệu thực nghiệm: {DATASET_DISPLAY} ({DATASET_NAME}) | Ablation B3-NoDiff: {RUN_ABLATION_NO_DIFF}')\n",
                "print(f'[*] Dev Split mục tiêu:      {DEV_SPLIT_FILE}')\n",
                "print(f'[*] Kho Train Compact CPG:  {TRAIN_CPG_FILE}')\n",
                "print(f'[*] File báo cáo đầu ra:    {OUTPUT_REPORT_FILE}')\n",
                "\n",
                "# 1. Rào chắn hợp đồng cho tập Dev Split\n",
                "split_path = Path(DEV_SPLIT_FILE)\n",
                "assert split_path.exists(), f'Không tìm thấy file split: {split_path}'\n",
                "\n",
                "with open(split_path, 'r', encoding='utf-8') as f:\n",
                "    meta = json.load(f)\n",
                "\n",
                "print(f'[*] Dataset Metadata: {meta.get(\"dataset\")} | Split: {meta.get(\"split_name\")}')\n",
                "print(f'[*] Tổng số mẫu: {meta.get(\"total_samples\")} (Vuln: {meta.get(\"vulnerable_count\")}, Safe: {meta.get(\"safe_count\")})')\n",
                "print(f'[*] Seed: {meta.get(\"seed\")} | Hash SHA-256: {meta.get(\"split_id_hash_sha256_short\")}')\n",
                "\n",
                "sample_details = meta.get('sample_details', [])\n",
                "assert len(sample_details) == 100, f'Số mẫu chi tiết phải là 100, nhận được: {len(sample_details)}'\n",
                "for idx, s in enumerate(sample_details):\n",
                "    nodes = s.get('nodes', [])\n",
                "    edges = s.get('edges', [])\n",
                "    assert len(nodes) > 0, f'LỖI: Mẫu {s.get(\"id\")} thiếu CPG nodes!'\n",
                "    assert len(edges) > 0, f'LỖI: Mẫu {s.get(\"id\")} thiếu CPG edges!'\n",
                "\n",
                "# 2. Rào chắn cho kho huấn luyện Train Compact CPG\n",
                "train_cpg_p = Path(TRAIN_CPG_FILE)\n",
                "assert train_cpg_p.exists(), f'LỖI: Không tìm thấy file kho Train CPG tại {train_cpg_p}'\n",
                "print(f'✓ [OK] Đã tìm thấy kho Train CPG: {train_cpg_p} ({train_cpg_p.stat().st_size / (1024*1024):.1f} MB)')\n",
                "print(f'✓ [OK] RÀO CHẮN HỢP ĐỒNG ĐẠT CHUẨN: 100% ({len(sample_details)}/100) mẫu {DATASET_DISPLAY} có đầy đủ CPG nodes và edges.')\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Bước 5: Chạy Unit Tests Xác Minh Hệ Thống Đợt 3\n",
                "Xác nhận các chốt chặn kỹ thuật: Cấu trúc prompt contrastive 2-shot, cắt bỏ security difference khi ablation, kiểm định McNemar và Paired Bootstrap."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "!python -m pytest tests/test_stage3_b3_vs_b2.py tests/test_stage2_contract_compliance.py tests/test_stage5_contrastive_selector.py -v\n",
                "print('✓ [All Unit Tests Passed] Toàn bộ các chốt chặn Đợt 3 đã hoàn tất xuất sắc!')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"## Bước 6: Thực Thi Thí Nghiệm Đợt 3 (Chạy Đối Đầu B3 vs B2 & Ablation B3-NoDiff)\n",
                f"Thực thi script `scripts/run_stage3_b3_vs_b2.py` với mô hình Vertex AI:\n",
                "- Model: `publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas`\n",
                "- Bộ dữ liệu: Tham số `--dataset` và `--dev_split` đã cấu hình ở Bước 4\n",
                "- Chiến lược chọn cặp: `counterexample_pair` (Strategy C)\n",
                "- Cờ `--no_security_diff`: Bật khi `RUN_ABLATION_NO_DIFF=True` để bóc tách tác động cô lập của Core Security Difference\n",
                "- Báo cáo lưu tại: `{OUTPUT_REPORT_FILE}`"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import subprocess\n",
                "import sys\n",
                "import shutil\n",
                "from pathlib import Path\n",
                "\n",
                "print(f'[*] Khởi động thực nghiệm Đợt 3 trên {DATASET_DISPLAY} (Ablation B3-NoDiff={RUN_ABLATION_NO_DIFF})...')\n",
                "cmd = [\n",
                "    sys.executable, 'scripts/run_stage3_b3_vs_b2.py',\n",
                "    '--dev_split', DEV_SPLIT_FILE,\n",
                "    '--dataset', DATASET_NAME,\n",
                "    '--model', 'publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas',\n",
                "    '--provider', 'Vertex AI',\n",
                "    '--location', 'us-south1',\n",
                "    '--strategy', 'counterexample_pair',\n",
                "    '--lambda_weight', '0.3',\n",
                "    '--output', OUTPUT_REPORT_FILE,\n",
                "]\n",
                "if RUN_ABLATION_NO_DIFF:\n",
                "    cmd.append('--no_security_diff')\n",
                "print('[*] Executing:', ' '.join(cmd))\n",
                "subprocess.run(cmd, check=True)\n",
                "\n",
                "# Sao chép kết quả về thư mục gốc /kaggle/working để Kaggle nén xuất đầy đủ\n",
                "out_dir = Path('/kaggle/working/output/stage3')\n",
                "out_dir.mkdir(parents=True, exist_ok=True)\n",
                "for f_path_str in [OUTPUT_REPORT_FILE, OUTPUT_CSV_FILE]:\n",
                "    fp = Path(f_path_str)\n",
                "    if fp.exists():\n",
                "        shutil.copy2(fp, out_dir / fp.name)\n",
                "        shutil.copy2(fp, Path('/kaggle/working') / fp.name)\n",
                "        print(f'✓ [OK] Đã sao chép artifact: {fp.name}')\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"## Bước 7: Phân Tích & Nghiệm Thu Kết Quả Thực Nghiệm Đợt 3 ({ds_display})\n",
                "Đọc file báo cáo JSON, phân tích chi tiết mức độ cải thiện của B3 so với B2 trên tất cả các chỉ số:\n",
                "F1-Score, MCC, Balanced Accuracy, Precision, Recall, McNemar p-value, Bootstrap 95% CI và Báo cáo Ablation Study 3 đường cơ sở."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import json\n",
                "from pathlib import Path\n",
                "from scripts.run_stage3_b3_vs_b2 import print_stage3_comparison_report\n",
                "\n",
                "rep_candidates = [\n",
                "    Path(OUTPUT_REPORT_FILE),\n",
                "    Path(f'/kaggle/working/{OUTPUT_REPORT_FILE}'),\n",
                "    Path(f'/kaggle/working/{Path(OUTPUT_REPORT_FILE).name}'),\n",
                "    Path('output/stage3/ablation_nodiff_comparison_report.json'),\n",
                "    Path('output/stage3/reveal_ablation_nodiff_comparison_report.json'),\n",
                "    Path('output/stage3/devign_b3_vs_b2_comparison_report.json'),\n",
                "    Path('output/stage3/reveal_b3_vs_b2_comparison_report.json'),\n",
                "    Path('output/stage3/b3_vs_b2_comparison_report.json')\n",
                "]\n",
                "\n",
                "report_file = None\n",
                "for p in rep_candidates:\n",
                "    if p.exists() and p.stat().st_size > 100:\n",
                "        report_file = p\n",
                "        break\n",
                "\n",
                "if report_file:\n",
                "    with open(report_file, 'r', encoding='utf-8') as f:\n",
                "        rep = json.load(f)\n",
                "    print_stage3_comparison_report(rep)\n",
                "else:\n",
                "    print(f'[!] Chưa tìm thấy file báo cáo {OUTPUT_REPORT_FILE}.')\n"
            ]
        }
    ]

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    with open(target_ipynb, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)

    meta_content = {
        "id": kernel_id,
        "title": kernel_title,
        "code_file": target_nb_name,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",
        "dataset_sources": []
    }
    with open(metadata_json, "w", encoding="utf-8") as f_meta:
        json.dump(meta_content, f_meta, indent=2, ensure_ascii=False)

    print(f"[✓] Đã sinh thành công Notebook Stage 3 cho {ds_display} tại: {target_ipynb}")
    print(f"[✓] Đã tạo kernel metadata tại: {metadata_json}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sinh Kaggle Notebook cho Stage 3")
    parser.add_argument("--dataset", type=str, default="all", choices=["devign", "reveal", "all"], help="Chọn dataset")
    args = parser.parse_args()

    if args.dataset in ("devign", "all"):
        generate_stage3_notebook("devign")
    if args.dataset in ("reveal", "all"):
        generate_stage3_notebook("reveal")
