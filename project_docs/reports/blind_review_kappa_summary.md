---
version: "1.0.0"
date: "2026-10-21"
type: "report"
status: "COMPLETED"
author: "Codex"
target_component: "Agreement between submitted Hiếu/Dũng review sheets"
tags: ["cohen_kappa", "review_agreement", "ai_assisted"]
summary: "50 cặp đánh giá hợp lệ; unweighted Cohen's Kappa = 0.3151, đồng thuận 48%. Nguồn đánh giá chưa xác lập là hai lượt chấm độc lập của con người."
---

# Kết quả Cohen's Kappa của hai bảng hiện tại

Đã kiểm tra 50/50 target ID duy nhất, sample index, target label và ánh xạ đáp án. Code target và demo A/B khớp sau chuẩn hóa CRLF/LF; không có lựa chọn trống/sai hoặc mẫu bị loại. Hai CSV giữ nguyên.

Tính bằng `scripts/evaluate_blind_review.py`, không bật sinh mock. Phân loại là Baseline / Security-Aware / Equal / Neither sau giải mã A/B, dùng kappa danh nghĩa không trọng số. Không gộp Equal và Neither. Không dùng A/B trực tiếp cho xác suất đồng thuận kỳ vọng vì vị trí phương pháp thay đổi theo từng mẫu.

| Hiếu \\ Dũng | Baseline | Security-Aware | Equal | Neither | Tổng |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 12 | 3 | 2 | 0 | 17 |
| Security-Aware | 2 | 3 | 3 | 0 | 8 |
| Equal | 1 | 1 | 4 | 0 | 6 |
| Neither | 4 | 7 | 3 | 5 | 19 |
| Tổng | 19 | 14 | 12 | 5 | 50 |

- Đồng thuận quan sát: Po = 24/50 = 0.48.
- Đồng thuận kỳ vọng: Pe = (17×19 + 8×14 + 6×12 + 19×5)/50² = 0.2408.
- **κ = (Po − Pe)/(1 − Pe) = 0.3150684932 ≈ 0.3151.**
- 26/50 mẫu bất đồng; mức đồng thuận thường được mô tả là thấp (*fair*) theo quy ước trong evaluator. Phân loại này không đo độ đúng của đánh giá và không chứng minh phương pháp retrieval nào tốt hơn.

Đã đối chiếu độc lập phép tính từ ma trận tần số, khớp kết quả evaluator. JSON lưu hash SHA-256 của hai bảng để định danh đầu vào.

## Nguồn đánh giá và giới hạn

Người dùng đã xác nhận bảng Hiếu là bản chấm của mình; ghi chú chuẩn bị trong từng dòng được bỏ theo yêu cầu, giữ nguyên lựa chọn. Bảng Dũng có toàn bộ 50 lựa chọn và 300 ô rubric trùng với kết quả quy tắc trong `scripts/fill_dung_review_sheet.py`, được kiểm tra bằng gọi hàm phân tích thuần, không chạy hàm ghi CSV. Việc trùng kết quả không xác nhận đã có lượt chấm tay độc lập.

Vì vậy, con số trên mô tả độ đồng thuận giữa **hai bảng hiện có**; chưa đủ cơ sở trình bày là độ tin cậy giữa hai người chấm độc lập. Cần giữ nguyên các bản trước đối soát; nếu có điều chỉnh sau thảo luận, lưu riêng để không thay thế kappa trước đối soát.

## Artifact

- `blind_review_evaluation_report.json`: kết quả, ma trận, nguồn đánh giá, hash đầu vào và chi tiết từng mẫu.
- `blind_review_discordant_cases.csv`: 26 mẫu cần đối soát cùng lựa chọn và ghi chú của cả hai bảng.
