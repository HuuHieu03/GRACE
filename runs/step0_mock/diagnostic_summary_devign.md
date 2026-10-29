# BÁO CÁO CHẨN ĐOÁN OFFLINE BƯỚC 0 — ĐỀ TÀI GRACE
**Bộ dữ liệu**: `DEVIGN` | **Thời gian**: Thực thi tự động | **Tài nguyên**: Offline (0 GPU)

---

## 1. Tóm tắt Kết luận Chẩn đoán (Executive Summary)

- **Đánh giá Thống kê ($\delta$-Verdict)**: 🟢 **BENEFIT (CÓ BỔ SUNG THỰC SỰ ≥ δ)**
- **Giải thích chi tiết**: Có bằng chứng lợi ích ≥ δ trong giao thức đã kiểm
- **Tổng số mẫu kiểm thử**: **100** (Lỗ hổng: 46 [46.0%], An toàn: 54)
- **Tính hợp lệ phản hồi LLM**: 99 hợp lệ (99.0%), 1 lỗi format (được fallback đối xứng về Gate)
- **Chênh lệch $\Delta$MCC ghép cặp (OOF)**: **0.2372** (95% CI: [0.1153, 0.3705])
- **Chênh lệch $\Delta$F1 ghép cặp**: **0.1422** (95% CI: [0.0679, 0.2333])
- **Chênh lệch $\Delta$AUROC**: **0.0596** (95% CI: [0.0207, 0.1072])

---

## 2. Ma trận Sửa - Hỏng theo Nhãn Thực tế (Repair / Harm Matrix)

> **Ý nghĩa**: Định lượng trực tiếp số lượng ca LLM Expert cứu chữa được lỗi của CodeT5 Gate ($R_y$) đối chiếu với số lượng ca LLM làm hỏng quyết định đúng ban đầu của Gate ($H_y$).

