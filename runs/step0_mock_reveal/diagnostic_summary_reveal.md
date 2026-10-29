# BÁO CÁO CHẨN ĐOÁN OFFLINE BƯỚC 0 — ĐỀ TÀI GRACE
**Bộ dữ liệu**: `REVEAL` | **Thời gian**: Thực thi tự động | **Tài nguyên**: Offline (0 GPU)

---

## 1. Tóm tắt Kết luận Chẩn đoán (Executive Summary)

- **Đánh giá Thống kê ($\delta$-Verdict)**: 🟢 **BENEFIT (CÓ BỔ SUNG THỰC SỰ ≥ δ)**
- **Giải thích chi tiết**: Có bằng chứng lợi ích ≥ δ trong giao thức đã kiểm
- **Tổng số mẫu kiểm thử**: **80** (Lỗ hổng: 34 [42.5%], An toàn: 46)
- **Tính hợp lệ phản hồi LLM**: 79 hợp lệ (98.8%), 1 lỗi format (được fallback đối xứng về Gate)
- **Chênh lệch $\Delta$MCC ghép cặp (OOF)**: **0.1822** (95% CI: [0.0748, 0.2994])
- **Chênh lệch $\Delta$F1 ghép cặp**: **0.1053** (95% CI: [0.0435, 0.1921])
- **Chênh lệch $\Delta$AUROC**: **0.0460** (95% CI: [0.0097, 0.0932])

---

## 2. Ma trận Sửa - Hỏng theo Nhãn Thực tế (Repair / Harm Matrix)

> **Ý nghĩa**: Định lượng trực tiếp số lượng ca LLM Expert cứu chữa được lỗi của CodeT5 Gate ($R_y$) đối chiếu với số lượng ca LLM làm hỏng quyết định đúng ban đầu của Gate ($H_y$).

