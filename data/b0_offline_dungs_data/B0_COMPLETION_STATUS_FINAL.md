# Trạng thái gói Bước 0 — đã xử lý validation thiếu

85 ID ban đầu vắng mặt vì không có prompt trong cohort validation cũ (8 Devign, 77 ReVeal). Đã tạo prompt theo pipeline H3-B cho các ID đó, gọi FPT AI Factory `DeepSeek-V4.1-Flash`, lưu raw responses và parse thành công 85/85 nhãn. Validation join hiện đủ 2.732 Devign và 2.273 ReVeal; test joins đủ 2.732/2.274.

Validation ghép 2.724/2.196 dự đoán Vertex AI MaaS cũ với 8/77 dự đoán FPT mới. Cột `llm_provider` ghi nguồn từng hàng. Complementarity JSON có provenance mixed-provider; không xem đó là benchmark đồng nhất provider. Graph coverage của 77 prompt ReVeal bổ sung là 77,9%; prompt cho các mẫu Joern không trích được graph ghi rõ graph unavailable.

ZIP kèm xpre/gate/join, prompt/retrieval/graph index của 85 mẫu, raw FPT response, predictions, manifest và complementarity JSON. Không đóng gói API key. Đối chiếu metric lịch sử mục 2.1 với sai khác <=0.001 chưa được thực hiện.
