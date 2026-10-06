# Quy Chuẩn & Hướng Dẫn Thiết Lập Nền Thực Nghiệm Thống Nhất (Experimentation & Evaluation Protocol)

> **Mã tài liệu**: `PROTOCOL_EXPERIMENTATION_AND_EVALUATION_GUIDE`  
> **Trạng thái**: Chuẩn hóa nội bộ nhóm nghiên cứu GRACE (Active Protocol)  
> **Áp dụng cho**: Toàn bộ các nhánh phát triển, pipeline thử nghiệm và đối chứng thực nghiệm  

Tài liệu này quy chuẩn hóa toàn diện quy trình kiểm thử, đánh giá và đối soát số liệu nhằm đảm bảo tính toàn vẹn học thuật, khả năng tái lập (Reproducibility) và sự công bằng khi so sánh giữa các phương pháp.

---

## 1. Bản Đồ Tài Nguyên Chuẩn Hóa Trong Codebase

Sau khi đồng bộ mã nguồn mới nhất từ kho lưu trữ Git, toàn bộ các thành phần phục vụ đánh giá và đối soát được tổ chức như sau:

```text
GRACE/
├── data/
│   └── splits/
│       ├── devign_test_ids.json    <- 2,732 Sample IDs chuẩn của Devign Test Set (SHA-256 Hash: 7aa7eddfd9617507)
│       └── reveal_test_ids.json    <- 2,274 Sample IDs chuẩn của ReVeal Test Set (SHA-256 Hash: 4a84c3d301d5e8a7)
├── src/
│   ├── common_evaluator.py         <- Script chấm điểm và reparse duy nhất cho mọi run
│   ├── evaluator.py                <- Module phân tích phản hồi LLM (đã sửa lỗi regex và cách ly invalid output)
│   ├── metrics.py                  <- Bộ đo lường học thuật: F1, MCC, Balanced Accuracy, Trivial Baselines
│   ├── run_pipeline.py             <- Pipeline điều phối (tách riêng train_sample_ratio và test_sample_ratio)
│   └── security_signature_audit.py <- Công cụ chẩn đoán phân phối chữ ký an ninh và đo lường SecSim ngẫu nhiên
├── project_docs/
│   ├── plans/
│   │   ├── GRACE_IMMEDIATE_ACTION_PLAN.md  <- Kế hoạch hành động 3 đợt phản hồi theo ý kiến GVHD
│   │   └── GRACE_RESEARCH_ROADMAP.md       <- Lộ trình nghiên cứu tổng thể các pha
│   └── reports/
│       └── GRACE_EXPERIMENT_RUN_REGISTRY.md <- Bảng quản lý tập trung toàn bộ các lần chạy thực nghiệm
└── tests/
    └── test_parser_audit.py        <- Bộ 35 unit tests kiểm thử các trường hợp biên của parser
```

---

## 2. Hợp Đồng Thực Nghiệm Cần Thống Nhất Giữa Các Thành Viên (Experimental Contract)

Để đảm bảo kết quả so sánh giữa các giải pháp phản ánh đúng năng lực thuật toán mà không bị sai lệch bởi điều kiện ngoại cảnh, các thành viên cần thống nhất 4 nguyên tắc sau:

### 2.1. Thống nhất tập kiểm thử cố định (Canonical Test Splits)
* **Không lấy mẫu ngẫu nhiên độc lập**: Mọi thử nghiệm trên tập kiểm thử phải đối soát chính xác với danh sách định danh trong:
  * Devign: `data/splits/devign_test_ids.json` (Tổng cộng đúng 2,732 hàm: 1,255 Vulnerable, 1,477 Safe).
  * ReVeal: `data/splits/reveal_test_ids.json` (Tổng cộng đúng 2,274 hàm: 230 Vulnerable, 2,044 Safe).
* Khi cần chạy thử trên một tập con nhỏ (Subset) để tiết kiệm thời gian hoặc chi phí API, các thành viên phải cùng trích xuất trên cùng một danh sách `subset_ids.json` có mã băm cố định.

### 2.2. Thống nhất kho mẫu truy xuất (Retrieval Bank Pool)
* Toàn bộ các ví dụ mẫu (*Demonstrations*) chỉ được phép truy xuất từ tập dữ liệu huấn luyện (*Train Set*).
* Mặc định sử dụng toàn bộ kho Train (`train_sample_ratio = 1.0` tương ứng 21,854 mẫu cho Devign và 18,187 mẫu cho ReVeal).
* Khi tiến hành so sánh trực tiếp tác dụng của các cơ chế xếp hạng (*Baseline Retriever vs. Security-Aware Reranker vs. Contrastive Selector*), hai giải pháp **bắt buộc phải nhận cùng một danh sách ứng viên ban đầu** (*Top-50 candidates*) cho từng hàm mục tiêu.

### 2.3. Thống nhất mô hình nền suy luận (Backbone Model & Inference Parameters)
* Việc sử dụng hai mô hình khác nhau (ví dụ một bên dùng `Qwen-Coder`, một bên dùng `Gemma`) chỉ được coi là nghiên cứu độc lập của từng pipeline, **không thể đưa vào cùng một bảng để kết luận giải pháp nào vượt trội**.
* Trong các vòng đối chứng chính (*Core Comparison*), bắt buộc chốt chung một mô hình mở (`Open-Weights LLM`) với cùng cấu hình suy luận:
  * `temperature = 0.0`
  * `seed = 42` (nếu mô hình hỗ trợ)
  * `max_tokens = 256`
  * Cùng quy chuẩn xử lý ngữ cảnh cắt ngắn (*Context Truncation Policy*).

