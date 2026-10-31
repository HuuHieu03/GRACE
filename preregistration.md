# Đăng Ký Trước Giao Thức Nghiên Cứu (Preregistration Protocol v1)

- **Study ID:** `grace_diag_replication_v1`
- **Version:** `prereg-v1`
- **Registration Date:** 2026-10-31
- **Repository Version / Git Tag:** `prereg-v1`
- **Protocol Configuration File:** `grace_diag_kit/configs/protocol.yaml`

---

## 1. Công Bố Minh Bạch Về Tiếp Xúc Dữ Liệu Test (Test Exposure Disclosure)

Tập dữ liệu kiểm thử (test set) của Devign và ReVeal đã từng được tiếp xúc trong giai đoạn thăm dò sơ bộ ban đầu (gồm 36 lượt chạy API thử nghiệm, tập dev-100, và các phép đo động cơ H1–H3). 

Nhằm đảm bảo tính hợp thức và giá trị xác nhận khoa học:
1. Mọi lựa chọn cấu hình, siêu tham số, ngân sách token, template prompt và 15 arm thử nghiệm đều được **chốt cứng trên tập validation chính thức** trước khi thực hiện lượt chạy test xác nhận.
2. Ngưỡng phân lớp tối ưu $\tau^*$ của mọi arm được tìm kiếm và cố định hoàn toàn trên tập validation (`thresholds.json`), không bao giờ điều chỉnh dựa trên kết quả test.
3. Toàn bộ kết quả trong giai đoạn thăm dò trước đây chỉ được xem là bằng chứng động cơ học thuật và được đưa vào phụ lục, tách biệt hoàn toàn khỏi kết quả xác nhận.

---

## 2. Bảng 11 Giả Thuyết Nghiên Cứu (Table 4.3)

| Mã | Tên Giả Thuyết | Nội Dung Chi Tiết & Chuẩn Chấp Nhận / Bác Bỏ |
| :--- | :--- | :--- |
| **H1.1** | GRACE không vượt Zero-shot | Arm B2 (GRACE đầy đủ) không vượt B0 (zero-shot) vượt quá ngưỡng biên: khoảng tin cậy 95% $\Delta\text{MCC}(\text{B2} - \text{B0}) < 0.03$ và $\Delta\text{AUROC} < 0.02$. |
| **H1.2** | GRACE không đạt mức công bố | GRACE không tái lập được hiệu năng công bố trong bài gốc: $\text{MCC} < 0.15$ và $F_1(\text{B2}) < F_1(\text{always-vulnerable})$. |
| **H2.1** | Demo tác động qua nhãn | Sự hiện diện của demonstration tác động chủ yếu thông qua nhãn bề mặt: Độ nhạy nhãn thuần (Net label sensitivity) $\ge 15$ điểm phần trăm giữa B2 và B2-flip. |
| **H2.2** | Nội dung demo không mang tín hiệu | Nội dung mã nguồn của demo không bổ sung tín hiệu bản chất: $\Delta\text{AUROC}(\text{B2} - \text{B2-rand}) < 0.02$; $\text{B2-nolabel} - \text{B1} < 0.02$; và B2-labelonly tái tạo $\ge 80\%$ mức chênh lệch giữa B2 và B1. |
| **H2.3** | Cặp tương phản chỉ dịch chuyển điểm | Kỹ thuật cặp tương phản (B3) chỉ dịch chuyển điểm hoạt động (tăng tỷ lệ đoán 1) chứ không tăng khả năng phân tách: Tỷ lệ đoán 1 của B3 cao hơn B2 $\ge 10$ điểm phần trăm trong khi $\text{CI}_{95\%} \Delta\text{AUROC} < 0.02$. |
| **H3.1** | LLM không đọc Code Property Graph | Thông tin đồ thị CPG dạng văn bản không mang lại tín hiệu bổ sung cho LLM: $\Delta\text{AUROC}(\text{B1} - \text{B0}) < 0.02$, $\Delta\text{AUROC}(\text{B1} - \text{B1-shuf}) < 0.02$, và B1-H2 không khác biệt đáng kể so với B1. |
| **H4.1** | Đo không ngưỡng gần ngẫu nhiên | Khi đánh giá không phụ thuộc ngưỡng (AUROC), toàn bộ pipeline LLM chỉ đạt hiệu năng gần mức ngẫu nhiên: $\text{AUROC} \le 0.62$ trên cả Devign và ReVeal. |
| **H5.1** | Mốc có giám sát thắng rõ | Bộ phân lớp có giám sát truyền thống đơn giản vượt trội rõ rệt pipeline LLM: $\Delta\text{MCC}(\text{SUP-LR} - \text{B2}) \ge 0.15$ và $\text{AUROC}(\text{SUP-LR}) \ge 0.68$. |
| **H5.2** | LLM không bổ sung tín hiệu | Điểm số của LLM không bổ sung thêm tín hiệu trực giao sau khi đã có 34 đặc trưng cơ sở: $\text{CI}_{95\%} \Delta\text{MCC}(P_\text{post} - P_\text{pre}) < 0.02$. |
| **H5.3** | Không biết trước khi nào gọi LLM | Bộ định tuyến chất lượng (routing) dựa trên độ tự tin/lợi ích không vượt trội chiến lược gọi ngẫu nhiên: $\Delta\text{BA}(\text{benefit} - \text{random}) < 0.01$ tại ngân sách 10%; số ca sửa đúng không vượt bách phân vị 95% của random. |
| **H6.1** | Cơ chế truy hồi lệch hướng | Demonstration được truy hồi hiếm khi đúng cơ chế lỗi tương ứng: Tỷ lệ "Neither" $\ge 40\%$; khoảng tin cậy của chênh lệch độ chính xác chứa 0 trong kiểm toán mù. |

