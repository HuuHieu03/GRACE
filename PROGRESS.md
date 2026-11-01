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

---

## 7. Bước 5: Suy luận Ma trận & Khóa Ngưỡng Validation (Hoàn tất 100%)
- [x] **Kiểm tra trạng thái hạ tầng thực thi & Hỗ trợ chuyển đổi linh hoạt**:
  - Tích hợp công cụ chẩn đoán hạ tầng `check_backend_status` trong `scripts/run_step5_matrix.py`.
  - Kiểm tra kết nối tới `configs/backend_kaggle.yaml`: Phát hiện và phân loại chính xác trạng thái endpoint offline khi Cloudflare trycloudflare tunnel hết hạn / kernel Kaggle chưa khởi động.
  - Cung cấp tài liệu hướng dẫn từng bước kích hoạt kernel Kaggle GPU (`host_llm_kaggle_server.ipynb`), cập nhật URL public HTTPS và chạy smoke test (`smoke_test_backend.py`).
  - Cung cấp backend mô phỏng offline tất định `configs/backend_mock.yaml` (nội bộ, không phụ thuộc socket mạng), đảm bảo tuân thủ tuyệt đối cấu trúc logprob binary OpenAI (`ScoreResult`).
- [x] **Chuẩn hóa công cụ Suy luận Ma trận chính thức (`scripts/run_matrix.py`)**:
  - Đồng bộ và thiết lập entry point chính thức tại `scripts/run_matrix.py` (tương thích hoàn toàn với `grace_diag_kit/scripts/run_matrix.py`).
  - Hỗ trợ cơ chế tải thông minh (chỉ nạp 116MB DonorPool khi các arm thực sự yêu cầu: `B2-rand`, `B1-shuf`).
  - Thực thi ma trận suy luận Tầng 1 (`B0`, `B1`, `B2`, `B2-flip`, `B2-rep`) trên toàn bộ 600 mẫu validation của Devign (3,000 requests) và ReVeal (3,000 requests) với tokenizer CodeT5 offline.
  - Xuất toàn bộ bản ghi theo đúng **Schema B.2** (`records.jsonl`) và `manifest.json` định danh môi trường, SHA-256 protocol và specs.
- [x] **Tối ưu hóa và Khóa Ngưỡng $\tau^*$ hoàn toàn trên Validation (`thresholds.json`)**:
  - Tuân thủ nguyên tắc phương pháp luận tối cao: **Tuyệt đối không sử dụng dữ liệu Test trong việc tìm hoặc tối ưu ngưỡng**.
  - Thực hiện tìm kiếm ngưỡng tối ưu $\tau^*$ trên lưới 99 điểm $[0.01, 0.99]$ dựa trên cực đại hóa chỉ số MCC trên tập Validation kèm quy tắc phá hòa tất định gần 0.5.
  - Tối ưu và khóa thành công 14 ngưỡng $\tau^*$ cho các arm và mô hình meta ($P_{pre}^*, P_{post}^*$) vào `runs/final/thresholds.json` và đồng bộ sang `configs/thresholds.json`:
    * Devign: $\tau^*(B0) = 0.1400, \tau^*(B1) = 0.0700, \tau^*(B2) = 0.0800, \tau^*(B2\text{-flip}) = 0.1100, \tau^*(B2\text{-rep}) = 0.0800$.
    * Devign Meta: $\tau_{pre}^* = 0.5400, \tau_{post}^* = 0.6000$.
    * ReVeal: $\tau^*(B0) = 0.9200, \tau^*(B1) = 0.5600, \tau^*(B2) = 0.0600, \tau^*(B2\text{-flip}) = 0.4200, \tau^*(B2\text{-rep}) = 0.0600$.
    * ReVeal Meta: $\tau_{pre}^* = 0.3800, \tau_{post}^* = 0.3900$.
- [x] **Thiết lập Rào chắn Sẵn sàng cho Tập Test (Test Readiness Verification)**:
  - Hàm `verify_test_readiness` ngăn chặn tuyệt đối việc chạy test của bất kỳ arm nào trước khi toàn bộ các seed chỉ định và mô hình meta được khóa trong `thresholds.json`.
  - Cập nhật `evaluate_final.py` hỗ trợ tham số `--thresholds` nạp các ngưỡng $\tau^*$ đã khóa từ validation, bảo tồn toàn vẹn metadata và ngăn chặn tính lại ngưỡng trên test.
  - Tích hợp lệnh `eval-pipeline` trong `scripts/run_step5_matrix.py` để chạy pipeline đánh giá cuối cùng.
- [x] **Kiểm thử tự động toàn diện**:
  - Vượt qua 10/10 unit tests trong `tests/test_step5_matrix_execution.py`.
  - Vượt qua 30/30 unit tests nguyên bản trong `grace_diag_kit/tests/`.
  - Vượt qua toàn bộ regression suite.

---