| Phân nhóm Nhãn | Tổng số mẫu ($N$) | Ca Sửa ($R_y$) | Ca Hỏng ($H_y$) | Cả hai cùng Đúng | Cả hai cùng Sai | Hiệu quả Sửa Ròng ($R - H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Safe ($y=0$)** | 46 | 5 | 2 | 39 | 0 | **3** |
| **Vulnerable ($y=1$)** | 33 | 3 | 1 | 29 | 0 | **2** |
| **Toàn bộ (Total)** | **79** | **8** | **3** | **68** | **0** | **5** |

- **Tỷ lệ sửa lỗi của Gate**: Đạt **100.00%** (8 / 8 ca Gate đoán sai).
- **Tỷ lệ làm hỏng quyết định đúng**: Ở mức **4.17%** (3 / 71 ca Gate đoán đúng).

---

## 3. Đối chứng với 3 Chuyên gia Tham chiếu (Reference Experts)

> **Nguyên lý kiểm định của Thầy**: Một chuyên gia đoán ngẫu nhiên (lật đồng xu) cũng có thể 'sửa' được một lượng lớn lỗi của Gate do may rủi. LLM chỉ được coi là có tri thức khi số ca sửa ròng vượt trội rõ rệt mốc Random.

| Chuyên gia / Mô hình | Số ca Sửa ($R$) | Số ca Hỏng ($H$) | Sửa Ròng ($R - H$) | Trần Oracle Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **LLM Expert (Đề xuất)** | **8** | **3** | **5** | **1.0000** |
| Random Expert (rate=0.43) | 4.7 [3.0, 7.5] | 32.5 [12.6, 40.0] | -27.8 | 0.9587 |
| Constant-0 (Luôn đoán An toàn) | 5 | 31 | -26 | 0.9625 |
| Constant-1 (Luôn đoán Lỗ hổng) | 3 | 41 | -38 | 0.9375 |

---

## 4. Trần Lý thuyết Chẩn đoán (Oracle Ceiling Analysis)

> **Định nghĩa**: Bộ chọn Oracle lý tưởng nếu biết trước nhãn thật để chọn bên đúng giữa Gate và LLM. Đây là giới hạn trên tuyệt đối không thể vượt qua của bất kỳ bộ kết hợp nào.

| Cấu hình Đánh giá | Accuracy | F1-Score | MCC | Balanced Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **CodeT5 Gate Standalone** (tau=0.5) | 0.9000 | 0.8857 | 0.7980 | 0.9015 |
| **LLM Standalone** (Fallback) | 0.9625 | 0.9565 | 0.9239 | 0.9636 |
| **Trần Lý thuyết Oracle** | **1.0000** | **1.0000** | **1.0000** | **1.0000** |
| *Dư địa tối đa tiềm năng (Oracle - Gate)* | *+0.1000* | *+0.1143* | *+0.2020* | *+0.0985* |

---

## 5. Mô hình Đối chứng Ghép cặp (Matched Meta-Model: $P_{pre}$ vs $P_{post}$)

> **Thiết kế kiểm định**: Cùng số fold (5), cùng scaler, cùng OOF, chỉ khác duy nhất 4 đặc trưng bổ sung từ LLM ($s, \text{valid}, s \times p, s - p$).

| Chỉ số Đánh giá | $P_{pre}$ (Gate + Đặc trưng nền) | $P_{post}$ (Thêm đặc trưng LLM) | Chênh lệch $\Delta$ | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: |
| **MCC** | 0.8178 | 1.0000 | **0.1822** | [0.0748, 0.2994] |
| **F1-Score** | 0.8947 | 1.0000 | **0.1053** | [0.0435, 0.1921] |
| **Accuracy** | 0.9000 | 1.0000 | **0.1000** | [0.0375, 0.1750] |
| **Balanced Accuracy** | 0.9130 | 1.0000 | 0.0870 | — |
| **AUROC** | 0.9540 | 1.0000 | **0.0460** | [0.0097, 0.0932] |
| *Ngưỡng tối ưu $\tau^*$* | *0.25* | *0.40* | — | — |

---

## 6. Kiểm định McNemar & Hiệu chỉnh Holm (Family-wise Significance)

| Cặp Mô hình So sánh | Số ca $A$ đúng / $B$ sai ($b$) | Số ca $A$ sai / $B$ đúng ($c$) | $p$-value (Raw) | $p$-value (Holm) | Ý nghĩa ($\alpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `P_pre_vs_P_post` | 0 | 8 | 0.0078 | 0.0312 | ✅ Có ý nghĩa |
| `Gate_vs_P_post` | 0 | 8 | 0.0078 | 0.0312 | ✅ Có ý nghĩa |
| `Gate_vs_LLM_fallback` | 3 | 8 | 0.2266 | 0.4531 | ❌ Chưa có ý nghĩa |
| `Gate_vs_P_pre` | 6 | 6 | 1.0000 | 1.0000 | ❌ Chưa có ý nghĩa |

---

## 7. Phân tích Định tuyến theo Ngân sách Gọi LLM (Selective Routing Curves — RQ5b)

> **Ý nghĩa**: Đánh giá hiệu năng đạt được khi chỉ gửi một tỷ lệ nhỏ ($q$) các hàm cần kiểm thử sang LLM (dành cho môi trường hạn chế chi phí / độ trễ).

| Chính sách (Policy) | Tỷ lệ gọi ($q$) | Số truy vấn | MCC | F1-Score | Balanced Accuracy | Số ca Sửa ($R$) | Số ca Hỏng ($H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `gate_only` | 0% | 0 | 0.7980 | 0.8857 | 0.9015 | — | — |
| `full_expert_with_fallback` | 100% | 80 | 0.9239 | 0.9565 | 0.9636 | — | — |
| `confidence` | 5% | 4 | 0.8761 | 0.9296 | 0.9418 | 3 | 0 |
| `oracle` | 5% | 4 | 0.8996 | 0.9429 | 0.9527 | 4 | 0 |
| `random` | 5% | 4 | 0.7992 | 0.8862 | 0.9019 | — | — |
| `confidence` | 10% | 8 | 0.9268 | 0.9577 | 0.9674 | 5 | 0 |
| `oracle` | 10% | 8 | 1.0000 | 1.0000 | 1.0000 | 8 | 0 |
| `random` | 10% | 8 | 0.8132 | 0.8942 | 0.9090 | — | — |
| `confidence` | 25% | 20 | 0.9748 | 0.9855 | 0.9891 | 7 | 0 |
| `oracle` | 25% | 20 | 1.0000 | 1.0000 | 1.0000 | 8 | 0 |
| `random` | 25% | 20 | 0.8232 | 0.8993 | 0.9134 | — | — |
| `confidence` | 50% | 40 | 0.9748 | 0.9855 | 0.9891 | 7 | 0 |
| `oracle` | 50% | 40 | 1.0000 | 1.0000 | 1.0000 | 8 | 0 |
| `random` | 50% | 40 | 0.8644 | 0.9223 | 0.9338 | — | — |

---

## 8. Khuyến nghị Kỹ thuật cho Bước Tiếp theo

1. **Bàn giao Dữ liệu**: Khi Dũng cung cấp các file thực nghiệm chính thức từ CodeT5 và 36 runs LLM, pipeline này có thể chạy hoàn thành trong dưới 30 giây để cung cấp ngay bộ số chính thức cho báo cáo nghiệm thu.
2. **Khóa Ngưỡng**: Giữ nguyên $\tau = 0.5$ (hoặc $\tau_{\text{train}}$ cố định) cho toàn bộ so sánh, không thực hiện fine-tune lại trên tập Test nhằm tuân thủ quy chuẩn nghiên cứu.
3. **Tích hợp Monorepo**: Sẵn sàng đón nhận bộ trích xuất CPG và đặc trưng 34 chiều của Dũng vào thư mục `src/gate/` sau khi phê duyệt Bước 0.

> *Báo cáo này được tự động kết xuất từ module `grace_diag` theo chuẩn đề tài nghiên cứu khoa học.*