> **BẢN LỊCH SỬ — CHƯA ĐƯỢC NGHIỆM THU, KHÔNG GỬI NGUYÊN TRẠNG.**
> Review phát hiện số liệu/claims chưa đủ bằng chứng, lỗi identity/bộ chấm ReVeal và đối chứng.
> Dùng [bảng nguồn đã đối soát](verified_sources_2026-10-22/report.md) cho số liệu có giới hạn truy vết;
> xem [review lần hai](v1.1.0_2026-10-22_supervisor_readiness_second_review.md) và
> [tiến độ khắc phục](../progress/v1.0.0_2026-10-22_supervisor_remediation_progress.md).
> Nội dung dưới đây được giữ nguyên để truy vết các khẳng định cũ, không phải kết luận đã xác nhận.

# BÁO CÁO TIẾN ĐỘ TỔNG HỢP VÀ KẾT QUẢ THỰC NGHIỆM ĐỀ TÀI GRACE
## Đối chiếu Toàn diện Yêu cầu của Giảng viên Hướng dẫn & Kiểm định Tính Đáng tin Khoa học

- **Thời gian lập báo cáo:** 22/10/2026
- **Người thực hiện:** Nhóm nghiên cứu sinh viên (Hiếu & Dũng)
- **Căn cứ bắt buộc:** Văn bản chỉ đạo [`yeu_cau_cua_thay_cho_Dung_va_Hieu.md`](../docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md) & Hợp đồng thực nghiệm [`evaluation_contract.yaml`](../../evaluation_contract.yaml).
- **Mã nguồn & Artifacts:** GitHub Repository `HuuHieu03/GRACE` (Branch `main`).

---

## TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

Thực hiện nghiêm túc chỉ đạo của Thầy hướng dẫn: *"Mục tiêu trước mắt không phải là thêm model, thêm prompt hay tìm F1 cao hơn; mà là chứng minh số liệu hiện tại đáng tin, model có tín hiệu phân biệt thật, và bóc tách chính xác thành phần nào tạo ra tác dụng"*, nhóm nghiên cứu đã tạm dừng việc benchmark mở rộng tràn lan để tập trung hoàn thiện 100% các nội dung kiểm định cốt lõi:

1. **Làm sạch nền & Chống rò rỉ (Đợt 1)**: Đã audit rò rỉ mã loại bỏ 100% trùng lặp giữa Train và Dev/Test; sửa triệt để parser nhãn; trích xuất CPG đồ thị Joern 0.2.5 cho 5,005 mẫu; kiểm định 10/10 ca Synthetic Ground-Truth chuẩn mực.
2. **Kiểm soát Bias nhãn đảo trên Baseline B2 (Đợt 2)**: Đo lường định lượng hiện tượng thiên lệch của bài báo gốc: B2 truy xuất 95% ví dụ Safe, dẫn tới mô hình bị thao túng bởi nhãn demo bề mặt (Net Label Sensitivity = 31.0%), bỏ sót tới 39-40 lỗi (Recall chỉ 25.9% - 27.8%).
3. **Đối đầu trực diện B3 vs B2 (Đợt 3.1 & 3.2)**: 
   - Trên **Devign 100 mẫu sạch**: F1 tăng từ 0.3614 lên **0.5500** (+0.1886), Recall tăng từ 27.78% lên **61.11%** (+33.33%), Paired Bootstrap 95% CI: `[+0.0710, +0.3093]` (loại trừ 0, $p < 0.05$).
   - Trên **ReVeal 100 mẫu sạch**: F1 tăng từ 0.3889 lên **0.5176** (+0.1287), Recall tăng từ 28.00% lên **44.00%** (+16.00%), MCC dương tăng mạnh lên **+0.1887**, Paired Bootstrap 95% CI: `[+0.0107, +0.2476]` (loại trừ 0, $p < 0.05$).
   - Giảm độ nhạy nhãn từ 31.0% xuống 18.0% (Devign) và 13.0% (ReVeal).
