# Đăng Ký Trước Giao Thức Nghiên Cứu (Preregistration Protocol v1)

- **Study ID:** `grace_diag_replication_v1`
- **Version:** `prereg-v1`
- **Registration Date:** 2026-10-31 (Cập nhật chuẩn hóa hoàn thiện Bước 4: 2026-11-02)
- **Repository Version / Git Tag:** `prereg-v1`
- **Protocol Configuration File:** `grace_diag_kit/configs/protocol.yaml` & `configs/protocol.yaml`
- **Locked Thresholds File:** `configs/thresholds.json` & `configs/thresholds_flat.json`
- **Tài liệu đề cương gốc:** `00_Reports_and_Docs/De_cuong_nghien_cuu_GRACE_hop_nhat.pdf`

---

## 1. Công Bố Minh Bạch Về Tiếp Xúc Dữ Liệu Test (Test Exposure Disclosure)

Tập dữ liệu kiểm thử (test set) của Devign và ReVeal đã từng được tiếp xúc trong giai đoạn thăm dò sơ bộ ban đầu (gồm 36 lượt chạy API thử nghiệm, tập dev-100, và các phép đo động cơ H1–H3). 

Nhằm đảm bảo tính hợp thức và giá trị xác nhận khoa học:
1. Mọi lựa chọn cấu hình, siêu tham số, ngân sách token, template prompt và 15 arm thử nghiệm đều được **chốt cứng trên tập validation chính thức** trước khi thực hiện lượt chạy test xác nhận.
2. Ngưỡng phân lớp tối ưu $\tau^*$ của mọi arm được tìm kiếm và cố định hoàn toàn trên tập validation (`thresholds.json`), không bao giờ điều chỉnh dựa trên kết quả test. Cam kết Zero-Test-Exposure.
3. Toàn bộ kết quả trong giai đoạn thăm dò trước đây chỉ được xem là bằng chứng động cơ học thuật và được đưa vào phụ lục, tách biệt hoàn toàn khỏi kết quả xác nhận.
4. Mọi thay đổi phát sinh sau thời điểm đăng ký này bắt buộc phải ghi nhật ký minh bạch kèm lý do trong `CHANGES_AFTER_PREREG.md`.

---

## 2. Bảng 11 Giả Thuyết Nghiên Cứu (Table 4.3)

