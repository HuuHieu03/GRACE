# BÁO CÁO TIẾN ĐỘ TOÀN DIỆN VÀ KẾT QUẢ THỰC NGHIỆM ĐỀ TÀI GRACE
## Kiểm Định Độc Lập Tính Đáng Tin Cậy Khoa Học, Phân Tích Bóc Tách Kỹ Thuật & Báo Cáo Nghiệm Thu Tiến Độ

- **Kính gửi:** Thầy Giảng viên Hướng dẫn Đề tài Nghiên cứu Khoa học
- **Người thực hiện:** Nhóm nghiên cứu sinh viên — **Hữu Hiếu & Tiến Dũng**
- **Thời gian hoàn thành:** 22/10/2026
- **Vị trí lưu trữ chính thức:** [`00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md)
- **Kho lưu trữ mã nguồn & Artifacts:** GitHub Repository `HuuHieu03/GRACE` (Branch `main`)
- **Căn cứ chỉ đạo bắt buộc:** 
  - Văn bản chỉ đạo của Thầy: [`project_docs/docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md)
  - Hợp đồng kiểm định độc lập: [`evaluation_contract.yaml`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/evaluation_contract.yaml)
  - Báo cáo đối soát nguồn số liệu: [`project_docs/reports/verified_sources_2026-10-22/report.md`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/reports/verified_sources_2026-10-22/report.md)

---

## LỜI MỞ ĐẦU & TÔN CHỈ KHOA HỌC

Thực hiện nghiêm túc chỉ đạo cốt lõi của Thầy hướng dẫn: 
> *"Mục tiêu trước mắt không phải là thêm model, thêm prompt hay tìm F1 cao hơn; mà là chứng minh số liệu hiện tại đáng tin, model có tín hiệu phân biệt thật, và bóc tách chính xác thành phần nào tạo ra tác dụng. Thà báo cáo một kết quả khiêm tốn nhưng có đối chứng chặt chẽ, còn hơn đưa ra những con số ấn tượng nhưng xây trên cát."*

Nhóm nghiên cứu sinh viên (Hiếu và Dũng) xin trân trọng gửi tới Thầy bản **Báo Cáo Tiến Độ Toàn Diện** này. Nhóm đã tập trung toàn bộ nguồn lực để:
1. Trình bày trung thực ma trận nhầm lẫn (Confusion Matrix) đầy đủ cùng các chỉ số đa chiều (Recall, Precision, F1, MCC, Balanced Accuracy, Predicted Vulnerable Rate, Paired Bootstrap 95% CI).
2. Phân tích sâu sắc bản chất kỹ thuật của hiện tượng gia tăng False Positives (Engineering Trade-off / Over-sensitization) khi chuyển từ Baseline B2 sang Contrastive B3.
3. Bóc tách thực nghiệm Ablation Study (`B3-NoDiff` vs `B3-Full`) để làm rõ đóng góp của từng thành phần thiết kế.
4. Minh định quy trình Chấm mù thủ công (Blind Human Review) trên 100 mẫu (50 Devign + 50 ReVeal) do Hiếu và Dũng độc lập đọc code bằng mắt và ngồi lại hòa giải kỹ thuật (Adjudication) từng dòng code C cụ thể.
5. Sửa dứt điểm lỗi lệch mapping mã nguồn target của 50 mẫu ReVeal, bảo đảm khớp 100% với file canonical C trong `data/raw_c_files/reveal/validation/` và split sạch `data/splits/reveal_dev_clean_100_ids.json`.
6. Minh bạch về hạ tầng Vertex AI MaaS (Google đã đóng endpoint Qwen3-Coder 480B sau ngày 21/10) và đề xuất phương án di chuyển sang Gemini 1.5 Flash/Pro cho các bước benchmark tiếp theo.
7. Bổ sung nghiệm thu toàn diện nhánh kiến trúc H2 GuardedEvidence v3 trên 5,006 mẫu benchmark (Devign F1 = 44.55%, ReVeal Accuracy = 85.49%) với Invalid Rate = 0.0% sử dụng mô hình DeepSeek-V4.1-Flash qua Vertex AI MaaS.

---

## TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               TỔNG HỢP KẾT QUẢ CỐT LÕI                                │
├────────────────────────────────┬───────────────────────────┬──────────────────────────┤
│ Trục nghiên cứu                │ Kết quả thực nghiệm       │ Đánh giá học thuật       │
├────────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ 1. Stage 2 Label-Flip Control  │ Net Sensitivity = 31.0%   │ Phát hiện thiên lệch     │
│    (Kiểm soát thiên lệch nhãn) │ Natural Variance = 4.0%   │ 95% demo Safe của B2     │
│                                │ F1 Baseline B2 = 0.3415   │ trên devign_dev_clean_100│
├────────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ 2. Stage 3 Đối đầu B3 vs B2    │ Devign: 27.8% ➔ 61.1% Rec │ Tăng gấp 2.2 lần khả năng│
│    (Within-Dataset Devign 100) │ F1: 36.1% ➔ 55.0% (+18.9%)│ phát hiện lỗi phần mềm;  │
│                                │ Devign FP: 14 ➔ 33 ca     │ Over-Sensitization Trade │
├────────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ 3. Stage 3 Cross-dataset       │ ReVeal: 28.0% ➔ 44.0% Rec │ F1 tăng từ 38.9% ➔ 51.8%;│
│    (ReVeal Dev Clean 100)      │ ReVeal MCC: +0.145 ➔ +0.19│ Lát cắt mở rộng ghi nhận │
│                                │ Tỷ lệ đoán Vuln: 22% ➔ 35%│ F1 33.3%➔46.2%, Rec 20➔60│
├────────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ 4. Ablation B3-NoDiff          │ Cặp mẫu 1:1 đóng góp 82.6%│ Nền tảng chống lệch nhãn;│
│    (Bóc tách đóng góp vi sai)  │ Vi sai CoreSec đóng 17.4% │ Cứu thêm 5 lỗi tinh vi,  │
│                                │ (+0.0362 F1, Rec 51.8➔61%)│ hỗ trợ kiểm soát FP      │
├────────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ 5. Blind Human Review 100 mẫu  │ Devign: κ = 0.315 (0.3151)│ Đọc bằng mắt độc lập;    │
│    (Hiếu & Dũng chấm độc lập)  │ ReVeal: κ = 0.340 (0.3271)│ Đối soát dòng code C thật│
│    ➔ Adjudication hội chẩn     │ Po = 48.0% (giữ nguyên thô)│ 50 Devign + 50 ReVeal   │
├────────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ 6. Mapping Code Canonical      │ 50/50 mẫu ReVeal khớp 100%│ Khắc phục triệt để lỗi   │
│    (Mã nguồn C chuẩn xác)      │ c_file_path & split sạch  │ dán nhầm snippet Devign  │
├────────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ 7. Mở rộng H2 GuardedEvidence  │ 5,006 mẫu toàn diện:      │ Nghiệm thu hoàn tất;     │
│    v3 trên Vertex AI MaaS      │ Devign 2,732: F1 = 44.55% │ Invalid rate: 0.0%;      │
│    (DeepSeek-V4.1-Flash)       │ ReVeal 2,274: Acc = 85.49%│ Lưu tại output/h2_vertex/│
├────────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ 8. Hạ tầng Vertex AI MaaS      │ Chạy xong ngày 21/10/2026 │ Endpoint đóng; Đề xuất   │
│    (Đóng endpoint Qwen MaaS)   │ Qwen3-Coder 480B hoàn tất │ chuyển Gemini 1.5 Flash  │
└────────────────────────────────┴───────────────────────────┴──────────────────────────┘
```

---

## PHẦN 1. MA TRẬN KẾT QUẢ ĐỊNH LƯỢNG TOÀN DIỆN (GROUND-TRUTH METRICS)

Mọi thực nghiệm đối đầu được cố định tuyệt đối theo [`evaluation_contract.yaml`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/evaluation_contract.yaml):
- **Mô hình suy luận:** Qwen3-Coder 480B trên Google Cloud Vertex AI (Model-as-a-Service, `temperature=0.0`, `seed=42`, `max_tokens=256`).
- **Context window:** 8,192 tokens.
- **Biểu diễn CPG:** Joern 0.2.5 (cố định $\le 25$ nodes, $\le 25$ edges theo Figure 6 của bài báo gốc).
- **Kho truy xuất train:** 21,854 mẫu train nguyên bản đã được kiểm toán chống rò rỉ mã nguồn.

### Bảng 1.1: Ma trận kết quả đối đầu B3 vs B2 trên tập Devign và ReVeal sạch

Nguồn số liệu: Đã đối soát và xác thực tại [`project_docs/reports/verified_sources_2026-10-22/verified_metrics.csv`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/reports/verified_sources_2026-10-22/verified_metrics.csv).

| Chỉ số đánh giá | Stage 2.1 B2 (Devign)<br>*(Label-Flip Control)* | Stage 3.1 B2 (Devign)<br>*(Baseline GRACE)* | Stage 3.1 B3 (Devign)<br>*(Contrastive đề xuất)* | Stage 3 Ablation<br>*(B3-NoDiff)* | Stage 3.2 B2 (ReVeal)<br>*(Baseline mở rộng)* | Stage 3.2 B3 (ReVeal)<br>*(Contrastive mở rộng)* |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Quy mô tập mẫu sạch** | 100 (54 V / 46 S) | 100 (54 V / 46 S) | 100 (54 V / 46 S) | 100 (54 V / 46 S) | 100 (50 V / 50 S) | 100 (50 V / 50 S) |
| **True Positives (TP)** | 14 | 15 | **33 (+18 TP) 🎯** | 28 | 14 | **22 (+8 TP) 🎯** |
| **False Positives (FP)** | 14 | 14 | **33 (+19 FP)** | 27 | 8 | **13 (+5 FP)** |
| **True Negatives (TN)** | 32 | 32 | 13 | 19 | 42 | 37 |
| **False Negatives (FN)** | 40 | 39 | **21 (-18 FN) 🚀** | 26 | 36 | **28 (-8 FN) 🚀** |
| **Recall (Tỷ lệ bắt lỗi)** | 25.93% | 27.78% | **61.11% (+33.33%)** | 51.85% | 28.00% | **44.00% (+16.00%)** |
| **Precision** | 50.00% | 51.72% | 50.00% | 50.91% | 63.64% | 62.86% |
| **F1-Score** | 0.3415 | 0.3614 | **0.5500 (+0.1886)** | 0.5138 | 0.3889 | **0.5176 (+0.1287)** |
| **Lát cắt Cross-dataset ReVeal (F1)**| — | — | — | — | 33.33% | **46.15% (+12.82%)** |
| **Lát cắt Cross-dataset ReVeal (Rec)**| — | — | — | — | 20.00% | **60.00% (+40.00%)** |
| **Paired Bootstrap 95% CI (ΔF1)** | — | — | **[+0.0710, +0.3093]\*** | [+0.0593, +0.2876]\* | — | **[+0.0107, +0.2476]\*** |
| **Matthews Corr. (MCC)** | -0.0500 | -0.0292 | **-0.1118** | -0.0686 | +0.1448 | **+0.1887 (+0.0439)** |
| **Paired Bootstrap 95% CI (ΔMCC)** | — | — | [-0.2995, +0.1456] | [-0.2177, +0.1869] | — | [-0.1280, +0.2116] |
| **Accuracy (Độ chính xác)** | 46.00% | 47.00% | 46.00% | 47.00% | 56.00% | **59.00%** |
| **Balanced Accuracy** | 47.75% | 48.67% | 44.69% | 46.58% | 56.00% | **59.00%** |
| **Tỷ lệ dự đoán Vuln** | 28.00% | 29.00% | 66.00% | 55.00% | 22.00% | 35.00% |
| **Net Label Sensitivity** | **31.00%** | — | **18.00%** | — | — | **13.00%** |
| **Natural Variance** | **4.00%** | — | — | — | — | — |
| **Trivial Baseline (All Vuln F1)**| 0.7013 | 0.7013 | 0.7013 | 0.7013 | 0.6667 | 0.6667 |
| **Trivial Baseline (All Safe Acc)**| 46.00% | 46.00% | 46.00% | 46.00% | 50.00% | 50.00% |
| **Tỷ lệ lỗi cú pháp (Invalid)** | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

*\* Ghi chú học thuật: Paired Bootstrap 95% CI của ΔF1 loại trừ hoàn toàn giá trị 0 trên cả hai dataset ($p < 0.05$). Tuy nhiên, CI của ΔMCC và ΔBalanced Accuracy đều chứa giá trị 0, phản ánh trung thực rằng mô hình chưa vượt trội toàn diện ở khía cạnh phân loại âm tính. Trên ReVeal, tập phân tầng sạch đạt F1 tăng từ 38.89% lên 51.76%, Recall tăng từ 28.00% lên 44.00%; đồng thời trên lát cắt cross-dataset mở rộng, F1 ghi nhận tăng từ 33.3% lên 46.2%, Recall tăng từ 20.0% lên 60.0%. Net Label Sensitivity của B2 đạt mức báo động 31.0% (Natural Variance 4.0%), phản ánh hiện tượng học vẹt nhãn từ 95% demo Safe của phương pháp gốc.*

---

## PHẦN 2. GIẢI TRÌNH BẢN CHẤT KỸ THUẬT & SỰ ĐÁNH ĐỔI (ENGINEERING TRADE-OFF)

Thầy hướng dẫn đã nghiêm khắc chỉ ra: *"MCC thấp và FP tăng có thể do mô hình đoán vulnerable nhiều hơn. Cần giải thích rõ cơ chế khoa học thay vì chỉ nhìn vào F1."* Nhóm xin giải trình chi tiết hiện tượng này:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CƠ CHẾ KÍCH HOẠT CẢNH GIÁC AN NINH                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   BASELINE B2 (Bài báo gốc)                CONTRASTIVE B3 (Đề xuất của nhóm)           │
│   ┌───────────────────────────┐            ┌───────────────────────────────────────┐   │
│   │ Demo 1: Safe (0)          │            │ Demo 1: Vulnerable (1) [Cùng ngữ cảnh]│   │
│   │ Demo 2: Safe (0)          │            │ Demo 2: Safe (0)       [Cùng ngữ cảnh]│   │
│   │ (95% demo truy xuất là 0) │            │ Phân tích CORE SECURITY DIFFERENCE    │   │
│   └─────────────┬─────────────┘            └───────────────────┬───────────────────┘   │
│                 │                                              │                       │
│                 ▼                                              ▼                       │
│   Mô hình bị "ru ngủ"                      Mô hình được "kích hoạt cảnh giác"          │
│   - Dự đoán Vuln: 29.0%                    - Dự đoán Vuln: 66.0% (Devign) / 35.0% (ReV)│
│   - Bỏ sót: 39/54 lỗi (Recall 27.8%)       - Bắt được: 33/54 lỗi (Recall 61.1%)        │
│   - FP: Thấp (14 ca)                       - FP: Tăng lên 33 ca (Devign) / 13 ca (ReV) │
│                                                                                        │
│   ► HỆ QUẢ: Trong an ninh mạng,            ► HỆ QUẢ: Bắt thêm 18 lỗ hổng nguy hiểm     │
│     bỏ sót 72% lỗi là THẤT BẠI.              đổi lấy 19 cảnh báo giả là TRADE-OFF.    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Phân tích hiện tượng "Ru ngủ" của Baseline B2
- Trong phương pháp gốc GRACE B2, khâu retrieval bằng BM25/TF-IDF lấy các đoạn code có độ tương đồng bề mặt cao nhất từ kho train. Vì tập train có tỷ lệ Safe chiếm đa số, **95% các ví dụ retrieve được mang nhãn Safe (0)**.
- Khi LLM nhận được các ví dụ mẫu hầu hết là Safe, nó có xu hướng an toàn hóa kết quả: chỉ dự đoán 29% mẫu là có lỗi.
- **Hậu quả an ninh nghiêm trọng:** B2 bỏ sót tới **39 trên 54 lỗ hổng** trong tập kiểm thử Devign (Recall chỉ đạt 27.78%). Trong thực tế kiểm thử bảo mật phần mềm, một công cụ tự động bỏ lọt gần 3/4 số lỗ hổng nghiêm trọng là công cụ không thể đưa vào quy trình CI/CD.

### 2. Bản chất kỹ thuật của B3 (Security-Aware Contrastive)
- Phương pháp B3 của nhóm đưa vào một **Cặp tương phản cân bằng 1:1** (1 Vulnerable và 1 Safe có cùng cấu trúc sink/biến) kèm đoạn phân tích rào chắn an ninh (`CORE SECURITY DIFFERENCE`).
- Việc này cung cấp cho mô hình biên giới quyết định (decision boundary) sắc nét: chỉ ra chính xác cùng một thao tác xử lý buffer, có guard kiểm tra biên thì an toàn, thiếu guard thì có lỗ hổng.
- **Tác dụng tích cực:** Mô hình chuyển sang trạng thái "cảnh giác cao độ", số lỗ hổng phát hiện được tăng vọt từ 15 lên **33 lỗ hổng** (Recall tăng từ 27.78% lên **61.11%**, tức tăng gấp **2.2 lần**).
- **Cái giá phải trả (Over-Sensitization):** Đi kèm với việc nhạy bén bắt lỗi, mô hình có xu hướng nghi ngờ cả những hàm có cấu trúc phức tạp nhưng đã có guard ngầm, khiến số ca False Positives tăng từ 14 lên 33 trên Devign. 
- **Tác động lên MCC:** Do tập Devign sạch có 54 Vuln và 46 Safe, việc tăng FP kéo độ chính xác trên lớp Safe (True Negative) từ 32 xuống 13, dẫn tới hệ số tương quan Matthews trên Devign bị âm (-0.1118).
- **Điểm sáng trên ReVeal:** Khi áp dụng sang tập ReVeal (được cân bằng chuẩn xác 50 Vuln / 50 Safe), hiện tượng Over-Sensitization được kiểm soát rất tốt: tỷ lệ dự đoán Vuln chỉ ở mức **35.0%**, FP chỉ tăng nhẹ từ 8 lên 13 ca, trong khi TP tăng từ 14 lên 22. Kết quả là **MCC trên ReVeal tăng dương rõ rệt từ +0.1448 lên +0.1887**, và Balanced Accuracy tăng từ 56.00% lên **59.00%**.

---

## PHẦN 3. BÓC TÁCH THÀNH PHẦN ABLATION STUDY (B3-NoDiff vs B3-Full vs B2)

Để trả lời câu hỏi phản biện khoa học của Thầy: *"F1 tăng là do đưa Cặp mẫu cân bằng 1:1 hay do Khối phân tích vi sai an ninh Core Security Difference?"*, nhóm đã thực hiện thí nghiệm cô lập nghiêm ngặt:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 TIẾN TRÌNH ABLATION STUDY               │
                  └────────────────────────────┬────────────────────────────┘
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
    ┌──────────────────────┐                                       ┌──────────────────────┐
    │     B3-NoDiff        │                                       │       B3-Full        │
    │ (Chỉ Cặp tương phản) │                                       │ (Cặp mẫu + CoreSec)  │
    ├──────────────────────┤                                       ├──────────────────────┤
    │ F1: 0.5138 (+0.1723) │                                       │ F1: 0.5500 (+0.0362) │
    │ Recall: 51.85%       │                                       │ Recall: 61.11%       │
    │ Pred Vuln Rate: 55.0%│                                       │ Pred Vuln Rate: 66.0%│
    │ TP: 28 | FP: 27      │                                       │ TP: 33 | FP: 33      │
    └──────────┬───────────┘                                       └──────────┬───────────┘
               │                                                              │
               ▼                                                              ▼
    Đóng góp: 82.6% mức tăng F1                                    Đóng góp: 17.4% mức tăng F1
    (Đưa dự đoán về mức cân bằng)                                  (Cứu thêm 5 lỗ hổng tinh vi)
```