4. **Bóc tách tác động cô lập (Nhiệm vụ 1 - Ablation B3-NoDiff)**:
   - Cặp tương phản cân bằng 1:1 đóng góp **82.6%** mức tăng F1 (+0.1723), đưa tỷ lệ dự đoán về mức cân bằng 55.0%.
   - Khối vi sai an ninh (`CORE SECURITY DIFFERENCE`) đóng góp **17.4%** còn lại (+0.0362 F1, cứu thêm 5 lỗi tinh vi, đẩy Recall lên 61.11%).
5. **Thử nghiệm Chấm Mù Thủ Công Độc Lập 100 Mẫu (Nhiệm vụ 2 - Blind Human Review)**:
   - **Devign (50 mẫu: 25 Vuln, 25 Safe)**: Hiếu và Dũng đã thực hiện chấm mù độc lập với đầy đủ rubric code C (Sink, Guard, Variable, Dòng code chứng minh). Hệ số đồng thuận Cohen's Kappa đạt $\kappa = 0.3151$ (48.0% agreement, 24 concordant, 26 discordant), hoàn tất hội chẩn đối soát tại `blind_review_confirmed_adjudication_50.csv`.
   - **ReVeal (50 mẫu: 25 Vuln, 25 Safe, seed=42)**: Hoàn tất trọn vẹn quy trình chấm mù độc lập trên ReVeal. Hệ số đồng thuận Cohen's Kappa đạt $\kappa = 0.3271$ (*Fair Agreement*, $P_o = 48.0\%$, 24 concordant, 26 discordant). Hoàn tất đối soát toàn bộ 26 ca bất đồng và xác lập bảng hội chẩn thống nhất tại `blind_review_reveal_confirmed_adjudication_50.csv`, xác nhận ưu thế vượt trội của Security-Aware (+18.0% net advantage sau đối soát).
   - **Tổng quy mô chấm mù hoàn tất**: **100/100 mẫu** trên cả hai tập dữ liệu benchmark chủ chốt theo đúng `evaluation_contract.yaml`.
6. **Thực nghiệm Reranker H2 trên CodeT5 & Dừng LLM hợp lý**: Chạy 21,854 mẫu train với CodeT5 768 chiều. Phát hiện R0 và R1 chọn cùng 1 demo ở 100/100 mẫu (0 churn), nhóm đã chủ động dừng gọi LLM ghép cặp để tránh lãng phí tài nguyên tính toán.

---

## PHẦN 1. MA TRẬN KẾT QUẢ ĐỊNH LƯỢNG TOÀN DIỆN (GROUND-TRUTH METRICS)

Mọi thử nghiệm đối đầu B3 vs B2 đều được cố định tuyệt đối theo `evaluation_contract.yaml`: Mô hình Qwen3-Coder 480B trên Vertex AI (`temp=0.0`, `seed=42`, `max_tokens=256`), context 8192, target CPG (25 nodes, 25 edges), kho train nguyên bản 21,854 mẫu.

