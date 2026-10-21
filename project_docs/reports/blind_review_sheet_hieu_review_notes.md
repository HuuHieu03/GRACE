---
version: "1.0.0"
date: "2026-10-21"
type: "report"
status: "DRAFT"
author: "Codex (AI-assisted review for Hiếu)"
target_component: "Blind review sheet — Hiếu"
tags: ["blind_review", "ai_assisted", "pending_human_review"]
summary: "Đã điền 50/50 dòng theo code snippet; đây là bản AI hỗ trợ, chưa phải kết quả chấm độc lập được Hiếu xác nhận."
---

# Bản chấm AI hỗ trợ cho bảng của Hiếu

Đã điền `blind_review_sheet_hieu.csv`: 50 lựa chọn, 300 ô rubric và bằng chứng riêng cho từng dòng. Giữ nguyên ID, nhãn, thứ tự A/B và code snippet. Bảng chưa điền được lưu ở `blind_review_sheet_hieu_unrated_backup.csv`. Bảng của Dũng không thay đổi.

## Quy ước chấm

- `1`: khớp cơ chế theo bằng chứng code trong snippet.
- `Partial`: khớp một phần; khác thao tác, đối tượng hoặc điều kiện được ghi trong evidence.
- `0`: không khớp cơ chế đang xét.
- `Unknown`: chưa xác định từ snippet/hợp đồng caller hiện có.
- `Equal`: hai demo có mức phù hợp tương đương; không đồng nghĩa cả hai tốt.
- `Neither`: cả hai thiếu bằng chứng phù hợp đủ để chọn, kể cả khi A/B giống nhau.

Không dùng target label để ưu tiên demonstration. Không mở đáp án ánh xạ A/B sang phương pháp trong lượt chấm này. Không suy diễn phần code đã cắt; không coi cả hai thiếu guard là bằng chứng guard khớp. Đây là đánh giá mức liên quan của demo, không phải xác nhận nhãn vulnerability.

## Kết quả và kiểm tra

| Lựa chọn | Số dòng |
| --- | ---: |
| A | 12 |
| B | 13 |
| Equal | 6 |
| Neither | 19 |

A/B có snippet giống hệt nhau ở dòng 22, 32, 44, 45. Dòng 45 chọn Neither vì cả hai không phù hợp cơ chế port I/O; ba dòng còn lại chọn Equal.

Đã đọc lại CSV bằng bộ đọc CSV, xác nhận đủ 50 dòng, các ô rubric/evidence đều có nội dung, sáu cột nguồn giữ nguyên từng giá trị và SHA-256 bảng Dũng không đổi.

## Trạng thái sử dụng

Mỗi dòng evidence ghi rõ `AI-assisted draft (Codex); Hiếu chưa xác nhận.` Hiếu cần đọc và tự quyết định từng dòng trước khi sử dụng như đánh giá của mình; giữ công khai việc có AI hỗ trợ. Không báo cáo bảng này là lượt chấm mù độc lập thuần con người. Chưa chạy tổng hợp ưu thế phương pháp hoặc Cohen's Kappa cho hai người chấm.
