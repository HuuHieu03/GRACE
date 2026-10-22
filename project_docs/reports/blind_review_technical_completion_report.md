---
version: "1.0.0"
date: "2026-10-21"
type: "report"
status: "COMPLETED"
author: "Codex — technical adjudication"
target_component: "Hoàn tất rà soát kỹ thuật hồ sơ chấm demonstration"
tags: ["blind_review", "technical_adjudication", "failure_analysis"]
summary: "Rà soát 50 mẫu theo rubric thống nhất, xử lý kỹ thuật 26 ca bất đồng, bổ sung 15 file code đầy đủ cho 5 ca; giữ nguyên hai phiếu và kappa gốc. Chưa xác lập đồng thuận độc lập của hai người."
---

# Kết quả hoàn thiện hồ sơ rà soát demonstration

Đã hoàn tất phần rà soát kỹ thuật có thể thực hiện từ dữ liệu dự án: toàn bộ 50 mẫu được áp dụng cùng rubric, 26 ca bất đồng có quyết định kỹ thuật và bằng chứng, 5 ca thiếu ngữ cảnh được bổ sung hàm đầy đủ từ split/bank cục bộ. Hai phiếu chấm gốc giữ nguyên. Trạng thái COMPLETED của tài liệu này chỉ áp dụng cho rà soát kỹ thuật, không phải xác nhận hoàn tất hai lượt chấm mù độc lập của con người.

## 1. Kết quả gốc được giữ nguyên

- 50 cặp hợp lệ, 24 đồng thuận và 26 bất đồng.
- Cohen's Kappa không trọng số theo Baseline / Security-Aware / Equal / Neither: **0.3151**.
- Tỷ lệ đồng thuận: **48%**.
- Không tính kappa mới giữa một phiếu gốc với bảng tổng hợp kỹ thuật; phép tính đó không đại diện cho hai người chấm độc lập mới.

## 2. Kết quả rà soát kỹ thuật toàn bộ 50 mẫu

| Quyết định | Số mẫu | Tỷ lệ trên 50 |
| --- | ---: | ---: |
| Demo A | 5 | 10% |
| Demo B | 12 | 24% |
| Equal | 3 | 6% |
| Neither | 30 | 60% |

Sau giải mã, 10 mẫu ưu tiên Baseline và 7 mẫu ưu tiên Security-Aware, 3 Equal, 30 Neither. Đây là thống kê mô tả của lượt rà soát kỹ thuật, không phải phiếu đồng thuận của Hiếu/Dũng và không dùng để tuyên bố Baseline vượt trội thống kê.

Có 12 quyết định khác phiếu Hiếu. Trong đó 7 thuộc các mẫu hai phiếu ban đầu cùng lựa chọn: **6, 13, 14, 15, 19, 36, 48**. Việc rà lại cả các ca đồng thuận giúp áp dụng cùng ngưỡng về bằng chứng, thay vì chỉ sửa 26 ca bất đồng. Các lựa chọn gốc vẫn còn nguyên trong từng dòng để truy vết.

## 3. Xử lý 5 ca thiếu ngữ cảnh

| Mẫu | Quyết định kỹ thuật | Bằng chứng và giới hạn |
| --- | --- | --- |
| 26 | Neither | Hàm đầy đủ ghi dregs theo mask chỉ số và dispatch thanh ghi/DMA/IRQ; demo QCOW length-check và TPM size-check không cùng cơ chế. Thiếu CSState nên không xác nhận bound mảng đúng. |
| 28 | Neither | TCG có high-water check sau sinh mã, nhưng không tương đương channel-layout parity; demo decode frame cũng khác ràng buộc parity. |
| 34 | B | TIFF có check_size trước ghi header/entries và encode_strip/memcpy theo kích thước hàng; demo B có bound theo frame/byte-count, liên quan hơn TPM demo A. Chỉ khớp một phần; thiếu body helper nên không xác nhận tất cả write an toàn. |
| 39 | Neither | Có toàn bộ hàm chuyển màu; A SBR parser và B palette insert không cùng asm pixel-store. Thiếu body macro và hợp đồng padding nên guard target vẫn chưa xác định. |
| 50 | Neither | Phần cuối TTA có channel stepping và output samples; demo SCSI/socket không cùng Rice/filter/index. Overread-check trong comment không có hiệu lực thực thi; không vì vậy tự xác nhận vulnerability. |

15 file `.c` nằm trong `blind_review_full_context/`, có manifest SHA-256, ID nguồn và xác nhận code đầy đủ khớp prefix snippet gốc. Các file giữ hàm như dữ liệu cục bộ; không tạo thêm body macro/helper từ suy đoán.

## 4. Nhận định nghiên cứu có thể dùng

Trong lượt rà soát kỹ thuật này, nhiều demonstration thiếu liên hệ đủ cụ thể với thao tác, vai trò biến và điều kiện bảo vệ của target. Trùng từ trong comment, cùng pointer dereference, cùng phép bit hoặc cùng logging không đủ chứng minh cùng cơ chế an ninh. Hai demo giống hệt nhau vẫn có thể cùng không phù hợp với target.

Kết quả này gợi ý cần ưu tiên kiểm tra chất lượng liên kết guard–sink và khả năng chọn demo cùng cơ chế trước khi mở rộng benchmark. Không dùng chính lượt rà soát đã xem phương pháp/nhãn để tuyên bố cải tiến retrieval đã được xác nhận độc lập. Cũng không dùng tính liên quan của demo làm bằng chứng nhãn vulnerability của dataset là đúng.

## 5. Artifact và cách tái lập

- `blind_review_technical_review_50.csv`: quyết định, sáu ô rubric, bằng chứng và lựa chọn gốc cho tất cả mẫu.
- `blind_review_adjudication.csv`: 26 ca, giữ đề xuất cũ và thêm kết quả kỹ thuật; cột người chấm/consensus chưa được tự điền.
- `blind_review_technical_completion.json`: số liệu, giới hạn, hash hai phiếu và đáp án.
- `blind_review_full_context/manifest.json`: 15 file code cho các ca cần bổ sung.
- `scripts/finalize_blind_review_adjudication.py`: tái tạo artifact từ các quyết định đã ghi rõ trong script; không sinh phiếu người chấm và không gọi API.

Chạy: `python scripts/finalize_blind_review_adjudication.py`.

Đã kiểm tra đủ 50 mẫu khớp ID/code giữa hai phiếu, 26 ca có kết quả kỹ thuật, 15 code body khớp prefix snippet gốc, hai phiếu không đổi hash và các cột đồng thuận không bị điền thay người chấm. Nếu cần nghiệm thu đúng mục chấm mù độc lập theo yêu cầu thầy, phần còn lại là hai người thực hiện/ghi nhận quyết định riêng và xác nhận quá trình độc lập thực tế; không thể hoàn tất phần đó bằng cách đổi nhãn bảng kỹ thuật.