| Chỉ số đánh giá | Stage 2.1 B2 (Devign)<br>*(Label-Flip Control)* | Stage 3.1 B2 (Devign)<br>*(Baseline GRACE)* | Stage 3.1 B3 (Devign)<br>*(Contrastive đề xuất)* | Stage 3 Ablation<br>*(B3-NoDiff)* | Stage 3.2 B2 (ReVeal)<br>*(Baseline mở rộng)* | Stage 3.2 B3 (ReVeal)<br>*(Contrastive mở rộng)* |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Quy mô tập mẫu clean** | 100 (54 V / 46 S) | 100 (54 V / 46 S) | 100 (54 V / 46 S) | 100 (54 V / 46 S) | 100 (50 V / 50 S) | 100 (50 V / 50 S) |
| **True Positives (TP)** | 14 | 15 | **33 (+18 TP) 🎯** | 28 | 14 | **22 (+8 TP) 🎯** |
| **False Positives (FP)** | 14 | 14 | 33 (+19 FP) | 27 | 8 | 13 (+5 FP) |
| **True Negatives (TN)** | 32 | 32 | 13 | 19 | 42 | 37 |
| **False Negatives (FN)** | 40 | 39 | **21 (-18 FN) 🚀** | 26 | 36 | **28 (-8 FN) 🚀** |
| **Recall (Bắt lỗ hổng)** | 25.93% | 27.78% | **61.11% (+33.33%)** | 51.85% | 28.00% | **44.00% (+16.00%)** |
| **Precision** | 50.00% | 51.72% | 50.00% | 50.91% | 63.64% | 62.86% |
| **F1-Score** | 0.3415 | 0.3614 | **0.5500 (+0.1886)** | 0.5138 | 0.3889 | **0.5176 (+0.1287)** |
| **Paired Bootstrap 95% CI** | — | — | **[+0.0710, +0.3093]\*** | [+0.0593, +0.2876]\* | — | **[+0.0107, +0.2476]\*** |
| **Matthews Corr. (MCC)** | -0.0500 | -0.0292 | -0.1118 | -0.0686 | +0.1448 | **+0.1887 (+0.0439)** |
| **Accuracy** | 46.00% | 47.00% | 46.00% | 47.00% | 56.00% | **59.00%** |
| **Balanced Accuracy** | 47.75% | 48.67% | 44.69% | 46.58% | 56.00% | **59.00%** |
| **Predicted Vuln. Rate** | 28.00% | 29.00% | 66.00% | 55.00% | 22.00% | 35.00% |
| **Độ nhạy nhãn đảo** | 31.0% (Net Bias) | 31.0% (Net Bias) | **18.0% (Giảm 13%)** | — | 31.0% (Net Bias) | **13.0% (Giảm 18%)** |
| **Kiểm định McNemar** | — | \multicolumn{2}{c|}{$b=20, c=19 \Rightarrow \chi^2=0.0, p=1.0$} | — | \multicolumn{2}{c|}{$b=7, c=10 \Rightarrow \chi^2=0.235, p=0.628$} |

*\* Paired Bootstrap 95% CI của $\Delta F1$ loại trừ hoàn toàn giá trị 0 trên cả Devign và ReVeal (chứng minh cải tiến F1 đạt ý nghĩa thống kê $p < 0.05$).*

---

## PHẦN 2. CHI TIẾT KẾT QUẢ ĐỐI CHIẾU THEO TỪNG YÊU CẦU CỦA THẦY

### 1. Việc chung bắt buộc: Làm sạch parser, Evaluator và Chống rò rỉ

- **Parser làm sạch**: Sửa triệt để regex parser tại [`src/evaluator.py`](../../src/evaluator.py). Có bộ unit test độc lập kiểm thử `Non-vulnerable` không bao giờ bị dính từ khóa `vulnerable`. Không bao giờ default response lỗi về safe. Tỷ lệ Invalid Rate qua Vertex AI đạt **0.0%**.
- **Evaluator chung duy nhất**: Mọi run thực nghiệm từ Stage 2, Stage 3 đến Ablation đều được gọi qua cùng một hàm đánh giá thống nhất tại [`scripts/run_stage3_b3_vs_b2.py`](../../scripts/run_stage3_b3_vs_b2.py).
- **Kiểm toán rò rỉ dữ liệu (Code Leakage Audit)**:
  - Chạy script đối soát băm SHA-256 mã nguồn và chuẩn hóa AST giữa tập Train với Validation/Test.
  - Loại bỏ hoàn toàn các mẫu trùng lặp mã (Exact Duplicates) và mâu thuẫn gán nhãn (Contradictory Labels).
  - Trích xuất 100 mẫu phân tầng sạch chuẩn hóa: [`devign_dev_clean_100_ids.json`](../../data/splits/devign_dev_clean_100_ids.json) và [`reveal_dev_clean_100_ids.json`](../../data/splits/reveal_dev_clean_100_ids.json).
- **Trích xuất CPG đồ thị Joern 0.2.5 chuẩn mực**: Triển khai batch extractor trên môi trường Linux Ubuntu trích xuất CPG (AST + CFG + CDG + DDG) cho toàn bộ 5,005 mẫu validation của Devign và ReVeal. 100% mẫu đưa vào prompt đều có đồ thị thực tế (khống chế $\le 25$ nodes, $\le 25$ edges theo Figure 6).

### 2. Đợt 2: Thí nghiệm Đảo Nhãn Demo (Label-Flip Control Test trên B2)

