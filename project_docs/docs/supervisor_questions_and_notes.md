---
version: "1.0.0"
date: "2026-10-14"
type: "notes"
status: "RESOLVED"
author: "Nhóm nghiên cứu sinh viên (Hữu Hiếu & Tiến Dũng)"
target_component: "Supervisor Questions & Technical Clarifications"
tags: ["questions", "supervisor", "notes", "evaluation"]
summary: "Ghi chú các câu hỏi cốt lõi của Thầy hướng dẫn về định dạng input/output và chuẩn hóa dữ liệu."
---

# Ghi Chú: Các Câu Hỏi Cốt Lõi Của Thầy Hướng Dẫn & Lời Giải

## 1. Output LLM đưa ra đang theo định dạng gì? Có phải là 1, 0 hay không?
- **Hiện trạng ban đầu:** Output tự do hoặc chuỗi văn bản dài khiến parser cũ gặp lỗi trích xuất hoặc nuốt lỗi.
- **Biện pháp khắc phục đã chốt:** Sử dụng `ExactLastLineBinaryParser` chuẩn mực từ `strict_parser.py`. Chỉ chấp nhận dòng cuối cùng là `0` hoặc `1`. Mọi kết quả không đúng format lập tức bị gán nhãn `invalid` với Invalid Rate = 0.0% trên toàn bộ 5,006 mẫu thực tế.

## 2. Input đưa vào đang có format như thế nào?
- **Format chuẩn:** Cấu trúc theo Figure 6 bài báo gốc kết hợp Cặp mẫu tương phản Contrastive:
  - Header hướng dẫn bài toán phát hiện lỗ hổng C/C++.
  - Ví dụ mẫu 1 (Vulnerable) kèm trích đoạn code và nhãn `1`.
  - Ví dụ mẫu 2 (Safe) kèm trích đoạn code và nhãn `0`.
  - Phân tích vi sai ranh giới an ninh (`CORE SECURITY DIFFERENCE`).
  - Biểu diễn đồ thị Joern CPG (AST, CFG, PDG) rút gọn ($\le 25$ nodes/edges).
  - Code hàm mục tiêu cần phân loại (được bảo vệ bằng Truncation Guard 8,192 bytes).

## 3. Dữ liệu đã được làm sạch và chuẩn hóa về cùng format khi đưa vào mô hình chưa? Các trường dữ liệu đã đồng nhất chưa?
- **Đã hoàn tất 100%:** Toàn bộ tập dữ liệu Devign và ReVeal đã được chuẩn hóa qua `data_loader.py` và Data Contract v2 (`data/manifests/function_uid_v2/`). Các trường dữ liệu `func`, `target`, `nodes`, `edges` đã được đồng nhất tuyệt đối, ngăn ngừa triệt để hiện tượng rò rỉ mã nguồn (Code Leakage) và near-clone.