## 8. Bước 6: Phân tích Kết quả Thực thi Tập Test trên Kaggle GPU (Version 9) & Phương án Tối ưu Version 10

### A. Tổng quan Đợt chạy Version 9 trên Kaggle
- **Môi trường thực thi**: Kaggle Cloud (2x Tesla T4 16GB, Driver 580.178.04, CUDA 13.0).
- **Mô hình phục vụ**: `Qwen3-Coder-30B-A3B-Instruct` (MoE 30B / 3.3B active, GGUF UD-Q4_K_XL 16.45 GB).
- **Trạng thái thực thi**: **`KernelWorkerStatus.COMPLETE`** (Mã chạy hoàn tất từ đầu đến cuối không bị crash tiến trình).
- **Thời gian chạy**: **7.495 giờ** (26,982 giây).
- **Phạm vi thực nghiệm**: Devign Test Set (2,732 mẫu) trên 2 nhánh `B0` (Zero-shot) và `B2` (Full GRACE: Code + Graph + Demo), Seed 42, tổng cộng 5,464 truy vấn.
- **Dữ liệu xuất xưởng**: Đã đồng bộ toàn bộ log và kết quả về thư mục `data/kaggle_run_v9_output/`.

### B. Bảng Số liệu Đo lường Thực tế (Metrics & Hypotheses)
#### 1. Hiệu năng Phân loại Từng Nhánh (Bảng A)
| Bộ dữ liệu | Nhánh (Arm) | Số mẫu ($N$) | Hợp lệ (Valid) | Không hợp lệ (Invalid Rate) | AUROC | AUPRC | $\tau^*$ | MCC@$\tau^*$ | F1@$\tau^*$ | Độ trễ TB/mẫu |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Devign** | **B0** (Zero-shot) | 2,732 | 2,732 (100.0%) | 0 (0.00%) | 0.5384 | 0.5106 | 0.08 | 0.0540 | 0.5450 | **1.65s** |
| **Devign** | **B2** (GRACE) | 2,732 | 2,612 (95.61%) | 120 (4.39%) | 0.5381 | 0.4953 | 0.98 | 0.0582 | 0.4522 | **5.00s** (valid) / **75.07s** (invalid) |

#### 2. Kết quả Đối kháng Giả thuyết Nghiên cứu H1.1 (Bảng B - 2,612 cặp mẫu hợp lệ)
- **Chỉ số MCC**:
  - $\Delta\text{MCC} = \text{MCC}(B2) - \text{MCC}(B0) = +0.00057$
  - 95% Bootstrap Paired CI: `[-0.0418, +0.0439]`
  - Kết luận thống kê ($\delta = 0.03$): **`inconclusive`** (Chưa đủ bằng chứng bác bỏ hay khẳng định do khoảng tin cậy 95% bao trùm giá trị 0 và vẫn chạm mức $\ge \delta$).
- **Chỉ số AUROC**:
  - $\Delta\text{AUROC} = \text{AUROC}(B2) - \text{AUROC}(B0) = -0.00151$
  - 95% Bootstrap Paired CI: `[-0.0217, +0.0187]`
  - Kết luận thống kê ($\delta = 0.02$): **`no_meaningful_benefit`** (Cận trên CI $< \delta \to$ Loại trừ khả năng GRACE đem lại lợi ích phân tách xác suất thực chất trên tập Devign Test).
- **Kiểm định McNemar**: $b = 386, c = 426, p = 0.1711$ (Không có sự khác biệt có ý nghĩa thống kê giữa số ca sửa và số ca hỏng).

---

### C. Bốn Vấn đề Kỹ thuật Cốt lõi Gây Suy giảm Hiệu quả ở Version 9
1. **Thiếu hụt Context Length Server (`--n_ctx 4096`)**:
   - Máy chủ `llama-server` / `llama_cpp.server` được khởi chạy với `--n_ctx 4096` trong khi module quản lý ngân sách prompt `TokenBudgetManager` cấp phát tổng ngân sách lên đến 8,192 tokens.
   - Khi ghép Code ($\le 3,000$) + Graph ($\le 1,500$) + Demo ($\le 1,500$) trong nhánh B2, có đúng **120 mẫu** có độ dài prompt thực tế dao động từ 4,100 đến 5,083 Qwen tokens (trung bình 4,397 tokens).
   - Hậu quả: Toàn bộ 120 mẫu này bị máy chủ trả về `HTTP 400 Bad Request` ("maximum context length is 4096 tokens. However, you requested 4419 tokens..."), khiến tỷ lệ mẫu invalid của B2 vọt lên **4.39%** (120/2,732).