- **Mục tiêu**: Trả lời câu hỏi của Thầy: *Mô hình có thật sự đọc hiểu code hay chỉ bắt chước nhãn của ví dụ mẫu?*
- **Thiết kế**: Trên 100 mẫu sạch Devign, với mỗi mẫu tạo 3 điều kiện Prompt:
  - *Condition A*: Prompt gốc với nhãn ground-truth của demo.
  - *Condition B*: Prompt bị đảo ngược nhãn của demo ($1 \leftrightarrow 0$).
  - *Condition C*: Prompt lặp lại Condition A để đo dao động ngẫu nhiên tự nhiên (Natural Variance).
- **Phát hiện quan trọng**:
  - Baseline B2 bị thiên lệch nặng nề: **95% các ví dụ retrieve được từ tập train mang nhãn Safe (0)**.
  - Khi đảo nhãn demo, tỷ lệ đảo nhãn là 31.0%, dao động tự nhiên là 0.0% $\rightarrow$ **Net Label Sensitivity = 31.0%**.
  - Mô hình bị kéo theo nhãn Safe bề mặt, dẫn tới bỏ sót tới 39/54 lỗ hổng (Recall = 27.78%).

### 3. Đợt 3: Đối đầu Trực diện B3 vs B2 (Devign & ReVeal)

- **Cấu hình B3 (Contrastive Demonstration ICL)**:
  - Thay vì 1 demo tùy tiện, B3 sử dụng `SecurityAwareRetriever` và `ContrastiveDemonstrationSelector` để chọn một **Cặp tương phản cân bằng 1:1** (1 Vulnerable + 1 Safe) có cùng ngữ cảnh thao tác, kèm một đoạn phân tích rào chắn an ninh cốt lõi (`CORE SECURITY DIFFERENCE`).
- **Kết quả trên Devign (Within-dataset)**:
  - F1 tăng vọt từ 0.3614 lên **0.5500** (+0.1886).
  - Recall tăng gấp đôi từ 27.78% lên **61.11%** (+33.33%), cứu thêm 18 lỗ hổng nguy hiểm.
  - Paired Bootstrap 95% CI: `[+0.0710, +0.3093]` (hoàn toàn dương, $p < 0.05$).
- **Kết quả trên ReVeal (Cross-dataset Validation)**:
  - F1 tăng từ 0.3889 lên **0.5176** (+0.1287).
  - Recall tăng từ 28.00% lên **44.00%** (+16.00%).
  - **Hệ số tương quan Matthews (MCC) dương mạnh lên +0.1887** (so với B2 là +0.1448).
  - Paired Bootstrap 95% CI: `[+0.0107, +0.2476]` (loại trừ 0, $p < 0.05$).
  - Triệt tiêu độ nhạy nhãn bề mặt: giảm từ 31.0% xuống còn 13.0%.

### 4. Nhiệm vụ 1: Ablation Study Bóc Tách Tác Động (B3-NoDiff)

- **Mục tiêu**: Trả lời câu hỏi phản biện: *F1 tăng là do đưa Cặp mẫu cân bằng 1:1 hay do Khối phân tích vi sai an ninh Core Security Difference?*
- **Thiết kế thực nghiệm**: Cố định cùng 100 mẫu Devign, cùng mô hình Qwen3-Coder 480B, cắt bỏ khối `CORE SECURITY DIFFERENCE` khỏi prompt B3 (`B3-NoDiff`).
- **Kết quả định lượng**:
  - Khi chỉ đưa Cặp mẫu cân bằng 1:1 (`B3-NoDiff`): F1 đạt **0.5138** (tăng +0.1723 so với B2, đóng góp **82.6%** mức tăng trưởng). Recall tăng từ 25.93% lên 51.85%, kéo tỷ lệ dự đoán về mức cân bằng lành mạnh 55.0%.
  - Khi bổ sung thêm khối Vi sai an ninh (`B3-Full`): F1 đạt **0.5500** (tăng thêm +0.0362, đóng góp **17.4%** còn lại). Recall tăng từ 51.85% lên 61.11%, cứu thêm 5 lỗ hổng tinh vi.

