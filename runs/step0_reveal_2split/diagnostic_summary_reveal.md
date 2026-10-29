# BÁO CÁO CHẨN ĐOÁN OFFLINE BƯỚC 0 — ĐỀ TÀI GRACE
**Bộ dữ liệu**: `REVEAL` | **Quy chuẩn**: 🟢 **Chuẩn 2-Split Độc lập (Methodology Standard)** — Fit meta-model & chọn ngưỡng trên Validation; Đánh giá trên Test độc lập. | **Tài nguyên**: Offline (0 GPU)

---

## 1. Tóm tắt Kết luận Chẩn đoán (Executive Summary)

- **Đánh giá Thống kê ($\delta$-Verdict)**: 🟢 **BENEFIT (CÓ BỔ SUNG THỰC SỰ ≥ δ)**
- **Giải thích chi tiết**: Có bằng chứng lợi ích ≥ δ trong giao thức đã kiểm
- **Tổng số mẫu kiểm thử**: **100** (Lỗ hổng: 39 [39.0%], An toàn: 61)
- **Phân bổ mẫu**: Validation Split = **100** mẫu | Test Split = **100** mẫu
- **Tính hợp lệ phản hồi LLM**: 96 hợp lệ (96.0%), 4 lỗi format (được fallback đối xứng về Gate)
- **Chênh lệch $\Delta$MCC ghép cặp**: **0.2310** (95% CI: [0.0845, 0.3875])
- **Chênh lệch $\Delta$F1 ghép cặp**: **0.1768** (95% CI: [0.0679, 0.2912])
- **Chênh lệch $\Delta$AUROC**: **0.0761** (95% CI: [0.0379, 0.1335])

---

## 2. Ma trận Sửa - Hỏng theo Nhãn Thực tế (Repair / Harm Matrix)

> **Ý nghĩa**: Định lượng trực tiếp số lượng ca LLM Expert cứu chữa được lỗi của CodeT5 Gate ($R_y$) đối chiếu với số lượng ca LLM làm hỏng quyết định đúng ban đầu của Gate ($H_y$).

