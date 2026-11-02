# BÁO CÁO CHẨN ĐOÁN OFFLINE BƯỚC 0 — ĐỀ TÀI GRACE
**Bộ dữ liệu**: `REVEAL` | **Quy chuẩn**: 🟢 **Chuẩn 2-Split Độc lập (Methodology Standard)** — Fit meta-model & chọn ngưỡng trên Validation; Đánh giá trên Test độc lập. | **Tài nguyên**: Offline (0 GPU)

---

## 1. Tóm tắt Kết luận Chẩn đoán (Executive Summary)

- **Đánh giá Thống kê ($\delta$-Verdict)**: 🟡 **NO MEANINGFUL BENEFIT (KHÔNG ĐẠT NGƯỠNG HIỆU ỨNG δ)**
- **Giải thích chi tiết**: Có bằng chứng loại trừ lợi ích ≥ δ (cận trên CI < δ)
- **Tổng số mẫu kiểm thử**: **2274** (Lỗ hổng: 230 [10.1%], An toàn: 2044)
- **Phân bổ mẫu**: Validation Split = **2273** mẫu | Test Split = **2274** mẫu
- **Tính hợp lệ phản hồi LLM**: 2274 hợp lệ (100.0%), 0 lỗi format (được fallback đối xứng về Gate)
- **Đơn vị Bootstrap (Cluster Unit)**: **Cluster Bootstrap** (646 clusters (file hashes) | 5000 reps | seed=20261117) (tuân thủ `protocol.yaml` line 55)
- **Chênh lệch $\Delta$MCC ghép cặp**: **-0.0274** (95% CI: [-0.0561, 0.0006])
- **Chênh lệch $\Delta$F1 ghép cặp**: **-0.0237** (95% CI: [-0.0490, 0.0014])
- **Chênh lệch $\Delta$AUROC**: **0.0026** (95% CI: [-0.0030, 0.0086])

---

## 2. Ma trận Sửa - Hỏng theo Nhãn Thực tế (Repair / Harm Matrix)

> **Ý nghĩa**: Định lượng trực tiếp số lượng ca LLM Expert cứu chữa được lỗi của CodeT5 Gate ($R_y$) đối chiếu với số lượng ca LLM làm hỏng quyết định đúng ban đầu của Gate ($H_y$).