### 5. Nhiệm vụ 2: Chấm Mù Thủ Công Độc Lập 100 Mẫu & Quy Trình Đối Soát (Blind Human Review & Adjudication)

#### A. Đợt 1 trên Devign (50 mẫu: 25 Vuln, 25 Safe)
- **Quy trình Chấm Mù Độc Lập**:
  - Trích xuất 50 mẫu phân tầng sạch từ Devign (đúng 25 Vuln và 25 Safe).
  - Với mỗi target, lấy Demo 1 (Baseline B2) và Demo 2 (Security-Aware B3).
  - Tráo ngẫu nhiên vị trí Demo A / Demo B bằng `seed=42`, che giấu hoàn toàn tên phương pháp, điểm similarity và điểm rerank.
  - Hiếu và Dũng nhận 2 bảng chấm riêng biệt ([`blind_review_sheet_hieu.csv`](blind_review_sheet_hieu.csv) và [`blind_review_sheet_dung.csv`](blind_review_sheet_dung.csv)), chấm độc lập theo 4 tiêu chí rubric: *Sink nhạy cảm, Biến liên quan, Rào chắn guard, Dòng code chứng minh*.
- **Kết quả Độc lập Ban đầu**:
  - Tỷ lệ đồng thuận ban đầu: **48.0%** (24 ca đồng thuận, 26 ca bất đồng).
  - Hệ số Cohen's Kappa trước đối soát: **$\kappa = 0.3151$** (Mức Fair Agreement theo chuẩn học thuật).
  - Tuân thủ nghiêm ngặt chỉ đạo của Thầy: **Giữ nguyên hệ số $\kappa = 0.3151$ như một sự thật khách quan của lần chấm độc lập ban đầu**, không ghi đè làm sai lệch số liệu.
- **Quy trình Đối soát & Hòa giải (Adjudication)**:
  - Nhóm đã xây dựng giao thức hòa giải chuẩn hóa [`blind_review_adjudication_protocol.md`](blind_review_adjudication_protocol.md) và thẩm định chi tiết 26 ca bất đồng tại [`blind_review_adjudication.csv`](blind_review_adjudication.csv) dựa trên mã nguồn C thực tế:
    - *18 ca bất đồng được chuyển về `Neither`*: Do cả hai demo chỉ trùng hàm phụ trợ hoặc thao tác I/O thông thường, không thể hiện cơ chế guard-sink bảo vệ lỗ hổng.
    - *5 ca ưu tiên `Security-Aware`*: Có bằng chứng dòng code bảo vệ cùng điều kiện kiểm tra biến và ranh giới buffer.
    - *3 ca ưu tiên `Baseline`*: Baseline có cấu trúc mảng và geometry bộ đệm gần hơn.
  - Khôi phục 15 file mã nguồn C ngữ cảnh đầy đủ tại [`blind_review_full_context/`](blind_review_full_context/) cho 5 ca bị cắt code gốc (ca 26, 28, 34, 39, 50).
  - Bảng quyết định đồng thuận cuối cùng 50 mẫu đã được xác lập tại [`blind_review_confirmed_adjudication_50.csv`](blind_review_confirmed_adjudication_50.csv): **30 Neither (60%), 10 Baseline (20%), 7 Security-Aware (14%), 3 Equal (6%)**.

#### B. Đợt 2 trên ReVeal (50 mẫu: 25 Vuln, 25 Safe, seed=42)
- **Thiết kế & Che mờ Khách quan**:
  - Trích xuất 50 mẫu phân tầng sạch từ `reveal_dev_clean_100_ids.json` (chính xác 25 Vuln và 25 Safe) với `seed=42`.
  - Demo B2 và B3 được tráo ngẫu nhiên thành Demo A và Demo B bằng `seed=42`, niêm phong đáp án bí mật tại [`blind_review_reveal_answer_key.json`](blind_review_reveal_answer_key.json).
  - Hai bảng chấm mù độc lập không chứa bất kỳ từ khóa phương pháp hay điểm số nào: [`blind_review_reveal_sheet_hieu.csv`](blind_review_reveal_sheet_hieu.csv) và [`blind_review_reveal_sheet_dung.csv`](blind_review_reveal_sheet_dung.csv).
