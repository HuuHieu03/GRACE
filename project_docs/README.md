# Quy Chuẩn Quản Lý Tài Liệu Dự Án (Project Documentation Specification)

Tài liệu này định nghĩa quy chuẩn quản lý tài liệu, theo dõi tiến độ và nhật ký hoạt động cho dự án. Quy chuẩn này được tối ưu hóa đồng thời cho **Con người** (dễ đọc, trực quan) và **AI Agent** (dễ đọc frontmatter, index nhanh, chính xác token).

---

## 1. Cấu Trúc Thư Mục (Directory Hierarchy)

```text
project_docs/
├── README.md                 # Tài liệu hướng dẫn quy chuẩn này
├── plans/                    # Kế hoạch thực thi, định hướng tính năng cho từng phiên bản
│   ├── TEMPLATE_plan.md      # Khung mẫu tạo kế hoạch mới
│   └── vX.Y.Z_..._plan.md    # Kế hoạch phiên bản vX.Y.Z
├── progress/                 # Theo dõi danh sách công việc & tiến độ thực hiện
│   ├── TEMPLATE_progress.md  # Khung mẫu theo dõi tiến độ
│   └── vX.Y.Z_..._progress.md # Tiến độ phiên bản vX.Y.Z
├── logs/                     # Nhật ký công việc, ghi chép lỗi & sửa lỗi chi tiết
│   ├── TEMPLATE_log.md       # Khung mẫu nhật ký
│   └── vX.Y.Z_YYYY-MM-DD_..._log.md # Nhật ký chi tiết theo phiên bản và ngày
└── docs/reports/             # Báo cáo chuyên sâu, đối chiếu thực nghiệm và phân tích kỹ thuật
    ├── TEMPLATE_report.md    # Khung mẫu báo cáo nghiên cứu
    └── vX.Y.Z_..._report.md  # Báo cáo chuyên đề phiên bản vX.Y.Z
```

---

## 2. Quy Chuẩn Đặt Tên File (File Naming Conventions)

Tất cả tên file đều sử dụng chữ thường, ngăn cách bằng dấu gạch dưới `_`, ngoại trừ tiền tố phiên bản `vX.Y.Z`.

| Thư mục | Quy tắc đặt tên file | Ví dụ |
| :--- | :--- | :--- |
| `plans/` | `v<Version>_<YYYY-MM-DD>_<Topic/Feature>_plan.md` | `v1.0.0_2026-08-01_grace_analysis_plan.md` |
| `progress/` | `v<Version>_<YYYY-MM-DD>_<Topic/Feature>_progress.md` | `v1.0.0_2026-08-01_project_progress.md` |
| `logs/` | `v<Version>_<YYYY-MM-DD>_<Topic/Action>_log.md` | `v1.0.0_2026-08-01_init_log.md` |
| `docs/reports/` | `v<Version>_<YYYY-MM-DD>_<Topic>_report.md` | `v1.0.0_2026-08-24_prompt_comparison_report.md` |

---

## 3. Quy Chuẩn Định Dạng Nội Dung File (Content Formatting)

Mỗi file Markdown trong hệ thống **BẮT BUỘC** bao gồm 2 phần:

### Phần 1: YAML Frontmatter (Cho AI Agent Indexing)
Nằm ở đầu file, đặt giữa 2 dòng `---`.

```yaml
---
version: "1.0.0"
date: "YYYY-MM-DD"
type: "plan | progress | log"
status: "DRAFT | PLANNED | IN_PROGRESS | COMPLETED | DEPRECATED"
author: "Tên người tạo hoặc AI Agent"
target_component: "Tên thành phần / Module trong hệ thống"
tags: ["tag1", "tag2", "tag3"]
summary: "Tóm tắt ngắn gọn 1-2 câu về nội dung file để AI đọc nhanh context."
---
```

### Phần 2: Markdown Content (Cho Con người & AI đọc chi tiết)
- **Tiêu đề chính (`#`)**: Bao gồm mã phiên bản và tên chủ đề.
- **Các mục (`##`)**:
  - `## 1. Overview & Objectives` (Tổng quan & Mục tiêu)
  - `## 2. Scope & Specifications` (Phạm vi & Chi tiết kỹ thuật)
  - `## 3. Work Checklist` (Danh sách công việc với cú pháp `- [ ]`, `- [/]`, `- [x]`)
  - `## 4. AI Agent Context & Key Notes` (Các lưu ý kỹ thuật quan trọng cho AI)
  - `## 5. Changelog / Revision History` (Lịch sử cập nhật file)

---

## 4. Hướng Dẫn Sử Dụng Cho AI Agent

Khi nhận nhiệm vụ trong dự án này, AI Agent cần:
1. Đọc file `project_docs/README.md` để hiểu quy chuẩn.
2. Kiểm tra `plans/` để nắm kế hoạch tổng thể của phiên bản hiện tại.
3. Cập nhật `progress/` tương ứng khi bắt đầu (`[/]`) hoặc hoàn thành (`[x]`) một công việc.
4. Ghi chép chi tiết vào `logs/` nếu có phát sinh lỗi, thử nghiệm hoặc sửa lỗi quan trọng.
