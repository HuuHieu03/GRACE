# Quy Chuẩn Quản Lý Tài Liệu Dự Án (Project Documentation Specification)

Tài liệu này định nghĩa quy chuẩn quản lý tài liệu, theo dõi tiến độ và nhật ký hoạt động cho dự án. Quy chuẩn này được tối ưu hóa đồng thời cho **Con người** (dễ đọc, trực quan) và **AI Agent** (dễ đọc frontmatter, index nhanh, chính xác token).

---

## Tài liệu hiện tại — cập nhật 2026-10-22

- [Báo cáo tiến độ đã đối soát](reports/bao_cao_tien_do_da_doi_soat_20261022.md): **Bản hiện tại để trao đổi tiến độ với thầy**; chưa nghiệm thu cải tiến hoặc independent review. Ghi rõ B2 lịch sử mất, kết quả âm và phần nghiên cứu còn lại.
- [Bàn giao kỹ thuật protocol mới](reports/verified_protocol_2026-10-22/report.md): lưu vết/evaluator/payload/controls đã triển khai;586tests đạt,20synthetic conditions,0API. Chưa có run LLM thật mới.
- [Nguồn số liệu đã đối soát](reports/verified_sources_2026-10-22/report.md): bảng dùng cho báo cáo tiến độ, kèm registry SHA-256 và phân biệt metric tái tính với số chỉ còn tổng hợp; loại summary CSV mâu thuẫn khỏi nguồn báo cáo.
- [Tiến độ khắc phục tuần tự](progress/v1.0.0_2026-10-22_supervisor_remediation_progress.md): trạng thái sáu việc sau review, bằng chứng nghiệm thu và phần còn chờ.
- [Contract dữ liệu v2](reports/data_contract_v2_2026-10-22/report.md): UID riêng từng hàm, code/source verification, phân bố thật và lexical near-clone audit; không sửa nhãn hoặc artifact lịch sử.
- [Đầu vào bộ chấm mới](reports/verified_review_inputs_2026-10-22/report.md): chưa đủ actual B2 records Ver03/Ver04; generator cũ đã bị chặn, không tự tạo phiếu thay thế.
- [Review lần hai và checklist gửi thầy](reports/v1.1.0_2026-10-22_supervisor_readiness_second_review.md): **Kết luận mới nhất: chưa đủ gửi bản nghiệm thu hiện tại**. Bổ sung lỗi ID/code ReVeal, CSV lệch JSON, metadata split và graph ablation; H2 replay khớp, 900 Stage 2 raw responses reparse không đổi. Có checklist riêng trước báo cáo tiến độ và trước kết luận cải tiến.
- [Review mức sẵn sàng gửi thầy](reports/v1.0.0_2026-10-22_supervisor_readiness_review.md): **Đọc trước bản tổng hợp nghiệm thu**. Review phát hiện lỗi chọn demo theo target label trong bộ chấm cũ, thiếu raw/prompt Stage 3 và các kết luận vượt bằng chứng; chưa đủ điều kiện nghiệm thu cải tiến.
- [Bản tổng hợp nghiệm thu cũ](reports/bao_cao_tien_do_tong_hop_nghiem_thu_20261022.md): **Lịch sử, chưa đủ điều kiện gửi nguyên trạng**; giữ để truy vết các khẳng định trước review.
- [Báo cáo chấm ReVeal cũ](reports/blind_review_reveal_technical_report.md): artifact lịch sử; chưa nghiệm thu độc lập hoặc identity/code. Không dùng Kappa/tỷ lệ ưu tiên trong tài liệu này để xác nhận retriever tốt hơn.
- [Tiến độ tổng hợp H2 và E1.3](progress/v1.0.0_2026-10-22_h2_and_e13_progress.md): điểm bắt đầu để nắm trạng thái mới nhất.
- [Kế hoạch sink evidence và retrieval ablation](plans/v1.0.0_2026-10-21_sink_evidence_and_retrieval_ablation_plan.md): checklist đã đồng bộ với kết quả thực tế.
- [Báo cáo H2](reports/retrieval_h2/results_2026-10-22/report.md): R1 đổi 0/100 lựa chọn; không chạy paired LLM cho hai arm hiện tại.
- [Follow-up và bộ relevance review](reports/retrieval_h2/followup_2026-10-22/report.md): inventory Unknown, packet và rubric; hai phiếu còn trống.
- [E1.3 và trạng thái bước 1–3](reports/sink_evidence_v13/report.md): sửa declaration artifacts/output-role syntax, 63 tests đạt; chưa tích hợp production hoặc xác nhận semantic.
- [Nhật ký H2/E1.3](logs/v1.0.0_2026-10-22_h2_and_e13_log.md): artifact, kiểm tra và các giới hạn kết luận.

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