| Phân nhóm Nhãn | Tổng số mẫu ($N$) | Ca Sửa ($R_y$) | Ca Hỏng ($H_y$) | Cả hai cùng Đúng | Cả hai cùng Sai | Hiệu quả Sửa Ròng ($R - H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Safe ($y=0$)** | 54 | 8 | 3 | 43 | 0 | **5** |
| **Vulnerable ($y=1$)** | 45 | 4 | 3 | 38 | 0 | **1** |
| **Toàn bộ (Total)** | **99** | **12** | **6** | **81** | **0** | **6** |

- **Tỷ lệ sửa lỗi của Gate**: Đạt **100.00%** (12 / 12 ca Gate đoán sai).
- **Tỷ lệ làm hỏng quyết định đúng**: Ở mức **6.82%** (6 / 87 ca Gate đoán đúng).

---

## 3. Đối chứng với 3 Chuyên gia Tham chiếu (Reference Experts)

> **Nguyên lý kiểm định của Thầy**: Một chuyên gia đoán ngẫu nhiên (lật đồng xu) cũng có thể 'sửa' được một lượng lớn lỗi của Gate do may rủi. LLM chỉ được coi là có tri thức khi số ca sửa ròng vượt trội rõ rệt mốc Random.

| Chuyên gia / Mô hình | Số ca Sửa ($R$) | Số ca Hỏng ($H$) | Sửa Ròng ($R - H$) | Trần Oracle Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **LLM Expert (Đề xuất)** | **12** | **6** | **6** | **1.0000** |
| Random Expert (rate=0.45) | 6.9 [3.5, 10.6] | 41.3 [13.4, 51.5] | -34.4 | 0.9490 |
| Constant-0 (Luôn đoán An toàn) | 8 | 42 | -34 | 0.9600 |
| Constant-1 (Luôn đoán Lỗ hổng) | 4 | 46 | -42 | 0.9200 |

---

## 4. Trần Lý thuyết Chẩn đoán (Oracle Ceiling Analysis)

> **Định nghĩa**: Bộ chọn Oracle lý tưởng nếu biết trước nhãn thật để chọn bên đúng giữa Gate và LLM. Đây là giới hạn trên tuyệt đối không thể vượt qua của bất kỳ bộ kết hợp nào.

| Cấu hình Đánh giá | Accuracy | F1-Score | MCC | Balanced Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **CodeT5 Gate Standalone** (tau=0.5) | 0.8800 | 0.8750 | 0.7624 | 0.8824 |
| **LLM Standalone** (Fallback) | 0.9400 | 0.9348 | 0.8792 | 0.9396 |
| **Trần Lý thuyết Oracle** | **1.0000** | **1.0000** | **1.0000** | **1.0000** |
| *Dư địa tối đa tiềm năng (Oracle - Gate)* | *+0.1200* | *+0.1250* | *+0.2376* | *+0.1176* |

---

## 5. Mô hình Đối chứng Ghép cặp (Matched Meta-Model: $P_{pre}$ vs $P_{post}$)

> **Thiết kế kiểm định**: Cùng số fold (5), cùng scaler, cùng OOF, chỉ khác duy nhất 4 đặc trưng bổ sung từ LLM ($s, \text{valid}, s \times p, s - p$).

| Chỉ số Đánh giá | $P_{pre}$ (Gate + Đặc trưng nền) | $P_{post}$ (Thêm đặc trưng LLM) | Chênh lệch $\Delta$ | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: |
| **MCC** | 0.7429 | 0.9801 | **0.2372** | [0.1153, 0.3705] |
| **F1-Score** | 0.8471 | 0.9892 | **0.1422** | [0.0679, 0.2333] |
| **Accuracy** | 0.8700 | 0.9900 | **0.1200** | [0.0600, 0.1900] |
| **Balanced Accuracy** | 0.8635 | 0.9907 | 0.1272 | — |
| **AUROC** | 0.9400 | 0.9996 | **0.0596** | [0.0207, 0.1072] |
| *Ngưỡng tối ưu $\tau^*$* | *0.69* | *0.50* | — | — |

---

## 6. Kiểm định McNemar & Hiệu chỉnh Holm (Family-wise Significance)

| Cặp Mô hình So sánh | Số ca $A$ đúng / $B$ sai ($b$) | Số ca $A$ sai / $B$ đúng ($c$) | $p$-value (Raw) | $p$-value (Holm) | Ý nghĩa ($\alpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `P_pre_vs_P_post` | 1 | 13 | 0.0018 | 0.0073 | ✅ Có ý nghĩa |
| `Gate_vs_P_post` | 1 | 12 | 0.0034 | 0.0103 | ✅ Có ý nghĩa |
| `Gate_vs_LLM_fallback` | 6 | 12 | 0.2379 | 0.4758 | ❌ Chưa có ý nghĩa |
| `Gate_vs_P_pre` | 8 | 7 | 1.0000 | 1.0000 | ❌ Chưa có ý nghĩa |

---

## 7. Phân tích Định tuyến theo Ngân sách Gọi LLM (Selective Routing Curves — RQ5b)

> **Ý nghĩa**: Đánh giá hiệu năng đạt được khi chỉ gửi một tỷ lệ nhỏ ($q$) các hàm cần kiểm thử sang LLM (dành cho môi trường hạn chế chi phí / độ trễ).

| Chính sách (Policy) | Tỷ lệ gọi ($q$) | Số truy vấn | MCC | F1-Score | Balanced Accuracy | Số ca Sửa ($R$) | Số ca Hỏng ($H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `gate_only` | 0% | 0 | 0.7624 | 0.8750 | 0.8824 | — | — |
| `full_expert_with_fallback` | 100% | 100 | 0.8792 | 0.9348 | 0.9396 | — | — |
| `confidence` | 5% | 5 | 0.7887 | 0.8889 | 0.8949 | 2 | 1 |
| `oracle` | 5% | 5 | 0.8595 | 0.9247 | 0.9304 | 5 | 0 |
| `random` | 5% | 5 | 0.7653 | 0.8764 | 0.8838 | — | — |
| `confidence` | 10% | 10 | 0.8691 | 0.9293 | 0.9352 | 6 | 1 |
| `oracle` | 10% | 10 | 0.9597 | 0.9783 | 0.9799 | 10 | 0 |
| `random` | 10% | 10 | 0.7757 | 0.8818 | 0.8889 | — | — |
| `confidence` | 25% | 25 | 0.9416 | 0.9684 | 0.9722 | 10 | 1 |
| `oracle` | 25% | 25 | 1.0000 | 1.0000 | 1.0000 | 12 | 0 |
| `random` | 25% | 25 | 0.7769 | 0.8822 | 0.8896 | — | — |
| `confidence` | 50% | 50 | 0.9399 | 0.9677 | 0.9706 | 11 | 2 |
| `oracle` | 50% | 50 | 1.0000 | 1.0000 | 1.0000 | 12 | 0 |
| `random` | 50% | 50 | 0.8097 | 0.8983 | 0.9054 | — | — |

---

## 8. Khuyến nghị Kỹ thuật cho Bước Tiếp theo

1. **Bàn giao Dữ liệu**: Khi Dũng cung cấp các file thực nghiệm chính thức từ CodeT5 và 36 runs LLM, pipeline này có thể chạy hoàn thành trong dưới 30 giây để cung cấp ngay bộ số chính thức cho báo cáo nghiệm thu.
2. **Khóa Ngưỡng**: Giữ nguyên $\tau = 0.5$ (hoặc $\tau_{\text{train}}$ cố định) cho toàn bộ so sánh, không thực hiện fine-tune lại trên tập Test nhằm tuân thủ quy chuẩn nghiên cứu.
3. **Tích hợp Monorepo**: Sẵn sàng đón nhận bộ trích xuất CPG và đặc trưng 34 chiều của Dũng vào thư mục `src/gate/` sau khi phê duyệt Bước 0.

> *Báo cáo này được tự động kết xuất từ module `grace_diag` theo chuẩn đề tài nghiên cứu khoa học.*