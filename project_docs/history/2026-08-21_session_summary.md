# Session Summary - 2026-08-21

## 1. Mục tiêu phiên làm việc
- Hỗ trợ người dùng phân tích kết quả các lần chạy thực nghiệm trên Kaggle (`Ver05`, `Ver06`, `Ver07`).
- Chuẩn đoán và sửa triệt để lỗi không nạp được mô hình CodeT5 (`Salesforce/codet5-base`) do xung đột thư viện `transformers` mới trên Kaggle.
- Nâng cấp độ kiên cố của pipeline (GPU Batch Encoding, chống nghẽn Rate Limit HTTP 429 từ FPT AI API).
- Kiểm tra việc kích hoạt Graph Similarity và In-Context Learning theo đúng bài báo GRACE.
- Chuẩn hóa notebook và đóng gói để người dùng chạy trên 100% tập dữ liệu Devign.

---

## 2. Các công việc đã thực hiện
- **Phân tích log Ver05 & Ver06**: Phát hiện cảnh báo `extra_special_tokens: null` khiến hệ thống fallback về TF-IDF (256d).
- **Khắc phục triệt để CodeT5 Tokenizer**:
  - Triển khai chiến lược tải trực tiếp `vocab.json` và `merges.txt` qua `hf_hub_download` nạp vào `RobertaTokenizer`, hoàn toàn bỏ qua file `tokenizer_config.json` bị lỗi.
  - Sử dụng `T5EncoderModel` và bổ sung GPU Batching (`batch_size=32`), giúp mã hóa 1,091 mẫu chỉ trong 1.23 giây.
- **Nâng cấp LLM Evaluator**: Thêm cơ chế Smart Exponential Backoff tự động nghỉ 20s–60s khi gặp 429 và bổ sung micro-delay 0.05s.
- **Nghiệm thu kết quả Ver07**:
  - CodeT5 nạp thành công 100% (`(1091, 768)`).
  - F1-Score tăng mạnh từ `0.4643` lên `0.5043` (+4.0%), Precision đạt `0.5472`, Recall đạt `0.4677`.
- **Chuẩn hóa quy trình chạy 100% Full Dataset**: Loại bỏ bước Mock Warm-up dư thừa trong `build_kaggle_notebook.py` và cập nhật `GRACE_Kaggle_Reproduce.ipynb`.
- **Đóng gói mã nguồn**: Tái tạo tệp `grace_kaggle_clean_package.zip` (304.1 MB) chứa đầy đủ mã nguồn và dữ liệu đồ thị CPG.
- **Cập nhật tài liệu dự án**: Ghi nhật ký vào `project_docs/logs/`, cập nhật tiến độ vào `project_docs/progress/` và lưu trữ tóm tắt phiên vào `project_docs/history/`.

---

## 3. Các quyết định / Thảo luận quan trọng
- **Xác nhận CodeT5**: Đã nạp thành công vector ngữ nghĩa 768 chiều trên GPU Kaggle, bảng thông báo `lm_head.weight | UNEXPECTED` là bình thường do chỉ nạp phần Encoder để tối ưu GPU VRAM.
- **Xác nhận Graph & In-Context Learning**: Đã được kích hoạt 100% ở cả Stage 2 (Hybrid Reranking $0.7 \times \text{Jaccard} + 0.3 \times \text{GraphSim}$) và Stage 3 (Prompt Engine dẫn hướng 1-shot Figure 6 kèm luồng CPG graph tóm tắt).
- **Bỏ bước Warm-up Mock**: Đối với các lần chạy chính thức tiếp theo, bỏ qua bước Mock để tiết kiệm thời gian và giữ notebook tinh gọn.

---

## 4. Trạng thái hiện tại & Bước tiếp theo
- **Trạng thái hiện tại**: Mã nguồn và notebook đã ở trạng thái hoàn hảo 100%, sẵn sàng chạy chính thức toàn bộ dữ liệu.
- **Bước tiếp theo**: Người dùng chạy thực nghiệm trên 100% tập dữ liệu Devign (`--sample_ratio 1.0`, 2,732 mẫu test) trên Kaggle GPU và thu thập báo cáo nghiệm thu cuối cùng.
