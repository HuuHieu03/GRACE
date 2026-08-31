---
category: "Reproduction Notebooks"
author: "Nguyễn Hữu Hiếu"
role: "Nghiên cứu viên / Người thực hiện"
parent_project: "GRACE Enhancement Study"
last_updated: "2026-08-31"
---

# 01_Reproduce_Notebooks: Danh Mục Notebooks Thực Nghiệm Đã Lưu Kết Quả

Thư mục này chứa 3 notebook thực nghiệm tiêu chuẩn đã được chạy hoàn tất trên Kaggle GPU (Tesla T4) với mô hình `gemma-4-26B-A4B-it` (qua FPT AI Platform API).

> [!NOTE]
> **Độ Trung Thực Của Kết Quả:** Tất cả các notebook dưới đây đều **lưu giữ 100% cell outputs, logs suy luận từng mẫu, ma trận nhầm lẫn (Confusion Matrix) và bảng chỉ số đánh giá**. Người đọc và Giảng viên có thể mở trực tiếp để kiểm chứng kết quả mà không bắt buộc phải chạy lại từ đầu.

---

## 1. Danh Mục Các Tệp Notebook

| Tên File Notebook | Phân Loại | Kích Thước | Bộ Dữ Liệu | Kết Quả Đạt Được |
| :--- | :--- | :---: | :--- | :--- |
| 📄 [`stage5_contrastive_demonstration.ipynb`](stage5_contrastive_demonstration.ipynb) | **Stage 5 Cải tiến (Đột phá SOTA)** | **1.39 MB** | **Devign** (2,732 mẫu) & **ReVeal** (2,274 mẫu) | **Devign:** Recall **34.34% (+7.73%)**, F1 **41.66% (+5.84%)**, bắt trúng thêm +97 lỗ hổng.<br>**ReVeal:** Recall **27.39% (+2.61%)**, F1 **18.69%**. |
| 📄 [`devign_baseline_reproduce.ipynb`](devign_baseline_reproduce.ipynb) | **Baseline gốc phục dựng** | **612.9 KB** | **Devign** (2,732 mẫu) | Recall: 26.61%, Precision: 54.84%, F1: 35.82%, TP: 334, FN: 921 |
| 📄 [`reveal_baseline_reproduce.ipynb`](reveal_baseline_reproduce.ipynb) | **Baseline gốc phục dựng** | **514.0 KB** | **ReVeal** (2,274 mẫu) | Recall: 24.78%, Precision: 13.54%, F1: 17.51%, TP: 57, FN: 173 |

---

## 2. Hướng Dẫn Mở & Chạy Lại (Nếu Muốn)

1. **Cách 1: Mở xem trực tiếp trên VSCode / GitHub / Jupyter Lab**:
   * Chỉ cần click mở file notebook, toàn bộ biểu đồ, bảng chỉ số và log đã hiển thị sẵn.
2. **Cách 2: Chạy lại trên Kaggle Notebooks**:
   * Upload file `.ipynb` lên Kaggle.
   * Chọn môi trường: GPU Tesla T4 x2 hoặc P100.
   * Nhập API key của LLM (FPT AI / OpenAI / Local vLLM).
   * Nhấn **Run All**.
