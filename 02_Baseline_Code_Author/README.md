---
category: "Baseline Code Documentation"
author: "Nguyễn Hữu Hiếu"
role: "Nghiên cứu viên / Người thực hiện"
parent_project: "GRACE Enhancement Study"
last_updated: "2026-08-31"
---

# Thư Mục baseline code/: Mã Nguồn Phục Dựng Baseline

Thư mục này lưu trữ mã nguồn và gói dữ liệu dùng cho việc tái hiện (reproduce) mô hình GRACE Baseline theo bài báo gốc:

1. **Thư mục baseline_code_text/**:
   * Chứa toàn bộ các file mã nguồn Python (.py) chuẩn hóa phục dựng quy trình của bài báo (CodeT5 768d + Meta FAISS L2 + Hybrid Reranker).
   * Các file này có dung lượng nhẹ, cho phép xem trực tiếp trên GitHub.
2. **Tệp GRACE_source_code_baseline.zip (310.8 MB)**:
   * Gói đóng gói nguyên bản để upload lên Kaggle Dataset, bên trong tích hợp sẵn cả mã nguồn lẫn 4 file đồ thị JSON đã trích xuất (devign_train_processed.json, reveal_train_processed.json... nặng hơn 5.7 GB).
   * Tệp này được cấu hình trong .gitignore để không đẩy lên GitHub nhằm tránh vượt giới hạn 100MB của GitHub.