| Mã | Tên Giả Thuyết | Nội Dung Chi Tiết & Chuẩn Chấp Nhận / Bác Bỏ (Biên $\delta$ khai báo trước) |
| :--- | :--- | :--- |
| **H1.1** | GRACE không vượt Zero-shot trên Devign | Arm B2 (GRACE đầy đủ) không vượt B0 (zero-shot) về khả năng phân biệt trên Devign Test: Cận trên CI 95% của $\Delta\text{MCC}(\text{B2} - \text{B0}) < 0.03$ và của $\Delta\text{AUROC} < 0.02$ (biên thực chất $\delta = 0.02$). |
| **H1.2** | GRACE không vượt Zero-shot trên ReVeal & Không đạt mức công bố | Arm B2 không vượt B0 về khả năng phân biệt trên ReVeal Test: Cận trên CI 95% của $\Delta\text{MCC}(\text{B2} - \text{B0}) < 0.03$ và của $\Delta\text{AUROC} < 0.02$; GRACE không tái lập được hiệu năng công bố trong bài gốc: $\text{MCC}(\text{B2}) < 0.15$ trên cả hai dataset; $F_1(\text{B2})$ trên Devign thấp hơn $F_1$ luôn-vulnerable ($62.95\%$). |
| **H2.1** | Demo tác động qua nhãn | Demonstration tác động chủ yếu thông qua nhãn bề mặt: Độ nhạy nhãn thuần (Net label sensitivity) $\ge 15$ điểm phần trăm (tỷ lệ đổi khi đảo nhãn $\text{B2} \leftrightarrow \text{B2-flip}$ trừ biến động tự nhiên $\text{B2} \leftrightarrow \text{B2-rep}$). |
| **H2.2** | Nội dung demo không mang tín hiệu | Nội dung mã nguồn của demo không bổ sung tín hiệu bản chất: Cận trên CI của $\Delta\text{AUROC}(\text{B2} - \text{B2-rand}) < 0.02$ và của $\Delta\text{AUROC}(\text{B2-nolabel} - \text{B1}) < 0.02$; B2-labelonly tái tạo $\ge 80\%$ mức chênh lệch giữa B2 và B1. |
| **H2.3** | Cặp tương phản chỉ dịch chuyển điểm | Kỹ thuật cặp tương phản (B3) chỉ dịch chuyển điểm hoạt động chứ không tăng khả năng phân tách: Tỷ lệ đoán 1 của B3 cao hơn B2 $\ge 10$ điểm phần trăm trong khi cận trên CI 95% của $\Delta\text{AUROC}(\text{B3} - \text{B2}) < 0.02$. |
| **H3.1** | LLM không đọc Code Property Graph | Thông tin đồ thị CPG dạng văn bản không mang lại tín hiệu bổ sung cho LLM: Cận trên CI của $\Delta\text{AUROC}(\text{B1} - \text{B0}) < 0.02$ và của $\Delta\text{AUROC}(\text{B1} - \text{B1-shuf}) < 0.02$; B1-H2 không khác B1 theo cùng tiêu chí. |
| **H4.1** | Đo không ngưỡng gần ngẫu nhiên | Khi đánh giá không phụ thuộc ngưỡng (AUROC), toàn bộ pipeline LLM chỉ đạt hiệu năng gần mức ngẫu nhiên: $\text{AUROC} \le 0.62$ trên cả Devign và ReVeal đối với mọi arm LLM. |
| **H5.1** | Mốc có giám sát thắng rõ | Bộ phân lớp có giám sát đơn giản trên embedding đóng băng vượt trội rõ rệt pipeline LLM: $\Delta\text{MCC}(\text{SUP-LR} - \text{B2}) \ge 0.15$ với CI không chứa 0; $\text{AUROC}(\text{SUP-LR}) \ge 0.68$. |
| **H5.2** | LLM không bổ sung tín hiệu trực giao | Điểm số của LLM không bổ sung thêm tín hiệu trực giao sau khi đã có 34 đặc trưng cơ sở: Cận trên CI 95% của $\Delta\text{MCC}(P_\text{post} - P_\text{pre}) < 0.02$ (cùng 34 đặc trưng nền, cùng fold StratifiedGroupKFold, cùng ngưỡng $\tau^*$). |
| **H5.3** | Không biết trước khi nào gọi LLM (Routing $q=10\%$ Benefit vs Confidence & Complementarity) | Tại ngân sách gọi expert $q=10\%$, bộ định tuyến theo lợi ích (Benefit Router - Ridge) không vượt trội hơn bộ định tuyến theo độ tự tin (Confidence Router): Paired Bootstrap CI của $\Delta\text{Balanced Accuracy}(\text{benefit} - \text{confidence})$ và của $\Delta\text{MCC}$ có cận trên $< \delta = 0.02$ (phán quyết `no_meaningful_benefit`); đồng thời $\Delta\text{Balanced Accuracy}(\text{benefit} - \text{random})$ có cận trên CI $< 0.01$; số ca LLM sửa đúng không vượt khoảng $95\%$ của expert ngẫu nhiên cùng tỷ lệ đoán 1 (20 seed). |
| **H6.1** | Cơ chế truy hồi lệch hướng | Demonstration được truy hồi hiếm khi đúng cơ chế lỗi tương ứng; liên quan không kéo theo đúng: Tỷ lệ "Neither" $\ge 40\%$ trên Devign; chênh lệch accuracy giữa nhóm demo liên quan và không liên quan có CI chứa 0. |

### Cách Đọc Phán Quyết Cố Định Trước Cho Mọi So Sánh Cặp ($\Delta = \text{metric}(B) - \text{metric}(A)$)

