# BÁO CÁO TIẾN ĐỘ TUẦN — ĐỀ TÀI GRACE (DIAGNOSTIC REPLICATION)
**Ngày cập nhật**: 29/10/2026 | **Phiên họp**: Thứ Sáu hàng tuần (Mục 9.1 Đề cương)  
**Thành viên thực hiện**: Hữu Hiếu & Tiến Dũng

---

## 1. Việc đã xong (Done)

- [x] **Chuẩn hóa cấu trúc Prompt theo Hình 6 bài gốc (Figure 6 Canonical)**:
  - Khôi phục thứ tự 6 khối chuẩn xác: `[Target Code -> Task Instruction -> Node Info -> Edge Info -> Demonstration -> Answer Indicator]`.
  - Cập nhật `src/prompt_engine.py` và `src/prompt_contract.py` (`render_control_v2` với 10 probe conditions).
  - Ngăn chặn hoàn toàn rò rỉ nhãn mục tiêu trong `spec`.
- [x] **Xây dựng module quản lý ngữ cảnh Token (`src/token_budget.py`)**:
  - Dạng cắm-rút, phân bổ ngân sách: Code $\le 3000$, Graph $\le 1500$, Demo $\le 1500$, Reserve $= 64$, Context $\le 8192$.
  - Tương thích tokenizer `Qwen2.5-Coder-32B`, bảo toàn tuyệt đối đẳng thức `retained + omitted == full`.
- [x] **Tích hợp bộ công cụ đánh giá chuẩn mực của Thầy (`grace_diag_kit/`)**:
  - Trích xuất toàn bộ package từ `00_Reports_and_Docs/grace_diag_kit.zip` vào `./grace_diag_kit/` và cài đặt vào môi trường.
  - Vượt qua toàn bộ **30/30 unit tests nguyên bản** của Thầy.
- [x] **Nâng cấp Script Adapter Bước 0 sang chuẩn 2-Split (`scripts/run_step0_offline_diagnostic.py`)**:
  - Fit meta-model và chọn ngưỡng $\tau_{pre}^*, \tau_{post}^*$ trên **Validation OOF**.
  - Huấn luyện Ridge Benefit Router (`fit_benefit_router`) trên Validation.
  - Cố định và áp nguyên vẹn ngưỡng sang **Test độc lập** (nâng cấp `apply_pre_post`), tính Paired Bootstrap CI 95% và đường cong định tuyến selective routing 4 chính sách (`gate`, `expert`, `confidence`, `benefit`, `oracle`).
- [x] **Thiết kế hạ tầng Plug-in Host Mô hình trên Kaggle GPU (Bước 1 — 0 USD)**:
  - Cung cấp Model Registry pluggable: [`configs/kaggle_model_registry.yaml`](configs/kaggle_model_registry.yaml) (hỗ trợ Qwen 7B/14B/32B và DeepSeek; engines `llamacpp`, `vllm`, `transformers`).
  - Cung cấp CLI Runner: [`scripts/kaggle_host_runner.py`](scripts/kaggle_host_runner.py) tự động sinh lệnh và xuất backend YAML tương thích với `grace_diag_kit`.
  - Cung cấp Notebook Kaggle 19 ô hoàn chỉnh: [`kaggle_notebooks/host_llm_kaggle_server.ipynb`](kaggle_notebooks/host_llm_kaggle_server.ipynb) hỗ trợ 2x T4 / P100, Cloudflared tunnel, và cell kiểm thử tự động tại chỗ bằng `curl` và Python Client.
- [x] **Kiểm thử tự động toàn diện**:
  - **57/57 tests PASSED (100%) trong 7.81s** (`grace_diag_kit/tests`, `tests/test_step0_offline_diagnostic.py`, `tests/test_prompt_standardization.py`, `tests/test_kaggle_model_registry.py`).

---

