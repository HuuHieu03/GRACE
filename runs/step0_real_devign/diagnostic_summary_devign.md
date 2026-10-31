# BÁO CÁO CHẨN ĐOÁN OFFLINE BƯỚC 0 — ĐỀ TÀI GRACE
**Bộ dữ liệu**: `DEVIGN` | **Quy chuẩn**: 🟢 **Chuẩn 2-Split Độc lập (Methodology Standard)** — Fit meta-model & chọn ngưỡng trên Validation; Đánh giá trên Test độc lập. | **Tài nguyên**: Offline (0 GPU)

---

## 1. Tóm tắt Kết luận Chẩn đoán (Executive Summary)

- **Đánh giá Thống kê ($\delta$-Verdict)**: 🟡 **NO MEANINGFUL BENEFIT (KHÔNG ĐẠT NGƯỠNG HIỆU ỨNG δ)**
- **Giải thích chi tiết**: Có bằng chứng loại trừ lợi ích ≥ δ (cận trên CI < δ)
- **Tổng số mẫu kiểm thử**: **2732** (Lỗ hổng: 1255 [45.9%], An toàn: 1477)
- **Phân bổ mẫu**: Validation Split = **2732** mẫu | Test Split = **2732** mẫu
- **Tính hợp lệ phản hồi LLM**: 2732 hợp lệ (100.0%), 0 lỗi format (được fallback đối xứng về Gate)
- **Đơn vị Bootstrap (Cluster Unit)**: **Cluster Bootstrap** (2068 clusters (commit IDs) | 5000 reps | seed=20261117) (tuân thủ `protocol.yaml` line 55)
- **Chênh lệch $\Delta$MCC ghép cặp**: **-0.0080** (95% CI: [-0.0286, 0.0124])
- **Chênh lệch $\Delta$F1 ghép cặp**: **-0.0398** (95% CI: [-0.0536, -0.0263])
- **Chênh lệch $\Delta$AUROC**: **0.0015** (95% CI: [-0.0015, 0.0046])

---

## 2. Ma trận Sửa - Hỏng theo Nhãn Thực tế (Repair / Harm Matrix)

> **Ý nghĩa**: Định lượng trực tiếp số lượng ca LLM Expert cứu chữa được lỗi của CodeT5 Gate ($R_y$) đối chiếu với số lượng ca LLM làm hỏng quyết định đúng ban đầu của Gate ($H_y$).

