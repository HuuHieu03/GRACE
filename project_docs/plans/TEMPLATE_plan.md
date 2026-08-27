---
version: "1.0.0"
date: "YYYY-MM-DD"
type: "plan"
status: "DRAFT" # DRAFT | PLANNED | IN_PROGRESS | COMPLETED | CANCELLED
author: "Author Name / AI Agent"
target_component: "Component Name"
tags: ["feature", "plan"]
summary: "Tóm tắt 1-2 câu về mục tiêu và kế hoạch thiết kế cho tính năng này."
---

# Kế Hoạch: [Tên Kế Hoạch / Feature Name] (Phiên bản vX.Y.Z)

## 1. Tổng Quan & Mục Tiêu (Overview & Objectives)
- **Bối cảnh (Context)**: Mô tả ngắn gọn lý do triển khai tính năng / nâng cấp này.
- **Mục tiêu chính (Key Objectives)**:
  - Objective 1
  - Objective 2

## 2. Phạm Vi & Thay Đổi Kiến Trúc (Scope & Architecture Changes)
- **Các file ảnh hưởng**:
  - `path/to/file1.py` - [NEW / MODIFY / DELETE]
  - `path/to/file2.py` - [MODIFY]

- **Sơ đồ / Luồng xử lý (Workflow)**:
  ```text
  [Input] --> [Module A] --> [Module B] --> [Output]
  ```

## 3. Danh Sách Công Việc (Task Breakdowns)
- [ ] Task 1: Thiết kế giao diện / hàm cơ sở
- [ ] Task 2: Cài đặt logic chính
- [ ] Task 3: Viết unit test / kiểm thử nghiệm thu

## 4. Phương Án Kiểm Thử & Kiểm Duyệt (Verification Plan)
- **Tự động**: Lệnh test (`pytest`, `python test.py`, v.v.)
- **Thủ công**: Quy trình xác minh bằng tay.

## 5. Lưu Ý Cho AI Agent (AI Agent Directives)
- Các lưu ý về dependency, constraint kỹ thuật hoặc API contract không được phá vỡ.

## 6. Lịch Sử Cập Nhật (Revision History)
| Ngày | Tác giả | Thay đổi chính |
| :--- | :--- | :--- |
| YYYY-MM-DD | Name | Khởi tạo kế hoạch ban đầu |
