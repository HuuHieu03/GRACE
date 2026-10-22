# Rà soát kỹ thuật sau H2 — 2026-10-22

Trạng thái: hoàn tất kiểm kê 58 query thiếu active evidence nhưng có Unknown,
kiểm tra kỹ thuật có chọn lọc 18 ca và chuẩn bị bộ chấm relevance cho 100 demo.
**Chưa có phiếu relevance độc lập mới**. Nội dung kỹ thuật có Codex hỗ trợ.
Không thay registry, parser, policy hoặc kết quả H2 đã đóng băng; không gọi LLM.

## 1. Không thể hiểu 36/36 family-match là 36 demo phù hợp

Trong 36 query có active evidence:

- 5 cặp chỉ chung family `format_string`: Q-00007, Q-00015, Q-00018,
  Q-00069, Q-00071.
- 3 cặp chung family nhưng không chung API: Q-00031, Q-00054, Q-00079.
  Đây chỉ là mô tả, không tự động chứng minh mismatch.

Đọc mã của 5 cặp format-only cho thấy:

| Query | Bằng chứng kỹ thuật | Hàm ý |
|---|---|---|
| Q-00007 | Query tạo packet GDB, `fprintf(stderr, ...)` báo lỗi format; demo ghi header ảnh PPM bằng `fprintf(f, ...)`. | Cùng API nhưng vai trò đầu ra khác nhau. |
| Q-00015 | Hai hàm EHCI cùng log rồi `exit(1)` khi gặp độ rộng MMIO không hỗ trợ. | Đối chứng: không được loại mọi format-only match. |
| Q-00018 | Query tạo/đăng ký opcode table; demo duyệt và in instruction table. | Cùng `printf` không chứng minh tương ứng thao tác chính. |
| Q-00069 | Query kết nối socket với EINTR/nonblocking; demo tạo/bind/join multicast. | Cùng lĩnh vực mạng nhưng khác giao thức tài nguyên và guard cần xét. |
| Q-00071 | Query tạo media stream; demo khởi tạo monitor/chardev. | `fprintf` báo lỗi có thể là giống nhau phụ trợ. |

Q-00049 là một kiểm tra chống kết luận quá tay: mặc dù API trùng chỉ là
`fprintf`, hai hàm còn chung family `pointer_free` qua `g_free`/`free` và cùng
thao tác sắp xếp alarm timer. Không xếp ca này vào nhóm format-family-only.

Các ca được chọn có chủ đích, không phải mẫu ngẫu nhiên để ước lượng error rate.
Chưa gán điểm relevance hay nhãn lỗ hổng từ các nhận xét này.

## 2. Kiểm kê 58 query Unknown

Có **492 vị trí**, **252 tên khác nhau**. Mọi offset/expression đã đối chiếu
với code gốc. Phân luồng sơ bộ theo cú pháp/tên, không phải gold semantic:

| Nhóm | Vị trí |
|---|---:|
| Cần định nghĩa helper hoặc ngữ cảnh để kết luận | 380 |
| Tên assertion; không mặc định là sink hay guard hiệu quả | 10 |
| Tên gợi ý logging; cần ngữ cảnh | 43 |
| `RENAME`, macro chọn tên symbol chưa được mở rộng | 36 |
| Khai báo bị ghi nhận thành Unknown call | 1 |
| Macro COPY cục bộ đã đọc định nghĩa: gán field | 22 |

Tìm trong full train được đầu mối định nghĩa cho 60/252 tên. Đây chỉ là
candidate: nhiều phiên bản/project/static scope có thể khác, và phép tìm
header chưa xử lý đủ macro hoặc function pointer. Không có đầu mối không
chứng minh định nghĩa không tồn tại. Có đầu mối không chứng minh đúng callee.

Các cơ chế thiếu bằng chứng đã quan sát trực tiếp:

- **Khai báo và macro tên hàm:** Q-00045 báo `uint8_t` từ tham số
  `uint8_t (*layout_map)[3]`; Q-00040 có RENAME trong tên hàm. Đây không phải
  bằng chứng runtime call để thêm registry.