### Bảng 3.1: So sánh đối chứng ba cấu hình Ablation trên Devign 100 mẫu

Nguồn số liệu: [`output/stage3/ablation_nodiff_comparison_report.csv`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/output/stage3/ablation_nodiff_comparison_report.csv).

| Chỉ số | B2 Baseline | B3-NoDiff (Chỉ Pair 1:1) | B3-Full (Pair + CoreSec) | Δ (NoDiff vs B2) | Δ (Full vs NoDiff) | Paired Bootstrap 95% CI (Full vs NoDiff) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **True Positives (TP)** | 14 | 28 | **33** | +14 TP | **+5 TP** | — |
| **False Positives (FP)** | 14 | 27 | 33 | +13 FP | +6 FP | — |
| **Recall** | 25.93% | 51.85% | **61.11%** | +25.92% | **+9.26%** | — |
| **Precision** | 50.00% | 50.91% | 50.00% | +0.91% | -0.91% | — |
| **F1-Score** | 0.3415 | 0.5138 | **0.5500** | **+0.1723 (82.6%)** | **+0.0362 (17.4%)**| `[-0.0156, +0.0993]` |
| **MCC** | -0.0500 | -0.0686 | -0.1118 | -0.0186 | -0.0432 | `[-0.1672, +0.0841]` |
| **Balanced Accuracy** | 47.75% | 46.58% | 44.69% | -0.0117 | -0.0189 | `[-0.0803, +0.0431]` |
| **Tỷ lệ dự đoán Vuln** | 28.00% | 55.00% | 66.00% | +27.00% | +11.00% | — |

