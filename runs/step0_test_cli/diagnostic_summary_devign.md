# BÁO CÁO CHẨN ĐOÁN OFFLINE BƯỚC 0 — ĐỀ TÀI GRACE
**Bộ dữ liệu**: `DEVIGN` | **Quy chuẩn**: 🟢 **Chuẩn 2-Split Độc lập (Methodology Standard)** — Fit meta-model & chọn ngưỡng trên Validation; Đánh giá trên Test độc lập. | **Tài nguyên**: Offline (0 GPU)

---

## 1. Tóm tắt Kết luận Chẩn đoán (Executive Summary)

- **Đánh giá Thống kê ($\delta$-Verdict)**: 🟢 **BENEFIT (CÓ BỔ SUNG THỰC SỰ ≥ δ)**
- **Giải thích chi tiết**: Có bằng chứng lợi ích ≥ δ trong giao thức đã kiểm
- **Tổng số mẫu kiểm thử**: **100** (Lỗ hổng: 45 [45.0%], An toàn: 55)
- **Phân bổ mẫu**: Validation Split = **100** mẫu | Test Split = **100** mẫu
- **Tính hợp lệ phản hồi LLM**: 96 hợp lệ (96.0%), 4 lỗi format (được fallback đối xứng về Gate)
- **Chênh lệch $\Delta$MCC ghép cặp**: **0.2444** (95% CI: [0.0995, 0.4004])
- **Chênh lệch $\Delta$F1 ghép cặp**: **0.1379** (95% CI: [0.0505, 0.2381])
- **Chênh lệch $\Delta$AUROC**: **0.0832** (95% CI: [0.0329, 0.1414])

---

## 2. Ma trận Sửa - Hỏng theo Nhãn Thực tế (Repair / Harm Matrix)

> **Ý nghĩa**: Định lượng trực tiếp số lượng ca LLM Expert cứu chữa được lỗi của CodeT5 Gate ($R_y$) đối chiếu với số lượng ca LLM làm hỏng quyết định đúng ban đầu của Gate ($H_y$).

