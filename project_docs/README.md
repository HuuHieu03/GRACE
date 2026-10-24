# Quy Chuẩn Quản Lý Thư Mục Làm Việc Cá Nhân & Nội Bộ (Internal Project Documentation)

> 📌 **CHỈ DẪN QUAN TRỌNG VỀ PHÂN ĐỊNH THƯ MỤC**:
> - **Thư mục Báo cáo Chính thức gửi Thầy hướng dẫn**: [`00_Reports_and_Docs/`](../00_Reports_and_Docs/)  
>   *(Thầy và Hội đồng nghiệm thu vui lòng vào thẳng thư mục [`00_Reports_and_Docs/`](../00_Reports_and_Docs/) để đọc báo cáo chính thức [`BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md`](../00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md)).*
> - **Thư mục `project_docs/` (Thư mục này)**: Là không gian làm việc cá nhân và nội bộ nhóm nghiên cứu sinh viên (**Hữu Hiếu & Tiến Dũng**). Thư mục này phục vụ lưu trữ tài liệu làm việc, kế hoạch kỹ thuật chi tiết, nhật ký thực thi, bảng chấm nháp, dữ liệu đối soát trung gian và biên bản hội chẩn nội bộ.

---

## 1. Cấu Trúc Phân Cấp Gọn Gàng & Tường Minh (Directory Hierarchy)

```text
project_docs/
├── README.md                 # Tài liệu này: Quy hoạch thư mục cá nhân/nội bộ
│
├── docs/                     # Tài liệu chỉ đạo bắt buộc, hướng dẫn kỹ thuật & protocol
│   ├── yeu_cau_cua_thay_cho_Dung_va_Hieu.md         # Văn bản chỉ đạo trực tiếp của Thầy hướng dẫn
│   ├── PROTOCOL_EXPERIMENTATION_AND_EVALUATION_GUIDE.md # Quy chuẩn thí nghiệm và đánh giá khoa học
│   ├── v1.0.0_kaggle_deployment_guide.md            # Hướng dẫn chi tiết triển khai GPU trên Kaggle
│   ├── supervisor_questions_and_notes.md            # Giải đáp các câu hỏi kỹ thuật cốt lõi của Thầy
│   ├── GRACE_phanhoibaocaoDungHieu.docx/txt         # Bản phản hồi chi tiết của Thầy cho Hiếu & Dũng
│   └── reports/                                     # Lưu trữ các báo cáo chuyên đề lịch sử (Stage 1 - 5)
│
├── plans/                    # Kế hoạch thực thi kỹ thuật & Roadmap đề tài
│   ├── TEMPLATE_plan.md                             # Khung mẫu tạo kế hoạch mới
│   ├── GRACE_RESEARCH_ROADMAP.md                    # Lộ trình tổng thể đề tài nghiên cứu
│   ├── PLAN_SUPERVISOR_REQUIREMENTS_EXECUTION_20261014.md # Kế hoạch thực thi 6 yêu cầu của Thầy
│   ├── GRACE_IMMEDIATE_ACTION_PLAN.md               # Kế hoạch hành động khẩn cấp
│   └── v1.0.0_2026-10-21_sink_evidence_and_retrieval_ablation_plan.md # Kế hoạch bóc tách Ablation & Sink
│
├── reports/                  # Báo cáo nội bộ, dữ liệu đối soát thực nghiệm & Bảng chấm mù
│   ├── bao_cao_tien_do_da_doi_soat_20261022.md      # Báo cáo đối soát nội bộ 22/10
│   ├── verified_sources_2026-10-22/                 # Registry nguồn số liệu đối soát (SHA-256)
│   ├── verified_protocol_2026-10-22/                # Bàn giao kỹ thuật protocol mới
│   ├── data_contract_v2_2026-10-22/                 # Hợp đồng dữ liệu v2 chống rò rỉ mã nguồn
│   ├── blind_review_sheet_hieu.csv                  # Bảng chấm mù độc lập của Hiếu (50 Devign)
│   ├── blind_review_sheet_dung.csv                  # Bảng chấm mù độc lập của Dũng (50 Devign)
│   ├── blind_review_confirmed_adjudication_50.csv   # Biên bản hòa giải kỹ thuật Devign 50 mẫu
│   ├── blind_review_reveal_sheet_hieu.csv           # Bảng chấm mù độc lập của Hiếu (50 ReVeal)
│   ├── blind_review_reveal_sheet_dung.csv           # Bảng chấm mù độc lập của Dũng (50 ReVeal)
│   ├── blind_review_reveal_confirmed_adjudication_50.csv # Biên bản hòa giải kỹ thuật ReVeal 50 mẫu
│   ├── blind_review_kappa_summary.md                # Tổng hợp hệ số Cohen's Kappa trước hòa giải
│   ├── v1.0.0_2026-10-21_stage3_b3_vs_b2_comparison_report.md # Báo cáo chi tiết đối đầu B3 vs B2
│   ├── v1.0.0_2026-10-22_supervisor_readiness_review.md # Rà soát mức độ sẵn sàng báo cáo Thầy (Lần 1)
│   └── v1.1.0_2026-10-22_supervisor_readiness_second_review.md # Rà soát mức độ sẵn sàng báo cáo Thầy (Lần 2)
│
├── progress/                 # Theo dõi tiến độ công việc tuần tự
│   ├── TEMPLATE_progress.md                         # Khung mẫu theo dõi tiến độ
│   ├── v1.0.0_2026-10-22_supervisor_remediation_progress.md # Tiến độ thực hiện các yêu cầu của Thầy
│   └── v1.0.0_2026-10-22_h2_and_e13_progress.md     # Tiến độ triển khai nhánh H2 và E1.3
│
├── logs/                     # Nhật ký công việc, ghi chép lỗi kỹ thuật & runtime logs
│   ├── TEMPLATE_log.md                              # Khung mẫu nhật ký
│   ├── v1.0.0_2026-10-22_supervisor_remediation_log.md # Nhật ký chi tiết khắc phục sự cố theo review
│   └── v1.0.0_2026-10-22_h2_and_e13_log.md          # Nhật ký triển khai thực nghiệm H2 / Vertex AI
│
└── history/                  # Tóm tắt các phiên làm việc và mốc lịch sử dự án
    ├── README.md                                    # Chỉ mục lịch sử
    └── YYYY-MM-DD_session_summary.md                # Tóm tắt các phiên làm việc trước đây
```