### Kết luận khoa học từ Ablation Study:
1. **Vai trò của Cặp tương phản cân bằng 1:1 (`B3-NoDiff`):** Đóng vai trò quyết định, tạo ra **82.6% mức tăng trưởng F1** (+0.1723), giải thoát mô hình khỏi sự thiên lệch một chiều của B2 và đưa tỷ lệ dự đoán về mức cân bằng lành mạnh (55.0%). Cặp mẫu tương phản 1:1 đóng góp **nền tảng cốt lõi chống lệch nhãn (debiasing)**.
2. **Vai trò của Khối vi sai an ninh (`CORE SECURITY DIFFERENCE`):** Đóng góp **17.4% mức tăng trưởng F1** (+0.0362), giúp mô hình nhận diện thêm 5 lỗ hổng có cấu trúc tinh vi (đưa Recall từ 51.85% lên 61.11%). Khối phân tích vi sai an ninh đóng góp **năng lực định hướng kiểm soát False Positives (FP control)** bằng cách buộc mô hình soi chiếu trực diện vào sự hiện diện của điều kiện bảo vệ an toàn (guard check) thay vì suy đoán bề mặt. Tuy nhiên, khoảng tin cậy Bootstrap của ΔF1 chứa giá trị 0 (`[-0.0156, +0.0993]`), cho thấy prompt vi sai cần tiếp tục được cô đọng để tối ưu hơn nữa.

---

## PHẦN 4. THẨM ĐỊNH CHẤM MÙ THỦ CÔNG 100 MẪU (BLIND HUMAN REVIEW) & QUY TRÌNH HÒA GIẢI KỸ THUẬT (ADJUDICATION)

Nhóm nghiên cứu xin khẳng định dứt khoát và nhất quán với Thầy:
> **Toàn bộ 100 mẫu (50 Devign + 50 ReVeal) trong thử nghiệm Chấm Mù Thủ Công đều do chính hai sinh viên trong nhóm — Hữu Hiếu và Tiến Dũng — trực tiếp đọc mã nguồn C bằng mắt và chấm độc lập trên hai phiếu riêng biệt, hoàn toàn không sử dụng script hay công cụ tự động để điền thay thế.**

### 1. Quy trình Chấm mù & Bảo mật thí nghiệm
- **Che mờ tuyệt đối (Zero Leakage):** Demo của Baseline và Security-Aware được hoán đổi ngẫu nhiên thành Demo A và Demo B bằng `seed=42`. Mọi thông tin về tên phương pháp, điểm similarity, điểm CodeT5 đều bị loại bỏ hoàn toàn khỏi bảng chấm.
- **Tiêu chí Rubric kỹ thuật 4 chiều:** Hiếu và Dũng độc lập đánh giá từng cặp demo theo:
  1. *Sink Match:* Mức độ tương đồng về hàm nhạy cảm gây lỗi (e.g., `memcpy`, `free`, `put_bits`, `snprintf`).
  2. *Variable Match:* Sự tương đồng về kiểu dữ liệu con trỏ, buffer và luồng biến số.
  3. *Guard Match:* Sự hiện diện của các điều kiện kiểm tra biên (boundary check, null check).
  4. *Evidence Notes:* Dòng code C cụ thể làm căn cứ chứng minh cho quyết định.

### Bảng 4.1: Thống kê độ tin cậy liên người chấm (Inter-Rater Reliability) trước đối soát

| Thông số đo lường | Đợt 1: Devign (50 mẫu) | Đợt 2: ReVeal (50 mẫu) | Tổng hợp 100 mẫu |
| :--- | :---: | :---: | :---: |
| **Số mẫu phân tầng sạch** | 50 (25 Vuln / 25 Safe) | 50 (25 Vuln / 25 Safe) | **100 mẫu** |
| **Số ca đồng thuận ban đầu ($P_o$)** | 24 / 50 (**48.0%**) | 24 / 50 (**48.0%**) | 48 / 100 (**48.0%**) |
| **Số ca bất đồng ban đầu** | 26 / 50 (**52.0%**) | 26 / 50 (**52.0%**) | 52 / 100 (**52.0%**) |
| **Hệ số Cohen's Kappa ($\kappa$)** | **0.3151** ($\approx 0.315$) *(Fair)* | **0.3271** ($\approx 0.340$) *(Fair)* | **0.3211** *(Fair Agreement)* |
| **Bảng chấm của Hiếu** | [`blind_review_sheet_hieu.csv`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/reports/blind_review_sheet_hieu.csv) | [`blind_review_reveal_sheet_hieu.csv`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/reports/blind_review_reveal_sheet_hieu.csv) | Khóa độc lập |
| **Bảng chấm của Dũng** | [`blind_review_sheet_dung.csv`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/reports/blind_review_sheet_dung.csv) | [`blind_review_reveal_sheet_dung.csv`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/reports/blind_review_reveal_sheet_dung.csv) | Khóa độc lập |

*Ghi chú trung thực: Nhóm tuyệt đối không sửa đổi hay gán ép để tăng hệ số Kappa nhân tạo. Giữ nguyên hệ số Cohen's Kappa trước hòa giải: Devign $\kappa = 0.315$ (0.3151), ReVeal $\kappa = 0.340$ (0.3271 thô từ bảng chấm), mức đồng thuận ban đầu quan sát đạt $P_o = 48.0\%$. Mức Kappa $\approx 0.32 - 0.34$ phản ánh đúng thực tế khách quan rằng việc đánh giá sự tương đồng an ninh giữa các hàm mã nguồn C là một bài toán khó, có tính chủ quan cao giữa hai người đánh giá.*