- **`benefit` (Có bằng chứng lợi ích):** CI nằm hoàn toàn trên 0 ($\text{cận dưới} > 0$) và $\Delta \ge \delta$.
- **`no_meaningful_benefit` (Không có lợi ích đáng kể):** Cận trên CI $< \delta$.
- **`harm` (Gây hại hiệu năng):** CI nằm hoàn toàn dưới 0 ($\text{cận trên} < 0$).
- **`inconclusive` (Chưa đủ bằng chứng):** Khoảng CI chứa 0 hoặc cận trên $\ge \delta$ nhưng cận dưới $\le 0$.

Biên $\delta$ khai báo trước: Quy chuẩn chung cho biên thực chất khoa học là $\delta = 0.02$ (chi tiết: $\delta_\text{MCC} = 0.03$, $\delta_\text{AUROC} = 0.02$, $\delta_\text{BA} = 0.01$, $\delta_\text{MCC\_meta} = 0.02$, $\delta_\text{routing} = 0.02$).

---

## 3. Quy Tắc Phân Tích & Phương Pháp Luận Thống Kê (Mục 6)

1. **Khử trùng & Khóa Kho Dữ Liệu:**
   - Dữ liệu donor train được loại bỏ toàn bộ các mẫu trùng lặp chính xác với validation và test (sau khi chuẩn hóa bỏ khoảng trắng và chú thích).
   - Trong kho donor, giữ một đại diện cho nhóm mã trùng cùng nhãn; loại bỏ các nhóm mã trùng có mâu thuẫn nhãn.
   - Các cặp gần trùng (Jaccard token 3-gram $\ge 0.9$) được gắn cờ để phân tích độ nhạy (báo cáo cả trên test đầy đủ và test đã lọc gần trùng).
2. **Khóa 14 Ngưỡng Quyết Định Tối Ưu ($\tau^*$):**
   - Không dùng ngưỡng tùy tiện.
   - Tìm kiếm ngưỡng tối ưu $\tau^*$ trên lưới 99 điểm $[0.01, 0.99]$ (bước 0.01) dựa trên cực đại hóa chỉ số MCC trên tập validation:
     $$\tau^* = \operatorname{argmax}_{\tau \in [0.01, 0.99]} \left(\operatorname{MCC}(y_\text{val}, \hat{y}_\tau), -|\tau - 0.5|\right)$$
   - Khóa toàn bộ 14 ngưỡng tối ưu $\tau^*$ vào `configs/thresholds.json` và `configs/thresholds_flat.json` trước khi chạy suy luận trên test:
     - **Devign LLM Arms**: `devign|B0|42` = 0.08, `devign|B1|42` = 0.88, `devign|B2|42` = 0.98, `devign|B2-flip|42` = 0.50, `devign|B2-rep|42` = 0.98.
     - **ReVeal LLM Arms**: `reveal|B0|42` = 0.44, `reveal|B1|42` = 0.74, `reveal|B2|42` = 0.99, `reveal|B2-flip|42` = 0.46, `reveal|B2-rep|42` = 0.99.
     - **Meta-Models**: `devign|P-PRE|42` = 0.54, `devign|P-POST|42` = 0.60; `reveal|P-PRE|42` = 0.38, `reveal|P-POST|42` = 0.10.
3. **Thống Kê Khẳng Định & So Sánh Cặp (Bảng B):**
   - Paired Bootstrap $B = 5000$ lần lặp với seed cố định `20261117`.
   - Đơn vị gom nhóm (Cluster Units):
     - **Devign:** Cluster Bootstrap theo `commit_id` (2,068 cụm độc lập trên tập Test $N = 2,732$).
     - **ReVeal:** Cluster Bootstrap theo File-level Hashes (`file_hash`, 646 cụm độc lập trên tập Test $N = 2,274$, giải quyết triệt để rủi ro sụp đổ nhóm chrome/debian theo chuẩn Bước 0).
   - Phân chia fold meta-model: `StratifiedGroupKFold` (3 folds) trên tập Validation bảo đảm tính độc lập nhóm mã nguồn.
   - Hiệu chỉnh họ đa kiểm định theo phương pháp Holm-Bonferroni (`family_correction: holm`).