---

## 3. Quy Tắc Phân Tích & Phương Pháp Luận Thống Kê (Mục 6)

1. **Khử trùng & Khóa Kho Dữ Liệu:**
   - Dữ liệu donor train được loại bỏ toàn bộ các mẫu trùng lặp chính xác với validation và test.
   - Các nhóm mẫu có mâu thuẫn nhãn trong train bị loại bỏ khỏi donor bank.
   - Các cặp gần trùng (Jaccard token 3-gram $\ge 0.9$) được gắn cờ để báo cáo cả trên tập đầy đủ và tập đã làm sạch.
2. **Khóa Ngưỡng Quyết Định ($\tau^*$):**
   - Không dùng ngưỡng mặc định cố định nếu không có căn cứ.
   - Tìm kiếm ngưỡng tối ưu $\tau^*$ trên lưới 99 điểm $[0.01, 0.99]$ dựa trên cực đại hóa chỉ số MCC trên tập validation:
     $$\tau^* = \operatorname{argmax}_{\tau} \left(\operatorname{MCC}(y_\text{val}, \hat{y}_\tau), -|\tau - 0.5|\right)$$
   - Khóa $\tau^*$ vào `thresholds.json` trước khi chạy bất kỳ suy luận nào trên test set.
3. **Thống Kê Khẳng Định & So Sánh Cặp (Bảng B):**
   - Bootstrap ghép cặp phân tầng theo cụm (`commit_id` nếu có, hoặc mẫu độc lập) với $B = 5000$ lần lặp (seed cố định `20261117`).
   - Hiệu chỉnh đa giả thuyết trong cùng họ đối chứng theo thủ tục Holm-Bonferroni.
   - Biên khác biệt tối thiểu đáng quan tâm được ấn định trước: $\delta_\text{MCC} = 0.03$, $\delta_\text{AUROC} = 0.02$, $\delta_\text{BA} = 0.01$.
   - Quy tắc phán quyết:
     - `benefit`: $\text{CI}_{95\%} > 0$ và $\Delta \ge \delta$.
     - `no_meaningful_benefit`: Cận trên $\text{CI}_{95\%} < \delta$.
     - `harm`: $\text{CI}_{95\%} < 0$.
     - `inconclusive`: Trường hợp còn lại.
4. **Phân Tích Bổ Sung (Complementarity & Routing):**
   - 34 đặc trưng cơ sở $P_\text{pre}$ bao gồm 5 logit từ các mô hình nền tảng, xác suất tổng hợp $p$, $|p - 0.5|$, độ lệch MLP-Lexical, và 26 code metrics.
   - 4 đặc trưng từ LLM gồm: điểm $s$, cờ $valid$, tương tác $s \cdot p$, và độ lệch $s - p$.
   - Mô hình meta sử dụng Logistic Regression ($C = 1.0$), 3-fold Out-Of-Fold (OOF).
   - Kiểm tra định tuyến tại các mức ngân sách 5%, 10%, 25% với 20 seed ngẫu nhiên cho baseline RANDOM và trần Oracle.

---

## 4. Quy Tắc Dừng (Stopping Rules)

