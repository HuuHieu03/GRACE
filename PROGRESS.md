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

## 2. Việc đang kẹt / Chờ đợi (Blocked / Awaiting)

- [ ] **Chờ Dũng xuất 4 tệp dữ liệu thực nghiệm H3-B**:
  - Để hoàn thành kết xuất báo cáo chính thức Bước 0 cho Thầy, Dũng cần xuất 4 file cho mỗi dataset (Devign và ReVeal) theo đúng hướng dẫn tại `INTEGRATION.md`:
    1. `gate_validation.csv` & `gate_test.csv` (các cột `id, y, p_gate`).
    2. `xpre_validation.npz` & `xpre_test.npz` (mảng 34 đặc trưng mã nguồn).
    3. File kết quả dự đoán của LLM (`predictions.jsonl` hoặc `records.jsonl`).
  - *(Khi có file, script `scripts/run_step0_offline_diagnostic.py` chỉ cần 30 giây để hoàn tất toàn bộ phân tích).*
- [ ] **Thực hiện pilot smoke test trên Kaggle GPU**:
  - Cần chạy notebook `host_llm_kaggle_server.ipynb` trên session Kaggle active để kiểm tra tốc độ thực tế của `qwen2.5-coder-7b-instruct` và `qwen2.5-coder-32b-instruct-q4`.

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
