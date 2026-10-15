# Kế Hoạch Hành Động Chi Tiết — Đáp Ứng Toàn Diện Yêu Cầu Của Giảng Viên Hướng Dẫn

> **Mã tài liệu**: `PLAN_SUPERVISOR_REQUIREMENTS_EXECUTION_20261014`  
> **Thời gian khởi tạo**: 14/10/2026  
> **Căn cứ chỉ đạo**: [`project_docs/docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md`](../docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md)  
> **Trạng thái**: Kế hoạch chính thức thi công (Active Implementation Plan)  

---

## 1. Tôn Chỉ & Nguyên Tắc Cốt Lõi (Non-Negotiable Principles)

1. **Tuyệt đối chưa chạy lại full benchmark lớn**: Không chạy 2,732 mẫu Devign hay 2,274 mẫu ReVeal ở thời điểm này.
2. **Không kết luận dựa trên một chỉ số đơn lẻ**: Mọi bảng biểu đều phải đọc kèm $Confusion\ Matrix$, $MCC$, $Balanced\ Accuracy$, $Predicted\ Vulnerable\ Rate$, và 2 đường cơ sở $Always-Vulnerable$ / $Always-Safe$. F1 cao mà $MCC \approx 0$ là tín hiệu suy biến/đoán mò.
3. **Mỗi ablation chỉ đổi đúng 1 thành phần duy nhất**: Cô lập hoàn toàn các yếu tố ngoại cảnh (giữ nguyên target IDs, full retrieval pool, candidate list, model backbone, prompt order, truncation limit).
4. **Nghiên cứu thất bại cũng là một đóng góp học thuật có giá trị**: Nếu sau khi kiểm tra nghiêm ngặt mà mô hình không có tín hiệu phân biệt, trọng tâm sẽ chuyển sang phân tích lỗi (*Failure Mode Analysis*) để giải thích vì sao Code Similarity thất bại trong việc phát hiện lỗ hổng.

---

## 2. Ma Trận Công Việc Phân Cấp Theo 3 Đợt