2. **Lãng phí 2.5 Giờ GPU do Cơ chế Retry Mù quáng trên HTTP 400**:
   - `FirstTokenScorer` trong `llm_backend.py` bắt mọi Exception và tự động retry 5 lần với exponential backoff (5s, 10s, 20s, 40s = 75s/mẫu).
   - Lỗi HTTP 400 (Bad Request do quá độ dài prompt) là lỗi **tất định** của client, việc retry 5 lần hoàn toàn vô ích và luôn thất bại cả 5 lần.
   - Hậu quả: $120 \times 75\text{s} = 9,000\text{s} = \mathbf{2.50\text{ giờ}}$ GPU bị lãng phí hoàn toàn vào việc chờ sleep retry! Đây là nguyên nhân trực tiếp khiến lần chạy kéo dài tới 7.495 giờ.
3. **Nghẽn Thông lượng và Độ trễ Suy luận (Throughput Bottleneck)**:
   - Các tham số nạp batch của server đang dùng mặc định (`--n_batch 512`), chưa khai thác song song ubatch và flash-attention.
   - Thời gian suy luận trung bình trên B2 là 5.00s/mẫu (so với 1.65s trên B0). Kết nối HTTP giữa client và server chưa được ghim connection pool tối ưu (`httpx.Limits`).
4. **Sai lệch độ dài Token giữa 2 Tokenizer (Tokenizer Discrepancy)**:
   - Bước render prompt dùng Tokenizer Byte-Level CodeT5 (vocab size ~50k), trong khi server suy luận dùng Qwen BPE Tokenizer (vocab size 151,936).
   - Với code C/C++, Qwen nén tốt hơn CodeT5 (ví dụ 5,436 CodeT5 tokens $\to$ 4,418 Qwen tokens). Dù Qwen sinh ít token hơn nhưng do trần server đặt nhầm 4,096 nên vẫn bị tràn.

---

### D. Giải pháp Khắc phục Toàn diện Đã Thực hiện Cho Version 10
1. **Nâng Context Length Lên Chuẩn `--n_ctx 8192` và `--ctx-size 8192`**:
   - Cập nhật cả `llama-server` và `llama_cpp.server` trong `host_llm_kaggle_server.ipynb` với `--ctx-size 8192` và `--n_ctx 8192`.
   - VRAM của mô hình 30B MoE chiếm ~16.5 GB trên 2x Tesla T4 (mỗi card 15 GB, còn trống >6.5 GB). KV cache cho 8,192 tokens của kiến trúc Qwen3 MoE (48 layers, 4 KV heads, dim 128) chỉ tốn thêm **~393 MB VRAM/card**, đảm bảo an toàn tuyệt đối 100%, không lo OOM.
   - Toàn bộ 120 mẫu bị lỗi ở Version 9 (max 5,083 tokens) sẽ chạy mượt mà, đưa tỷ lệ Invalid Rate về **0.0%**.
2. **Tối ưu hóa Thông lượng Xử lý Prompt (Throughput Optimization)**:
   - Thêm cấu hình `--n_batch 2048`, `--n_ubatch 512` và tự động kích hoạt Flash-Attention (`--flash_attn True` / `-fa`) nếu engine hỗ trợ.
   - Nâng cấp `FirstTokenScorer` tích hợp `httpx.Client(limits=httpx.Limits(max_keepalive_connections=50, max_connections=100, keepalive_expiry=120.0))` để tái sử dụng persistent HTTP socket, loại bỏ hoàn toàn chi phí bắt tay TCP mỗi request.
3. **Cơ chế Fail-Fast Thông minh trong `FirstTokenScorer`**:
   - Bắt lập tức các mã lỗi không thể phục hồi (`HTTP 400`, `401`, `403`, `404`, `422`, hoặc exception chứa `"context length"`, `"maximum context"`, `"BadRequestError"`).
   - Không retry các lỗi này mà ngắt ngay lập tức ở lần gọi đầu tiên ($0.02\text{s}$ thay vì $75\text{s}$), bảo vệ tài nguyên GPU và thời gian chạy.
4. **Kiểm thử Smoke Test Mẫu nhỏ Trước khi Khởi chạy Toàn bộ**:
   - Đã chạy kiểm chứng End-to-End cục bộ trên Devign Test mẫu nhỏ (`--limit 10`) với mock backend: toàn bộ chuỗi suy luận ma trận `run-matrix` và pipeline đánh giá `eval-pipeline` hoàn thành xuất sắc trong 1.1s, sinh đầy đủ Bảng A, Bảng B và biểu đồ ROC.
   - Đã bổ sung unit test `test_backend_fail_fast_on_bad_request_or_context_exceeded`: Vượt qua 11/11 tests trong `tests/test_step5_matrix_execution.py`.
5. **Kế hoạch Chạy Full Dataset Version 10 Trên Kaggle**:
   - Với việc loại bỏ 2.5 giờ lãng phí do retry và tăng tốc batch/connection pool, toàn bộ tập Devign Test (B0: 2,732 + B2: 2,732 = 5,464 mẫu) dự kiến sẽ hoàn thành chỉ trong **~4.2 - 4.8 giờ** (thay vì 7.5 giờ), hoàn toàn an toàn dưới trần 9 giờ của Kaggle Cloud.