| Phân nhóm Nhãn | Tổng số mẫu ($N$) | Ca Sửa ($R_y$) | Ca Hỏng ($H_y$) | Cả hai cùng Đúng | Cả hai cùng Sai | Hiệu quả Sửa Ròng ($R - H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Safe ($y=0$)** | 2044 | 160 | 95 | 1747 | 42 | **65** |
| **Vulnerable ($y=1$)** | 230 | 20 | 102 | 15 | 93 | **-82** |
| **Toàn bộ (Total)** | **2274** | **180** | **197** | **1762** | **135** | **-17** |

- **Tỷ lệ sửa lỗi của Gate**: Đạt **57.14%** (180 / 315 ca Gate đoán sai).
- **Tỷ lệ làm hỏng quyết định đúng**: Ở mức **10.06%** (197 / 1959 ca Gate đoán đúng).

---

## 3. Đối chứng với 3 Chuyên gia Tham chiếu (Reference Experts)

> **Nguyên lý kiểm định của Thầy**: Một chuyên gia đoán ngẫu nhiên (lật đồng xu) cũng có thể 'sửa' được một lượng lớn lỗi của Gate do may rủi. LLM chỉ được coi là có tri thức khi số ca sửa ròng vượt trội rõ rệt mốc Random.

| Chuyên gia / Mô hình | Số ca Sửa ($R$) | Số ca Hỏng ($H$) | Sửa Ròng ($R - H$) | Trần Oracle Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **LLM Expert (Đề xuất)** | **180** | **197** | **-17** | **0.9406** |
| Random Expert (rate=0.08) | 194.1 [184.4, 203.1] | 249.2 [228.8, 271.1] | -55.1 | 0.9468 |
| Constant-0 (Luôn đoán An toàn) | 202 | 117 | 85 | 0.9503 |
| Constant-1 (Luôn đoán Lỗ hổng) | 113 | 1842 | -1729 | 0.9112 |

---

## 4. Trần Lý thuyết Chẩn đoán (Oracle Ceiling Analysis)

> **Định nghĩa**: Bộ chọn Oracle lý tưởng nếu biết trước nhãn thật để chọn bên đúng giữa Gate và LLM. Đây là giới hạn trên tuyệt đối không thể vượt qua của bất kỳ bộ kết hợp nào.

| Cấu hình Đánh giá | Accuracy | F1-Score | MCC | Balanced Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **CodeT5 Gate Standalone** (tau=0.17) | 0.8615 | 0.4262 | 0.3559 | 0.7049 |
| **LLM Standalone** (Fallback) | 0.8540 | 0.1741 | 0.0971 | 0.5426 |
| **Trần Lý thuyết Oracle** | **0.9406** | **0.6699** | **0.6439** | **0.7876** |
| *Dư địa tối đa tiềm năng (Oracle - Gate)* | *+0.0792* | *+0.2437* | *+0.2881* | *+0.0826* |

---

## 5. Mô hình Đối chứng Ghép cặp (Matched Meta-Model: $P_{pre}$ vs $P_{post}$)

> **Thiết kế kiểm định**: Cùng số fold (3), cùng scaler, chỉ khác duy nhất 4 đặc trưng bổ sung từ LLM ($s, \text{valid}, s \times p, s - p$).
> **Quy chuẩn 2-Split**: Ngưỡng tối ưu $\tau_{pre}^* = 0.22$, $\tau_{post}^* = 0.19$ được xác định hoàn toàn từ tập Validation và khóa chặt khi đánh giá tập Test.
> **Quy chuẩn Bootstrap**: 95% Paired Bootstrap CI được tính toán qua **Cluster Bootstrap** (646 clusters (file hashes) | 5000 reps | seed=20261117).

| Chỉ số Đánh giá | $P_{pre}$ (Gate + Đặc trưng nền) | $P_{post}$ (Thêm đặc trưng LLM) | Chênh lệch $\Delta$ | 95% Bootstrap CI |
| :--- | :---: | :---: | :---: | :---: |
| **MCC** | 0.3760 | 0.3486 | **-0.0274** | [-0.0561, 0.0006] |
| **F1-Score** | 0.4436 | 0.4199 | **-0.0237** | [-0.0490, 0.0014] |
| **Accuracy** | 0.8720 | 0.8615 | **-0.0106** | [-0.0177, -0.0038] |
| **Balanced Accuracy** | 0.7089 | 0.6991 | -0.0097 | — |
| **AUROC** | 0.8093 | 0.8120 | **0.0026** | [-0.0030, 0.0086] |
| *Ngưỡng tối ưu $\tau^*$* | *0.22* | *0.19* | — | — |

---

## 6. Kiểm định McNemar & Hiệu chỉnh Holm (Family-wise Significance)

| Cặp Mô hình So sánh | Số ca $A$ đúng / $B$ sai ($b$) | Số ca $A$ sai / $B$ đúng ($c$) | $p$-value (Raw) | $p$-value (Holm) | Ý nghĩa ($\alpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `P_pre_vs_P_post` | 47 | 23 | 0.0060 | 0.0239 | ✅ Có ý nghĩa |
| `Gate_vs_P_post` | 73 | 73 | 0.9340 | 0.9340 | ❌ Chưa có ý nghĩa |
| `Gate_vs_LLM_fallback` | 197 | 180 | 0.4099 | 0.8198 | ❌ Chưa có ý nghĩa |
| `Gate_vs_P_pre` | 34 | 58 | 0.0165 | 0.0495 | ✅ Có ý nghĩa |

---

## 7. Phân tích Định tuyến theo Ngân sách Gọi LLM (Selective Routing Curves — RQ5b)

> **Ý nghĩa**: Đánh giá hiệu năng đạt được khi chỉ gửi một tỷ lệ nhỏ ($q$) các hàm cần kiểm thử sang LLM qua 4 chính sách: `confidence` (gần biên), `benefit` (học máy Ridge), `oracle` (trần lý tưởng), và `random` (đối chứng ngẫu nhiên).

| Chính sách (Policy) | Tỷ lệ gọi ($q$) | Số truy vấn | MCC | F1-Score | Balanced Accuracy | Số ca Sửa ($R$) | Số ca Hỏng ($H$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `gate_only` | 0% | 0 | 0.3559 | 0.4262 | 0.7049 | — | — |
| `full_expert_with_fallback` | 100% | 2274 | 0.0971 | 0.1741 | 0.5426 | — | — |
| `confidence` | 5% | 114 | 0.3474 | 0.4184 | 0.6924 | 33 | 21 |
| `benefit` | 5% | 114 | 0.3255 | 0.3967 | 0.6700 | 50 | 27 |
| `oracle` | 5% | 114 | 0.5129 | 0.5621 | 0.7560 | 114 | 0 |
| `random` | 5% | 114 | 0.3458 | 0.4174 | 0.6970 | — | — |
| `confidence` | 10% | 228 | 0.3509 | 0.4202 | 0.6867 | 62 | 34 |
| `benefit` | 10% | 228 | 0.2666 | 0.3349 | 0.6252 | 84 | 55 |
| `oracle` | 10% | 228 | 0.6439 | 0.6699 | 0.7876 | 180 | 0 |
| `random` | 10% | 228 | 0.3339 | 0.4069 | 0.6883 | — | — |
| `confidence` | 25% | 569 | 0.2752 | 0.3419 | 0.6284 | 121 | 87 |
| `benefit` | 25% | 569 | 0.2151 | 0.2730 | 0.5888 | 122 | 84 |
| `oracle` | 25% | 569 | 0.6439 | 0.6699 | 0.7876 | 180 | 0 |
| `random` | 25% | 569 | 0.3045 | 0.3802 | 0.6667 | — | — |
| `confidence` | 50% | 1137 | 0.1698 | 0.2394 | 0.5743 | 169 | 159 |
| `benefit` | 50% | 1137 | 0.1940 | 0.2552 | 0.5808 | 139 | 110 |
| `oracle` | 50% | 1137 | 0.6439 | 0.6699 | 0.7876 | 180 | 0 |
| `random` | 50% | 1137 | 0.2353 | 0.3146 | 0.6207 | — | — |

### So sánh Đối chứng Ghép cặp tại Ngân sách $q=10%$ (`benefit` vs `confidence`)

> **Mục đích**: Kiểm định ghép cặp xem Ridge Benefit Router có vượt trội có ý nghĩa thống kê so với Confidence Router tại ngưỡng ngân sách thực tế 10% hay không (**Cluster Bootstrap** (646 clusters (file hashes) | 5000 reps | seed=20261117)).

| Chỉ số So sánh | Chênh lệch $\Delta$ (Benefit − Confidence) | 95% Bootstrap CI | Đơn vị Bootstrap | Kết luận Thống kê |
| :--- | :---: | :---: | :---: | :---: |
| **Balanced Accuracy ($\Delta$BA - Chỉ số chính)** | **-0.0615** | [-0.0943, -0.0287] | cluster | Bất lợi (CI < 0) |
| **MCC ($\Delta$MCC - Chỉ số phụ)** | **-0.0843** | [-0.1461, -0.0247] | cluster | Bất lợi (CI < 0) |

---

## 8. Khuyến nghị Kỹ thuật cho Bước Tiếp theo

1. **Bàn giao Dữ liệu**: Khi có kết quả chính thức từ CodeT5 và LLM, hãy chạy pipeline 2-Split với `--gate-val`, `--gate-test`, `--llm-val`, `--llm-test` để khóa ngưỡng tối ưu trên Validation và đánh giá trung thực trên Test.
2. **Khóa Ngưỡng**: Giữ nguyên $\tau = 0.5$ (hoặc $\tau_{\text{val}}$ cố định) cho toàn bộ so sánh, không thực hiện fine-tune lại trên tập Test nhằm tuân thủ quy chuẩn nghiên cứu.
3. **Tích hợp Monorepo**: Sẵn sàng đón nhận bộ trích xuất CPG và đặc trưng 34 chiều vào thư mục `src/gate/` sau khi hoàn tất Bước 0.

> *Báo cáo này được tự động kết xuất từ module `grace_diag` theo chuẩn đề tài nghiên cứu khoa học.*