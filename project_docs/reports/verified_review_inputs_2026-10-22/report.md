---
version: "1.0.0"
date: "2026-10-22"
type: "report"
status: "IN_PROGRESS"
target_component: "Verified review inputs preflight"
tags: ["review", "missing_input", "provenance"]
summary: "Target và B3 pair đã kiểm identity; thiếu actual B2 records của chính Stage3 Ver03/Ver04 nên chưa tạo packet, không lấy Stage2/B3 đối nhãn thay thế."
---

# Việc 3 — đã kiểm đầu vào, chưa đủ để dựng bộ chấm hợp lệ

`input_inventory_private.json` đã xác minh code/UID của 100 target và 200 B3 demo members mỗi dataset bằng contract v2. Giữ cả hai demo B3, không dùng nhãn target để chọn một thành viên. File này là inventory riêng, không gửi cho người chấm mù.

**Đã chốt với người dùng:** record lựa chọn/prediction/raw response/prompt B2 thực của đúng Stage3 Devign **Ver03** và ReVeal **Ver04** hoàn toàn không còn/không tồn tại. Xác nhận lưu tại `historical_availability.json`. JSON hiện có chỉ giữ B3 và B2 metrics tổng hợp. Raw/per-ID B2 Stage2 là run khác, không tự thay thế. Không tạo demo B2 từ thành viên đối nhãn trong cặp B3.

Quyết định: không tiếp tục tìm hoặc dựng lại review cho hai run lịch sử này. Cần run mới với lưu vết đúng sau khi sửa việc 4–5, rồi mới tạo bộ chấm của thí nghiệm mới. Không thể phục hồi bằng suy đoán hoặc chỉ bằng metric tổng hợp.

Đã chặn entrypoint `generate_blind_sheets` và CLI generator cũ để tránh tiếp tục tạo phiếu phụ thuộc nhãn target hoặc ghi đè phiếu lịch sử. Các loader/evaluator lịch sử vẫn import được; không xóa phiếu hoặc thay lựa chọn đã được ghi nhận.

Sau khi có inputs đúng: tạo packet full code với mapping riêng, kiểm hash target/demo, tráo arm, gửi hai phiếu riêng; người chấm tự điền, khóa trước đối soát. Ghi rõ ai đã xem nhãn/phương pháp/technical notes. Không dùng xác nhận đối soát thay cho bằng chứng hai lượt chấm độc lập.

Tái kiểm inventory: `python scripts/prepare_verified_review_inputs.py`. Script không gọi API, không tạo packet thay thế, không điền điểm hoặc quyết định của người chấm.