| Phân nhóm Nhãn | Tổng số mẫu ($N$) | Ca Sửa ($R_y$) | Ca Hỏng ($H_y$) | Cả hai cùng Đúng | Cả hai cùng Sai | Hiệu quả Sửa Ròng ($R - H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Safe ($y=0$)** | 61 | 4 | 7 | 50 | 0 | **-3** |
| **Vulnerable ($y=1$)** | 35 | 5 | 5 | 25 | 0 | **0** |
| **Toàn bộ (Total)** | **96** | **9** | **12** | **75** | **0** | **-3** |

- **Tỷ lệ sửa lỗi của Gate**: Đạt **90.00%** (9 / 9 ca Gate đoán sai).
- **Tỷ lệ làm hỏng quyết định đúng**: Ở mức **13.33%** (12 / 87 ca Gate đoán đúng).

---

## 3. Đối chứng với 3 Chuyên gia Tham chiếu (Reference Experts)

> **Nguyên lý kiểm định của Thầy**: Một chuyên gia đoán ngẫu nhiên (lật đồng xu) cũng có thể 'sửa' được một lượng lớn lỗi của Gate do may rủi. LLM chỉ được coi là có tri thức khi số ca sửa ròng vượt trội rõ rệt mốc Random.

| Chuyên gia / Mô hình | Số ca Sửa ($R$) | Số ca Hỏng ($H$) | Sửa Ròng ($R - H$) | Trần Oracle Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **LLM Expert (Đề xuất)** | **9** | **12** | **-3** | **0.9900** |
| Random Expert (rate=0.39) | 4.6 [3.0, 7.0] | 42.4 [32.5, 56.7] | -37.8 | 0.9460 |
| Constant-0 (Luôn đoán An toàn) | 4 | 33 | -29 | 0.9400 |
| Constant-1 (Luôn đoán Lỗ hổng) | 6 | 57 | -51 | 0.9600 |

---

## 4. Trần Lý thuyết Chẩn đoán (Oracle Ceiling Analysis)

> **Định nghĩa**: Bộ chọn Oracle lý tưởng nếu biết trước nhãn thật để chọn bên đúng giữa Gate và LLM. Đây là giới hạn trên tuyệt đối không thể vượt qua của bất kỳ bộ kết hợp nào.

| Cấu hình Đánh giá | Accuracy | F1-Score | MCC | Balanced Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **CodeT5 Gate Standalone** (tau=0.5) | 0.9000 | 0.8684 | 0.7886 | 0.8903 |
| **LLM Standalone** (Fallback) | 0.8700 | 0.8354 | 0.7282 | 0.8657 |
| **Trần Lý thuyết Oracle** | **0.9900** | **0.9870** | **0.9791** | **0.9872** |
| *Dư địa tối đa tiềm năng (Oracle - Gate)* | *+0.0900* | *+0.1186* | *+0.1905* | *+0.0969* |

---

## 5. Mô hình Đối chứng Ghép cặp (Matched Meta-Model: $P_{pre}$ vs $P_{post}$)

> **Thiết kế kiểm định**: Cùng số fold (5), cùng scaler, chỉ khác duy nhất 4 đặc trưng bổ sung từ LLM ($s, \text{valid}, s \times p, s - p$).
> **Quy chuẩn 2-Split**: Ngưỡng tối ưu $\tau_{pre}^* = 0.46$, $\tau_{post}^* = 0.50$ được xác định hoàn toàn từ tập Validation và khóa chặt khi đánh giá tập Test.

| Chỉ số Đánh giá | $P_{pre}$ (Gate + Đặc trưng nền) | $P_{post}$ (Thêm đặc trưng LLM) | Chênh lệch $\Delta$ | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: |
| **MCC** | 0.6429 | 0.8739 | **0.2310** | [0.0845, 0.3875] |
| **F1-Score** | 0.7463 | 0.9231 | **0.1768** | [0.0679, 0.2912] |
| **Accuracy** | 0.8300 | 0.9400 | **0.1100** | [0.0400, 0.1800] |
| **Balanced Accuracy** | 0.7959 | 0.9369 | 0.1410 | — |
| **AUROC** | 0.9012 | 0.9773 | **0.0761** | [0.0379, 0.1335] |
| *Ngưỡng tối ưu $\tau^*$* | *0.46* | *0.50* | — | — |

---

## 6. Kiểm định McNemar & Hiệu chỉnh Holm (Family-wise Significance)

| Cặp Mô hình So sánh | Số ca $A$ đúng / $B$ sai ($b$) | Số ca $A$ sai / $B$ đúng ($c$) | $p$-value (Raw) | $p$-value (Holm) | Ý nghĩa ($\alpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `P_pre_vs_P_post` | 3 | 14 | 0.0127 | 0.0509 | ❌ Chưa có ý nghĩa |
| `Gate_vs_P_post` | 5 | 9 | 0.4240 | 0.8479 | ❌ Chưa có ý nghĩa |
| `Gate_vs_LLM_fallback` | 12 | 9 | 0.6636 | 0.8479 | ❌ Chưa có ý nghĩa |
| `Gate_vs_P_pre` | 11 | 4 | 0.1185 | 0.3554 | ❌ Chưa có ý nghĩa |

---

## 7. Phân tích Định tuyến theo Ngân sách Gọi LLM (Selective Routing Curves — RQ5b)

> **Ý nghĩa**: Đánh giá hiệu năng đạt được khi chỉ gửi một tỷ lệ nhỏ ($q$) các hàm cần kiểm thử sang LLM qua 4 chính sách: `confidence` (gần biên), `benefit` (học máy Ridge), `oracle` (trần lý tưởng), và `random` (đối chứng ngẫu nhiên).

| Chính sách (Policy) | Tỷ lệ gọi ($q$) | Số truy vấn | MCC | F1-Score | Balanced Accuracy | Số ca Sửa ($R$) | Số ca Hỏng ($H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `gate_only` | 0% | 0 | 0.7886 | 0.8684 | 0.8903 | — | — |
| `full_expert_with_fallback` | 100% | 100 | 0.7282 | 0.8354 | 0.8657 | — | — |
| `confidence` | 5% | 5 | 0.8101 | 0.8831 | 0.9031 | 1 | 0 |
| `benefit` | 5% | 5 | 0.7679 | 0.8571 | 0.8821 | 0 | 1 |
| `oracle` | 5% | 5 | 0.8953 | 0.9333 | 0.9405 | 5 | 0 |
| `random` | 5% | 5 | 0.7867 | 0.8674 | 0.8897 | — | — |
| `confidence` | 10% | 10 | 0.8524 | 0.9091 | 0.9241 | 3 | 0 |
| `benefit` | 10% | 10 | 0.7461 | 0.8421 | 0.8693 | 0 | 2 |
| `oracle` | 10% | 10 | 0.9791 | 0.9870 | 0.9872 | 9 | 0 |
| `random` | 10% | 10 | 0.7848 | 0.8663 | 0.8889 | — | — |
| `confidence` | 25% | 25 | 0.9369 | 0.9610 | 0.9662 | 8 | 1 |
| `benefit` | 25% | 25 | 0.6863 | 0.8101 | 0.8447 | 0 | 5 |
| `oracle` | 25% | 25 | 0.9791 | 0.9870 | 0.9872 | 9 | 0 |
| `random` | 25% | 25 | 0.7740 | 0.8594 | 0.8837 | — | — |
| `confidence` | 50% | 50 | 0.9159 | 0.9487 | 0.9580 | 9 | 3 |
| `benefit` | 50% | 50 | 0.6489 | 0.7901 | 0.8283 | 1 | 8 |
| `oracle` | 50% | 50 | 0.9791 | 0.9870 | 0.9872 | 9 | 0 |
| `random` | 50% | 50 | 0.7493 | 0.8449 | 0.8724 | — | — |

---

## 8. Khuyến nghị Kỹ thuật cho Bước Tiếp theo

1. **Bàn giao Dữ liệu**: Khi có kết quả chính thức từ CodeT5 và LLM, hãy chạy pipeline 2-Split với `--gate-val`, `--gate-test`, `--llm-val`, `--llm-test` để khóa ngưỡng tối ưu trên Validation và đánh giá trung thực trên Test.
2. **Khóa Ngưỡng**: Giữ nguyên $\tau = 0.5$ (hoặc $\tau_{\text{val}}$ cố định) cho toàn bộ so sánh, không thực hiện fine-tune lại trên tập Test nhằm tuân thủ quy chuẩn nghiên cứu.
3. **Tích hợp Monorepo**: Sẵn sàng đón nhận bộ trích xuất CPG và đặc trưng 34 chiều vào thư mục `src/gate/` sau khi hoàn tất Bước 0.

> *Báo cáo này được tự động kết xuất từ module `grace_diag` theo chuẩn đề tài nghiên cứu khoa học.*