1. **Lợi thế SUP-LR biến mất:** Nếu sau khi khử trùng và kiểm toán nhãn, mô hình SUP-LR không còn vượt trội B2, dừng nghiên cứu để rà soát toàn bộ quy trình tiền xử lý dữ liệu trước khi viết báo cáo.
2. **Thất bại Kiểm toán Prompt Audit:** Nếu tỷ lệ demonstration rỗng $> 1\%$, tỷ lệ thiếu đồ thị $> 5\%$, hoặc phát hiện rò rỉ nhãn target $> 0$, dừng quy trình, sửa hợp đồng dựng prompt, và chạy lại toàn bộ arm bị ảnh hưởng.
3. **Thất bại Smoke Test Backend:** Nếu tỷ lệ phản hồi hợp lệ có token 0/1 trong top-5 logprob $< 99\%$, không tiến hành chạy ma trận xác nhận cho đến khi backend mô hình đạt độ ổn định định lượng.
4. **Đóng băng Giao thức Nghiêm ngặt:** Tuyệt đối không mở thêm arm, không thêm mô hình, không điều chỉnh ngưỡng sau khi đã quan sát dữ liệu test. Bất kỳ phân tích bổ sung nào phát sinh sau thời điểm này đều phải phân loại là "thăm dò sau đăng ký" (exploratory post-hoc) và ghi rõ trong bài báo.

---

## 5. Bảng Băm Manifest & Thông Tin Checkpoint

### 5.1. Bảng Mã Băm SHA-256 Của Manifest & Dữ Liệu

| Tập Dữ Liệu | Phân Vùng / Mục | Số Dòng (Samples) | Tỷ Lệ Positive (Vuln) | Mã Băm SHA-256 |
| :--- | :--- | :--- | :--- | :--- |
| **Devign** | Raw Train | 21,854 | 45.84% | `28f2cfb804daeb2ee4d4f8f480370425c2859194bbba737243c96291a134d1b8` |
| **Devign** | Raw Validation | 2,732 | 43.45% | `19ffbca7540bf96495df9c74d32047efbca0feee8aa410d47d519cb7d4981180` |
| **Devign** | Raw Test | 2,732 | 45.94% | `a39031d27ae85c96b8a2e57fae155c5679c118aa95a0225114704b2b24bb0908` |
| **Devign** | Clean Donors Bank | 21,711 | 45.91% | `66432650ee451551a37c9a9ca38bb06cb8c3f58a98a0050275817a02237a3465` |
| **Devign** | **Manifest Stats** | - | - | **`8e9722a165d65e8d73309de1cb1013d3ff218468fd597b79051b8c1d7c070246`** |
| **Devign** | Val Subset 600 (Seed 42) | 600 | 43.50% | `25bc4ce799f2a08f51dfb3e4ae6cfec42ff843a0ae5ee04d22da6df578da69c1` |
| **ReVeal** | Raw Train | 18,187 | 9.90% | `a37ea81896d8f8d29bce055b8aa62e6d6eb1f3647f54c9fa6a8e52dbb06fe6cb` |
| **ReVeal** | Raw Validation | 2,273 | 9.24% | `9846b0d1e38c9284227ba1be9cb6ba312bca01e23ce0eb7e35b7194f4ce0461f` |
| **ReVeal** | Raw Test | 2,274 | 10.11% | `b4904bf37d2f939433ffae1a19694ff8a3eb2dff1a7e4369e4f0d3fc35ea2983` |
| **ReVeal** | Clean Donors Bank | 17,620 | 9.57% | `003b5f6b2169738ef9ff5b1747833a67746535f29c48858f7082f5b4974fbf35` |
| **ReVeal** | **Manifest Stats** | - | - | **`5bf4cba74c426e142832c0dc814aee7e127dce72c207d1fdf14eb1508b9e87ab`** |
| **ReVeal** | Val Subset 600 (Seed 42) | 600 | 9.17% | `22956fef38f1618e77840ecf43407bb075c32c0734a74c76b92a40ae906a2444` |

### 5.2. Checkpoint Mô Hình & Môi Trường Suy Luận

- **Primary Architecture:** Qwen/Qwen3-Coder-30B-A3B-Instruct (MoE, 30.5B total params, 3.3B active params per token).
- **Target Serving Format:** llama.cpp GGUF Quantization Q4_K_XL (`Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf`, 16.45 GB) trên Kaggle 2×T4 hoặc vLLM (FP8/bf16) trên cloud GPU.
- **Decoding Configuration:** `temperature = 0.0`, `max_tokens = 1`, `logprobs = true`, `top_logprobs = 5`, `seed = 42`.
- **Scoring Function:** $s = \frac{p(1)}{p(0) + p(1)}$ trích xuất từ top-5 logprob của token đầu tiên.
