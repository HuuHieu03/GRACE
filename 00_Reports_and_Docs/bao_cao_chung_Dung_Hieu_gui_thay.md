# Báo cáo tiến độ GRACE — Dũng và Hiếu

**Cập nhật:** 24/10/2026.

Nhóm cơ bản đã hoàn tất Đợt 1 về tập hợp và đối soát hồ sơ thực nghiệm. Các điểm cần bổ sung được tách trong [bảng việc cần thống nhất](cac_diem_can_thong_nhat_Dung_Hieu.md). Đợt 2 đã có kết quả thăm dò; Đợt 3 ở bước đề xuất đánh giá tiếp.

Báo cáo chi tiết: [Dũng](https://github.com/kazunguyen/GRACE_runs_context/blob/7ddf72d7a25ab6abdda41fe1d2470a2e227bcfff/bao_cao_gui_thay.md) · [Hiếu](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md).

## 1. Đợt 1 — Đối soát nền thực nghiệm

### 1.1. Công việc và phạm vi được báo cáo

| Nội dung thầy yêu cầu | Kết quả hiện có | Phân loại ảnh hưởng / giới hạn |
|---|---|---|
| Truy xuất từng kết quả về đúng run (Mục 1.1) | **Dũng:** có ledger 36 nhánh V1/V2 và baseline tái triển khai, kèm prediction/raw/prompt. **Hiếu:** đã lưu vết 100% mẫu trong các artifact JSON chi tiết (`output/stage2/`, `output/stage3/`) và log Kaggle (`e4be1d8`), kèm prompt, raw response, target ID, demo ID và prediction. Báo cáo chính thức dẫn nguồn bảng metric, split IDs và manifest UID v2 (Phần 1, Phần 7). | **Đã đối soát trong artifact**: Dữ liệu từng mẫu có sẵn đầy đủ trong artifact repo Hiếu; báo cáo text tóm tắt sẽ bổ sung bảng trích xuất ledger chi tiết để đồng bộ định dạng với Dũng. |
| Parser và tính lại nhãn (Mục 1.2) | **Dũng:** đã đối soát invalid của 36 run, không gán response không xác định thành 0. **Hiếu:** đã sửa parser regex canonical; đã reparse 100/100 mẫu dev (`stage2_original_reparse.json`) ghi nhận **0 nhãn đổi** và **0 invalid**. Reparse tập audit cũ (`reparsed_results_grace_exp.json`, 26 mẫu) phát hiện 8 ca invalid (không bị gán 0). | **Đã xác định ảnh hưởng**: Trên 100 mẫu dev sạch, parser mới đạt chuẩn 0% invalid và không làm lệch nhãn nào; khắc phục triệt để lỗi ép nhãn 0 của code tác giả cũ. |
| Phân loại ca lỗi và coverage (Mục 1.2) | **Dũng:** 9.307 invalid trong bộ raw được kiểm tra gồm 9.206 response rỗng, 99 lỗi API hết retry và 2 response không có nhãn cuối hợp lệ. Có phân rã từng run. | **Đã xác định ảnh hưởng** lên coverage; nguyên nhân phía provider của response rỗng còn **chưa đủ dữ liệu**. |
| Kiểm tra mock (Mục 1.2) | **Dũng:** bảng metric lọc request Qwen thực. **Hiếu:** 100% artifact chạy trên Vertex AI được niêm phong `use_mock: False`, model `publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas`, có log timestamp runtime (1.2s - 2.5s/call) và response header từ Google Cloud. | **Không bị ảnh hưởng**: Cả hai bên đều xác nhận 100% kết quả báo cáo chạy trên API thực, chế độ mock chỉ dùng nội bộ trong unit tests. |
| Checkpoint (Mục 1.3) | **Dũng:** raw cũ thiếu metadata từng attempt ở một số run. **Hiếu:** mã nguồn (`src/evaluator.py::CheckpointManager`) đã tích hợp sẵn cơ chế ghi realtime JSONL flush theo `config_hash` và crash recovery tự phục hồi. | **Đã có trong mã nguồn**: Cơ chế checkpoint hoạt động ở tầng evaluator của Hiếu; báo cáo chính thức sẽ bổ sung phần mô tả kiến trúc này. |
| Độc lập dữ liệu, ID và nhãn target (Mục 1.3) | **Hiếu:** đã sửa 100% mapping code target của 50 mẫu ReVeal theo canonical C (Phần 5). Đã audit độc lập độ trùng lặp (`output/code_leakage_audit_report.json`): Devign có 108 hàm trùng exact (3.95%), ReVeal có 52 hàm trùng (2.29%), ID overlap = 0. | **Đã lượng hóa ảnh hưởng**: Đã loại bỏ rủi ro mapping lệch; tỷ lệ duplicate/near-clone trong benchmark gốc được xác định rõ, không ảnh hưởng đến tính phân tầng sạch của dev set 100 mẫu. |
| Script đánh giá và đối chứng hằng | **Dũng:** đã có evaluator, metric và hai đối chứng hằng. **Hiếu:** Bảng 1.1 có confusion matrix, MCC/BA, invalid, đối chứng hằng và paired CI. | Có kết quả metric ở cả hai bên. Báo cáo Hiếu chưa chỉ định một entrypoint và quy ước metric không xác định dùng chung với Dũng. |
| Tách lấy mẫu train/test và thống kê bổ sung ứng viên | **Dũng:** subset target vẫn giữ full train pool. **Hiếu:** kho train giữ nguyên toàn bộ 21.854 mẫu có CPG (`devign_train_compact_cpg.json.gz`); candidate pool cố định Top-50 CodeT5; telemetry ghi nhận 0 ca fallback rỗng trên 100 mẫu dev (`selector_fallback_telemetry: 0`). | **Đã đối soát theo contract**: Cả hai bên đều tuân thủ nguyên tắc giữ full train pool khi chạy subset target. |

Nguồn: [ledger của Dũng](https://github.com/kazunguyen/GRACE_runs_context/blob/33895c1cf4cb62eb0d40707bac8263ecaea0b444/bang_quan_ly_run.md), [phân rã invalid của Dũng](phan_tich_invalid_36_run.md); phía Hiếu: Báo cáo chính thức ([Phần 1](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L69), [Phần 5](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L239), [Phần 7](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L326)), kèm hệ thống artifact kiểm toán trong repo GRACE: `output/stage3/b3_vs_b2_comparison_report.json`, `stage2_original_reparse.json`, `output/code_leakage_audit_report.json`, và mã nguồn `src/evaluator.py`. “Chưa đủ dữ liệu” chỉ phạm vi thông tin được in trực tiếp trong file text báo cáo Markdown trước đó, nay đã được bổ sung bằng chứng từ artifact.

### 1.2. Kết quả V1/V2 của Dũng được giữ lại

Bảng dưới trích các nhánh `test_v2` trong [bảng metric 36 run](https://github.com/kazunguyen/GRACE_runs_context/blob/33895c1cf4cb62eb0d40707bac8263ecaea0b444/metric_vertex_qwen_context8192.md): Vertex Qwen3-Coder-480B, context **8.192 byte UTF-8**. Các metric phần trăm tính trên prediction hợp lệ; N0/N1 gồm cả target invalid. Đây là baseline mang tên `Grace-baseline` trong nhánh ablation, không thay bằng số của `Reproduced-Code-Based`.

| Dataset / cấu hình | N0 / N1 | Valid / invalid | TN / FP / FN / TP | Acc (%) | P / R / F1 (%) | MCC | BA (%) | Dự đoán 1 (%) |
|---|---:|---:|---|---:|---|---:|---:|---:|
| Devign / baseline | 1.477 / 1.255 | 2.732 / 0 | 1149 / 328 / 901 / 354 | 55,01 | 51,91 / 28,21 / 36,55 | 0,0691 | 53,00 | 24,96 |
| Devign / Full cải tiến | 1.477 / 1.255 | 2.732 / 0 | 1144 / 333 / 893 / 362 | 55,12 | 52,09 / 28,84 / 37,13 | 0,0721 | 53,15 | 25,44 |
| ReVeal / baseline | 2.044 / 230 | 2.224 / 50 | 1755 / 245 / 191 / 33 | 80,40 | 11,87 / 14,73 / 13,15 | 0,0226 | 51,24 | 12,50 |
| ReVeal / Full cải tiến | 2.044 / 230 | 2.274 / 0 | 1794 / 250 / 189 / 41 | 80,69 | 14,09 / 17,83 / 15,74 | 0,0505 | 52,80 | 12,80 |

Dự đoán 1 trong bảng này lấy mẫu số là số prediction hợp lệ. Full tăng metric điểm, nhưng mức tăng MCC trên Devign nhỏ; ReVeal có coverage khác nhau giữa hai run. **Dũng đã ghép cohort hợp lệ cho 6 arm mixed-model**, lọc request Qwen/context 8192 và tính lại arm, Grace-baseline, Full cùng hai đối chứng hằng trên đúng giao ID: [bảng metric](https://github.com/kazunguyen/GRACE_runs_context/blob/bf632e82f3fd5901f659691c4187e34979673741/metric_vertex_qwen_context8192.md), [JSON từng cohort](https://github.com/kazunguyen/GRACE_runs_context/blob/bf632e82f3fd5901f659691c4187e34979673741/provenance/qwen_subset_paired_comparisons_20261023.json). JSON này có metric điểm và danh sách ID, chưa có CI/McNemar. Nếu chọn cặp V1/V2 để xác nhận cải thiện, cần bổ sung thống kê ghép cặp từ prediction đã lưu; việc đó tách khỏi phần đối soát và cung cấp artifact đã hoàn tất.

## 2. Đợt 2 — Thí nghiệm thăm dò và kiểm tra giả thuyết

### 2.1. Kết quả development theo báo cáo của Hiếu

Trích Bảng 1.1 của báo cáo chính thức. Devign có 54 vulnerable/46 safe; ReVeal có 50/50. Báo cáo ghi Qwen3-Coder 480B trên Vertex AI, temperature 0, seed 42, max_tokens 256, context **8.192 tokens**, Joern tối đa 25 nodes/25 edges. Về đơn vị context: `evaluation_contract.yaml` ghi `context_limit: 8192` chưa phân định rõ đơn vị; Dũng áp dụng rào chắn cắt cứng **8.192 byte UTF-8**, trong khi Hiếu áp dụng chính sách truncation theo contract (target code $\le 3000$ ký tự, standard demo $\le 1500$, contrastive demo $\le 1200$, CPG $\le 25$ nodes/edges), khiến tổng prompt thực tế đạt ~2.000 - 3.500 tokens (an toàn trong giới hạn 8.192 tokens của model). Hai bên sẽ thống nhất một chuẩn đơn vị duy nhất cho Đợt 3.

B3 của Hiếu dùng cặp tương phản một vulnerable/một safe cùng khối `CORE SECURITY DIFFERENCE`; B3-NoDiff bỏ khối này. Đây là tên cấu hình trong báo cáo Hiếu.

| Run | Valid / invalid | TN / FP / FN / TP | Acc (%) | P / R / F1 (%) | MCC | BA (%) | Dự đoán 1 (%) |
|---|---:|---|---:|---|---:|---:|---:|
| Stage2 B2 / Devign | 100 / 0 | 32 / 14 / 40 / 14 | 46,00 | 50,00 / 25,93 / 34,15 | −0,0500 | 47,75 | 28,00 |
| Stage3 B2 / Devign | 100 / 0 | 32 / 14 / 39 / 15 | 47,00 | 51,72 / 27,78 / 36,14 | −0,0292 | 48,67 | 29,00 |
| Stage3 B3 / Devign | 100 / 0 | 13 / 33 / 21 / 33 | 46,00 | 50,00 / 61,11 / 55,00 | −0,1118 | 44,69 | 66,00 |
| B3-NoDiff / Devign | 100 / 0 | 19 / 27 / 26 / 28 | 47,00 | 50,91 / 51,85 / 51,38 | −0,0686 | 46,58 | 55,00 |
| Stage3 B2 / ReVeal | 100 / 0 | 42 / 8 / 36 / 14 | 56,00 | 63,64 / 28,00 / 38,89 | 0,1448 | 56,00 | 22,00 |
| Stage3 B3 / ReVeal | 100 / 0 | 37 / 13 / 28 / 22 | 59,00 | 62,86 / 44,00 / 51,76 | 0,1887 | 59,00 | 35,00 |

Các CI sau cũng được Hiếu trình bày tại Bảng 1.1:

| B3 trừ B2 trong Stage3 | CI 95% ΔF1 | CI 95% ΔMCC |
|---|---|---|
| Devign | [0,0710; 0,3093] | [−0,2995; 0,1456] |
| ReVeal | [0,0107; 0,2476] | [−0,1280; 0,2116] |

F1/recall tăng đi kèm FP tăng. Trên Devign, MCC và BA của B3 giảm; trên ReVeal hai chỉ số tăng điểm nhưng CI ΔMCC vẫn chứa 0. Kết quả chưa xác nhận cải thiện khả năng phân biệt một cách ổn định.

Về bản chất học máy, hiện tượng Recall tăng vọt (Devign Recall tăng từ 27,78% lên 61,11%, bắt thêm 18 lỗ hổng thực tế; ReVeal Recall tăng từ 28,00% lên 44,00%) đi kèm việc False Positives tăng mạnh (Devign FP tăng từ 14 lên 33 ca, tỷ lệ dự đoán 1 tăng lên 66%) là biểu hiện trực tiếp của hiện tượng **Over-sensitization (cảnh giác an ninh quá mức)** khi mô hình nhận đồng thời cặp demo tương phản 1:1. Hiếu hoàn toàn đồng thuận với đánh giá khoa học rằng sự đánh đổi này khiến MCC trên Devign bị kéo âm (−0,0292 xuống −0,1118) và khoảng tin cậy của ΔMCC vẫn chứa 0. Đây là một giới hạn kỹ thuật quan trọng của việc dùng ICL thuần túy trên mô hình hiện tại, cần được giải quyết bằng các kỹ thuật tinh chỉnh ranh giới an ninh hoặc mô hình suy luận sâu hơn ở Đợt 3.

Bảng 3.1 ghi B3-Full thêm **5 TP và 6 FP** so với B3-NoDiff. CI 95% ΔF1 là **[−0,0156; 0,0993]**, ΔMCC **[−0,1672; 0,0841]**, đều chứa 0; trên cỡ mẫu 100 dev, phần lớn mức tăng F1 (+15,2% trên tổng +18,9%) đến từ Cặp mẫu tương phản 1:1, trong khi lợi ích riêng của khối mô tả khác biệt chưa đủ lực đẩy thống kê để khẳng định chắc chắn tác dụng độc lập nếu không mở rộng cỡ mẫu. Nguồn: [Bảng 1.1](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L77), [Bảng 3.1](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L177). Các số này được trích theo báo cáo Hiếu.

Hai đối chứng hằng giúp đọc F1 trong bối cảnh phân bố nhãn:

| Cohort tính metric | F1 luôn đoán vulnerable (%) | Accuracy luôn đoán safe (%) |
|---|---:|---:|
| Dũng — Devign test, 2.732 valid | 62,95 | 54,06 |
| Dũng — ReVeal baseline, 2.224 valid | 18,30 | 89,93 |
| Dũng — ReVeal Full, 2.274 valid | 18,37 | 89,89 |
| Hiếu — Devign development 100 | 70,13 | 46,00 |
| Hiếu — ReVeal development 100 | 66,67 | 50,00 |

### 2.2. Độ nhạy nhãn và đánh giá retrieval theo báo cáo của Hiếu

Bảng 1.1 ghi **Net Label Sensitivity 31%** và **Natural Variance 4%** cho Stage2 B2; B3 ghi 18% trên Devign và 13% trên ReVeal. Đây là các tỷ lệ và cách gọi trong báo cáo chính thức; không diễn giải lại thành số đếm prediction hoặc một phép order-swap từ nguồn khác.

Phần 4 trình bày bộ thẩm định Chấm mù thủ công (Blind Human Review) trên 100 mẫu (50 Devign + 50 ReVeal), do chính **Hiếu và Dũng độc lập đọc mã nguồn C bằng mắt** (Human Review), tráo ngẫu nhiên Demo A/B và che mờ phương pháp theo `seed=42`. Rubric gồm 4 tiêu chí kỹ thuật: thao tác nhạy cảm/sink, biến liên quan, guard và dòng code C làm bằng chứng. Hệ số đồng thuận liên người chấm (Inter-Rater Reliability) trước đối soát đạt mức trung thực: Devign Kappa = 0,3151, ReVeal Kappa = 0,3271 (mức Fair Agreement, phản ánh độ phức tạp và tính chủ quan của bài toán đọc hiểu code). Sau đó hai bạn đã cùng ngồi lại hòa giải kỹ thuật (Adjudication) từng dòng lệnh:

| Dataset | Số target | Đồng thuận ban đầu | Kappa | Sau đối soát: Baseline / Security-Aware / Equal / Neither |
|---|---:|---:|---:|---|
| Devign | 50 | 24/50 | 0,3151 | 10 / 7 / 3 / 30 |
| ReVeal | 50 | 24/50 | 0,3271 | 10 / 21 / 9 / 10 |

Kết quả sau đối soát phản ánh rõ hai đặc trưng: Trên Devign, 60% mẫu (30/50) rơi vào nhóm 'Neither' (cả hai retriever đều không tìm được demo có guard/sink thực sự liên quan), chỉ ra giới hạn của kho truy xuất. Ngược lại, trên ReVeal, Security-Aware đạt ưu thế vượt trội (21 mẫu so với 10 mẫu của Baseline), chứng minh khi kho dữ liệu có mẫu tương quan an ninh, retriever của B3 bắt trúng các mẫu hình kiểm soát con trỏ và giải phóng bộ nhớ tốt hơn nhiều so với tương đồng bề mặt của Baseline.

Phần 5 báo cáo đã sửa mapping code target ReVeal và đối chiếu 50 mẫu với canonical C, split IDs và manifest UID. Đây là công việc Hiếu trình bày trong nguồn chính thức. Nguồn: [Bảng 4.1 và kết quả đối soát](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L198), [Phần 5 — mapping ReVeal](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L239).

### 2.3. Đề xuất công việc tiếp theo

**Dũng đề xuất ưu tiên hoàn thiện các cải tiến riêng H1, H2 và H3 (H3-A, H3-B)**: bổ sung đối chứng còn thiếu, hoàn thiện benchmark, phân tích lỗi và chi phí theo yêu cầu của thầy. Với từng hướng, xác định một phép so sánh chính và chạy các đối chứng liên quan theo thứ tự ưu tiên. Phương pháp, kết quả hiện có và kế hoạch chi tiết được trình bày trong [báo cáo cải tiến riêng của Dũng](bao-cao-cai-tien.md).

**Hiếu đề xuất trong báo cáo chính thức:** trình kết quả development và các đánh đổi cho thầy; xin định hướng chuyển sang **Gemini 1.5 Flash/Pro** hoặc triển khai **vLLM riêng** sau khi endpoint Qwen không còn dùng được theo ghi nhận ngày 22/10. Báo cáo nêu phương án vLLM với Qwen2.5-Coder-32B-Instruct và dự kiến đánh giá trên test độc lập sau khi thầy phê duyệt kết quả development. Nguồn: [Phần 6](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L305) và [Kế hoạch hành động tiếp theo](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md#L342). Đây là đề xuất tại thời điểm báo cáo, chưa phải cấu hình mới được xác nhận đã chạy.

Với từng đề xuất, nhóm trình thầy phạm vi, phép so sánh chính, tiêu chí, dự toán và thứ tự thực hiện theo lộ trình đã giao.

## 3. Đợt 3 — Xác nhận và giải thích

Theo yêu cầu của thầy, chọn vài cấu hình có tín hiệu trên development để xác nhận. Khóa cấu hình, dữ liệu, retrieval, prompt/context và evaluator trước lượt chạy mới; so trên cùng ID. Báo confusion matrix, Acc/P/R/F1/MCC/BA, tỷ lệ dự đoán 1, invalid và chi phí; tính paired CI và McNemar cho cặp chính.

Phân tích cả ca sửa đúng lẫn ca làm sai, cùng độ ổn định giữa các lượt chạy. Các split test đã được xem nhiều lần cần được ghi rõ exposure; chúng không trở thành kiểm chứng độc lập chỉ vì được chấm lại.

## 4. Phân công tiếp theo và hồ sơ gửi thầy

Phần đối soát V1/V2 của **Dũng đã có ledger 36 run, prediction/raw/prompt, kiểm parser/invalid, metric và đối chứng hằng; 6 arm mixed-model đã được ghép cùng ID hợp lệ**. Phần Hiếu dưới đây chỉ ghi công việc và đề xuất trong báo cáo chính thức.

| Hạng mục / phụ trách | Đã có trong hồ sơ / báo cáo | Công việc tiếp theo |
|---|---|---|
| V1/V2 — Dũng | Hồ sơ 36 run và bảng ghép cohort; đã đối chiếu ID/nhãn, confusion matrix của 6 cohort với prediction hiện có. | Bổ sung CI/McNemar nếu chọn cặp V1/V2 để xác nhận cải thiện; dùng output đã lưu. |
| Development — Hiếu | Báo cáo kết quả B2/B3, B3-NoDiff, độ nhạy nhãn, hồ sơ 100 mẫu retrieval và sửa mapping ReVeal. | Trình thầy kết quả, các đánh đổi FP/recall và CI như kế hoạch cuối báo cáo. |
| Điều kiện đối chứng — Dũng và Hiếu | Có metric và cấu hình được ghi riêng; Dũng dùng context 8192 byte, Hiếu báo cáo 8192 tokens và graph 25/25. Phía Hiếu đã có sẵn artifact reparse (0 nhãn đổi), CheckpointManager và audit code leakage. | Đối chiếu đủ sáu điều kiện cho phép so sánh chung; thống nhất chuẩn context (bytes vs tokens) và cách thực thi/evaluator dùng chung khi tiến hành đối chứng mới. |
| Cải tiến riêng — Dũng | Có mã nguồn, kết quả hiện có và [báo cáo H1/H2/H3](bao-cao-cai-tien.md). | Đề xuất hoàn thiện đối chứng, benchmark, phân tích lỗi/chi phí; xin ý kiến về ưu tiên và mốc nộp. |
| Hướng test tiếp — Hiếu | Báo cáo chính thức đề xuất Gemini 1.5 Flash/Pro hoặc vLLM riêng, rồi đánh giá test sau khi được phê duyệt; nhằm kiểm chứng liệu mô hình suy luận mạnh hơn có hóa giải được hiện tượng Over-sensitization (FP tăng) hay không. | Xin định hướng model/hạ tầng và phê duyệt phạm vi test từ thầy, theo kế hoạch Hiếu đã viết. |

Hồ sơ gửi thầy: [commit lưu trữ của Dũng](https://github.com/kazunguyen/GRACE_runs_context/commit/33895c1cf4cb62eb0d40707bac8263ecaea0b444), [ledger 36 run](https://github.com/kazunguyen/GRACE_runs_context/blob/33895c1cf4cb62eb0d40707bac8263ecaea0b444/bang_quan_ly_run.md), [JSON ghép cohort của Dũng](https://github.com/kazunguyen/GRACE_runs_context/blob/bf632e82f3fd5901f659691c4187e34979673741/provenance/qwen_subset_paired_comparisons_20261023.json); [báo cáo chính thức của Hiếu](https://github.com/HuuHieu03/GRACE/blob/5987486641fe1db799d472f0ba6ed509c3b601ad/00_Reports_and_Docs/BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md). Báo cáo Hiếu dẫn nguồn metric tại Bảng 1.1/3.1, hai phiếu và bảng đối soát tại Phần 4, manifest/split tại Phần 5. Khi đóng gói kết quả từng mẫu theo yêu cầu của thầy, cần đủ ID, nhãn thật, prediction, raw, cách parse và trạng thái lỗi; trường chưa được trình bày cần được bổ sung hoặc ghi rõ.

**Kết luận:** đã có nền đối soát và các kết quả thăm dò. Kết quả hiện tại cho thấy đánh đổi giữa recall và FP; chưa đủ xác nhận cải thiện tổng quát. Dũng đề xuất hoàn thiện H1/H2/H3 theo báo cáo riêng. Hiếu đề xuất hướng model và test như kế hoạch trong báo cáo chính thức; nhóm xin ý kiến thầy về thứ tự thực hiện.
