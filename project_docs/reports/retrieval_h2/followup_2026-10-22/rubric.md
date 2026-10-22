# Chấm relevance độc lập cho một demo

Đây là đánh giá độ phù hợp của một ví dụ tham chiếu với query, không phải chấm
nhãn có/không có lỗ hổng. R0/R1 đã chọn cùng demo nên không tạo hai lựa chọn
giả. Mỗi người chấm nhận `relevance_review_packet.md` hoặc bản JSON tương ứng,
rubric này và một sheet riêng. Không mở source map, diagnostics hay technical
case notes trước khi khóa phiếu. Hai người chấm làm riêng và chưa đối soát.

Mã nguồn được giữ nguyên, không cắt; nhãn dataset, tên tệp gốc, điểm truy hồi,
arm và nhận xét kỹ thuật được loại khỏi packet. Tên hàm và nội dung code có
thể tiết lộ dự án/phiên bản; đây không phải bảo đảm ẩn danh tuyệt đối.

Điền các cột sau, kèm trích đoạn ngắn từ cả query và demo:

| Cột | Giá trị hợp lệ và ý nghĩa |
|---|---|
| operation_alignment | same / related / different / insufficient: thao tác chính có tương ứng hay chỉ cùng API phụ trợ? |
| object_role_alignment | same / partial / different / insufficient: buffer/resource/đối tượng có cùng vai trò không? |
| guard_comparability | comparable / different / not_applicable / insufficient: có thể so sánh điều kiện kiểm tra và thao tác được bảo vệ không? Không mặc định một `if`/assert là guard hiệu quả. |
| overall_relevance | relevant / partial / irrelevant / insufficient: demo có giúp phân tích query với bằng chứng cụ thể không? |
| query_evidence, demo_evidence | Trích đoạn mã để giải thích quyết định; không dùng nhãn dataset. |
| notes | Lý do, giới hạn ngữ cảnh, helper/macro cần định nghĩa hoặc code thiếu. |

`relevant` yêu cầu tương ứng rõ về thao tác và đối tượng. `partial` dùng khi có
thông tin hữu ích nhưng khác vai trò/điều kiện quan trọng. `irrelevant` dùng khi
chỉ giống bề mặt hoặc khác thao tác chính. `insufficient` dùng khi thiếu ngữ
cảnh để phân biệt các trường hợp trên. Có thể hai hàm cùng API ghi log nhưng
không relevant; cũng có thể cả hai chỉ log rồi thoát và lại khá tương ứng.

Không biến số lượng sink/family/API trùng nhau thành điểm chấm tự động. Không
điền sheet thay người chấm bằng inventory hay technical notes. Sau khi có hai
phiếu đã khóa mới tính agreement và Cohen's Kappa cho overall_relevance như
nhãn danh nghĩa; giữ phiếu gốc trước khi đối soát. Không tự gộp `insufficient`
vào `irrelevant` hoặc loại bỏ để làm đẹp agreement.

Các file mẫu hiện để trống. Việc chuẩn bị packet có Codex hỗ trợ; chưa có kết
quả chấm relevance độc lập được tạo ra trong bước này.