### 2.4. Quy chuẩn bộ chỉ số báo cáo (Academic Evaluation Metrics)
Tuyệt đối không kết luận sự cải tiến chỉ dựa trên một chỉ số đơn lẻ ($F1$ hoặc $Accuracy$). Mọi báo cáo nghiệm thu bắt buộc phải trình bày đồng thời:
1. **Confusion Matrix**: $TP$, $FP$, $TN$, $FN$.
2. **MCC (Matthews Correlation Coefficient)**: Thước đo đánh giá chất lượng phân loại nhị phân không bị ảnh hưởng bởi sự mất cân bằng dữ liệu ($MCC = 0$ tương đương đoán ngẫu nhiên).
3. **Balanced Accuracy**: Trung bình cộng giữa độ phủ trên lớp có lỗi ($Recall$) và lớp an toàn ($Specificity$).
4. **Tỷ lệ dự đoán nhãn dương (Predicted Vulnerable Rate)**: Đo lường mức độ thiên lệch phán đoán của LLM.
5. **Tỷ lệ phản hồi không hợp lệ (Invalid Rate)**: Tỷ lệ mẫu lỗi/rỗng/mâu thuẫn (không bị ép về $0$).
6. **Đường cơ sở tầm thường (Trivial Baselines)**: Đối chứng với bộ phân loại luôn đoán $1$ (*Always-Vulnerable*) và luôn đoán $0$ (*Always-Safe*).

---

## 3. Hướng Dẫn Sử Dụng Bộ Công Cụ Đánh Giá Chung (`common_evaluator.py`)

Bộ công cụ `src/common_evaluator.py` được thiết kế để tự động hóa toàn bộ quá trình tính toán chỉ số, lọc theo tập split chuẩn và hỗ trợ reparse dữ liệu cũ mà **không cần gọi lại LLM**.

### 3.1. Định dạng tệp kết quả đầu vào
Tệp kết quả của bất kỳ pipeline nào (dạng `.json`, `.jsonl` hoặc `.csv`) chỉ cần chứa các trường dữ liệu tối thiểu sau:
* `id`: Mã định danh của hàm kiểm thử (hỗ trợ cả dạng số nguyên `10000` hoặc tên tệp `id_10000_label_False_qemu.c`).
* `target`: Nhãn thực tế (`1` nếu có lỗ hổng, `0` nếu an toàn).
* `prediction`: Nhãn dự đoán của mô hình (`1` hoặc `0`).
* `llm_raw_response` *(khuyến nghị)*: Toàn bộ văn bản thô do LLM trả về trước khi bóc tách.

### 3.2. Lệnh thực thi đánh giá trực tiếp (Direct Evaluation)
Đánh giá tệp kết quả dự đoán và tự động lọc khớp với tập kiểm thử chuẩn:

```powershell
python src/common_evaluator.py `
    --input "duong_dan_file_ket_qua.json" `
    --split_ids "data/splits/devign_test_ids.json" `
    --run_name "Experiment_Name_Devign"
```

*Đầu ra hiển thị trực quan tỷ lệ mẫu khớp với canonical split, Confusion Matrix, $MCC$, $Balanced\ Accuracy$, $F1$, $Precision$, $Recall$ và các baseline đối chứng.*

### 3.3. Lệnh thực thi tái bóc tách phản hồi thô (Reparse Audit Mode)
Nếu tệp kết quả đã lưu trường `llm_raw_response`, thêm cờ `--reparse` để chạy lại bộ parser chuẩn hóa (giúp xử lý triệt để các ca `Non-vulnerable (0)` bị gán nhầm thành `1` và phát hiện các phản hồi lỗi):

```powershell
python src/common_evaluator.py `
    --input "duong_dan_file_ket_qua.json" `
    --split_ids "data/splits/devign_test_ids.json" `
    --run_name "Audit_Reparse_Devign" `
    --reparse `
    --save_reparsed "output/reparsed_audit_results.json"
```

*Đầu ra cung cấp bảng so sánh chi tiết Trước vs Sau Reparse, số lượng nhãn bị thay đổi ($0 \rightarrow 1, 1 \rightarrow 0$) và phân bố phương thức bóc tách.*

---

## 4. Các Đầu Việc Cần Rà Soát & Cập Nhật Sau Khi Đồng Bộ Git

Sau khi kéo mã nguồn về môi trường làm việc, mỗi thành viên cần thực hiện các bước sau:

1. **Kiểm tra tính toàn vẹn của môi trường**:
   Chạy lệnh kiểm thử đơn vị để xác nhận toàn bộ hệ thống hoạt động chính xác:
   ```powershell
   $env:PYTHONPATH="src;."
   pytest tests/test_parser_audit.py tests/test_stage3_eval.py
   ```
   *(Yêu cầu: Tất cả các test cases phải đạt trạng thái PASSED).*

2. **Cập nhật thông tin vào bảng quản lý thực nghiệm**:
   Mở tệp `project_docs/reports/GRACE_EXPERIMENT_RUN_REGISTRY.md` và bổ sung thông tin cho các phiên chạy trước đó thuộc phạm vi phụ trách:
   * Mã Git Commit tương ứng.
   * Cấu hình Backbone Model & Nhà cung cấp API.
   * Số lượng mẫu thực tế và đường dẫn lưu trữ file kết quả.
   * Trạng thái đối soát nhãn.

3. **Chốt danh sách các cấu hình cho vòng ablation tiếp theo**:
   Trước khi triển khai các phiên chạy tốn kém tài nguyên, các thành viên thống nhất cặp cấu hình cần kiểm chứng giả thuyết (ưu tiên cặp tối thiểu $B2$ vs $B3$ theo Action Plan: *Baseline Reranking vs. Security-Aware Reranking* trên 1 demonstration cố định).