4. **Phân Tích Bổ Sung (Complementarity & Routing):**
   - 34 đặc trưng cơ sở $P_\text{pre}$ bao gồm 5 logit từ các mô hình nền tảng, xác suất tổng hợp $p$, $|p - 0.5|$, độ lệch MLP-Lexical, và 26 code metrics.
   - 4 đặc trưng từ LLM gồm: điểm $s$, cờ $valid$, tương tác $s \cdot p$, và độ lệch $s - p$. Invalid được gán fallback đối xứng ($s = 0.5, valid = 0$).
   - Mô hình meta sử dụng Logistic Regression ($C = 1.0$), 3-fold Out-Of-Fold (OOF).
   - Kiểm tra định tuyến tại các mức ngân sách 5%, 10%, 25% với Paired Bootstrap CI trực tiếp giữa Benefit Router vs Confidence Router, 20 seed ngẫu nhiên cho baseline RANDOM và trần Oracle.

---

## 4. Ma Trận 15 Cấu Hình (Arms) & Quy Tắc Dựng Probe (Mục 6.3)

| Nhóm Tầng (Tier) | Mã Arm | Nội Dung Prompt & Đặc Tính Probe | Khác Biệt So Với Arm Gốc | RQ Tương Ứng |
| :--- | :--- | :--- | :--- | :--- |
| **Sàn & Mốc** | ALL-0, ALL-1, RAND | Dự đoán hằng số 0, hằng số 1, ngẫu nhiên theo phân bố nhãn | Không gọi LLM; baseline phân bố nhãn | Tất cả |
| **Sàn & Mốc** | SUP-LR, SUP-MLP, SUP-METRIC | Logistic Regression trên CodeT5 768d, MLP 768→128→1, LR trên 26 code metrics | Mốc có giám sát trên embedding đóng băng (3 seed 42, 43, 44) | RQ5 |
| **Tầng 1** | **B0** | Role + domain + target code + binary question | Zero-shot; không đồ thị CPG, không demonstration | RQ1 |
| **Tầng 1** | **B1** | B0 + CPG nodes & edges (prefix 25 nút / 25 cạnh) | Thêm đồ thị CPG như bản tái triển khai | RQ1, RQ3 |
| **Tầng 1** | **B2** | B1 + 1 demo truy hồi từ kho clean donor kèm nhãn thật | GRACE hoàn chỉnh | RQ1, RQ2 |
| **Tầng 1** | **B2-flip** | B2 nhưng đảo nhãn demo ($1 \leftrightarrow 0$) ở câu dẫn | Đo độ nhạy nhãn (label sensitivity) | RQ2 |
| **Tầng 1** | **B2-rep** | B2 chạy lần 2 với cùng prompt (bỏ qua cache) | Đo biến động tự nhiên từ batching / GPU nondeterminism | RQ2 |
| **Tầng 2** | **B2-rand** | B1 + 1 demo ngẫu nhiên từ kho clean donor kèm nhãn thật | Nội dung demo không liên quan cơ chế (3 seed: 42, 43, 44) | RQ2 |
| **Tầng 2** | **B2-nolabel** | B1 + demo truy hồi; đổi câu dẫn thành "The following is a related example." (không nhãn) | Bỏ nhãn demonstration | RQ2 |
| **Tầng 2** | **B2-labelonly** | B1 + câu dẫn "A function similar to the one above was labelled Vulnerable/Non-vulnerable." (không có mã demo) | Chỉ còn gợi ý nhãn bề mặt | RQ2 |
| **Tầng 2** | **B1-shuf** | B0 + CPG của một hàm khác cùng số nút ($\pm 10\%$), cùng ngân sách | Đồ thị không mang thông tin target (3 seed: 42, 43, 44) | RQ3 |
| **Tầng 3** | **B1-full** | B0 + CPG lấp đầy ngân sách 1,500 token | Đổi chính sách cắt đồ thị (nhiều nút hơn) | RQ3 |
| **Tầng 3** | **B1-H2** | B0 + cụm evidence của H2 guarded cùng 1,500 token | Đổi cách đóng gói đồ thị theo vết luồng thực thi | RQ3 |
| **Tầng 3** | **B3** | B1 + cặp demo tương phản (1 vuln, 1 safe) + khối Key difference | Phương pháp Contrastive ICL đề xuất | RQ2, RQ4 |
| **Tầng 3** | **B3-nodiff** | B3 nhưng lược bỏ khối Key difference | Tách tác dụng của khối phân tích khác biệt | RQ2 |
| **Tầng 3** | **B3-swap** | B3 nhưng đảo thứ tự xuất hiện giữa 2 demo | Đo thiên lệch vị trí (recency bias) | RQ2 |
| **Tầng 3** | **B3-flip** | B3 nhưng đảo nhãn cả 2 demo ($1 \leftrightarrow 0$) | Đo độ nhạy nhãn khi cấu trúc nhãn đã được cân bằng | RQ2 |

