# Tổng hợp phân tích mã nguồn và bài báo GRACE

Tài liệu này tổng hợp các phân tích, đối chiếu giữa bài báo "GRACE Empowering LLM-based software vulnerability detection with graph structure and in-context learning" và mã nguồn đính kèm, đồng thời đề xuất kế hoạch tái tạo kết quả.

## 1. Sự khác biệt giữa Bài báo và Mã nguồn hiện tại

Quá trình kiểm tra mã nguồn cho thấy kho lưu trữ hiện tại đang thiếu hụt và không khớp với lý thuyết được đề cập trong bài báo ở một số điểm cốt lõi:

### A. Tiền xử lý & Trích xuất đồ thị (Graph Structure)
*   **Lý thuyết:** Bài báo sử dụng công cụ **Joern** để phân tích mã nguồn C/C++ (các tập dữ liệu FFmpeg+Qemu, Big-Vul, Reveal) nhằm trích xuất Code Property Graph (CPG) bao gồm AST, PDG và CFG.
*   **Thực tế mã nguồn (`util.py`):** File này chứa mã JavaScript gọi tới `@solidity-parser/parser` thông qua thư viện `execjs` để phân tích AST của hợp đồng thông minh **Solidity**, không áp dụng cho C/C++. Mã nguồn để tự động chạy Joern và trích xuất CPG cho C/C++ bị **thiếu hoàn toàn**. Việc chạy mô hình hiện tại (ở file `llmpre.py`) đang phụ thuộc vào một file JSON đã được xử lý sẵn ở máy tác giả (`devign_test_processed.json`).

### B. Module Lựa chọn Ví dụ Mẫu (Demonstration Selection - `genexample.py`)
*   **Lý thuyết:** Sử dụng **CodeT5** để trích xuất đặc trưng ngữ nghĩa, dùng **T-SNE** giảm chiều dữ liệu và dùng **khoảng cách $L_2$** để đo lường độ tương đồng. Sau đó kết hợp độ tương đồng từ vựng (Jaccard) và cú pháp (SimSBT) để tính điểm hỗn hợp.
*   **Thực tế mã nguồn:** File `genexample.py` có vẻ như được copy/sửa đổi từ một bài toán khác (Code Summarization) vì chứa các biến như `nl_list` (Natural Language) và import `nlgeval`. Mã nguồn sử dụng FAISS (chỉ mục Inner Product) thay vì T-SNE và khoảng cách $L_2$. Hơn nữa, nó gọi tới một file `bert_whitening.py` không tồn tại trong thư mục, và các file model `.pkl` cũng đang bị thiếu.

### C. Mã nguồn chạy LLM (`basep.py`, `llmpre.py`)
*   **Đường dẫn cứng (Hardcoded paths):** Các script này đang bị fix cứng theo đường dẫn cá nhân của tác giả (ví dụ: `F:/pycharmfile/vulllm/devign_data/...`). Cần phải chỉnh sửa lại để chạy được trên máy khác.
*   **Lắp ráp Prompt (Prompt Assembly):** Trong bài báo (Hình 6), thông tin Nhận dạng (Identity) và Tên miền (Domain) được đặt *trước* đoạn code. Tuy nhiên trong file `llmpre.py`, chúng lại được nối vào *sau* đoạn code.

---

## 2. Kế hoạch Tái tạo Kết quả Thực nghiệm

Để tái tạo lại các thí nghiệm này một cách chính xác, chúng ta cần xây dựng lại các thành phần còn thiếu và cấu trúc lại mã nguồn theo 4 giai đoạn sau:

### Giai đoạn 1: Chuẩn bị dữ liệu và Xây dựng lại Pipeline tiền xử lý (với Joern)
Mục tiêu: Tự tạo lại được file `devign_test_processed.json` cho các tập dữ liệu C/C++.
1. Tải các tập dữ liệu Devign, Reveal, Big-Vul theo link trong `readme.md`.
2. Tải và cài đặt phiên bản Joern được cung cấp trong file readme.
3. Viết một script tự động (Python gọi CLI của Joern hoặc Scala script) quét qua các hàm C/C++ trong tập dữ liệu, trích xuất AST, node và edge, sau đó xuất ra định dạng JSON.

### Giai đoạn 2: Lập trình lại Module Lựa chọn Ví dụ (Demonstration Retrieval)
Mục tiêu: Viết lại `retrieve_demos.py` bám sát lý thuyết bài báo, thay thế `genexample.py` đang bị lỗi:
1. Sử dụng mô hình `CodeT5` để lấy vector đặc trưng của các đoạn code trong tập huấn luyện.
2. Sử dụng FAISS (với index $L_2$ thay vì Inner Product) để lọc ra top K ví dụ tương đồng nhất về mặt ngữ nghĩa.
3. Lập trình logic tính toán độ tương đồng Jaccard (từ vựng) và SimSBT/Levenshtein (cú pháp) để xếp hạng lại top K ví dụ này, sau đó cập nhật chúng vào file JSON cấu trúc.

### Giai đoạn 3: Chỉnh sửa Script Đánh giá LLM
Mục tiêu: Làm cho `llmpre.py` và `basep.py` hoạt động ổn định trên mọi môi trường:
1. Loại bỏ các đường dẫn cứng `F:/`, thay bằng đường dẫn tương đối hoặc tham số dòng lệnh.
2. Thêm tính năng nạp `API Key` của OpenAI từ biến môi trường (ví dụ file `.env`) thay vì fix cứng trong code.
3. Sắp xếp lại thứ tự cấu trúc prompt để khớp hoàn toàn với Hình 6 trong bài báo.
4. Bổ sung cơ chế xử lý lỗi tự động thử lại (Retry) và lưu tiến độ (Checkpoint) vì việc gọi API GPT-4 cho hàng nghìn dòng code sẽ tốn thời gian và dễ gặp lỗi giới hạn API.

### Giai đoạn 4: Chạy thử và Đối chiếu
Mục tiêu: Xác minh tính đúng đắn của việc tái tạo.
1. Sử dụng dữ liệu sau tiền xử lý để chạy mô hình trên một tập nhỏ (khoảng 10-50 hàm) để kiểm tra luồng hoạt động.
2. So sánh kết quả của các chỉ số Accuracy, Precision, Recall và F1 trên tập kiểm tra với kết quả được báo cáo trong bài báo (Ví dụ: Devign đạt khoảng ~65.11% F1).

---

> **LƯU Ý QUAN TRỌNG TRƯỚC KHI BẮT ĐẦU:**
> Để có thể thực thi bản kế hoạch này, bạn cần chuẩn bị:
> 1. Đảm bảo đã tải xuống các **tập dữ liệu** (Devign, Reveal...) theo liên kết trong readme.
> 2. Đảm bảo đã cài đặt công cụ **Joern** thành công.
> 3. Cung cấp một **OpenAI API Key** hợp lệ để có thể chạy được mô hình LLM (GPT-4) khi đến Giai đoạn 3 và 4.
