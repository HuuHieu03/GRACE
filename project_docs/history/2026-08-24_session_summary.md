# Session Summary - 2026-08-24

## 1. Mục tiêu phiên làm việc
- Kiểm tra, phân tích và nghiệm thu kết quả chạy thực nghiệm Baseline trên 100% tập dữ liệu **Devign (Ver12)** và **Reveal (Ver13)** với cấu trúc chuẩn nguyên bản Figure 6 bài báo gốc GRACE.
- Đối chiếu hiệu năng chéo giữa các phiên bản và phân tích quy luật hành vi của mô hình LLM mã nguồn mở (Gemma-26B).
- Cập nhật toàn diện hệ thống tài liệu dự án (`project_docs/logs/`, `project_docs/progress/`, `project_docs/history/`).
- Tổng kết toàn bộ Giai đoạn Baseline (Stage 4) và sẵn sàng chuyển sang Giai đoạn Nghiên cứu Cải tiến Đột phá (Stage 5).

---

## 2. Kết quả nghiệm thu 2 bộ Benchmark Chuẩn Nguyên Bản (Figure 6)

### A. Tập Devign (Ver12 - 2,732 mẫu test):
* **Accuracy**: **56.19%**
* **Precision**: **54.75%** (Tăng từ 53.27%, vượt mốc 54.58% của GPT-4 trong paper)
* **Recall**: **26.61%**
* **F1-Score**: **35.82%**
* **Confusion Matrix**: TP = 334, FN = 921, TN = 1,201, FP = 276 (Giảm 174 ca báo động giả).

### B. Tập Reveal (Ver13 - 2,274 mẫu test):
* **Accuracy**: **76.39%** (Tăng vọt +6.21% so với bản cũ 70.18%)
* **Precision**: **13.54%** (Tăng +1.12% so với bản cũ 12.42%)
* **Recall**: **24.78%**
* **F1-Score**: **17.51%**
* **Confusion Matrix**: TP = 57, FN = 173, TN = 1,680, FP = 364 (Giảm 158 ca báo động giả).

---

## 3. Tổng kết & Định hướng Giai đoạn Tiếp theo
* **Hoàn tất 100% Giai đoạn 4 (Baseline Reproduction)**: Chúng ta đã có bộ số liệu Baseline chuẩn xác, khách quan và khoa học trên cả 2 dataset chuẩn SOTA.
* **Giai đoạn 5 (Novel Proposals)**: Bắt đầu thiết kế và triển khai 3 hướng cải tiến chính:
  1. **Security Chain-of-Thought (CoT)**: Tăng Recall và khả năng giải thích của mô hình.
  2. **Contrastive In-Context Learning (2-shot tương phản)**: Giảm thiên kiến nhãn và cân bằng phán đoán.
  3. **Vulnerability-Focused Program Slicing**: Tối ưu biểu diễn đồ thị CPG, tập trung vào các điểm nguy hiểm.
