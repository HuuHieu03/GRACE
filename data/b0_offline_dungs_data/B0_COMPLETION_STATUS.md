# Trạng thái gói Bước 0

Gói chứa xpre và gate CSV cho validation/test của Devign và ReVeal, test join đầy đủ, validation Devign ghép được, danh sách 85 dự đoán validation còn thiếu, cùng CLI và hướng dẫn export.

**Chưa phải bộ kết quả Bước 0 hoàn chỉnh:** thiếu 8 dự đoán expert validation Devign và 77 ReVeal. Không có log xác nhận invalid nên không gán `valid=0`. Chưa sinh complementarity JSON chính thức, chưa xác nhận metric lịch sử sai khác <= 0.001. `s_llm` trong join test là nhãn 0/1, không phải logprob.

Các xpre được xuất bằng artifact H3-B đã khóa; X[:,5] khớp gate score file tương ứng với sai số tuyệt đối < 1e-5. Test IDs và code SHA-256 khớp đầy đủ.