| Phân nhóm Nhãn | Tổng số mẫu ($N$) | Ca Sửa ($R_y$) | Ca Hỏng ($H_y$) | Cả hai cùng Đúng | Cả hai cùng Sai | Hiệu quả Sửa Ròng ($R - H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Safe ($y=0$)** | 1477 | 678 | 24 | 569 | 206 | **654** |
| **Vulnerable ($y=1$)** | 1255 | 16 | 834 | 244 | 161 | **-818** |
| **Toàn bộ (Total)** | **2732** | **694** | **858** | **813** | **367** | **-164** |

- **Tỷ lệ sửa lỗi của Gate**: Đạt **65.41%** (694 / 1061 ca Gate đoán sai).
- **Tỷ lệ làm hỏng quyết định đúng**: Ở mức **51.35%** (858 / 1671 ca Gate đoán đúng).

---

## 3. Đối chứng với 3 Chuyên gia Tham chiếu (Reference Experts)

> **Nguyên lý kiểm định của Thầy**: Một chuyên gia đoán ngẫu nhiên (lật đồng xu) cũng có thể 'sửa' được một lượng lớn lỗi của Gate do may rủi. LLM chỉ được coi là có tri thức khi số ca sửa ròng vượt trội rõ rệt mốc Random.

| Chuyên gia / Mô hình | Số ca Sửa ($R$) | Số ca Hỏng ($H$) | Sửa Ròng ($R - H$) | Trần Oracle Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **LLM Expert (Đề xuất)** | **694** | **858** | **-164** | **0.8657** |
| Random Expert (rate=0.18) | 757.0 [739.3, 770.0] | 986.4 [963.9, 1005.0] | -229.4 | 0.8887 |
| Constant-0 (Luôn đoán An toàn) | 884 | 1078 | -194 | 0.9352 |
| Constant-1 (Luôn đoán Lỗ hổng) | 177 | 593 | -416 | 0.6764 |

---

## 4. Trần Lý thuyết Chẩn đoán (Oracle Ceiling Analysis)

> **Định nghĩa**: Bộ chọn Oracle lý tưởng nếu biết trước nhãn thật để chọn bên đúng giữa Gate và LLM. Đây là giới hạn trên tuyệt đối không thể vượt qua của bất kỳ bộ kết hợp nào.

| Cấu hình Đánh giá | Accuracy | F1-Score | MCC | Balanced Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **CodeT5 Gate Standalone** (tau=0.36) | 0.6116 | 0.6702 | 0.2885 | 0.6302 |
| **LLM Standalone** (Fallback) | 0.5516 | 0.2980 | 0.0668 | 0.5257 |
| **Trần Lý thuyết Oracle** | **0.8657** | **0.8564** | **0.7307** | **0.8661** |
| *Dư địa tối đa tiềm năng (Oracle - Gate)* | *+0.2540* | *+0.1862* | *+0.4422* | *+0.2359* |

---

## 5. Mô hình Đối chứng Ghép cặp (Matched Meta-Model: $P_{pre}$ vs $P_{post}$)

> **Thiết kế kiểm định**: Cùng số fold (3), cùng scaler, chỉ khác duy nhất 4 đặc trưng bổ sung từ LLM ($s, \text{valid}, s \times p, s - p$).
> **Quy chuẩn 2-Split**: Ngưỡng tối ưu $\tau_{pre}^* = 0.46$, $\tau_{post}^* = 0.50$ được xác định hoàn toàn từ tập Validation và khóa chặt khi đánh giá tập Test.
> **Quy chuẩn Bootstrap**: 95% Paired Bootstrap CI được tính toán qua **Cluster Bootstrap** (2068 clusters (commit IDs) | 5000 reps | seed=20261117).

| Chỉ số Đánh giá | $P_{pre}$ (Gate + Đặc trưng nền) | $P_{post}$ (Thêm đặc trưng LLM) | Chênh lệch $\Delta$ | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: |
| **MCC** | 0.3046 | 0.2966 | **-0.0080** | [-0.0286, 0.0124] |
| **F1-Score** | 0.6046 | 0.5647 | **-0.0398** | [-0.0536, -0.0263] |
| **Accuracy** | 0.6567 | 0.6530 | **-0.0037** | [-0.0143, 0.0070] |
| **Balanced Accuracy** | 0.6502 | 0.6408 | -0.0095 | — |
| **AUROC** | 0.7180 | 0.7195 | **0.0015** | [-0.0015, 0.0046] |
| *Ngưỡng tối ưu $\tau^*$* | *0.46* | *0.50* | — | — |

---

## 6. Kiểm định McNemar & Hiệu chỉnh Holm (Family-wise Significance)

| Cặp Mô hình So sánh | Số ca $A$ đúng / $B$ sai ($b$) | Số ca $A$ sai / $B$ đúng ($c$) | $p$-value (Raw) | $p$-value (Holm) | Ý nghĩa ($\alpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `P_pre_vs_P_post` | 105 | 95 | 0.5245 | 0.5245 | ❌ Chưa có ý nghĩa |
| `Gate_vs_P_post` | 467 | 580 | < 0.001 | 0.0011 | ✅ Có ý nghĩa |
| `Gate_vs_LLM_fallback` | 858 | 694 | < 0.001 | < 0.001 | ✅ Có ý nghĩa |
| `Gate_vs_P_pre` | 367 | 490 | < 0.001 | < 0.001 | ✅ Có ý nghĩa |

---

## 7. Phân tích Định tuyến theo Ngân sách Gọi LLM (Selective Routing Curves — RQ5b)

> **Ý nghĩa**: Đánh giá hiệu năng đạt được khi chỉ gửi một tỷ lệ nhỏ ($q$) các hàm cần kiểm thử sang LLM qua 4 chính sách: `confidence` (gần biên), `benefit` (học máy Ridge), `oracle` (trần lý tưởng), và `random` (đối chứng ngẫu nhiên).

| Chính sách (Policy) | Tỷ lệ gọi ($q$) | Số truy vấn | MCC | F1-Score | Balanced Accuracy | Số ca Sửa ($R$) | Số ca Hỏng ($H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `gate_only` | 0% | 0 | 0.2885 | 0.6702 | 0.6302 | — | — |
| `full_expert_with_fallback` | 100% | 2732 | 0.0668 | 0.2980 | 0.5257 | — | — |
| `confidence` | 5% | 137 | 0.2991 | 0.6720 | 0.6382 | 50 | 23 |
| `benefit` | 5% | 137 | 0.2879 | 0.6665 | 0.6342 | 58 | 40 |
| `oracle` | 5% | 137 | 0.3748 | 0.7006 | 0.6768 | 137 | 0 |
| `random` | 5% | 137 | 0.2688 | 0.6596 | 0.6245 | — | — |
| `confidence` | 10% | 274 | 0.2991 | 0.6697 | 0.6406 | 87 | 49 |
| `benefit` | 10% | 274 | 0.2864 | 0.6609 | 0.6371 | 116 | 82 |
| `oracle` | 10% | 274 | 0.4600 | 0.7342 | 0.7235 | 274 | 0 |
| `random` | 10% | 274 | 0.2495 | 0.6477 | 0.6181 | — | — |
| `confidence` | 25% | 683 | 0.3030 | 0.6605 | 0.6488 | 219 | 143 |
| `benefit` | 25% | 683 | 0.2686 | 0.6323 | 0.6341 | 265 | 217 |
| `oracle` | 25% | 683 | 0.7230 | 0.8527 | 0.8624 | 683 | 0 |
| `random` | 25% | 683 | 0.2098 | 0.6131 | 0.6037 | — | — |
| `confidence` | 50% | 1366 | 0.2771 | 0.6093 | 0.6386 | 424 | 344 |
| `benefit` | 50% | 1366 | 0.2747 | 0.5923 | 0.6360 | 472 | 390 |
| `oracle` | 50% | 1366 | 0.7307 | 0.8564 | 0.8661 | 694 | 0 |
| `random` | 50% | 1366 | 0.1587 | 0.5409 | 0.5792 | — | — |

---

## 8. Khuyến nghị Kỹ thuật cho Bước Tiếp theo

1. **Bàn giao Dữ liệu**: Khi có kết quả chính thức từ CodeT5 và LLM, hãy chạy pipeline 2-Split với `--gate-val`, `--gate-test`, `--llm-val`, `--llm-test` để khóa ngưỡng tối ưu trên Validation và đánh giá trung thực trên Test.
2. **Khóa Ngưỡng**: Giữ nguyên $\tau = 0.5$ (hoặc $\tau_{\text{val}}$ cố định) cho toàn bộ so sánh, không thực hiện fine-tune lại trên tập Test nhằm tuân thủ quy chuẩn nghiên cứu.
3. **Tích hợp Monorepo**: Sẵn sàng đón nhận bộ trích xuất CPG và đặc trưng 34 chiều vào thư mục `src/gate/` sau khi hoàn tất Bước 0.

> *Báo cáo này được tự động kết xuất từ module `grace_diag` theo chuẩn đề tài nghiên cứu khoa học.*