```text
                                LỘ TRÌNH 3 ĐỢT THỰC THI
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ĐỢT 1: LÀM SẠCH NỀN THỰC NGHIỆM & KIỂM TOÁN NỘI BỘ (ĐANG THỰC HIỆN - TUẦN NÀY)         │
│  - Hoàn thiện các chốt chặn kỹ thuật trong Codebase (Mock, Checkpoint, Empty Set Jaccard)│
│  - Reparse toàn bộ raw response cũ, phân tích nhãn đổi & ảnh hưởng của bug parser cũ    │
│  - Thống kê tỷ lệ Fallback của Contrastive Selector & Audit data-flow security rules   │
│  - Soát rò rỉ dữ liệu (Data Leakage & Duplicate Code giữa Train và Test)               │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│ ĐỢT 2: KIỂM CHỨNG MỘT GIẢ THUYẾT DUY NHẤT & HỆ THỐNG ĐÁNH GIÁ 3 CHÂN KIỀNG (TUẦN TỚI)   │
│  - Thí nghiệm Đảo Nhãn Demo (Label-Flip Control): Đo LLM học code hay học vẹt nhãn     │
│  - Ablation B2 vs B3 trên Dev Set (100-200 mẫu): Đo tác dụng cô lập của Security Reranker│
│  - Chấm mù độc lập (Blind Human Review: 50 Devign + 50 ReVeal) giữa 2 bạn (Cohen Kappa)│
│  - Synthetic Ground-Truth Verification: 10 ca vi mô chuẩn hóa 100% ground-truth an ninh│
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│ ĐỢT 3: XÁC NHẬN, ĐO KHOẢNG TIN CẬY & ĐÓNG GÓI CÔNG BỐ KHOA HỌC                         │
│  - Ghép cặp Bootstrap 95% Confidence Interval & Kiểm định McNemar                      │
│  - Mở rộng sang cặp tương phản B5 vs B6 (nếu B2 vs B3 chứng minh có tín hiệu thật)     │
│  - Viết báo cáo khoa học giải thích cơ chế thành công hoặc phân tích failure mode      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Kế Hoạch Chi Tiết Đợt 1 — Làm Sạch Nền & Kiểm Toán Kỹ Thuật

Mục tiêu của Đợt 1 là hoàn thiện triệt để toàn bộ các chốt chặn học thuật trước khi bất kỳ một lời gọi LLM nào được thực hiện.

### Nhiệm vụ 1.1: Khắc phục 3 chốt chặn kỹ thuật trong Codebase Hiếu
* **Hạng mục A (Loại bỏ Fail-to-Mock âm thầm)**:
  * *Vị trí*: [`src/evaluator.py`](../../src/evaluator.py) class `LLMEvaluator`.
  * *Hành vi cũ*: Khi thiếu API key hoặc lỗi kết nối, chương trình log warning và tự chuyển `self.use_mock = True`.
  * *Hành vi mới*: Bắt buộc ném ngoại lệ rõ ràng (`raise RuntimeError("Thiếu API key hoặc không thể kết nối tới LLM...")`). Chỉ chạy mock khi người dùng chủ động truyền flag `--use_mock`.
* **Hạng mục B (Checkpoint mang mã băm toàn vẹn cấu hình)**:
  * *Vị trí*: [`src/evaluator.py`](../../src/evaluator.py) class `CheckpointManager`.
  * *Hành vi cũ*: Tên file checkpoint chỉ phụ thuộc vào `experiment_name`.
  * *Hành vi mới*: Tạo SHA-256 hash từ `(dataset_name, split, model_name, prompt_mode, retrieval_method, seed)`. Nếu nạp checkpoint cũ mà hash không khớp, từ chối khôi phục và báo lỗi để tránh lẫn lộn dữ liệu giữa các run.
* **Hạng mục C (Quy ước Jaccard 2 tập rỗng trong Security Signature)**:
  * *Vị trí*: [`src/security_signature/similarity.py`](../../src/security_signature/similarity.py) hàm `compute_jaccard_set`.
  * *Vấn đề*: Khi cả 2 hàm đều không có Sink hoặc không có Sanitizer, `compute_jaccard_set(set(), set())` trả về `1.0` $\rightarrow$ Thổi phồng điểm SecSim giữa 2 hàm không liên quan lên 93%–96%.
  * *Khắc phục*: Quy ước rõ ràng: Hai tập rỗng không thể coi là tương đồng bảo mật tuyệt đối. Trả về `0.0` (hoặc trọng số cảnh báo `has_evidence=False`), chỉ cho điểm tương đồng dương khi có ít nhất 1 đặc trưng an ninh xuất hiện ở cả hai hàm.

### Nhiệm vụ 1.2: Reparse toàn bộ raw responses cũ & Báo cáo tác động của Parser
* *Mục tiêu*: Không gọi lại LLM (chi phí 0 đồng). Dùng parser mới trong [`src/common_evaluator.py`](../../src/common_evaluator.py) để phân tích lại toàn bộ các file log/kết quả đã lưu từ Kaggle.
* *Đầu ra báo cáo*:
  * Tổng số nhãn bị thay đổi.
  * Số mẫu $0 \rightarrow 1$ (do lỗi parser cũ bỏ sót từ khóa).
  * Số mẫu $1 \rightarrow 0$ (do lỗi parser cũ bắt nhầm `Non-vulnerable (0)` thành 1).
  * Số lượng mẫu rơi vào trạng thái `Invalid` (phản hồi rỗng/lỗi).
  * Bảng so sánh $Accuracy, Precision, Recall, F1, MCC, Balanced\ Accuracy$ Trước vs Sau reparse.

### Nhiệm vụ 1.3: Thống kê & Kiểm toán phân nhánh Fallback trong Contrastive Selector
* *Vị trí*: [`src/contrastive_selector.py`](../../src/contrastive_selector.py).
* *Vấn đề*: Khi top-50 ứng viên của một target thiếu nhãn (ví dụ thiếu mẫu Safe hoặc thiếu mẫu Vuln), mã nguồn hiện tại đang lấy ngẫu nhiên 5 mẫu đầu tiên của tập train gán điểm mặc định $0.5$.
* *Việc cần làm*:
  * Thêm bộ đo ghi vết (*Telemetry Log*): Ghi lại `target_id`, `fallback_triggered (True/False)`, `missing_label`, `top_50_label_distribution`, `selected_fallback_id`.
  * Đo trên 100 mẫu thử: Tần suất fallback rate trên Devign là bao nhiêu %? Trên ReVeal (lệch lớp 90% an toàn) là bao nhiêu %?
  * Đánh giá xem có hiện tượng "một vài mẫu train đầu tiên bị gán lặp đi lặp lại cho hàng loạt target khác nhau" hay không.

### Nhiệm vụ 1.4: Kiểm tra rò rỉ dữ liệu (Data Leakage & Duplicate Code Audit)
* *Hiện trạng*: Đã kiểm tra trùng lặp ID giữa Train và Test trên Devign: **0 trùng lặp ID** ($Overlap = 0$).
* *Cần làm tiếp*: Viết script kiểm tra trùng lặp chuỗi mã nguồn thô (*Exact Code Duplicate*) và mã nguồn chuẩn hóa (*Normalized Token Duplicate*) giữa kho Retrieval Bank (Train set) và tập kiểm thử (Test set). Báo cáo rõ tỷ lệ hàm bị trùng lặp nếu có.

---

## 4. Kế Hoạch Chi Tiết Đợt 2 — Kiểm Chứng Một Giả Thuyết Chính (Ablation B2 vs B3 & Controls)

Sau khi hoàn thành Đợt 1, bước sang Đợt 2 nhóm sẽ thực hiện các thí nghiệm có kiểm soát trên tập **Development Set quy mô nhỏ (100–200 mẫu)**:

### Thí nghiệm 2.1: Thí nghiệm Đảo Nhãn Demonstration (Label-Flip Control Test)
* *Mục tiêu*: Đo lường xem LLM có thực sự đọc hiểu cấu trúc mã nguồn hay chỉ "học vẹt nhãn" đi kèm ví dụ.
* *Thiết kế thực nghiệm*:
  * Giữ nguyên 100% mã nguồn target, mã nguồn demonstration, thứ tự và câu lệnh hướng dẫn trong prompt.
  * Chỉ đảo ngược nhãn hiển thị của demonstration: $Label: 1 \rightarrow Label: 0$ và ngược lại.
  * Chạy lặp lại 2 lần với prompt gốc (không đảo nhãn) ở `temperature = 0.0` để đo độ dao động tự nhiên (*Stochastic Variance*) của mô hình.
* *Cách đọc kết quả*:
  * Nếu tỷ lệ dự đoán của LLM đổi chiều theo nhãn demo cao vượt trội so với độ dao động tự nhiên $\rightarrow$ **Mô hình bị dẫn dắt bởi nhãn bề mặt, không đọc hiểu ngữ nghĩa an ninh**. Đây là kết quả then chốt cần biết trước khi đầu tư sâu vào bất kỳ thuật toán chọn demo nào.

### Thí nghiệm 2.2: Ablation Cô Lập B2 vs B3 (Security-Aware Reranker)
* *Câu hỏi khoa học*: "Khi giữ nguyên toàn bộ điều kiện, việc tái xếp hạng bằng chữ ký an ninh (Security-aware reranking) có thực sự tốt hơn xếp hạng tương đồng cú pháp GRACE (Baseline reranking) hay không?"
* *Thiết kế đối chứng chặt chẽ*:
  * **Cấu hình B2**: Target Code + Graph + 1 Demonstration lấy từ Top-1 của Baseline Retriever.
  * **Cấu hình B3**: Target Code + Graph + 1 Demonstration lấy từ Top-1 của Security-Aware Retriever (trên cùng danh sách Top-50 ứng viên của B2).
  * **Cố định tuyệt đối**: Cùng danh sách target IDs, cùng kho train pool, cùng model LLM, cùng temperature, cùng số token, cùng prompt format.
* *Đánh giá*: So sánh chênh lệch $\Delta MCC$ và $\Delta Balanced\ Accuracy$ giữa B2 và B3.

### Thí nghiệm 2.3: Bộ Chấm Mù Thủ Công Độc Lập (Blind Human Review Protocol)
* *Quy mô*: 50 hàm Devign và 50 hàm ReVeal từ tập phát triển (bao gồm cả mẫu có lỗi và an toàn).
* *Phương thức chấm mù*:
  * Với mỗi target, trích xuất 2 demo từ 2 retriever (Baseline và Security-Aware).
  * Ẩn tên phương pháp, ẩn điểm số tự động, xáo trộn ngẫu nhiên vị trí Demo A và Demo B.
  * Hiếu và Dũng tiến hành chấm độc lập dựa trên Rubric bằng chứng code cụ thể:
    1. *Thao tác nguy hiểm (Sink)* có tương đồng không?
    2. *Biến liên quan* có cùng cơ chế không?
    3. *Điều kiện bảo vệ (Guard)* có cùng bản chất không?
    4. Ghi nhận dòng code cụ thể làm bằng chứng hoặc ghi `Chưa xác định`.
  * Đối soát ca bất đồng trước khi thống nhất và so sánh điểm chấm tay với điểm tương đồng tự động.

### Thí nghiệm 2.4: Đánh Giá Khách Quan Bằng Thước Đo Ground-Truth Phụ (Synthetic Micro-Benchmarks Suite)
* *Mục tiêu*: Hoàn thiện **Hệ Thống Đánh Giá 3 Chân Kiềng (Triangulation)** nhằm triệt tiêu hoàn toàn vấn đề "vừa đá bóng vừa thổi còi" khi đánh giá bộ chọn mẫu (Retrieval / Reranker).
* *Lưu ý học thuật*: Phương pháp CWE-alignment tạm thời chưa kích hoạt vì tập eval Devign/ReVeal hiện tại chưa được gán nhãn CWE chuẩn hóa trên diện rộng. Thay vào đó, nhóm tập trung toàn lực vào **Synthetic Ground-Truth Suite** có đáp án an ninh chuẩn 100% không thể tranh cãi.
* *Thiết kế 10 ca kiểm thử vi mô tổng hợp*:
  1. `SYNTH-01` (Guard Variable Relevance): Guard kiểm tra đúng biến (`len <= max`) vs biến rác (`retry > 0`).
  2. `SYNTH-02` (Guard Ordering Flow): Guard đặt TRƯỚC Sink vs Guard đặt SAU Sink.
  3. `SYNTH-03` (Sink Semantic Matching): Sink cùng nhóm bộ đệm (`memcpy`/`memmove`) vs Sink khác loại (`system`).
  4. `SYNTH-04` (Null Pointer Guard Binding): Kiểm tra đúng con trỏ (`ptr != NULL`) vs kiểm tra biến khác (`other != NULL`).
  5. `SYNTH-05` (Memory Lifecycle & UAF): Vòng đời giải phóng bộ nhớ (`free`) vs hàm toán học không liên quan.
  6. `SYNTH-06` (Integer Arithmetic Bounds): Kiểm tra chống tràn tích số nguyên vs nhân tự do.
  7. `SYNTH-07` (Array Access Bounds Guard): Kiểm tra biên chỉ số mảng vs truy cập không kiểm soát.
  8. `SYNTH-08` (Format String Safety): Định dạng có kiểm soát vs format string thô.
  9. `SYNTH-09` (Vulnerable Target Preference): Target có lỗi phải ưu tiên demo có cùng lỗ hổng thay vì demo an toàn.
  10. `SYNTH-10` (End-to-End Reranker Selection): SecurityAwareRetriever lọc bỏ distractor chỉ trùng cú pháp bề mặt.
* *Ngưỡng định lượng*: Mỗi ca phải đạt $\text{SecSim}(Target, Positive) > \text{SecSim}(Target, Distractor)$ với $\text{Margin} \ge \text{Min Margin}$ quy định (tối thiểu $+0.05$ đến $+0.20$).

---

## 5. Kế Hoạch Chi Tiết Đợt 3 — Đo Khoảng Tin Cậy & Đóng Gói Công Bố

Khi và chỉ khi Đợt 2 cho thấy tín hiệu cải thiện thực sự ($MCC$ tăng rõ rệt và vượt qua các baseline đối chứng), nhóm sẽ tiến hành:
1. **Tính Paired Bootstrap 95% Confidence Interval**:
   * Rút mẫu có hoàn lại 2,000 lần trên tập ID kiểm thử để tính phân phối của $\Delta MCC$ và $\Delta F1$.
   * Nếu khoảng tin cậy 95% chứa giá trị 0 $\rightarrow$ Kết luận khoa học trung thực: *"Chưa đủ bằng chứng thống kê về lợi ích của phương pháp"*.
2. **Kiểm định McNemar**: Đánh giá sự khác biệt có ý nghĩa thống kê trên các cặp mẫu bất đồng ($A\ đúng\ B\ sai$ vs $A\ sai\ B\ đúng$).
3. **Mở rộng sang Cặp Tương Phản (B5 vs B6)**: Đo lường thuật toán Contrastive Pair Selection có mang lại lợi ích thực sự ngoài việc cung cấp một mẫu cho mỗi lớp nhãn hay không.

---

## 6. Bảng Phân Công Nhiệm Vụ & Thời Hạn Cụ Thể (Actionable Checklist)

| STT | Đầu việc cụ thể | Người phụ trách | File / Module liên quan | Hạn hoàn thành | Trạng thái |
| :---: | :--- | :---: | :--- | :---: | :---: |
| **1** | Bỏ cơ chế tự động chuyển mock, ném exception khi thiếu API key | Hiếu | `src/evaluator.py` | 15/10/2026 | 🟢 Hoàn thành |
| **2** | Bổ sung hash cấu hình vào CheckpointManager | Hiếu | `src/evaluator.py` | 15/10/2026 | 🟢 Hoàn thành |
| **3** | Sửa quy ước 2 tập rỗng trong Jaccard Similarity (không để 1.0) | Hiếu | `src/security_signature/similarity.py` | 15/10/2026 | 🟢 Hoàn thành |
| **4** | Thêm telemetry log đo tần suất fallback của Contrastive Selector | Hiếu | `src/contrastive_selector.py` | 16/10/2026 | 🟢 Hoàn thành |
| **5** | Viết script reparse toàn bộ raw responses đã lưu trong các notebook | Hiếu | `src/common_evaluator.py` | 15/10/2026 | 🟢 Hoàn thành |
| **6** | Đo exact duplicate code giữa Train và Test split | Hiếu | `scripts/audit_code_leakage.py` | 15/10/2026 | 🟢 Hoàn thành |
| **7** | Điền thông tin các run V1/V2 vào Bảng Quản lý Thực nghiệm | Dũng | `project_docs/reports/GRACE_EXPERIMENT_RUN_REGISTRY.md` | 18/10/2026 | ⚪ Chờ Dũng |
| **8** | Chạy re-parse trên các raw response mà pipeline Dũng còn lưu | Dũng | `src/common_evaluator.py` | 18/10/2026 | ⚪ Chờ Dũng |
| **9** | Thiết kế kịch bản Thí nghiệm Đảo Nhãn Demo (Label-Flip Control) | Hiếu & Dũng | `scripts/run_label_flip_test.py` | 19/10/2026 | ⚪ Đợt 2 |
| **10**| Lập bảng chấm mù 50 Devign + 50 ReVeal và chấm độc lập | Hiếu & Dũng | `project_docs/reports/manual_retrieval_review.csv` | 21/10/2026 | ⚪ Đợt 2 |
| **11**| Chạy đối chứng B2 vs B3 trên Dev Set 100-200 mẫu | Hiếu & Dũng | `src/run_pipeline.py` | 23/10/2026 | ⚪ Đợt 2 |
| **12**| Xây dựng Synthetic Ground-Truth Suite & Script kiểm thử tự động | Hiếu | `scripts/run_synthetic_ground_truth_eval.py` | 15/10/2026 | 🟢 Hoàn thành |
| **13**| Xây dựng Unit Tests kiểm tra Synthetic Ground-Truth Suite | Hiếu | `tests/test_stage5_synthetic_ground_truth.py` | 15/10/2026 | 🟢 Hoàn thành |
| **14**| (Tạm hoãn) Trích xuất và đo lường CWE-alignment trên CVE | Nhóm | `scripts/audit_cwe_alignment.py` | — | ⏸️ Tạm hoãn (chờ nhãn CWE) |
