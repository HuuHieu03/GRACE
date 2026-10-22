---
version: "1.0.0"
date: "2026-10-21"
type: "report"
status: "IN_PROGRESS"
author: "Codex"
target_component: "Đối soát 26 mẫu bất đồng"
tags: ["blind_review", "adjudication", "rubric"]
summary: "Chuẩn hóa rubric và đề xuất xử lý 26 ca; giữ nguyên phiếu gốc và kappa trước đối soát, chưa gán đề xuất thành đồng thuận của hai người."
---

# Đối soát các mẫu bất đồng

Người dùng đã xác nhận bảng Hiếu là bản chấm của mình và yêu cầu bỏ ghi chú AI trong CSV. Việc bỏ ghi chú không thay đổi lựa chọn hay bằng chứng. Lịch sử tạo bảng vẫn được giữ trong tài liệu trước đó; không suy diễn thành hai lượt chấm độc lập thuần con người.

## Rubric thống nhất cho lượt đối soát

1. Sink: xác định thao tác cụ thể và dữ liệu tác động. Cùng có `->`, phép bit, logging hoặc tên hàm chứa `read` không đủ để coi cùng sink.
2. Variable: so vai trò như địa chỉ, độ dài, chỉ số, đối tượng được lookup, tài nguyên được cấp phát. Không dùng từ trong comment, từ khóa C, chuỗi log hoặc chỉ trùng tên để kết luận liên quan.
3. Guard: nêu biểu thức, biến được kiểm tra, vị trí trước/sau sink và nhánh ngăn thao tác. Logging cảnh báo không tự ngăn sink. Nhánh tính năng không tự là guard bảo mật; thiếu guard ở cả hai không tính là khớp.
4. Chọn A/B khi có quan hệ cụ thể về thao tác/dòng dữ liệu hoặc một mẫu guard bảo vệ đúng vai trò đối tượng. Ghi rõ mức khớp một phần và khác biệt còn lại. Chỉ cùng xử lý lỗi chung hoặc cùng lĩnh vực là chưa đủ.
5. Equal khi cả hai đủ liên quan và không có ưu thế rõ. Neither khi cả hai không đạt ngưỡng, kể cả code A/B giống nhau.
6. Snippet bị cắt: chỉ dùng phần thấy được. Nếu thiếu phần quyết định kết luận, để trạng thái NEEDS_CONTEXT, không tự kết luận an toàn/có lỗi hay suy diễn phần bị cắt.

Đây là rubric đề xuất để hai người dùng khi đối soát; không áp đặt như rubric đã được thống nhất trước lượt chấm gốc. Nếu được áp dụng chính thức, cần rà lại cả 24 ca đồng thuận để tránh chỉ sửa các ca bất đồng theo chuẩn mới.

## Bảng đối soát

`blind_review_adjudication.csv` gồm 26 ca, code target/A/B, lựa chọn gốc, bằng chứng của hai bảng, nguồn bất đồng, bằng chứng trọng tâm, đề xuất, mức chắc chắn và hành động tiếp theo. Không đưa tên phương pháp hoặc điểm retrieval vào bảng làm việc.

Các cột `hieu_recheck`, `dung_recheck`, `consensus_choice`, `consensus_evidence` để trống cho lượt đối soát thực tế. `proposed_choice` là đề xuất kỹ thuật của Codex, không phải kết quả thống nhất. Không tính kappa mới từ đề xuất này.

## Quy trình tiếp theo

**Cập nhật sau rà soát kỹ thuật:** Đã xuất `blind_review_technical_review_50.csv` cho toàn bộ 50 mẫu và bổ sung các cột `technical_choice`, `technical_evidence`, `context_resolution`, `technical_status` vào bảng 26 ca. Các đề xuất ban đầu được giữ nguyên để theo dõi lịch sử. Cả 5 ca đã có đủ hàm cục bộ để đưa ra quyết định về mức liên quan demo; các thiếu hụt macro/helper/caller được ghi riêng, không coi là chứng minh an toàn. Các cột xác nhận của Hiếu/Dũng và kết luận đồng thuận vẫn để trống vì chưa có lượt đối soát thực tế của hai người.

1. Xem nhóm đủ ngữ cảnh trước, bắt đầu từ dòng 1/3/5/24/45 để hiệu chỉnh ngưỡng Neither và Equal.
2. Đọc nhóm chọn đối lập 11/18/28/34/38, đối chiếu biểu thức cụ thể thay vì điểm lexical.
3. Thu thập phần code còn thiếu cho các ca NEEDS_CONTEXT. Giữ nguyên vị trí A/B; nếu cung cấp code đầy đủ, ghi rõ đây là phiên bản ngữ cảnh mở rộng.
4. Mỗi người ghi quyết định kiểm tra lại trước khi thảo luận chung. Lưu mọi thay đổi kèm lý do; bất đồng còn lại giữ unresolved hoặc nhờ người thứ ba.
5. Nếu thay rubric, chấm lại toàn bộ 50 mẫu theo rubric mới và lưu thành phiên bản riêng. Báo cáo riêng kết quả lượt đầu, lượt chấm lại và đồng thuận sau thảo luận; không dùng kết quả sau thảo luận để thay thế độ đồng thuận độc lập ban đầu.

Kappa ban đầu theo bốn nhóm phương pháp/Equal/Neither: **0.3151**, đồng thuận **24/50 (48%)**. Con số này không đổi khi bỏ tiền tố ghi chú trong CSV.