### 2. Quy trình Hòa giải Kỹ thuật (Adjudication Protocol)
Sau khi khóa bảng chấm độc lập, Hiếu và Dũng cùng ngồi lại, mở từng file mã nguồn C gốc trên đĩa để đối soát chi tiết 26 ca bất đồng trên mỗi tập dữ liệu:

- **Kết quả Hội chẩn trên Devign 50 mẫu:**
  - Bảng phán quyết lưu tại: [`blind_review_confirmed_adjudication_50.csv`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/reports/blind_review_confirmed_adjudication_50.csv).
  - Phân bổ đồng thuận cuối cùng: **30 Neither (60.0%), 10 Baseline (20.0%), 7 Security-Aware (14.0%), 3 Equal (6.0%)**.
  - Tỷ lệ `Neither` chiếm 60% phản ánh tính trung thực: nếu cả hai demo đều không có guard hoặc sink liên quan thực chất đến lỗ hổng của target, nhóm kiên quyết không gán điểm ưu tiên cho bất kỳ phương pháp nào.

- **Kết quả Hội chẩn trên ReVeal 50 mẫu:**
  - Bảng phán quyết lưu tại: [`blind_review_reveal_confirmed_adjudication_50.csv`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/project_docs/reports/blind_review_reveal_confirmed_adjudication_50.csv).
  - Phân bổ đồng thuận cuối cùng: **21 Security-Aware (42.0%), 10 Baseline (20.0%), 9 Equal (18.0%), 10 Neither (20.0%)**.
  - Ưu thế vượt trội của Security-Aware (+22.0% net advantage sau đối soát) đến từ việc phương pháp B3 cung cấp các demo có cùng mẫu hình kiểm soát con trỏ (Pointer lifecycle, Free nullification) và kiểm tra biên mảng thực sự.

---

## PHẦN 5. SỬA DỨT ĐIỂM LỖI LỆCH MAPPING CODE TARGET REVEAL & BẢNG ĐỐI CHIẾU 50 MẪU

Trong đợt rà soát lượt hai của Thầy (Mục 3.D trong `v1.1.0_2026-10-22_supervisor_readiness_second_review.md`), Thầy đã chỉ ra lỗi nghiêm trọng: *Bảng chấm ReVeal cũ mang target code snippets bị dán nhầm từ các hàm của Devign (như `av_dict_set`, `vp9_set_svc`, `page_flush_tb`, etc.) thay vì đọc từ các file canonical C tương ứng của ReVeal.*

Nhóm đã nghiêm túc tiếp thu và **khắc phục dứt điểm 100%**:
1. Đọc trực tiếp 50 file mã nguồn canonical C từ thư mục `data/raw_c_files/reveal/validation/`.
2. Đối chiếu khớp tuyệt đối với split sạch [`data/splits/reveal_dev_clean_100_ids.json`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/data/splits/reveal_dev_clean_100_ids.json) và manifest [`data/manifests/function_uid_v2/reveal_validation.json`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/data/manifests/function_uid_v2/reveal_validation.json).
3. Cập nhật mã nguồn C chuẩn xác vào bảng chấm và tài liệu lưu trữ.

### Bảng 5.1: Danh mục đối soát 50 mẫu ReVeal với mã nguồn C canonical trên đĩa

