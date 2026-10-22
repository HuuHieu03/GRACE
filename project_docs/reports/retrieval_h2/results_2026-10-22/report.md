# Kết quả H2 trên Kaggle — 2026-10-22

Trạng thái: **COMPLETE, đã kiểm tra lại từ dữ liệu tải về**.

Notebook: https://www.kaggle.com/code/huuhieu3333/grace-h2-shared-top50-r0-r1

Commit thực thi: `827aab9b50039647f2f1136dee3c6a1fa5640374`.
CodeT5 thật chạy CUDA, vocabulary 32.100, embedding 768 chiều, mean pooling
theo attention mask, tối đa 512 token. Toàn bộ 21.854 hàm train và 100 query
đã có embedding hoàn tất. Không gọi LLM.

| Chỉ số | Kết quả |
|---|---:|
| Query được đánh giá | 100 |
| Có bằng chứng E1.2 active | 36/100 |
| Có ứng viên cùng active family trong top-50 | 36/100 |
| R0 đã chọn ứng viên cùng family, trong nhóm có bằng chứng | 36/36 |
| R1 đổi lựa chọn so với R0 | **0/100** |
| R1 fallback về R0 vì query không có active family | 64/100 |
| Query chỉ có bằng chứng conditional | 0 |
| Trong 64 query thiếu active evidence: có Unknown call | 58 |
| Ứng viên cùng family khi có match: min / median / max | 2 / 18,5 / 41 |
| Query trùng code train sau khi bỏ whitespace | 0 |

## Kiểm tra tính toàn vẹn

- Hash dữ liệu train/query khớp dữ liệu cục bộ đã đóng băng.
- Hai ma trận vector đúng shape/dtype, hữu hạn và checkpoint đã hoàn tất.
- Tính lại tìm kiếm L2 trên full train cho 100 query: top-50 khớp.
- Tính lại điểm, thứ tự R0, policy R1, evidence và các thống kê: khớp toàn bộ.
- Mỗi query có đúng 50 ứng viên riêng biệt, hai arm dùng chung tập ứng viên.

R0 sau rerank giữ nguyên ứng viên L2 top-1 ở 48/100 query. Như vậy reranker
có tác động so với tìm kiếm embedding thuần; phần ưu tiên family bổ sung của
R1 không làm thay đổi thêm lựa chọn trên split này. Đây không phải phép so sánh
chất lượng với B2 gốc: cả hai arm hiện tại đều dùng adapter E1.2.

## Diễn giải và bước tiếp theo

H2 xác nhận **R1 chưa tạo ra khác biệt quan sát được về lựa chọn demo** trên
100 query hiện tại. Không có cặp demo khác nhau để quy kết chênh lệch cho policy
R1 trong một thí nghiệm LLM ghép cặp. Chưa nên chạy hai arm LLM chỉ để tìm lợi
ích của policy này; nếu chạy hai lượt với cùng demo, chênh lệch đầu ra không
thể được quy cho việc R1 chọn ví dụ khác.

Kết quả chưa cho biết demo đã phù hợp về ngữ nghĩa hay phát hiện lỗ hổng tốt.
Family có thể quá rộng; E1.2 không chứng minh guard có hiệu lực, và các thành
phần non-sink cũ vẫn có giới hạn đã ghi trong protocol.

Bước tiếp theo nên là review relevance độc lập trên các demo đã chọn và audit
58 query có Unknown call nhưng thiếu active evidence. Cần phân biệt helper
thực hiện thao tác nhạy cảm với lời gọi thông thường trước khi thêm registry.
Giữ nguyên kết quả H2 này; mọi sửa policy/registry tiếp theo phải có phiên bản
mới và được kiểm tra trên dữ liệu chưa dùng để sửa. Không tăng rule chỉ để
làm cho R1 có số ca đổi lựa chọn.

## Tái lập và dữ liệu

Chạy `python -m scripts.analyze_retrieval_h2_results` sau khi tải đầu ra bằng
`python scripts/pull_kaggle_h2_results.py`.

- `audit_summary.json`: thống kê và các kiểm tra hoàn tất.
- `per_query.csv`: evidence coverage, số ứng viên match và lựa chọn từng query.
- Dữ liệu thô, embedding và log lưu tại `artifacts/retrieval_h2_kaggle_run`;
  source map có nhãn được giữ riêng, không dùng để chọn hoặc đánh giá relevance.

Đây là phân tích kỹ thuật. Không tạo thêm phiếu chấm độc lập hoặc kết quả
accuracy/F1/Kappa mới từ lần chạy này.
