# E1.3 và trạng thái các bước 1–3 — 2026-10-22

## Bước 1: kiểm tra phiếu và chuẩn bị tính agreement/Kappa

Đã kiểm tra hai sheet relevance hiện tại: A = **0/100 hoàn tất**, B =
**0/100 hoàn tất**. Chưa có dữ liệu để tính agreement, Kappa hoặc đối soát.
Hai phiếu được giữ nguyên. Không điền hai bộ quyết định bằng cùng một lượt
đánh giá rồi coi là hai người chấm độc lập.

Đã triển khai `python -m scripts.check_h2_relevance_reviews`: kiểm tra ID,
giá trị hợp lệ, độ đầy đủ và evidence; chỉ tính agreement/Kappa danh nghĩa
khi cả hai phiếu hoàn tất. Trường hợp expected agreement bằng 1 cho Kappa
không xác định thay vì gán 1. Công cụ không xác minh được tính độc lập của
người chấm chỉ từ nội dung CSV. Kết quả hiện tại lưu tại
`../retrieval_h2/followup_2026-10-22/review_completion_status.json`.

## Bước 2: tổng hợp bằng chứng kỹ thuật hiện có

Kết quả H2 vẫn là R1 đổi **0/100** lựa chọn. Kiểm kê 58 query thiếu active
evidence ghi nhận 492 vị trí Unknown/252 tên; 18 ca đã được đọc có chọn lọc.
Đây là dữ liệu chẩn đoán, chưa phải tỷ lệ demo relevant/irrelevant của hai
người chấm.

Các vấn đề có anchor mã cụ thể:

1. 5 cặp chỉ cùng family format_string; Q-00007/Q-00071 có vai trò đầu ra
   hoặc lĩnh vực khác nhau, trong khi Q-00015 là hai hàm MMIO khá tương ứng.
   Vì vậy không nên loại mọi printf/fprintf hoặc mọi format-family match.
2. Q-00045: `uint8_t (*layout_map)[3]` là khai báo tham số, không phải call.
3. Q-00040/Q-00076/Q-00078/Q-00094: RENAME trong tên khai báo hàm đang được
   ghi nhận thành Unknown call. RENAME trong thân hàm còn cần ngữ cảnh riêng.
4. Truy cập bộ nhớ trực tiếp, indirect calls, local macros và asm chưa thể
   được giải quyết chỉ bằng thêm tên wrapper.

Chi tiết: `../retrieval_h2/followup_2026-10-22/report.md` và
`technical_case_notes.json` trong cùng thư mục follow-up.

## Bước 3: triển khai phiên bản sửa đổi nhỏ, có thể kiểm chứng

Đã tạo `src/security_signature/sink_evidence_v13.py` riêng biệt:

- Loại mẫu array-pointer parameter của các scalar type cố định khi nằm
  trong header, trước thân hàm; không loại lời gọi tương tự trong thân hàm.
- Loại RENAME dạng tên hàm macro trong declaration header; giữ RENAME trong
  thân hàm là Unknown. Không thêm rule COPY/RENAME vào registry sink.
- Bổ sung output_role dựa trên cú pháp: `fprintf(stderr,...)` →
  diagnostic_stderr; stdout/printf → standard_stdout; snprintf/sprintf →
  buffer_formatting; stream khác → stream_output_unresolved.

Vai trò này mô tả đích ghi, không chứng minh thao tác chính, nguy cơ format
string hay guard hiệu quả. `fprintf(f,...)` chưa được khẳng định là ghi file
nếu không có dataflow chứng minh nguồn của f. Chưa thay điểm reranker hay
loại bất kỳ format_string evidence nào khỏi việc chọn demo.

E1.2, kết quả H2 và pipeline production giữ nguyên. E1.3 là thử nghiệm,
chưa có kết luận cải thiện relevance hoặc độ chính xác dự đoán.

## Kiểm tra

**63 tests đạt**: 11 tests E1.3, 4 tests công cụ review, 41 regression E1.2
và 7 tests policy H2.

| Tập | Hàm | Recognized sites được giữ nguyên | Syntax artifacts loại khỏi Unknown |
|---|---:|---:|---:|
| Development canonical100 | 100 | 114/114 | 5: 4 RENAME header + 1 array-pointer declaration |
| Fresh validation50 | 50 | 47/47 | 3 RENAME header |

50 input mới được chọn bằng seed 20261022 sau khi đóng băng E1.3, loại các
mã trùng sau bỏ whitespace với full train, canonical100 và E1.1 dev50 trước
đó. Không dùng nhãn/prediction để chọn. Không khẳng định loại hết near clones;
đây vẫn là Devign validation, không phải final test.

Đã kiểm tra trực tiếp cả 3 RENAME mới được loại ở E13-009/E13-043/E13-047:
đều thuộc header tên hàm. Offset/expression và các recognized callsites được
đối chiếu; inactive evidence không thay đổi. Đây là kiểm tra tính nhất quán
và cú pháp trên input mới, **không phải precision/recall semantic**. Packet
annotation mới vẫn chưa có gold. Không có vòng sửa E1.3 dựa trên kết quả mới.

Tái lập: `python -m scripts.evaluate_sink_evidence_v13`.

## Việc còn lại

Cần hai phiếu relevance thực trước khi hoàn tất bước 1 và phần tổng hợp
relevance của bước 2. Sau đó mới quyết định có dùng output_role trong
reranker phiên bản mới và đánh giá semantic trên dữ liệu chưa dùng để sửa.
Không chạy lại LLM hoặc công bố Kappa/relevance cải thiện từ kiểm tra kỹ thuật
hiện tại.