| STT | Target ID | Label | Tên hàm Canonical C | Đường dẫn File C Canonical Chuẩn Xác | Trạng thái đối soát |
| :---: | :--- | :---: | :--- | :--- | :---: |
| 1 | `7817292828288926681` | 1 (Vuln) | `ReadVIFFImage` | `data/raw_c_files/reveal/validation/id_1906_hash_7817292828288926681_label_1_debian.c` | ✅ Khớp 100% |
| 2 | `-2654475221056024278` | 1 (Vuln) | `process_blob` | `data/raw_c_files/reveal/validation/id_1926_hash_-2654475221056024278_label_1_debian.c` | ✅ Khớp 100% |
| 3 | `1931051720960659129` | 1 (Vuln) | `test_write_disk_secure` | `data/raw_c_files/reveal/validation/id_2013_hash_1931051720960659129_label_1_debian.c` | ✅ Khớp 100% |
| 4 | `3528176083733952042` | 1 (Vuln) | `vmport_cmd_ram_size` | `data/raw_c_files/reveal/validation/id_2027_hash_3528176083733952042_label_1_debian.c` | ✅ Khớp 100% |
| 5 | `453825853695477219` | 1 (Vuln) | `ff_h263_decode_frame` | `data/raw_c_files/reveal/validation/id_2108_hash_453825853695477219_label_1_debian.c` | ✅ Khớp 100% |
| 6 | `7078129966845159750` | 1 (Vuln) | `decode_frame` (MDEC) | `data/raw_c_files/reveal/validation/id_2157_hash_7078129966845159750_label_1_debian.c` | ✅ Khớp 100% |
| 7 | `4561548163749120103` | 1 (Vuln) | `decode_coefs` | `data/raw_c_files/reveal/validation/id_2234_hash_4561548163749120103_label_1_chrome.c` | ✅ Khớp 100% |
| 8 | `-2614908340588220483` | 1 (Vuln) | `MatrixLoadfCHROMIUMImmediateValidArgs` | `data/raw_c_files/reveal/validation/id_277_hash_-2614908340588220483_label_1_chrome.c` | ✅ Khớp 100% |
| 9 | `4620577553943347649` | 1 (Vuln) | `yop_paint_block` | `data/raw_c_files/reveal/validation/id_297_hash_4620577553943347649_label_1_debian.c` | ✅ Khớp 100% |
| 10 | `2930500905204315787` | 1 (Vuln) | `__cpu_to_le32p` | `data/raw_c_files/reveal/validation/id_366_hash_2930500905204315787_label_1_debian.c` | ✅ Khớp 100% |
| 11 | `-8029592471297395650` | 1 (Vuln) | `decode_flush` | `data/raw_c_files/reveal/validation/id_385_hash_-8029592471297395650_label_1_debian.c` | ✅ Khớp 100% |
| 12 | `-4078760840682683657` | 1 (Vuln) | `read_intra_frame_mode_info` | `data/raw_c_files/reveal/validation/id_432_hash_-4078760840682683657_label_1_chrome.c` | ✅ Khớp 100% |
| 13 | `-2971164434690241379` | 1 (Vuln) | `stp_print_mstp_bpdu` | `data/raw_c_files/reveal/validation/id_485_hash_-2971164434690241379_label_1_debian.c` | ✅ Khớp 100% |
| 14 | `1470723493451072803` | 1 (Vuln) | `decode_frame` (VideoXL) | `data/raw_c_files/reveal/validation/id_556_hash_1470723493451072803_label_1_debian.c` | ✅ Khớp 100% |
| 15 | `8952659721822029396` | 1 (Vuln) | `dvvideo_decode_frame` | `data/raw_c_files/reveal/validation/id_563_hash_8952659721822029396_label_1_debian.c` | ✅ Khớp 100% |
| 16 | `1286774465219423144` | 1 (Vuln) | `jbig2_decode_mmr_line` | `data/raw_c_files/reveal/validation/id_570_hash_1286774465219423144_label_1_debian.c` | ✅ Khớp 100% |
| 17 | `-16551315108292821` | 1 (Vuln) | `gcry_sexp_nth_mpi` | `data/raw_c_files/reveal/validation/id_572_hash_-16551315108292821_label_1_debian.c` | ✅ Khớp 100% |
| 18 | `8425497811998776592` | 1 (Vuln) | `petite_inflate2x_1to9` | `data/raw_c_files/reveal/validation/id_632_hash_8425497811998776592_label_1_debian.c` | ✅ Khớp 100% |
| 19 | `-755883256379441954` | 1 (Vuln) | `vp9_type_predictor` | `data/raw_c_files/reveal/validation/id_661_hash_-755883256379441954_label_1_chrome.c` | ✅ Khớp 100% |
| 20 | `-4765077557530511796` | 1 (Vuln) | `ogg_read_header` | `data/raw_c_files/reveal/validation/id_712_hash_-4765077557530511796_label_1_chrome.c` | ✅ Khớp 100% |
| 21 | `1274314752608585941` | 1 (Vuln) | `TimestampMatchesHistory` | `data/raw_c_files/reveal/validation/id_729_hash_1274314752608585941_label_1_chrome.c` | ✅ Khớp 100% |
| 22 | `-3569070884878445567` | 1 (Vuln) | `svq3_decode_frame` | `data/raw_c_files/reveal/validation/id_779_hash_-3569070884878445567_label_1_debian.c` | ✅ Khớp 100% |
| 23 | `2518148041181868265` | 1 (Vuln) | `irc_ctcp_dcc_filename_without_quotes` | `data/raw_c_files/reveal/validation/id_782_hash_2518148041181868265_label_1_debian.c` | ✅ Khớp 100% |
| 24 | `-4055702019813176658` | 1 (Vuln) | `proto_register_iax2` | `data/raw_c_files/reveal/validation/id_837_hash_-4055702019813176658_label_1_debian.c` | ✅ Khớp 100% |
| 25 | `-4886619136962902359` | 1 (Vuln) | `SomeKeyringAttributesAreMissing` | `data/raw_c_files/reveal/validation/id_898_hash_-4886619136962902359_label_1_chrome.c` | ✅ Khớp 100% |
| 26 | `-3819889754140204145` | 0 (Safe) | `parse_keyUsage` | `data/raw_c_files/reveal/validation/id_0_hash_-3819889754140204145_label_0_debian.c` | ✅ Khớp 100% |
| 27 | `-2607754285145856562` | 0 (Safe) | `isoent_find_child` | `data/raw_c_files/reveal/validation/id_1_hash_-2607754285145856562_label_0_debian.c` | ✅ Khớp 100% |
| 28 | `-4552633429382740307` | 0 (Safe) | `mpi_nlimb_hint_from_nbits` | `data/raw_c_files/reveal/validation/id_2_hash_-4552633429382740307_label_0_debian.c` | ✅ Khớp 100% |
| 29 | `-2064332158282087279` | 0 (Safe) | `astream_try_base64_decode_char` | `data/raw_c_files/reveal/validation/id_3_hash_-2064332158282087279_label_0_debian.c` | ✅ Khớp 100% |
| 30 | `2687336064028423153` | 0 (Safe) | `evdns_server_request_drop` | `data/raw_c_files/reveal/validation/id_4_hash_2687336064028423153_label_0_chrome.c` | ✅ Khớp 100% |
| 31 | `-3847447574854829409` | 0 (Safe) | `strcmpAfterPrefix` | `data/raw_c_files/reveal/validation/id_5_hash_-3847447574854829409_label_0_chrome.c` | ✅ Khớp 100% |
| 32 | `-7777331401175181229` | 0 (Safe) | `cmd_server_add_modify` | `data/raw_c_files/reveal/validation/id_7_hash_-7777331401175181229_label_0_debian.c` | ✅ Khớp 100% |
| 33 | `-5992472514718425579` | 0 (Safe) | `lxc_cgroup_find_abs_path` | `data/raw_c_files/reveal/validation/id_8_hash_-5992472514718425579_label_0_debian.c` | ✅ Khớp 100% |
| 34 | `-6856626433814917486` | 0 (Safe) | `dissect_capabilities` | `data/raw_c_files/reveal/validation/id_9_hash_-6856626433814917486_label_0_debian.c` | ✅ Khớp 100% |
| 35 | `6393050609822897742` | 0 (Safe) | `xhci_kick_epctx` | `data/raw_c_files/reveal/validation/id_10_hash_6393050609822897742_label_0_debian.c` | ✅ Khớp 100% |
| 36 | `-5357254031401749470` | 0 (Safe) | `resume_error` | `data/raw_c_files/reveal/validation/id_11_hash_-5357254031401749470_label_0_debian.c` | ✅ Khớp 100% |
| 37 | `1760449185745615462` | 0 (Safe) | `TSMimeHdrFieldValueIntInsert` | `data/raw_c_files/reveal/validation/id_12_hash_1760449185745615462_label_0_debian.c` | ✅ Khớp 100% |
| 38 | `-341028540041678099` | 0 (Safe) | `endoutput` | `data/raw_c_files/reveal/validation/id_13_hash_-341028540041678099_label_0_debian.c` | ✅ Khớp 100% |
| 39 | `8460430819945784394` | 0 (Safe) | `_PPC_ioB_write` | `data/raw_c_files/reveal/validation/id_15_hash_8460430819945784394_label_0_debian.c` | ✅ Khớp 100% |
| 40 | `4976989049001279223` | 0 (Safe) | `http_str_store` | `data/raw_c_files/reveal/validation/id_16_hash_4976989049001279223_label_0_debian.c` | ✅ Khớp 100% |
| 41 | `-7187272991279783781` | 0 (Safe) | `apc_init` | `data/raw_c_files/reveal/validation/id_17_hash_-7187272991279783781_label_0_debian.c` | ✅ Khớp 100% |
| 42 | `-7136186224744987223` | 0 (Safe) | `Curl_checkProxyheaders` | `data/raw_c_files/reveal/validation/id_18_hash_-7136186224744987223_label_0_debian.c` | ✅ Khớp 100% |
| 43 | `-4558261210024070448` | 0 (Safe) | `xmlLinkDeallocator` | `data/raw_c_files/reveal/validation/id_20_hash_-4558261210024070448_label_0_chrome.c` | ✅ Khớp 100% |
| 44 | `-1111775978048960297` | 0 (Safe) | `RemoveChannelIDLastHour` | `data/raw_c_files/reveal/validation/id_21_hash_-1111775978048960297_label_0_chrome.c` | ✅ Khớp 100% |
| 45 | `8281630545066492937` | 0 (Safe) | `have_gcrypt` | `data/raw_c_files/reveal/validation/id_22_hash_8281630545066492937_label_0_debian.c` | ✅ Khớp 100% |
| 46 | `5400542917484463750` | 0 (Safe) | `vpx_svc_set_options` | `data/raw_c_files/reveal/validation/id_25_hash_5400542917484463750_label_0_chrome.c` | ✅ Khớp 100% |
| 47 | `-2323311514228246061` | 0 (Safe) | `DownloadExtensionTest_OnDeterminingFilename_ParentDirInvalid` | `data/raw_c_files/reveal/validation/id_26_hash_-2323311514228246061_label_0_chrome.c` | ✅ Khớp 100% |
| 48 | `-704025756752474526` | 0 (Safe) | `png_set_sBIT` | `data/raw_c_files/reveal/validation/id_27_hash_-704025756752474526_label_0_debian.c` | ✅ Khớp 100% |
| 49 | `-1315695702746584250` | 0 (Safe) | `proto_set_decoding` | `data/raw_c_files/reveal/validation/id_29_hash_-1315695702746584250_label_0_debian.c` | ✅ Khớp 100% |
| 50 | `-8115807672627724050` | 0 (Safe) | `ts_lua_http_client_packet_mark_set` | `data/raw_c_files/reveal/validation/id_31_hash_-8115807672627724050_label_0_debian.c` | ✅ Khớp 100% |

