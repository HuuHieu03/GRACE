# Session Summary - 2026-08-22

## 1. Mục tiêu phiên làm việc
- Kiểm tra và nghiệm thu kết quả chạy Baseline trên 100% tập dữ liệu Reveal (`Ver11_Reveal_baseline/grace-baseline.ipynb`).
- Tổng hợp và đối chiếu kết quả 3 chiều: Paper GRACE (GPT-4) vs Source code gốc tác giả vs Bản Reproduce của chúng ta (trên cả 2 benchmark Devign và Reveal).
- Rà soát tính chính xác của cấu trúc Prompt theo Hình 6 (Figure 6) và Mục 3.3 trong bài báo khoa học GRACE.
- Chuẩn hóa mã nguồn `prompt_engine.py` và cập nhật tài liệu kỹ thuật trong `project_docs/`.

---

## 2. Các kết quả & Công việc đã hoàn thành
- **Nghiệm thu Reveal Baseline**:
  - Chạy thành công 100% (2,274 mẫu test) không phát sinh lỗi, xử lý hoàn hảo các lần chạm rate-limit HTTP 429 qua cơ chế smart backoff retry.
  - Kết quả đạt: Accuracy = 70.18%, Recall = 32.17%, Precision = 12.42%, F1-Score = 0.1792.
- **Đối chiếu Benchmark & Phân tích nguyên nhân chênh lệch**:
  - Devign: Precision của bản reproduce (53.27%) bám sát rất gần so với GPT-4 (54.58%). Recall thấp hơn do mô hình 26B thận trọng hơn GPT-4 hàng trăm tỷ tham số.
  - Reveal: Hiện tượng mất cân bằng nhãn nặng (~9% lỗ hổng) gây nhiều báo động giả (522 FP) trên mô hình 26B.
- **Chuẩn hóa Prompt Engine Figure 6**:
  - Bỏ đồ thị CPG và reasoning tự chế trong phần Demonstration của ví dụ mẫu (chỉ giữ Code mẫu + Nhãn kết luận theo đúng Figure 6).
  - Giữ nguyên thông tin Node & Edge CPG cho hàm mục tiêu (Target Query).
  - Vượt qua 100% các bài test trong `tests/test_stage3_eval.py`.
- **Cập nhật tài liệu dự án**:
  - Ghi nhật ký vào `project_docs/logs/v1.0.0_2026-08-22_prompt_engine_standardization_log.md`.
  - Cập nhật tiến độ vào `project_docs/progress/v1.0.0_2026-08-22_project_progress.md`.
  - Lưu trữ tóm tắt phiên làm việc tại `project_docs/history/2026-08-22_session_summary.md`.

---

## 3. Trạng thái hiện tại & Bước tiếp theo
- **Trạng thái hiện tại**: Toàn bộ pipeline baseline đã được kiểm thử, nghiệm thu và chuẩn hóa 100% khớp với bài báo khoa học.
- **Bước tiếp theo**: Bắt đầu giai đoạn nghiên cứu & triển khai các hướng cải tiến đột phá (Program Slicing / Subgraph Extraction, Contrastive ICL, Security Chain-of-Thought).