- **Macro có nghĩa cục bộ:** Q-00062 định nghĩa COPY là `bak->a = src->a`.
  22 vị trí là gán field, chưa chứng minh bulk/deep buffer copy. Quy tắc toàn
  cục COPY → buffer_write sẽ đánh đồng macro cùng tên ở các dự án.
- **Thao tác trực tiếp:** Q-00039 có `*output++ = *src++` và casted pointer
  writes; Q-00040 có cập nhật mảng; Q-00097 cập nhật array dirty-page. Bổ sung
  tên wrapper không biểu diễn được những thao tác đó.
- **Lời gọi gián tiếp:** Q-00075 có `s->dsp.mct_decode[index](...)`; inventory
  chỉ có av_log. Callee thực và contract chưa được giải quyết.
- **Assembly và build config:** Q-00078/Q-00094/Q-00098 có asm/macro và
  memory operands. Cần mô hình khác với danh sách API; chưa đủ định nghĩa để
  gán contract cho WRITEBGR24 hoặc các macro assembly khác.
- **Có thể đúng là ngoài phạm vi:** Q-00017 chỉ assert và tính bit mask;
  không phải mọi Unknown đều đại diện một sink bị bỏ sót.

Chi tiết 18 ca và anchor mã nằm trong `technical_case_notes.json`. Các anchor
đã được kiểm tra với query và demo thật, không có phiếu người chấm được tạo.

## 3. Bộ relevance review đã sẵn sàng

`relevance_review_packet.md`/JSON gồm 100 query và demo đã chọn, thứ tự xáo
trộn bằng seed 20261022 và ID H2R-001…100. Không hiển thị policy, điểm, nhãn
dataset, tên tệp hoặc nhận xét kỹ thuật. Code giữ nguyên; tên hàm trong code
vẫn có thể gợi ý project/phiên bản. Mapping để riêng trong file private.

Hai sheet reviewer_A/B còn trống. Rubric phân biệt thao tác chính, vai trò
đối tượng, khả năng so sánh guard và relevance tổng thể. Chỉ cung cấp packet,
rubric và sheet riêng cho mỗi người chấm; không cung cấp diagnostics, báo cáo
này hay technical notes trước khi khóa hai phiếu. Không cần chấm cặp R0/R1
vì hai arm chọn cùng demo ở cả 100 query.

Sau khi nhận hai phiếu thực mới tính agreement/Kappa và đối soát. Người chấm
đã xem technical notes sẽ không còn mù đối với các ca đó; cần ghi rõ mức phơi
nhiễm hoặc dùng người chưa xem. Không thể biến các ghi chú Codex thành hai
phiếu người chấm độc lập.

## 4. Quyết định kỹ thuật được đề xuất

Giữ H2 là kết quả **R1 chưa đổi lựa chọn**; không chạy hai arm LLM giống demo
để tìm lợi ích của policy. Tiếp tục review relevance trước khi quyết định
đổi reranker. Nếu triển khai phiên bản evidence tiếp theo, tách riêng:

1. Chặn declaration/symbol-macro artifacts bằng fixture có offset cụ thể.
2. Biểu diễn vai trò callsite (diagnostic/file output/buffer formatting),
   không loại toàn bộ format_string và không khẳng định guard hiệu quả.
3. Thiết kế kênh evidence riêng cho direct memory/indirect/asm, với Unknown
   và giới hạn rõ ràng; không lấp chỗ trống bằng rule tên quá rộng.
4. Chỉ thêm wrapper contract có định nghĩa phù hợp về project/version;
   mọi sửa trên canonical100 hiện tại là development, cần tập mới để xác minh.

Đây là đề xuất dựa trên kiểm tra kỹ thuật, chưa phải kết quả ablation mới hoặc
phê duyệt tự động để sửa toàn bộ pipeline.

Tái lập inventory/packet: `python -m scripts.prepare_h2_followup_review`.
Script không ghi đè các sheet đã tồn tại; không tạo điểm chấm, không đổi H2.