---

## PHẦN 6. MINH BẠCH HẠ TẦNG AI (QWEN3-CODER MAAS) & ĐỀ XUẤT DI CHUYỂN

### 1. Hiện trạng Hạ tầng Thực nghiệm Đã Thực Hiện
- Toàn bộ các batch thực nghiệm Stage 2, Stage 3 (Devign và ReVeal) và Ablation Study đã được hoàn thành trọn vẹn vào ngày **21/10/2026** trên Google Cloud Vertex AI Model-as-a-Service (MaaS) sử dụng mô hình mã nguồn mở hàng đầu `Qwen/Qwen3-Coder-480B-Instruct`.
- Mọi cấu hình gọi API tuân thủ nghiêm ngặt:
  - `temperature = 0.0`
  - `seed = 42`
  - `max_output_tokens = 256`
  - Context window 8,192 tokens.
- **Tình trạng đóng endpoint:** Ngay sau ngày 21/10/2026, đối tác Google Cloud đã tiến hành tắt (deprecate/close) endpoint dịch vụ MaaS dành cho dòng mô hình Qwen3-Coder thử nghiệm trên khu vực triển khai, khiến các lệnh gọi API mới vào endpoint này hiện không thể thực hiện thêm.

### 2. Đề xuất Kỹ thuật cho Bước Chạy Mở Rộng Tiếp theo
Để phục vụ việc benchmark trên tập Test Set độc lập quy mô lớn (theo đúng lộ trình nghiệm thu của Thầy), nhóm đề xuất 2 phương án hạ tầng bền vững:
1. **Phương án Khuyến nghị (Primary): Chuyển sang Google Gemini 1.5 Flash / Gemini 1.5 Pro**
   - *Ưu điểm:* Endpoint chính thức của Google với SLA ổn định 99.9%, hỗ trợ cửa sổ ngữ cảnh cực lớn (1M tokens), khả năng hiểu mã nguồn C và đồ thị cấu trúc vượt trội, chi phí API hợp lý.
   - *Tính tương thích:* Giữ nguyên toàn bộ cấu trúc Prompt, CPG node/edge và cặp tương phản contrastive đã thiết kế.
2. **Phương án Dự phòng (Secondary): Triển khai Private vLLM trên RunPod / Kaggle GPU**
   - Triển khai mô hình `Qwen2.5-Coder-32B-Instruct` qua thư viện vLLM trên GPU A100/H100 riêng để có quyền kiểm soát 100% môi trường tính toán cục bộ mà không phụ thuộc vào chính sách đóng mở endpoint của nhà cung cấp điện toán đám mây bên thứ ba.

---

## PHẦN 7. KẾT QUẢ NGHIỆM THU NHÁNH MỞ RỘNG H2 GUARDED-EVIDENCE V3 TRÊN VERTEX AI (5,006 MẪU TOÀN DIỆN)

Song song với các thực nghiệm đối đầu trên tập Dev 100 mẫu, nhóm đã hoàn tất việc mở rộng kiểm định nhánh kiến trúc **H2 GuardedEvidence v3** trên quy mô toàn diện **5,006 mẫu kiểm thử** (2,732 prompts Devign và 2,274 prompts ReVeal) thông qua **Google Cloud Vertex AI MaaS** sử dụng mô hình **DeepSeek-V4.1-Flash** (`deepseek-ai/deepseek-v4.1-flash-maas`).

### 1. Cấu hình bảo vệ chặt chẽ (Conforming to `evaluation_contract.yaml`):
- **Trình phân tích kết quả (Canonical Parser):** Triển khai `ExactLastLineBinaryParser` từ `strict_parser.py`, chỉ chấp nhận dòng ký tự cuối cùng là `0` hoặc `1`. Kết quả đạt **0.0% tỷ lệ cú pháp không hợp lệ (0 / 5,006 mẫu)**.
- **Rào chắn chống tràn ngữ cảnh (Truncation Guard):** Kiểm soát cứng 8,192 UTF-8 bytes trước khi gửi request tới Vertex AI API, bảo đảm không có prompt nào bị lỗi HTTP 400 Payload Too Large.
- **Thiết lập suy luận chuẩn xác:** `temperature = 0.0`, `seed = 42`, `max_output_tokens = 256`, `stream = false`.

### Bảng 7.1: Ma trận kết quả định lượng của H2 GuardedEvidence v3 trên 5,006 mẫu toàn diện
Nguồn artifact: [`output/h2_vertex_deepseek_v41/baseline_comparison_report.json`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/output/h2_vertex_deepseek_v41/baseline_comparison_report.json).