- [x] **Thực hiện pilot smoke test trên Kaggle GPU (Thành công 100%)**:
  - Đã đóng gói và đẩy kernel `huuhieu3333/grace-host-llm-server` lên Kaggle Linux Cloud có GPU.
  - Server `llama-server` đã nạp thành công mô hình `Qwen2.5-Coder-7B-Instruct-GGUF` (Q4_K_M) vào GPU memory.
  - Tốc độ suy luận prompt cực nhanh: **430.37 tokens/giây** (99.92 ms cho 43 tokens).
  - Cả Python Client và `curl` CLI đều nhận kết quả `HTTP 200 OK` có đầy đủ `top_logprobs=5` theo chuẩn của Thầy.
  - Khởi tạo thành công đường hầm công khai HTTPS qua Cloudflared Tunnel và xuất file `backend_kaggle.yaml`.
  - Kernel hoàn thành trọn vẹn với trạng thái: **`KernelWorkerStatus.COMPLETE`**.

---

## 2. Việc đang kẹt / Chờ đợi (Blocked / Awaiting)

- [ ] **Chốt kết quả Bước 0 từ gói dữ liệu Dũng gửi**:
  - Gói dữ liệu `requested_data_bundle_20261029_FINAL.zip` đã được đối soát và có đầy đủ 100% dữ liệu của cả Devign và ReVeal.
  - Đã chạy thử nghiệm thành công trên Devign (ra $\Delta$MCC = 0.0023, 95% CI chứa 0 $\to$ No meaningful benefit).
  - Sẵn sàng xuất báo cáo chính thức Bước 0 cho cả 2 bộ dữ liệu nộp Thầy.

---

## 3. Số liệu thực nghiệm mới sinh (New Metrics / Results)

### Kết quả Kiểm thử Dry-run 2-Split (Trích xuất từ `runs/step0_mock_2split/diagnostic_summary_devign.md`)
*Ghi chú: Số liệu dưới đây sinh ra từ bộ kiểm thử 2-split (100 mẫu Val, 100 mẫu Test độc lập).*