---

## 2. Quy Chuẩn Đặt Tên & Định Dạng Tài Liệu Nội Bộ

1. **Tiền tố phiên bản**: Tất cả tài liệu theo dõi tiến độ, kế hoạch và nhật ký tuân thủ cú pháp:  
   `v<Version>_<YYYY-MM-DD>_<Chủ_đề>_<Loại_tài_liệu>.md`  
   *Ví dụ:* `v1.0.0_2026-10-21_stage3_b3_vs_b2_comparison_report.md`
2. **YAML Frontmatter bắt buộc**: Mọi file Markdown đều có phần frontmatter ở đầu để AI Agent và thành viên nhóm đọc nhanh context:
   ```yaml
   ---
   version: "1.0.0"
   date: "YYYY-MM-DD"
   type: "plan | progress | log | report | guide | notes"
   status: "DRAFT | IN_PROGRESS | COMPLETED | APPROVED"
   author: "Hữu Hiếu / Tiến Dũng / AI Assistant"
   target_component: "Tên module hoặc đối tượng kiểm định"
   summary: "Mô tả ngắn gọn nội dung và kết luận chính."
   ---
   ```
3. **Nguyên tắc tính toán & Lưu trữ số liệu**:
   - Mọi bảng số liệu nội bộ đối soát phải liên kết chặt chẽ với file gốc tại `output/` hoặc `data/`.
   - Bảng chấm mù độc lập (Human Review) của Hiếu và Dũng phải được bảo lưu nguyên vẹn để bảo đảm tính liêm chính khoa học của hệ số Cohen's Kappa.
