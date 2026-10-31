# Đính chính complementarity Bước 0, 30/10/2026

> Cập nhật: tài liệu B3 yêu cầu train OOF làm ngưỡng chung cho phân tích chính. Ngưỡng validation trong bản đính chính bên dưới là mốc gate_tuned lịch sử riêng. Xem `THRESHOLD_POLICIES_20261030.md` để biết hai phép so và đầu ra mới.

Hai JSON được xuất 17:11 ngày 29/10, trước khi bảng join và checkpoint chuẩn được cập nhật lúc 18:29 cùng ngày. Không tìm được lệnh hoặc manifest đủ để chứng minh chính xác nguồn và cấu hình sinh hai JSON cũ. Chúng không khớp các bảng join hiện hành, nên không được coi là kết quả của checkpoint đã khóa.

Đã chạy lại với Devign checkpoint a93a831ac8416426a1d4, tau 0.53; ReVeal checkpoint b4564696e647259a09b9, tau 0.14. Kiểm tra ID, code hash, thứ tự X_pre và gate score của mỗi split trước khi chạy; so sánh độc lập repair, harm và gate accuracy sau khi chạy. Các đầu vào và hash được ghi trong provenance của JSON mới. Các file cũ giữ lại dưới hậu tố `.stale_20261029.json`.

Test: Devign 303 repair / 580 harm / oracle accuracy 0.7639092240; ReVeal 218 repair / 201 harm / oracle accuracy 0.9423922603. Dữ liệu này là thăm dò lịch sử, LLM score là nhãn 0/1, validation trộn provider và test dùng provider khác.

Chạy lại: `.venv-b0-312/Scripts/python.exe B0_offline/rebuild_complementarity_locked.py devign` và tương tự với `reveal`, sau đó kiểm tra trước khi promote. ZIP `requested_data_bundle_20261029_FINAL.zip` được cập nhật ngày 30/10 với các kết quả đã sửa.