| Phân nhóm Nhãn | Tổng số mẫu ($N$) | Ca Sửa ($R_y$) | Ca Hỏng ($H_y$) | Cả hai cùng Đúng | Cả hai cùng Sai | Hiệu quả Sửa Ròng ($R - H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Safe ($y=0$)** | 51 | 6 | 5 | 40 | 0 | **1** |
| **Vulnerable ($y=1$)** | 45 | 3 | 2 | 40 | 0 | **1** |
| **Toàn bộ (Total)** | **96** | **9** | **7** | **80** | **0** | **2** |

- **Tỷ lệ sửa lỗi của Gate**: Đạt **100.00%** (9 / 9 ca Gate đoán sai).
- **Tỷ lệ làm hỏng quyết định đúng**: Ở mức **7.69%** (7 / 87 ca Gate đoán đúng).

---

## 3. Đối chứng với 3 Chuyên gia Tham chiếu (Reference Experts)

> **Nguyên lý kiểm định của Thầy**: Một chuyên gia đoán ngẫu nhiên (lật đồng xu) cũng có thể 'sửa' được một lượng lớn lỗi của Gate do may rủi. LLM chỉ được coi là có tri thức khi số ca sửa ròng vượt trội rõ rệt mốc Random.

| Chuyên gia / Mô hình | Số ca Sửa ($R$) | Số ca Hỏng ($H$) | Sửa Ròng ($R - H$) | Trần Oracle Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **LLM Expert (Đề xuất)** | **9** | **7** | **2** | **1.0000** |
| Random Expert (rate=0.50) | 4.5 [2.0, 7.0] | 43.1 [36.0, 53.1] | -38.6 | 0.9555 |
| Constant-0 (Luôn đoán An toàn) | 6 | 42 | -36 | 0.9700 |
| Constant-1 (Luôn đoán Lỗ hổng) | 3 | 49 | -46 | 0.9400 |

---

## 4. Trần Lý thuyết Chẩn đoán (Oracle Ceiling Analysis)

> **Định nghĩa**: Bộ chọn Oracle lý tưởng nếu biết trước nhãn thật để chọn bên đúng giữa Gate và LLM. Đây là giới hạn trên tuyệt đối không thể vượt qua của bất kỳ bộ kết hợp nào.

| Cấu hình Đánh giá | Accuracy | F1-Score | MCC | Balanced Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **CodeT5 Gate Standalone** (tau=0.5) | 0.9100 | 0.9032 | 0.8208 | 0.9121 |
| **LLM Standalone** (Fallback) | 0.9300 | 0.9247 | 0.8610 | 0.9323 |
| **Trần Lý thuyết Oracle** | **1.0000** | **1.0000** | **1.0000** | **1.0000** |
| *Dư địa tối đa tiềm năng (Oracle - Gate)* | *+0.0900* | *+0.0968* | *+0.1792* | *+0.0879* |

---

## 5. Mô hình Đối chứng Ghép cặp (Matched Meta-Model: $P_{pre}$ vs $P_{post}$)

> **Thiết kế kiểm định**: Cùng số fold (5), cùng scaler, chỉ khác duy nhất 4 đặc trưng bổ sung từ LLM ($s, \text{valid}, s \times p, s - p$).
> **Quy chuẩn 2-Split**: Ngưỡng tối ưu $\tau_{pre}^* = 0.69$, $\tau_{post}^* = 0.50$ được xác định hoàn toàn từ tập Validation và khóa chặt khi đánh giá tập Test.

| Chỉ số Đánh giá | $P_{pre}$ (Gate + Đặc trưng nền) | $P_{post}$ (Thêm đặc trưng LLM) | Chênh lệch $\Delta$ | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: |
| **MCC** | 0.6964 | 0.9408 | **0.2444** | [0.0995, 0.4004] |
| **F1-Score** | 0.8276 | 0.9655 | **0.1379** | [0.0505, 0.2381] |
| **Accuracy** | 0.8500 | 0.9700 | **0.1200** | [0.0500, 0.2000] |
| **Balanced Accuracy** | 0.8455 | 0.9667 | 0.1212 | — |
| **AUROC** | 0.9131 | 0.9964 | **0.0832** | [0.0329, 0.1414] |
| *Ngưỡng tối ưu $\tau^*$* | *0.69* | *0.50* | — | — |

---

## 6. Kiểm định McNemar & Hiệu chỉnh Holm (Family-wise Significance)

| Cặp Mô hình So sánh | Số ca $A$ đúng / $B$ sai ($b$) | Số ca $A$ sai / $B$ đúng ($c$) | $p$-value (Raw) | $p$-value (Holm) | Ý nghĩa ($\alpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `P_pre_vs_P_post` | 2 | 14 | 0.0042 | 0.0167 | ✅ Có ý nghĩa |
| `Gate_vs_P_post` | 2 | 8 | 0.1094 | 0.3281 | ❌ Chưa có ý nghĩa |
| `Gate_vs_LLM_fallback` | 7 | 9 | 0.8036 | 0.8036 | ❌ Chưa có ý nghĩa |
| `Gate_vs_P_pre` | 10 | 4 | 0.1796 | 0.3591 | ❌ Chưa có ý nghĩa |

---

## 7. Phân tích Định tuyến theo Ngân sách Gọi LLM (Selective Routing Curves — RQ5b)

> **Ý nghĩa**: Đánh giá hiệu năng đạt được khi chỉ gửi một tỷ lệ nhỏ ($q$) các hàm cần kiểm thử sang LLM qua 4 chính sách: `confidence` (gần biên), `benefit` (học máy Ridge), `oracle` (trần lý tưởng), và `random` (đối chứng ngẫu nhiên).

| Chính sách (Policy) | Tỷ lệ gọi ($q$) | Số truy vấn | MCC | F1-Score | Balanced Accuracy | Số ca Sửa ($R$) | Số ca Hỏng ($H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `gate_only` | 0% | 0 | 0.8208 | 0.9032 | 0.9121 | — | — |
| `full_expert_with_fallback` | 100% | 100 | 0.8610 | 0.9247 | 0.9323 | — | — |
| `confidence` | 5% | 5 | 0.8826 | 0.9362 | 0.9434 | 3 | 0 |
| `benefit` | 5% | 5 | 0.8208 | 0.9032 | 0.9121 | 0 | 0 |
| `oracle` | 5% | 5 | 0.9203 | 0.9565 | 0.9616 | 5 | 0 |
| `random` | 5% | 5 | 0.8204 | 0.9031 | 0.9120 | — | — |
| `confidence` | 10% | 10 | 0.9192 | 0.9556 | 0.9596 | 6 | 1 |
| `benefit` | 10% | 10 | 0.8397 | 0.9130 | 0.9212 | 1 | 0 |
| `oracle` | 10% | 10 | 1.0000 | 1.0000 | 1.0000 | 9 | 0 |
| `random` | 10% | 10 | 0.8260 | 0.9060 | 0.9147 | — | — |
| `confidence` | 25% | 25 | 0.8990 | 0.9438 | 0.9485 | 7 | 3 |
| `benefit` | 25% | 25 | 0.8187 | 0.9011 | 0.9101 | 2 | 2 |
| `oracle` | 25% | 25 | 1.0000 | 1.0000 | 1.0000 | 9 | 0 |
| `random` | 25% | 25 | 0.8336 | 0.9097 | 0.9180 | — | — |
| `confidence` | 50% | 50 | 0.9192 | 0.9556 | 0.9596 | 9 | 4 |
| `benefit` | 50% | 50 | 0.8187 | 0.9011 | 0.9101 | 4 | 4 |
| `oracle` | 50% | 50 | 1.0000 | 1.0000 | 1.0000 | 9 | 0 |
| `random` | 50% | 50 | 0.8412 | 0.9137 | 0.9217 | — | — |

---

## 8. Khuyến nghị Kỹ thuật cho Bước Tiếp theo

1. **Bàn giao Dữ liệu**: Khi có kết quả chính thức từ CodeT5 và LLM, hãy chạy pipeline 2-Split với `--gate-val`, `--gate-test`, `--llm-val`, `--llm-test` để khóa ngưỡng tối ưu trên Validation và đánh giá trung thực trên Test.
2. **Khóa Ngưỡng**: Giữ nguyên $\tau = 0.5$ (hoặc $\tau_{\text{val}}$ cố định) cho toàn bộ so sánh, không thực hiện fine-tune lại trên tập Test nhằm tuân thủ quy chuẩn nghiên cứu.
3. **Tích hợp Monorepo**: Sẵn sàng đón nhận bộ trích xuất CPG và đặc trưng 34 chiều vào thư mục `src/gate/` sau khi hoàn tất Bước 0.

> *Báo cáo này được tự động kết xuất từ module `grace_diag` theo chuẩn đề tài nghiên cứu khoa học.*