---

## 5. Quy Chuẩn Prompt, Ngân Sách Token & Thứ Tự Section (Hình 6 & Mục 6.4)

1. **Thứ Tự Canonical (Figure 6 & Mã Tác Giả):**
   `[role_domain, target_code, question, node_info, edge_info, demonstration, answer]`
   *Quy tắc bất biến: Target code đi trước, graph ở giữa, demonstration ở cuối cùng ngay trước câu trả lời. Nhãn target tuyệt đối không bao giờ xuất hiện trong prompt.*
2. **Ngân Sách Token Tối Đa (8,192 Token Context):**
   - Mã nguồn target: $\le 3,000$ tokens.
   - Demonstration: $\le 1,500$ tokens mỗi demo.
   - Đồ thị CPG: $\le 1,500$ tokens.
   - Dự phòng (Reserve): $64$ tokens.
   - Đơn vị đo: Duy nhất bằng tokenizer của model (`Qwen3-Coder-30B-A3B-Instruct`).
3. **Đầu Ra & Cách Tính Điểm:**
   - Model trả đúng 1 token (`0` hoặc `1`).
   - Điểm số liên tục $s = \frac{p(1)}{p(0) + p(1)}$ trích xuất từ top-5 logprob của token đầu tiên.
   - Nếu cả hai token vắng mặt trong top-5 logprob, đánh dấu `invalid` và báo cáo tỷ lệ (không ép về 0).

---

## 6. Quy Tắc Dừng (Stopping Rules)

1. **Lợi thế SUP-LR biến mất:** Nếu sau khi khử trùng và kiểm toán nhãn, mô hình SUP-LR không còn vượt trội B2, dừng nghiên cứu để rà soát toàn bộ quy trình tiền xử lý dữ liệu trước khi viết báo cáo.
2. **Thất bại Kiểm toán Prompt Audit:** Nếu tỷ lệ demonstration rỗng $> 1\%$, tỷ lệ thiếu đồ thị $> 5\%$ (ngoài các ca Joern lỗi đã gắn cờ), hoặc phát hiện rò rỉ nhãn target $> 0$, dừng quy trình, sửa hợp đồng dựng prompt, và chạy lại toàn bộ arm bị ảnh hưởng.
3. **Thất bại Smoke Test Backend:** Nếu tỷ lệ phản hồi hợp lệ có token 0/1 trong top-5 logprob $< 99\%$, không tiến hành chạy ma trận xác nhận cho đến khi backend mô hình đạt độ ổn định định lượng.
4. **Đóng băng Giao thức Nghiêm ngặt:** Tuyệt đối không mở thêm arm, không thêm mô hình, không điều chỉnh ngưỡng sau khi đã quan sát dữ liệu test. Bất kỳ phân tích bổ sung nào phát sinh sau thời điểm này đều phải phân loại là "thăm dò sau đăng ký" (exploratory post-hoc) và ghi rõ trong bài báo.

---