#### A. Ma trận Sửa - Hỏng (Repair / Harm Matrix trên Test)
| Phân nhóm Nhãn | Tổng số mẫu ($N$) | Ca Sửa ($R_y$) | Ca Hỏng ($H_y$) | Cả hai cùng Đúng | Cả hai cùng Sai | Hiệu quả Sửa Ròng ($R - H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Safe ($y=0$)** | 54 | 8 | 1 | 45 | 0 | **+7** |
| **Vulnerable ($y=1$)** | 45 | 1 | 3 | 41 | 0 | **-2** |
| **Toàn bộ (Total)** | **99** | **9** | **4** | **86** | **0** | **+5** |

#### B. Mô hình Đối chứng Ghép cặp ($P_{pre}$ vs $P_{post}$ trên Test độc lập)
- **Ngưỡng tối ưu khóa từ Validation**: $\tau_{pre}^* = 0.6900, \tau_{post}^* = 0.5000$.
- **$\Delta$MCC ghép cặp (OOF)**: **0.1593** (95% CI: [0.0482, 0.2911])
- **$\Delta$F1 ghép cặp**: **0.0911** (95% CI: [0.0245, 0.1748])
- **$\Delta$AUROC**: **0.0385** (95% CI: [0.0091, 0.0820])
- **Đánh giá thống kê ($\delta$-Verdict)**: 🟢 **BENEFIT (CÓ BỔ SUNG THỰC SỰ $\ge \delta$)**.

#### C. Đường cong Định tuyến Lợi ích (Selective Routing theo Ngân sách $q$)
| Chính sách (Policy) | Tỷ lệ gọi ($q$) | Số truy vấn | MCC | F1-Score | Số ca Sửa ($R$) | Số ca Hỏng ($H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `gate_only` | 0% | 0 | 0.8208 | 0.9032 | — | — |
| `confidence` | 10% | 10 | 0.9192 | 0.9556 | 6 | 1 |
| **`benefit` (Ridge Router)** | **10%** | **10** | **0.8397** | **0.9130** | **1** | **0** |
| `oracle` | 10% | 10 | 1.0000 | 1.0000 | 9 | 0 |
| `random` | 10% | 10 | 0.8260 | 0.9060 | — | — |
| `full_expert` | 100% | 100 | 0.8610 | 0.9247 | — | — |

---

## 3. Bước 1: Hạ tầng Phục vụ Mô hình LLM (Kaggle Cloud 0 USD)

Đã hoàn tất thử nghiệm và đưa vào vận hành thành công hạ tầng tự host mô hình mã nguồn mở trên **Kaggle 2× Tesla T4 GPU (0 USD)** theo đúng đề cương nghiên cứu của Thầy:

### A. Mô hình & Kiến trúc Phục vụ
* **Mô hình mục tiêu**: `Qwen3-Coder-30B-A3B-Instruct` (MoE 30B tham số, 3.3B tham số kích hoạt per token; bản lượng tử hóa GGUF UD-Q4_K_XL dung lượng 16.45 GB).
* **Lưu trữ & Persistence**: Gắn trực tiếp qua Kaggle Model (`tnthnhneee/qwen3-30b-a3b/gguf/coder-instruct-ud-q4_k_xl`), mount tự động vào `/kaggle/input/` trong **0 giây** (không cần tải lại từ Hugging Face).
* **Phân bổ tài nguyên GPU (Layer Split)**:
  - Offload toàn bộ **49/49 layers** của mô hình trải đều qua 2 card GPU:
    * `CUDA0` (Tesla T4 #0): 8,485 MiB VRAM (~8.48 GB / 15 GB).
    * `CUDA1` (Tesla T4 #1): 8,189 MiB VRAM (~8.18 GB / 15 GB).
  - Tổng VRAM an toàn tuyệt đối, không có nguy cơ OOM.
* **Thời gian nạp trọng số**: ~126 giây hoàn tất nạp 16.45 GB và mở cổng HTTP server.
* **Engine phục vụ**: `llama-cpp-python` / `llama.cpp` FastAPI server hỗ trợ đầy đủ OpenAI-compatible API (`/v1/models`, `/v1/chat/completions`).
* **Đặc tính đầu ra**:
  - `top_logprobs=5`, `max_tokens=1`, `seed=42`, `temperature=0.0`.
  - Tính toán trực tiếp điểm xác suất liên tục $s = \frac{p(1)}{p(0) + p(1)}$.
* **Đường hầm mạng**: Cloudflare HTTPS Tunnel công khai (`trycloudflare.com`).
* **File cấu hình**: Tự động sinh `configs/backend_kaggle.yaml` phục vụ gọi từ máy trạm local.


---

## 4. Bước 2: Đóng băng dữ liệu, kho retrieval và specs (Hoàn tất 100%)
- [x] **Trích xuất dữ liệu CPG thô (Streaming Extraction)**:
  - Trích xuất toàn bộ 6 file JSONL thô vào `data/raw/` từ archive:
    * `devign_train.jsonl` (21,854 mẫu), `devign_validation.jsonl` (2,732 mẫu), `devign_test.jsonl` (2,732 mẫu).
    * `reveal_train.jsonl` (18,187 mẫu), `reveal_validation.jsonl` (2,273 mẫu), `reveal_test.jsonl` (2,274 mẫu).
    * Đầy đủ schema: `{id, func, target, nodes, edges, commit_id, project}`.
- [x] **Xây dựng Manifest & Khử trùng Kho Donor (`scripts/build_manifests.py`)**:
  - Chuẩn hóa mã nguồn (bỏ comment, khoảng trắng thừa), băm SHA-256 từng hàm.
  - Lọc trùng tuyệt đối (exact overlap with eval) và loại bỏ nhóm mâu thuẫn nhãn khỏi donor bank.
  - Gắn cờ gần trùng (Jaccard token 3-gram >= 0.9): Devign 607 cờ; ReVeal 998 cờ.
  - Kho donor sạch: Devign (21,711 hàm), ReVeal (17,620 hàm).
  - Băm manifest:
    * Devign: `5a084a10e5c191039e56e351bf8d722fe017424f159a84d6b92be86a1d0f4952`
    * ReVeal: `59498c4a4ab038babe558675c183c2b104b0145590fb0accf8b02cd5440d57f7`
- [x] **Đóng gói Specs (`scripts/build_specs.py`)**:
  - Ghép demo B2 từ lịch sử truy hồi (hoặc donor tương đồng), cặp tương phản B3 (1 vuln + 1 safe), khối khác biệt an ninh `security_difference`, và `h2_evidence` theo ngân sách 1,500 token.
  - Sinh toàn bộ file specs:
    * `data/specs/devign_validation.jsonl` (2,732 dòng)
    * `data/specs/devign_test.jsonl` (2,732 dòng)
    * `data/specs/reveal_validation.jsonl` (2,273 dòng)
    * `data/specs/reveal_test.jsonl` (2,274 dòng)
- [x] **Tạo Validation Subset 600 mẫu phân tầng (Stratified, Seed 42)**:
  - `data/specs/devign_val_subset600.jsonl` (261 vuln, 339 safe, pos_rate=0.4350)
  - `data/specs/reveal_val_subset600.jsonl` (55 vuln, 545 safe, pos_rate=0.0917)

---

## 5. Bước 3: Bộ dựng prompt, 15 Probes và Kiểm tra Toàn vẹn (Hoàn tất 100%)
- [x] **15 Arm / Probes**: Hoàn tất `render_arm` hỗ trợ đủ 15 arm từ B0 đến B3-flip, đảm bảo mỗi probe chỉ khác arm gốc đúng 1 khối (`diff_blocks`).
- [x] **Kiểm thử Unit Test**: 59/59 tests PASSED 100% (`grace_diag_kit/tests`, root regression tests).
- [x] **Dry-run ma trận 15 Arms trên Validation Subset 600**:
  - Chạy `run_matrix.py --dry-run` với tokenizer offline CodeT5 (`grace_diag_kit/tokenizer`) trên 600 mẫu validation của cả Devign (9,000 prompts) và ReVeal (9,000 prompts).
- [x] **Kiểm tra Toàn vẹn Prompt (`prompt_audit.py`)**:
  - `n_label_leak`: **0** trên toàn bộ 15 arms của cả 2 dataset.
  - `any_approx_tokens`: **false** trên toàn bộ 15 arms.
  - `rate_demo_empty`: $\le 1\%$ trên mọi arm (cao nhất 1.0% ở B2-rand, trung bình 0.3% - 0.6%).
  - `rate_graph_missing`: **0.0%**.
  - `tokens_max`: $\le 6,992$ (nằm an toàn trong ngân sách 8,192).
  - Xuất đủ `audit_summary.json`, `audit_rows.csv`, và `manual_sample.jsonl` (30 mẫu/dataset phân tầng theo tam phân vị độ dài $\times$ cờ cắt).

---

## 6. Bước 4: Đăng ký trước Giao thức Nghiên cứu (Preregistration - Hoàn tất 100%)
- [x] **Cập nhật `grace_diag_kit/configs/protocol.yaml`**:
  - Điền `registered_at: "2026-10-31"`.
  - Khóa mã băm `manifest_sha256` cho Devign và ReVeal.
  - Điền ghi chú cấu hình lượng tử hóa mô hình `Qwen3-Coder-30B-A3B-Instruct` GGUF Q4_K_XL (16.45 GB).
- [x] **Soạn thảo `preregistration.md`**:
  - Tuyên bố công khai tiếp xúc dữ liệu test và quy tắc cô lập.
  - Bảng 11 giả thuyết nghiên cứu (H1.1 - H6.1, Bảng 4.3 đề cương).
  - Quy tắc phân tích thống kê Mục 6 (ngưỡng tối ưu $\tau^*$, bootstrap 5000, Holm correction, meta-model $P_{pre}/P_{post}$, routing 5%/10%/25%).
  - Các quy tắc dừng (stopping rules).
  - Bảng băm toàn diện các tệp manifest, tập dữ liệu thô, tập specs và checkpoint.
- [x] **Tạo `CHANGES_AFTER_PREREG.md`**: Khởi tạo nhật ký theo dõi thay đổi sau đăng ký.
- [x] **Đóng gói Git Commit & Gắn Tag**: Tag `prereg-v1`.