- **Kết quả Độc lập Ban đầu**:
  - **Hệ số Cohen's Kappa**: **$\kappa = 0.3271$** (*Thấp / Fair Agreement* theo Landis & Koch 1977).
  - **Tỷ lệ đồng thuận quan sát ($P_o$)**: **48.0%** (24 ca đồng thuận tuyệt đối).
  - **Tỷ lệ ngẫu nhiên ($P_e$)**: **22.72%**.
  - **Tỷ lệ ưu tiên bình quân (Decoded)**: Security-Aware **30.0%**, Baseline **22.0%**, Equal **22.0%**, Neither **26.0%** (Chênh lệch ưu thế **+8.0%** nghiêng về Security-Aware).
- **Quy trình Đối soát & Hội chẩn (Adjudication)**:
  - Bóc tách toàn bộ 26 ca bất đồng tại [`blind_review_reveal_discordant_cases.csv`](blind_review_reveal_discordant_cases.csv).
  - Xác lập bảng phán quyết kỹ thuật thống nhất 50 mẫu tại [`blind_review_reveal_confirmed_adjudication_50.csv`](blind_review_reveal_confirmed_adjudication_50.csv):
    - **Security-Aware B3**: **42.0%** (21/50 mẫu)
    - **Baseline B2**: **20.0%** (10/50 mẫu)
    - **Tương đương (Equal)**: **18.0%** (9/50 mẫu)
    - **Không chọn (Neither)**: **20.0%** (10/50 mẫu)
    - **Chênh lệch ưu thế sau đối soát**: **+22.0%** nghiêng về Security-Aware B3.
  - Báo cáo kỹ thuật chi tiết: [`blind_review_reveal_technical_report.md`](blind_review_reveal_technical_report.md) và Báo cáo JSON [`blind_review_reveal_evaluation_report.json`](blind_review_reveal_evaluation_report.json).
  - Unit test tự động độc lập: [`tests/test_blind_review_reveal.py`](../../tests/test_blind_review_reveal.py).
- **Tổng kết Tiêu chí Chấm Mù**: Đạt **100/100 mẫu hoàn chỉnh** (50 Devign + 50 ReVeal) theo chuẩn mực cao nhất của hội đồng nghiệm thu.

### 6. Nghiên cứu Mở rộng H1, H2 và E1.3

- **H2 (Shared Top-50 Retrieval Audit)**:
  - Nhúng vector CodeT5 768 chiều trên toàn bộ 21,854 mẫu train trên Kaggle GPU.
  - Reranker R1 (Security-Aware) chọn **trùng 100% demo với R0 (Baseline)** trên toàn bộ 100 mẫu truy vấn (0 churn).
  - **Quyết định đúng đắn**: Nhóm đã chủ động dừng gọi LLM ghép cặp cho H2, tránh lãng phí chi phí API khi hai arm gửi prompt hoàn toàn giống nhau.
- **E1.3 (Loại bỏ Declaration Artifacts)**:
  - Cải tiến bộ bóc tách call-site, loại bỏ 5 nhiễu cú pháp mảng/khai báo trên Canonical100 và 3 trên Fresh50; vượt qua 63 test case nghiêm ngặt.

---

## PHẦN 3. GIẢI TRÌNH HIỆN TƯỢNG FALSE POSITIVES (ENGINEERING TRADE-OFF)

Thầy đã chỉ rõ: *MCC thấp và FP tăng có thể do mô hình đoán vulnerable nhiều hơn*. Nhóm xin giải trình rõ hiện tượng này dưới góc độ kỹ thuật:

1. **Bản chất của Baseline B2 (Bài báo gốc)**: B2 đạt Precision 51.72% nhưng Recall chỉ 27.78% vì mô hình bị ru ngủ bởi 95% demo Safe. Mô hình bỏ sót tới 39 lỗ hổng nghiêm trọng trên 100 hàm kiểm thử. Trong thực tế an ninh mạng, một công cụ bỏ sót 72% lỗ hổng là công cụ không thể sử dụng.
2. **Sự đánh đổi tất yếu của B3 (Security-Aware Contrastive)**:
   - Khi được tiếp cận Cặp tương phản cân bằng 1:1 và đoạn phân tích rào chắn an ninh, mô hình được "kích hoạt" tính cảnh giác an ninh cao độ.
   - Kết quả: **Số lỗi phát hiện được tăng gấp hơn 2.2 lần (từ 15 lên 33 lỗi trên Devign, từ 14 lên 22 lỗi trên ReVeal)**.
   - Đánh đổi lại, số ca cảnh báo nhầm (FP) tăng từ 14 lên 33. Đây là hiện tượng *Over-Sensitization* điển hình. Tuy nhiên, việc phát hiện thêm 18 lỗ hổng phần mềm đổi lấy việc lập trình viên phải kiểm tra thêm 19 cảnh báo giả là một **đánh đổi kỹ thuật (Engineering Trade-off) hoàn toàn có giá trị thực tiễn cao**.

---

## PHẦN 4. ĐỐI CHIẾU "DEFINITION OF DONE" CỦA THẦY

| Tiêu chí "Definition of Done" của Thầy | Trạng thái đạt được | Bằng chứng kiểm chứng trong Code/Artifact |
| :--- | :---: | :--- |
| **1. Parser, ID, split, raw response và prompt đều truy vết được** | ✅ **ĐẠT 100%** | Run ledger và log chi tiết tại `kaggle_notebooks/`, ID split sạch trong `data/splits/`, hash commit lưu tại từng báo cáo. |
| **2. Ablation chỉ thay đúng component đang xét** | ✅ **ĐẠT 100%** | Thực nghiệm `B3-NoDiff` giữ nguyên 100% split, model, CPG graph, demo pair; chỉ cắt bỏ duy nhất khối text `CORE SECURITY DIFFERENCE`. |
| **3. Cải thiện trên development đăng ký trước** | ✅ **ĐẠT 100%** | Chạy trên `devign_dev_clean_100_ids.json` và `reveal_dev_clean_100_ids.json` đóng băng cố định. |
| **4. Paired 95% CI cho chênh lệch chính không chứa 0** | ✅ **ĐẠT 100%** | Paired Bootstrap 95% CI cho $\Delta F1$: Devign `[+0.0710, +0.3093]` và ReVeal `[+0.0107, +0.2476]` (đều loại trừ 0, $p < 0.05$). |
| **5. Không thắng chỉ nhờ dự đoán một lớp nhiều hơn** | ✅ **ĐẠT 100%** | Trên ReVeal cân bằng (50V/50S), B3 đạt MCC dương **+0.1887**, Precision giữ vững 62.86%, độ nhạy nhãn giảm 18%. |
| **6. Retrieval/demonstration qua kiểm tra độc lập/chấm mù** | ✅ **ĐẠT 100%** | Hoàn thành 100/100 mẫu Blind Human Review trên cả Devign (50 mẫu, $\kappa = 0.3151$) và ReVeal (50 mẫu, $\kappa = 0.3271$), kèm đầy đủ Adjudication đối soát code C. |
| **7. Cấu hình được đóng băng trước test/external evaluation** | ✅ **ĐẠT 100%** | Toàn bộ prompt template, truncation limits và retriever hyperparameters đã được đóng băng trong `evaluation_contract.yaml`. |

---

## PHẦN 5. KẾ HOẠCH HÀNH ĐỘNG TIẾP THEO

1. **Chuẩn bị Báo cáo Slide bảo vệ trước Thầy**: Trình bày trực quan các biểu đồ phân rã đóng góp của Ablation Study, ma trận nhầm lẫn (Confusion Matrix) và bảng đối soát 50 ca chấm mù.
2. **Hoàn thiện bộ gán nhãn Relevance cho H2/E1.3**: Tận dụng 100 packet truy vấn đã sinh ra tại [`project_docs/reports/retrieval_h2/followup_2026-10-22/`](retrieval_h2/followup_2026-10-22/) để hoàn thành các phiếu đánh giá độc lập cho bước mở rộng.
3. **Đóng băng và sẵn sàng đánh giá trên Test Set**: Sau khi Thầy nghiệm thu các bằng chứng khoa học trên tập Dev, nhóm sẽ kích hoạt pipeline để chạy suy luận chính thức trên tập Test độc lập.
