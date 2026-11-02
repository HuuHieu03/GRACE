# TÀI LIỆU HƯỚNG DẪN KIỂM TOÁN VÀ ĐỐI SOÁT ĐỀ TÀI GRACE (AUDIT README)

> **Dự án**: GRACE - Empowering LLM-based Vulnerability Detection via Graph-Augmented Contrastive Learning  
> **Phiên bản nghiệm thu**: Version 10 (Chạy suy luận độc lập trên Kaggle Linux GPU 2× T4)  
> **Ngày đóng gói**: Tháng 11/2026  
> **Người thực hiện**: Nhóm nghiên cứu sinh viên (Hiếu & Dũng)  
> **Người hướng dẫn / Đơn vị kiểm toán**: Thầy hướng dẫn nghiên cứu khoa học  

---

## 1. Mục Đích Gói Tài Liệu Kiểm Toán (Audit Package Purpose)

Gói lưu trữ này được đóng gói đặc biệt nhằm mục đích **phục vụ công tác kiểm toán (audit) độc lập, khách quan và minh bạch**, đáp ứng đầy đủ các yêu cầu sau:
1. **Lưu trữ toàn vẹn tất cả tài liệu, đề cương và công cụ Thầy hướng dẫn gửi**.
2. **Cung cấp toàn bộ mã nguồn sạch, các script điều phối, kiểm thử (tests) và cấu hình khóa**.
3. **Cung cấp dữ liệu offline chuẩn hóa để tái lập Bước 0 (Step 0) và specs nén cho Bước 5 (Step 5)**.
4. **Cung cấp kết quả thực nghiệm hoàn chỉnh nhất (Version 10 Run)** với 100% bản ghi hợp lệ (`invalid_rate = 0.00%`), bảng thống kê A, bảng đối chứng B, kiểm định McNemar, Cluster Bootstrap CI và đồ thị ROC / Operating points.
5. **Loại bỏ triệt để các tệp dư thừa, tệp rác, lịch sử git nặng nề và các tệp cache tạm thời** để gói gọn nhẹ, rõ ràng và dễ đối soát.

---

## 2. Danh Mục Tài Liệu Của Thầy Hướng Dẫn (Teacher's Documents)

Toàn bộ các tài liệu do Thầy gửi cho nhóm nghiên cứu đều được bảo toàn nguyên vẹn trong thư mục `00_Reports_and_Docs/` và `project_docs/`:

### A. Tài liệu đề cương & Bài báo gốc (`00_Reports_and_Docs/`)
- [`De_cuong_nghien_cuu_GRACE_hop_nhat.pdf`](file:///00_Reports_and_Docs/De_cuong_nghien_cuu_GRACE_hop_nhat.pdf): **Đề cương nghiên cứu GRACE hợp nhất (Tài liệu chỉ đạo cốt lõi của Thầy)**, quy định chi tiết 5 Bước triển khai thực nghiệm chuẩn hóa.
- [`GRACE_De_cuong_nghien_cuu_tong_hop.pdf`](file:///00_Reports_and_Docs/GRACE_De_cuong_nghien_cuu_tong_hop.pdf): Đề cương nghiên cứu tổng hợp ban đầu.
- [`GRACE_Empowering_LLM_Original_Paper.pdf`](file:///00_Reports_and_Docs/GRACE_Empowering_LLM_Original_Paper.pdf): Bài báo gốc của tác giả đề xuất kiến trúc GRACE.
- [`grace_diag_kit.zip`](file:///00_Reports_and_Docs/grace_diag_kit.zip): Gói công cụ chẩn đoán ban đầu Thầy chuyển giao.
- [`GRACE_research_kit.zip`](file:///00_Reports_and_Docs/GRACE_research_kit.zip): Gói nghiên cứu bổ trợ từ Thầy.

### B. Các báo cáo phân tích mốc & phản hồi (`00_Reports_and_Docs/` & `project_docs/`)
- `00_Reports_and_Docs/01_Stage5_Contrastive_Benchmark_Report.md`: Báo cáo benchmark giai đoạn 5.
- `00_Reports_and_Docs/02_Baseline_Reproduction_and_Discrepancy_Report.md`: Báo cáo tái lập baseline và các độ lệch quan sát.
- `00_Reports_and_Docs/03_Retrieval_Failure_Analysis_Report.md`: Báo cáo phân tích lỗi truy vấn (retrieval failure).
- `00_Reports_and_Docs/04_Vulnerability_Aware_Contrastive_Design.md`: Thiết kế truy vấn tương phản nhạy lỗ hổng.
- `00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md`: Báo cáo tiến độ nghiệm thu chính thức gửi Thầy.
- `00_Reports_and_Docs/bao_cao_chung_Dung_Hieu_gui_thay.md`: Báo cáo chung của 2 sinh viên gửi Thầy.
- `project_docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md`: Yêu cầu chi tiết từ Thầy hướng dẫn cho 2 sinh viên.
- `project_docs/GRACE_phanhoibaocaoDungHieu.txt`: Toàn văn các ý kiến phản hồi, nhận xét của Thầy.
- `project_docs/supervisor_questions_and_notes.md`: Tổng hợp câu hỏi và ghi chú của Thầy.
- `project_docs/PROTOCOL_EXPERIMENTATION_AND_EVALUATION_GUIDE.md`: Bản hướng dẫn chi tiết quy trình thực nghiệm.

---

## 3. Cấu Trúc Mã Nguồn & Tổ Chức Dự Án

| Thư mục / Tệp tin | Vai trò & Nội dung chi tiết |
| :--- | :--- |
| `src/` | **Mã nguồn cốt lõi**: Bao gồm các mô-đun tiền xử lý đồ thị CPG, trích xuất đặc trưng CodeT5, công cụ truy xuất tương phản (retrieval), bộ sinh prompt (prompt engine) và client suy luận LLM. |
| `grace_diag_kit/` | **Bộ công cụ chẩn đoán chuẩn hóa**: Đã tích hợp các module `probes.py`, `stats.py`, `token_budget.py`, `prompt_audit.py`, script `run_matrix.py` và từ điển BPE tokenizer. |
| `scripts/` | **Tập lệnh vận hành**: Chạy Bước 0 offline (`run_step0_offline_diagnostic.py`), tạo dữ liệu specs (`build_specs.py`), kiểm tra tuân thủ hợp đồng (`verify_stage4_contracts.py`), đánh giá kết quả (`evaluate_runs.py`), tải artifacts Kaggle (`download_v10_artifacts.py`). |
| `configs/` | **Tệp cấu hình khóa (Locked configs)**: `protocol.yaml` (giao thức), `arms.yaml` (định nghĩa 14 nghiệm thức), `thresholds.json` (bảng khóa ngưỡng từ validation), `backend_kaggle.yaml` (cấu hình LLM backend). |
| `tests/` | **669 bài kiểm thử tự động (Pytest)**: Kiểm toán tuân thủ hợp đồng dữ liệu, ngăn ngừa rò rỉ mã nguồn (code leakage), kiểm định tính chính xác của công thức thống kê (Bootstrap, McNemar). |
| `kaggle_notebooks/` | **Môi trường tái lập trên Cloud**: Notebook `host_llm_kaggle_server.ipynb` triển khai `llama-server` (`Qwen3-Coder-30B-A3B-Instruct`, UD-Q4_K_XL, 16.45 GB, `--n_ctx 8192`) và chạy ma trận suy luận tự động. |
| `01_Reproduce_Notebooks/` | **Notebooks tái lập Baseline**: Devign, ReVeal và mô phỏng Stage 5 Contrastive. |
| `02_Baseline_Code_Author/` | **Mã nguồn tác giả gốc**: Toàn bộ script Python gốc của tác giả trong `author_original_scripts/` và `baseline_code_text/`. |
| `data/b0_offline_dungs_data/`| **Dữ liệu Bước 0 offline**: Lưu trữ dự đoán của mô hình và nhãn gốc của Devign & ReVeal, cho phép kiểm toán Bước 0 tức thì. |
| `data/specs/` | **Bộ đặc tả suy luận nén (`*.jsonl.gz`)**: Chứa dữ liệu prompt đầu vào cho từng tập mẫu. |
| `data/manifests/` | **Dữ liệu ghép cặp & thống kê**: Manifests ghép cặp donor và phân tách tập dữ liệu. |
| `runs/final/` | **Kết quả thực nghiệm hoàn chỉnh (Version 10)**: Chứa bản ghi dự đoán đầy đủ và báo cáo đánh giá cuối cùng. |
| `output/` | **Báo cáo kiểm toán chuyên đề**: Kiểm toán rò rỉ mã nguồn (`code_leakage_audit_report.json`), kiểm định tráo nhãn (`label_flip_test_report.json`), phân tích cắt bỏ ablation (`stage3/`). |
| `preregistration.md` | **Biên bản đăng ký trước thực nghiệm (Preregistration Protocol)**: Đóng băng giả thuyết nghiên cứu (H1.1, H1.2) trước khi chạy suy luận trên tập Test. |
| `PROGRESS.md` | **Nhật ký tiến độ toàn diện**: Ghi lại chi tiết từng bước chuyển đổi và kết quả của từng vòng chạy (Version 1 đến 10). |

---

## 4. Tóm Tắt Kết Quả Thực Nghiệm Chính Thức (Version 10 Run)

Thực nghiệm Version 10 được thực hiện trên tập kiểm thử **Devign Test ($N = 2,732$ mẫu)** với mô hình suy luận `Qwen3-Coder-30B-A3B-Instruct` (lượng tử hóa UD-Q4_K_XL, kích thước 16.45 GB, chạy trên `llama-server` với `--n_ctx 8192`) trên GPU T4 kép của Kaggle, giải quyết triệt để lỗi tràn ngữ cảnh và lỗi định dạng.

### Bảng A: Hiệu Năng Tại Ngưỡng Tối Ưu Khóa Từ Tập Validation ($\tau^*$)

| Phân Vùng | Cánh Thử Nghiệm (Arm) | Ngưỡng Khóa $\tau^*$ | AUROC | AUPRC | MCC | Balanced Acc (BA) | F1-Score | Ma Trận Nhầm Lẫn (TP / FP / TN / FN) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Devign Test** | **B0 (Zero-shot Baseline)** | $0.08$ | 0.5392 | 0.5109 | 0.0484 | 0.5238 | 0.5403 | TP=597, FP=617, TN=860, FN=658 |
| **Devign Test** | **B2 (GRACE: Code+CPG+Demo)** | $0.98$ | **0.5394** | 0.4940 | **0.0743** | **0.5358** | 0.4478 | TP=779, FP=834, TN=643, FN=476 |

### Bảng B: Kiểm Định Tương Phản Giả Thuyết H1.1 (Devign Test B0 vs B2)

- **Độ chênh lệch $\Delta\text{AUROC}$**: $+0.000244$
  - *95% Cluster Bootstrap CI*: $[-0.019390, +0.020274]$
- **Độ chênh lệch $\Delta\text{MCC}$**: $+0.025925$
  - *95% Cluster Bootstrap CI*: $[-0.020615, +0.070114]$
- **Kiểm định McNemar**:
  - $b$ (B0 đúng, B2 sai): $438$
  - $c$ (B2 đúng, B0 sai): $522$
  - Thống kê $\chi^2 = 7.18$, **$p\text{-value} = 0.007388 < 0.01$**
- **Kết luận khoa học (Scientific Verdict)**:
  - Kiểm định McNemar đạt mức ý nghĩa thống kê cao ($p < 0.01$), chứng minh việc bổ sung CPG và Retrieval mang lại sự thay đổi hành vi rõ rệt trong việc phân loại của mô hình.
  - Tuy nhiên, do khoảng tin cậy 95% của $\Delta\text{AUROC}$ và $\Delta\text{MCC}$ vẫn giao cắt với 0, kết luận thực nghiệm được xếp loại khách quan là **`inconclusive`** theo đúng tiêu chuẩn preregistration nghiêm ngặt.

---

## 5. Hướng Dẫn Tái Lập (Reproduction Instructions)

### Bước 1: Kiểm toán và chạy bộ kiểm thử đơn vị
```bash
pytest tests/ -v
```
Toàn bộ 669 bài test sẽ vượt qua (PASS), xác nhận tính toàn vẹn của mã nguồn và thuật toán thống kê.

### Bước 2: Tái lập kiểm định Bước 0 Offline (Step 0)
```bash
python scripts/run_step0_offline_diagnostic.py --dataset devign
python scripts/run_step0_offline_diagnostic.py --dataset reveal
```
Báo cáo chẩn đoán Bước 0 sẽ được sinh tự động tại `runs/step0_real_devign/` và `runs/step0_real_reveal/`.

### Bước 3: Đánh giá và xuất Bảng A, Bảng B
```bash
python scripts/evaluate_runs.py
```
Kết quả và đồ thị sẽ được cập nhật trong `runs/final/evaluation/`.

---

## 6. Danh Mục Các Thành Phần Đã Lược Bỏ (Exclusion Rationale)

Để đảm bảo gói kiểm toán gọn gàng, trong sáng và không chứa tệp rác thừa, các thành phần sau đã được loại trừ một cách có chủ đích:
1. **Lịch sử Git (`.git/`, ~236 MB)**: Không cần thiết cho việc đối soát mã nguồn và tài liệu.
2. **Bộ nhớ đệm tạm thời (`runs/**/_cache/`, >4,800 tệp JSON)**: Các tệp cache tạm của từng request API đã được lược bỏ vì bản ghi kết quả đầy đủ đã nằm tại `records.jsonl`.
3. **Bytecode và cache trình dịch (`__pycache__/`, `*.pyc`, `.pytest_cache/`)**.
4. **Cơ sở dữ liệu trích xuất Joern thô (`data/preproceed/joern/`, ~8.9 GB)**: Dữ liệu đồ thị thô có kích thước quá lớn, trong khi các vector biểu diễn và specs đã được nén trong `data/specs/*.jsonl.gz`.
5. **Tệp zip nén mã gốc tác giả (`02_Baseline_Code_Author/GRACE_source_code_baseline.zip`, ~310 MB)**: Lược bỏ tệp nén dung lượng lớn vì toàn bộ script Python trích xuất từ tác giả đã nằm sẵn trong `author_original_scripts/` và `baseline_code_text/`.
6. **Tệp zip chạy thử cũ của Dũng (`00_Reports_and_Docs/requested_data_bundle_20261029_FINAL.zip`, ~473 MB)**: Toàn bộ dữ liệu phục vụ tái lập Bước 0 đã được chuẩn hóa và tinh gọn tại `data/b0_offline_dungs_data/`.
7. **Tệp cấu hình nhạy cảm (`.env`, `.gcp_key.json`)**: Đảm bảo an toàn thông tin bảo mật.
