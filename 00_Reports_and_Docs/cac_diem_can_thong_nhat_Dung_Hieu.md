# Bảng Các Điểm Cần Thống Nhất Giữa Dũng và Hiếu (Chuẩn Bị Cho Đợt 3)

**Thời gian lập:** 25/10/2026  
**Mục đích:** Đồng bộ hóa quy chuẩn kỹ thuật, định dạng artifact và cơ sở hạ tầng thực nghiệm giữa hai thành viên trước khi tiến hành Đợt 3 (Xác nhận và giải thích trên Test Set độc lập).

---

## 1. Danh Mục Các Điểm Kỹ Thuật Cần Thống Nhất

| STT | Nội dung kỹ thuật | Hiện trạng phía Dũng | Hiện trạng phía Hiếu | Phương án thống nhất cho Đợt 3 |
|:---:|---|---|---|---|
| **1** | **Quy ước đơn vị Context Limit** | Giới hạn cứng **8.192 UTF-8 bytes** (cắt bớt nếu vượt byte). | Giới hạn theo **8.192 tokens** của Qwen, kết hợp phân bổ truncation ký tự theo contract (~2.000 - 3.500 tokens). | **Thống nhất:** Áp dụng song song cả 2 rào chắn: Kiểm soát token $\le 8.192$ VÀ kiểm soát dung lượng payload UTF-8 bytes trước khi gửi request để triệt tiêu lỗi HTTP 400. |
| **2** | **Trình phân tích kết quả (Canonical Parser)** | Đã đối soát 36 run, không gán response không xác định thành 0. | Dùng `parse_llm_prediction` chuẩn regex; reparse 100 mẫu dev ghi nhận 0% invalid và 0 nhãn đổi. | **Thống nhất:** Sử dụng chung một hàm parser duy nhất `strict_parser.py` (`ExactLastLineBinaryParser`), chỉ chấp nhận dòng cuối là `0` hoặc `1`, mọi response khác đánh dấu `invalid`. |
| **3** | **Định dạng bảng lưu vết từng mẫu (Run Ledger)** | Đã có ledger Markdown/CSV cho 36 run V1/V2. | Đã có đầy đủ trong artifact JSON (`output/stage3/`, `output/stage2/`) kèm commit SHA và log Kaggle. | **Thống nhất:** Chuẩn hóa xuất bản chung file CSV ledger gồm các cột: `sample_idx`, `target_id`, `target_label`, `predicted_label`, `status`, `commit_sha`, `prompt_hash`, `raw_response`. |
| **4** | **Cơ chế Checkpoint & Crash Recovery** | Từng run có metadata attempt; một số run cũ thiếu attempt. | Đã lập trình sẵn lớp `CheckpointManager` trong `src/evaluator.py`, flush realtime JSONL theo `config_hash`. | **Thống nhất:** Tích hợp `CheckpointManager` vào toàn bộ script thực thi Đợt 3 để đảm bảo tự phục hồi khi mạng gián đoạn, không mất token hay chi phí gọi API. |
| **5** | **Rào chắn cô lập Mock vs Real API** | Bảng metric đã lọc request Qwen thực tế. | Đóng dấu metadata `use_mock: False`, kiểm tra runtime timestamp và response header Vertex AI. | **Thống nhất:** Thêm assertion cứng `assert result["use_mock"] is False` trong script đánh giá nghiệm thu; mock chỉ kích hoạt khi truyền `--use_mock` trong unit test offline. |
| **6** | **Lựa chọn Mô hình & Hạ tầng Đợt 3** | Đề xuất hoàn thiện đối chứng nhánh cải tiến riêng (H1, H2, H3). | Đề xuất chuyển sang Gemini 1.5 Flash/Pro hoặc private vLLM (Qwen2.5-Coder-32B). | **Thống nhất:** Báo cáo Thầy hai hướng song song, xin chỉ đạo lựa chọn backbone chính thức cho Test Set (khuyến nghị Gemini 1.5 Flash vì SLA ổn định và context window lớn). |

---

## 2. Kế Hoạch Phối Hợp Tiếp Theo
1. **Trước buổi gặp Thầy:** Hai bạn cùng rà soát lại văn bản báo cáo chung và bảng thống nhất này để đạt sự đồng thuận 100%.
2. **Sau khi Thầy duyệt định hướng:** Đóng băng cấu hình, dữ liệu, prompt template và evaluator chung trước khi bấm nút chạy Test Set.