## 7. Bảng Băm Manifest & Checkpoint Đã Đóng Băng

### 7.1. Bảng Mã Băm SHA-256 Của Dữ Liệu & Manifest

| Tập Dữ Liệu | Phân Vùng / Mục | Số Dòng (Samples) | Tỷ Lệ Positive (Vuln) | Đường Dẫn Tệp | Mã Băm SHA-256 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Devign** | Raw Train | 21,854 | 45.84% | `data/raw/devign_train.jsonl` | `e456e20da10aa9a30df406d78dcf5f15f91da8c49fd5028584ca248b03f13f35` |
| **Devign** | Raw Validation | 2,732 | 43.45% | `data/raw/devign_validation.jsonl` | `7318bc4aab8fecdac3ce1afe51c7833714be1b807c5437ab2c7dc0384a6543e0` |
| **Devign** | Raw Test | 2,732 | 45.94% | `data/raw/devign_test.jsonl` | `7f77094d9328624036cbd43ab1281aaf0c3378e220d5b3a10ba0a98922ab39c6` |
| **Devign** | Clean Donors Bank | 21,711 | 45.91% | `data/manifests/devign_donor_clean.jsonl` | `5eda46695ea98091168c2a87591010b4fe6c08597a376c3361b4cf40297d1dfe` |
| **Devign** | **Manifest Concatenation** | - | - | `data/manifests/devign_manifest_stats.json` | **`5a084a10e5c191039e56e351bf8d722fe017424f159a84d6b92be86a1d0f4952`** |
| **Devign** | Val Subset 600 (Seed 42) | 600 | 43.50% | `data/specs/devign_val_subset600.jsonl` | `88f749c000a7b110ed87641d9d5dc4bc912b9f2fdb3dcc2a97753238a4dbcdfd` |
| **Devign** | Test Specs | 2,732 | 45.94% | `data/specs/devign_test.jsonl` | `bd0f4d025afd051c064ab58c1495a887c5851b6408e2d47d39ae64d421b898c6` |
| **ReVeal** | Raw Train | 18,187 | 9.90% | `data/raw/reveal_train.jsonl` | `87c6ec979d8724d1db25217ae6c5637fedaca5350fc954baab4c615efc56f66c` |
| **ReVeal** | Raw Validation | 2,273 | 9.24% | `data/raw/reveal_validation.jsonl` | `03ccd535ecc5c85601377d1880f05307d20577e195cc8808d2c5cbd880725d50` |
| **ReVeal** | Raw Test | 2,274 | 10.11% | `data/raw/reveal_test.jsonl` | `5132c4a2cab7cea81435b5039af964cab184e6ce7b4d9e2df524962b0f6d45f3` |
| **ReVeal** | Clean Donors Bank | 17,620 | 9.57% | `data/manifests/reveal_donor_clean.jsonl` | `9e891cf5b8dfa93c2c3d9d5039e328c5d36c115d173051c5991fc0939e1d372d` |
| **ReVeal** | **Manifest Concatenation** | - | - | `data/manifests/reveal_manifest_stats.json` | **`59498c4a4ab038babe558675c183c2b104b0145590fb0accf8b02cd5440d57f7`** |
| **ReVeal** | Val Subset 600 (Seed 42) | 600 | 9.17% | `data/specs/reveal_val_subset600.jsonl` | `72ce24b2629588a7edf5206c99b26865b630a489580a6b03964c368fad79858e` |
| **ReVeal** | Test Specs | 2,274 | 10.11% | `data/specs/reveal_test.jsonl` | `26d79cec7a31e45a99cf8f22266aa793f323eacb6328cf8d5bd2fc1b34131deb` |

### 7.2. Checkpoint Mô Hình & Môi Trường Suy Luận (Provenance Chuẩn Hóa)