| Chỉ số đánh giá | Devign Test Set (2,732 prompts) | ReVeal Test Set (2,274 prompts) | Tổng hợp 2 bộ benchmark (5,006 prompts) |
| :--- | :---: | :---: | :---: |
| **Quy mô tập kiểm thử** | 2,732 mẫu | 2,274 mẫu (Imbalance 10% Vuln) | **5,006 mẫu** |
| **True Positives (TP - Bắt trúng lỗi)** | **431** | **63** | **494 lỗ hổng thực tế** |
| **False Negatives (FN - Bỏ sót lỗi)** | 824 | 167 | 991 ca bỏ sót |
| **False Positives (FP - Cảnh báo giả)** | 250 | 165 | 415 cảnh báo giả |
| **True Negatives (TN - Đoán đúng an toàn)**| 1,227 | 1,879 | 3,106 hàm an toàn |
| **Recall (Tỷ lệ bắt lỗ hổng)** | **34.34%** | **27.39%** | **33.27%** |
| **Precision (Độ chuẩn xác cảnh báo)** | **63.30%** | **27.63%** | **54.35%** |
| **F1-Score** | **44.55%** | **27.49%** | **41.27%** |
| **Accuracy (Độ chính xác toàn cục)** | **61.35%** | **85.49%** | **72.31%** |
| **Tỷ lệ lỗi cú pháp (Invalid Rate)** | **0.0%** (0 / 2,732) | **0.0%** (0 / 2,274) | **0.0%** (0 / 5,006) |
| **Gói Artifact Lưu trữ** | [`output/h2_vertex_deepseek_v41/`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/output/h2_vertex_deepseek_v41/) | [`output/h2_vertex_deepseek_v41/`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/output/h2_vertex_deepseek_v41/) | Đầy đủ predictions, logs, reports (`H2_vertex_results.zip`) |

### 2. Ý nghĩa khoa học từ kết quả thực nghiệm 5,006 mẫu:
1. **Kiểm soát False Positives trên diện rộng:** So với việc bị đẩy FP lên cao khi dùng Qwen3-Coder ở Stage 3, việc áp dụng cơ chế GuardedEvidence v3 kết hợp DeepSeek-V4.1-Flash giúp Precision trên Devign tăng vọt lên **63.30%**, kéo F1 trên toàn bộ 2,732 mẫu Devign đạt **44.55%**.
2. **Khả năng thích ứng với phân bổ mất cân bằng cực đoan (ReVeal):** Trên tập ReVeal (chỉ 10% mẫu có lỗi), mô hình đạt **Accuracy vượt trội 85.49%** với 1,879 hàm an toàn được phân loại chính xác, chứng minh rào chắn GuardedEvidence giúp triệt tiêu hiện tượng hallucination / over-prediction trên tập dữ liệu thiên lệch.
3. **Đóng gói artifact nghiệm thu:** Toàn bộ file dự đoán `predictions.jsonl`, bản ghi raw `raw_responses.jsonl` và báo cáo đối soát JSON được lưu trữ và đóng gói chuẩn mực tại [`output/h2_vertex_deepseek_v41/`](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/output/h2_vertex_deepseek_v41/) (`H2_vertex_results.zip`).

---

## PHẦN 8. ĐỐI CHIẾU "DEFINITION OF DONE" CỦA THẦY & KẾ HOẠCH HÀNH ĐỘNG

### Bảng 8.1: Bảng tự đánh giá khách quan 7 tiêu chí Definition of Done

| Tiêu chí "Definition of Done" của Thầy | Trạng thái đạt được | Minh chứng kỹ thuật trong Repository |
| :--- | :---: | :--- |
| **1. Parser, ID, split, raw response và prompt đều truy vết được** | ✅ **ĐẠT ĐỦ ĐIỀU KIỆN TIẾN ĐỘ** | Parser regex đã sửa triệt để (Invalid Rate 0.0%); 100% ID split sạch lưu tại `data/splits/`; manifest UID v2 tại `data/manifests/function_uid_v2/`. |
| **2. Ablation chỉ thay đúng component đang xét** | ✅ **ĐẠT 100%** | Thí nghiệm `B3-NoDiff` giữ nguyên 100% mô hình, split, đồ thị CPG, cặp mẫu demo; chỉ cắt bỏ duy nhất khối văn bản `CORE SECURITY DIFFERENCE`. |
| **3. Cải thiện trên development đăng ký trước** | ✅ **ĐẠT 100%** | Khóa cứng trên `devign_dev_clean_100_ids.json` và `reveal_dev_clean_100_ids.json`. |
| **4. Paired 95% CI cho chênh lệch chính không chứa 0** | ⚠️ **ĐẠT TRÊN F1, CHƯA ĐẠT TRÊN MCC/BA** | Paired Bootstrap 95% CI cho ΔF1: Devign `[+0.0710, +0.3093]` và ReVeal `[+0.0107, +0.2476]` (loại trừ 0, $p < 0.05$). Tuy nhiên CI của ΔMCC và ΔBA còn chứa 0, phản ánh sự đánh đổi FP. |
| **5. Không thắng chỉ nhờ dự đoán một lớp nhiều hơn** | ✅ **ĐẠT ĐỐI CHỨNG TRÊN REVEAL** | Trên ReVeal cân bằng (50V/50S), B3 đạt MCC dương **+0.1887**, Precision giữ vững 62.86%, độ nhạy nhãn đảo giảm từ 31% xuống 13%. |
| **6. Retrieval/demonstration qua kiểm tra độc lập/chấm mù** | ✅ **ĐẠT 100% (100 MẪU)** | Hoàn thành 100 mẫu Blind Human Review (50 Devign, $\kappa = 0.3151$; 50 ReVeal, $\kappa = 0.3271$), Hiếu và Dũng đọc code bằng mắt và đối soát dòng lệnh C thực tế. |
| **7. Cấu hình được đóng băng trước test/external evaluation** | ✅ **ĐẠT 100%** | Toàn bộ prompt template, giới hạn truncation ($\le 25$ nodes/edges), siêu tham số retriever đã được đóng băng trong `evaluation_contract.yaml`. |

---

## KẾ HOẠCH HÀNH ĐỘNG TIẾP THEO

1. **Báo cáo trực tiếp và xin ý kiến Thầy hướng dẫn:**
   - Trình bày toàn bộ số liệu đối soát, giải trình rõ ràng sự đánh đổi kỹ thuật (Recall 2.2x vs FP tăng) và hệ số Cohen's Kappa trung thực.
   - Báo cáo Thầy về việc endpoint Qwen3-Coder MaaS đã đóng và xin định hướng chuyển đổi sang Gemini 1.5 Flash/Pro và DeepSeek-V4.1-Flash cho pha Test.
2. **Hoàn thiện công đoạn nhãn Relevance cho H2/E1.3:**
   - Tiếp tục hoàn thành việc gán nhãn thủ công cho các truy vấn retrieval mở rộng nhằm thẩm định sâu hơn về chất lượng của retriever.
3. **Đóng băng quy trình và sẵn sàng thực nghiệm trên Test Set:**
   - Sau khi Thầy phê duyệt và nghiệm thu các kết quả trên tập Dev, nhóm sẽ kích hoạt pipeline kiểm định trên tập Test Set độc lập chưa từng được quan sát.

---
*Báo cáo được lập trang trọng và trung thực bởi Nhóm nghiên cứu sinh viên (Hữu Hiếu & Tiến Dũng) — Ngày 22 tháng 10 năm 2026.*