- **Primary Architecture:** `Qwen/Qwen3-Coder-30B-A3B-Instruct` (MoE: 30.5B total params, 3.3B active params per token, 48 layers, 48 routed experts, 8 routed per token).
- **Target Serving Backend:** `llama-server` (llama.cpp b3920) với GGUF Quantization UD-Q4_K_XL (`Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf`, kích thước 16.45 GB) trên Kaggle Linux GPU 2× Tesla T4 (0 USD, split-mode: layer, CUDA0: 8.48 GB, CUDA1: 8.18 GB).
- **Serving Parameters:** `--n_ctx 8192`, `--ctx-size 8192`, `--n_batch 2048`, `--n_ubatch 512`, `--split-mode layer`, `--parallel 1`, Flash-Attention kích hoạt.
- **Kaggle Model Dataset Slug:** `tnthnhneee/qwen3-30b-a3b/gguf/coder-instruct-ud-q4_k_xl`.
- **API Interface:** OpenAI-compatible REST API `/v1/chat/completions` qua Cloudflare HTTPS Tunnel.
- **Decoding Hyperparameters:** `temperature = 0.0`, `max_tokens = 1`, `logprobs = true`, `top_logprobs = 5`, `seed = 42`.
- **Loại bỏ triệt để tồn dư:** Loại bỏ hoàn toàn mọi vết sót cũ về các dòng mô hình không chính thức hoặc cấu hình lượng tử hóa cũ trong toàn bộ tài liệu đăng ký và quy trình thực nghiệm.
- **Fallback Backend:** vLLM (FP8/bf16 trên GPU thuê) hoặc các dòng Qwen2.5-Coder (32B / 14B).

---

## 8. Checklist Nghiệm Thu Đăng Ký Trước (Phụ Lục C - Proposal)

- [x] **Bước 0:** Metric lịch sử tạo lại từ file từng mẫu (sai khác $\le 0.001$); bảng sửa–hỏng có hàng ALL-0 / ALL-1 / RANDOM; paired bootstrap 5,000 reps; cluster unit resolved: Devign (2,068 commit groups), ReVeal (646 file hash groups); StratifiedGroupKFold OOF; Paired Bootstrap CI cho Routing q=10% (Benefit vs Confidence).
- [x] **Smoke Test Backend:** $\ge 99\%$ prompt có token 0/1 trong top-5 logprob ($100\%$ đạt được); hai lần chạy trùng $\ge 98\%$ ($100\%$ trùng); thông lượng và độ trễ đã đo; fail-fast 0 retry khi context exceeded.
- [x] **Manifest Dữ Liệu:** Đã băm SHA-256 đóng băng; một kiểm toán trùng lặp duy nhất (loại 18 ca Devign, 129 ca ReVeal); kho donor đã khử trùng (21,711 Devign, 17,620 ReVeal).
- [x] **Kiểm Thử & Prompt Audit:** 669/669 tests xanh (100%); prompt audit: rò rỉ nhãn $= 0$, demo rỗng $\le 1\%$ ($0.0\%$ trên Devign, $0.7\%$ trên ReVeal); đồ thị thiếu được gắn cờ; 30 prompt mỗi dataset đã sẵn sàng trong `manual_sample.jsonl`.
- [x] **Giao Thức Nghiên Cứu:** `protocol.yaml` điền đủ; `preregistration.md` hoàn thiện gắn tag `prereg-v1` trước lượt test đầu tiên.
- [x] **Khóa Ngưỡng Bước 5:** 14/14 ngưỡng tối ưu $\tau^*$ của mọi arm chọn trên validation, ghi trong `thresholds.json` và `thresholds_flat.json` trước khi chạy test; rào chắn cấm chạy test nếu chưa có file ngưỡng.
- [x] **Schema Thực Thi B.2:** Mọi run test có `records.jsonl` đủ schema B.2 và `manifest.json` môi trường; cache theo identity đầy đủ; candidate-score validity và raw verdict validity được tách biệt minh bạch.
- [x] **Mô Hình Meta & Routing Bước 6:** SUP-LR/SUP-MLP/SUP-METRIC 3 seed; P_pre/P_post cùng fold StratifiedGroupKFold và fallback đối xứng; routing với random 20 seed, trần oracle và paired bootstrap CI tại q=10%.
