# GRACE — Audit và đánh giá mức sẵn sàng báo cáo giảng viên

**Thời điểm audit:** 02/11/2026, 07:48:01 (Asia/Bangkok, UTC+07:00)  
**Phạm vi:** đánh giá theo *Đề cương nghiên cứu tổng hợp*, đối chiếu hồ sơ thực nghiệm hiện có, kiểm tra lại các artifact/prediction được đóng gói và chạy một số test có liên quan.  
**Nguồn đã kiểm tra:**

- `GRACE_De_cuong_nghien_cuu_tong_hop.pdf`.
- `De_cuong_nghien_cuu_GRACE_hop_nhat.pdf`.
- `audit_package_grace.zip` (bản giải nén được cung cấp trong cuộc trao đổi).
- `grace_diag_kit.zip`.
- `GRACE_research_kit.zip`.

> **Kết luận dùng để quyết định:** Có thể gửi thầy **ngay dưới dạng báo cáo tiến độ/thực nghiệm thăm dò**, nhưng chưa đủ cơ sở để gửi như một nghiên cứu đã hoàn thành xác nhận. Không trình bày các kết quả hiện tại như bằng chứng cuối cùng rằng LLM có hoặc không có giá trị bổ sung. Các run hiện có khác model, khác nguồn sinh prediction và khác protocol; phải giữ chúng thành các nhánh bằng chứng riêng.

---

## 1. Verdict ngắn gọn

### Có đủ gửi thầy không?

**Có — nếu mục đích là báo cáo tiến độ, xin thầy góp ý và thống nhất lượt xác nhận tiếp theo.** Hiện đã có kết quả P_pre/P_post thực tế trên full test Devign và ReVeal trong `runs/step0_real_*`, có phân tích repair/harm, routing và khoảng tin cậy. Ngoài ra còn có một run B0/B2 trên Devign với Qwen3-Coder alias và logprob.

**Chưa — nếu định gửi với tư cách kết quả xác nhận hoàn chỉnh của đề cương tổng hợp.** Các kết quả quan trọng còn chịu ảnh hưởng của khác biệt provider giữa validation và test; P_pre/P_post OOF hiện chưa dùng group-aware folds; routing chưa có CI ghép cặp trực tiếp cho contrast chính; chưa có xác nhận ngoài trên cohort mới; và chưa có ba-seed/repeat evidence theo thiết kế mới.

### Định hướng nghiên cứu

Tiếp tục chọn **Đề cương nghiên cứu tổng hợp: đánh giá giá trị bổ sung của nhánh graph–LLM so với classifier nhẹ đã khóa**. Đây là hướng hợp lý hơn việc tiếp tục mở rộng H1/H2/H3 thành nhiều cải tiến độc lập.

Câu hỏi chính cần giữ:

1. **Sau truy vấn:** P_post có tốt hơn P_pre khi giữ cùng classifier nền, feature nền, meta-model, folds và quy trình chọn threshold không?
2. **Trước truy vấn:** benefit-router có tốt hơn confidence và random ở cùng ngân sách gọi expert không?
3. **Tính bền:** kết quả còn giữ khi đổi seed/repeat, kiểm overlap và chuyển sang cohort ngoài không?

Các probe graph/demo nên được giữ ở vai trò chẩn đoán có chọn lọc; không cần chạy toàn bộ ma trận trước khi có kết quả xác nhận của hai phép so chính.

---

## 2. Kết quả thực nghiệm hiện có — phải phân biệt hai nhánh

### 2.1. Nhánh Step 0: P_pre/P_post từ artifact H3-B lịch sử

Nguồn kết quả:

- `runs/step0_real_devign/diagnostic_summary_devign.md` và `diagnostic_report_devign.json`.
- `runs/step0_real_reveal/diagnostic_summary_reveal.md` và `diagnostic_report_reveal.json`.
- Dữ liệu đầu vào: `data/b0_offline_dungs_data/*_join_*.csv` và `xpre_*_locked_*.npz`.

Đây là **kết quả Step 0 thực tế**, không phải dry-run 100 mẫu. Script dùng validation để fit meta-model/chọn threshold và áp sang full test. Dữ liệu test có 2.732 mẫu Devign và 2.274 mẫu ReVeal.

#### P_pre vs P_post

| Dataset | N test | P_pre MCC | P_post MCC | ΔMCC (Post − Pre) | 95% CI | δ MCC | Verdict trong báo cáo |
|---|---:|---:|---:|---:|---:|---:|---|
| Devign | 2.732 | 0,3046 | 0,2966 | -0,0080 | [-0,0286; 0,0124] | 0,02 | No meaningful benefit trong setup đã đo |
| ReVeal | 2.274 | 0,3503 | 0,3675 | +0,0173 | [-0,0197; 0,0538] | 0,02 | Inconclusive |

Các chỉ số hỗ trợ:

| Dataset | ΔAUROC | 95% CI ΔAUROC | ΔF1 | 95% CI ΔF1 | McNemar P_pre/P_post |
|---|---:|---:|---:|---:|---:|
| Devign | +0,0015 | [-0,0015; 0,0046] | -0,0398 | [-0,0536; -0,0263] | p = 0,5245 |
| ReVeal | +0,0026 | [-0,0032; 0,0084] | +0,0165 | [-0,0170; 0,0497] | p = 0,7119; Holm = 0,8198 |

Bootstrap trong báo cáo dùng 5.000 reps, seed 20261117. Devign dùng cluster bootstrap theo 2.068 commit groups. ReVeal chuyển sang sample bootstrap vì dữ liệu chỉ có hai group lớn (`debian`, `chrome`); đây là lựa chọn đang được ghi trong script/report, nhưng giới hạn phụ thuộc group của ReVeal vẫn cần nêu.

**Diễn giải phù hợp:**

- Devign: trong setup lịch sử đang xét, cận trên CI ΔMCC là 0,0124, thấp hơn biên δ = 0,02. Đây là bằng chứng không đạt mức lợi ích thực tiễn đã định cho phép so này; không nên diễn đạt thành “LLM hoàn toàn không có thông tin bổ sung”.
- ReVeal: ước lượng điểm dương nhưng CI còn chứa 0 và mức tăng ≥ δ. Chưa đủ bằng chứng về lợi ích.
- Hai dataset chưa cho thấy bằng chứng xác nhận mạnh rằng nhánh LLM cải thiện P_pre.

#### Repair/harm theo lớp

| Dataset | Nhãn thật | Repair | Harm | Net repair |
|---|---|---:|---:|---:|
| Devign | Safe (y=0) | 678 | 24 | +654 |
| Devign | Vulnerable (y=1) | 16 | 834 | -818 |
| **Devign** | **Tổng** | **694** | **858** | **-164** |
| ReVeal | Safe (y=0) | 160 | 95 | +65 |
| ReVeal | Vulnerable (y=1) | 20 | 102 | -82 |
| **ReVeal** | **Tổng** | **180** | **197** | **-17** |

Điểm đáng chú ý: expert lịch sử có xu hướng sửa một số lỗi trên lớp safe nhưng tạo nhiều lỗi trên lớp vulnerable. Không được chỉ báo số repair mà bỏ qua harm hoặc phân rã theo lớp.

#### Routing tại ngân sách 10%

Các số dưới đây là kết quả point estimate trên test; random là trung bình của 20 lượt random trong report.

| Dataset | Policy | Query | MCC | Balanced Accuracy |
|---|---|---:|---:|---:|
| Devign | Gate only | 0% | 0,2885 | 0,6302 |
| Devign | Confidence | 10% | 0,2991 | 0,6406 |
| Devign | Benefit (Ridge) | 10% | 0,2864 | 0,6371 |
| Devign | Random | 10% | 0,2495 | 0,6181 |
| ReVeal | Gate only | 0% | 0,3559 | 0,7049 |
| ReVeal | Confidence | 10% | 0,3509 | 0,6867 |
| ReVeal | Benefit (Ridge) | 10% | 0,2666 | 0,6252 |
| ReVeal | Random | 10% | 0,3339 | 0,6883 |

**Diễn giải:** benefit-router hiện chưa vượt confidence ở q=10% trên cả hai dataset theo BA và MCC. ReVeal còn cho thấy benefit-router kém rõ so với confidence. Tuy nhiên, report hiện chưa cung cấp paired CI cho ΔBA/ΔMCC giữa benefit và confidence tại q=10%; do đó chưa được tuyên bố khác biệt có ý nghĩa thống kê.

### 2.2. Nhánh B0/B2: Qwen3-Coder, Devign test

Nguồn kết quả:

- `runs/final/evaluation/table_A_metrics.csv`.
- `runs/final/evaluation/table_B_contrasts.csv`.
- `runs/final/devign/test/B0/42/records.jsonl` và `B2/42/records.jsonl`.
- Manifest từng run ở cùng thư mục.

Đây là **một thí nghiệm khác** với Step 0 P_pre/P_post ở Mục 2.1. Không gộp chúng thành cùng một model/expert hoặc cùng một session.

| Metric tại threshold đã khóa | B0 | B2 |
|---|---:|---:|
| Threshold | 0,08 | 0,98 |
| MCC | 0,0484 | 0,0743 |
| AUROC | 0,5392 | 0,5394 |
| AUPRC | 0,5109 | 0,4940 |

Contrast B2 − B0:

- ΔMCC = +0,0259; 95% CI = [-0,0206; 0,0701]; δ = 0,03; verdict = inconclusive.
- ΔAUROC = +0,000244; 95% CI = [-0,0194; 0,0203]; δ = 0,02; verdict = inconclusive.
- McNemar p = 0,00739 cho thấy hai arm có pattern đúng/sai khác nhau, nhưng **không chứng minh MCC/AUROC được cải thiện**.

Kiểm tra trực tiếp 2.732 records mỗi arm:

- Đủ hai candidate token `0` và `1` trong `top5` ở cả 2.732/2.732 mẫu của B0 và B2; candidate score hiện tại có đủ dữ liệu để tính.
- Raw generated verdict không phải `0` hoặc `1` ở 41 mẫu B0 và 2 mẫu B2. Do đó `invalid_rate = 0` trong bảng đang phản ánh candidate-score validity, không phản ánh raw verdict contract validity. Cần tách hai khái niệm.

**Provenance model cần sửa:** manifest record dùng alias `qwen3-coder-30b-q4`; `PROGRESS.md` mô tả Qwen3-Coder-30B Q4_K_XL, nhưng `AUDIT_README.md` lại mô tả Qwen2.5-Coder-7B Q4_K_M. Manifest test chưa lưu hash/revision của file model GGUF. Trước khi dùng kết quả này trong báo cáo chính, cần xác minh model artifact thực tế và sửa tất cả mô tả cho thống nhất.

**Tokenizer/budget:** tokenizer trong `grace_diag_kit/tokenizer` có `tokenizer_class = RobertaTokenizer`, không phải tokenizer Qwen3-Coder. Vì vậy, các số token chia theo thành phần trong record không nên được gọi là token count chính xác của Qwen nếu chưa chứng minh tokenizer đó là tokenizer thực dùng. `usage.prompt_tokens` do server trả là nguồn đáng tin hơn cho tổng prompt tokens; nhưng chưa thay thế được kiểm toán token từng block bằng tokenizer đúng.

### 2.3. Không được gộp hai nhánh kết quả

| Nhánh | Expert/model ghi nhận | Dữ liệu được kiểm | Loại score | Ý nghĩa |
|---|---|---|---|---|
| Step 0 P_pre/P_post | DeepSeek-V4.1-Flash lịch sử, validation/test khác provider | Full test Devign + ReVeal | Nhãn expert nhị phân 0/1 | Phân tích giá trị bổ sung lịch sử, có provider shift |
| B0/B2 final | `qwen3-coder-30b-q4` theo record manifest | Devign test | Candidate logprob có đủ 0/1 | Pilot graph/demo vs code-only trên Devign |

Hiện chưa có một run thống nhất dùng cùng một serving/model contract để vừa tạo expert development, fit P_pre/P_post, vừa xác nhận trên cohort test ngoài. Đây là lý do không thể coi các bảng trên là một phép xác nhận duy nhất.

---

## 3. Audit provenance và chất lượng dữ liệu

### 3.1. Các kiểm tra đã thực hiện và kết quả tốt

Đối với dữ liệu Step 0, đã đối chiếu trực tiếp các file join với NPZ feature đã khóa:

- Devign validation: 2.732 rows, 2.732 unique IDs, không duplicate.
- Devign test: 2.732 rows, 2.732 unique IDs, không duplicate.
- ReVeal validation: 2.273 rows, 2.273 unique IDs, không duplicate.
- ReVeal test: 2.274 rows, 2.274 unique IDs, không duplicate.
- IDs trong các file join khớp đầy đủ với IDs trong các NPZ 34-feature.
- `code_sha256` trong join khớp với `code_sha256` trong NPZ cho toàn bộ IDs đã kiểm.

Đây là bằng chứng tốt về alignment của các artifact Step 0 đang đóng gói.

### 3.2. Provider shift trong dữ liệu LLM lịch sử

Theo `B0_COMPLETION_STATUS_FINAL.md`, `CORRECTION_20261030.md` và các file join:

| Dataset | Validation | Test |
|---|---|---|
| Devign | 2.724 Vertex AI MaaS + 8 FPT AI Factory | 2.732 FPT AI Factory |
| ReVeal | 2.196 Vertex AI MaaS + 77 FPT AI Factory | 2.274 FPT AI Factory |

Tên model đều được ghi là DeepSeek V4.1 Flash, nhưng provider/serving path khác nhau. Vì vậy, validation dùng để fit meta-model không hoàn toàn đồng nhất với test về môi trường sinh expert. Không gán mọi chênh lệch P_post/P_pre cho phương pháp; cần ghi đây là limitation/serving shift.

### 3.3. Expert score trong Step 0 không phải logprob

Các canonical Step 0 hiện có `s_llm` chỉ nhận giá trị 0 hoặc 1. File ReVeal test còn khai báo `llm_score_semantics = binary_prediction_proxy_not_logprob`. Do đó:

- P_post đang đo giá trị tăng thêm của **nhãn expert nhị phân** và các feature dẫn xuất từ nhãn đó.
- Không gọi `s_llm` là xác suất hoặc logprob đã hiệu chuẩn.
- AUROC của P_post là score của meta-model Logistic Regression, không phải AUROC lấy trực tiếp từ confidence của LLM.
- B0/B2 Qwen3 là nhánh có candidate logprob thực; không được lấy score của nó ghép vào các prediction DeepSeek lịch sử.

### 3.4. Test exposure

`preregistration.md` khai báo test Devign/ReVeal đã được xem trong các vòng phát triển trước (36 run API, dev-100, H1–H3). Thresholds cho một lượt mới có thể đã được khóa trên validation trước khi chạy inference mới, nhưng điều này **không biến test cũ thành holdout chưa từng được tiếp xúc**.

Vì vậy, kết quả test hiện tại phù hợp để báo cáo như tái phân tích/thăm dò có khóa quy trình mới. Để có xác nhận độc lập mạnh hơn, cần cohort ngoài hoặc split theo project/time chưa được dùng để chọn phương án.

---

## 4. Audit code và rủi ro có thể ảnh hưởng kết luận

### 4.1. Lỗi quan trọng: OOF meta-model chưa dùng group-aware folds

Trong `grace_diag_kit/src/grace_diag/complementarity.py`, `fit_pre_post()` dùng `StratifiedKFold`. Tham số `groups` được truyền vào hàm nhưng chỉ dùng cho bootstrap; nó không được dùng để tách fold.

Điều này có nghĩa các hàm thuộc cùng commit/project có thể xuất hiện ở cả train fold và validation fold của meta-model. Với Devign, báo cáo có 2.068 commit groups nên đây là điểm cần sửa trước phép xác nhận. Với ReVeal chỉ có hai group lớn, cần xác định rõ đơn vị grouping khả thi và nêu giới hạn; không tự khẳng định sample folds tương đương group holdout.

**Sửa tối thiểu:** tạo common group folds theo protocol (ví dụ StratifiedGroupKFold nếu phù hợp), dùng cùng fold assignments cho P_pre/P_post, lưu fold ID từng mẫu. Nếu group structure không hỗ trợ stratification ổn định, ghi phương án thay thế và sensitivity analysis.

### 4.2. Candidate logprob parser trong `grace_diag_kit` chấp nhận thiếu một candidate

Trong `grace_diag_kit/src/grace_diag/llm_backend.py::parse_top_logprobs`, logic hiện tại dùng:

```python
valid = lp["0"] is not None or lp["1"] is not None
```

và gán xác suất 0 cho candidate bị thiếu. Điều này không đủ điều kiện để tính:

`p(1) / (p(0) + p(1))`.

Nếu chỉ có một candidate, score có thể bị đẩy thành 0 hoặc 1 giả tạo. **Sửa thành yêu cầu cả hai candidate**; nếu thiếu một candidate thì score phải `null`/missing, giữ raw verdict và trạng thái riêng.

Lỗi parser này không làm sai candidate scores của B0/B2 Devign hiện được kiểm vì tôi đã xác nhận cả hai candidate đều hiện diện trong mọi record. Tuy nhiên phải sửa trước khi chạy backend/arm khác.

### 4.3. Step 0 adapter cần kiểm tra join chặt hơn

Trong `scripts/run_step0_offline_diagnostic.py`:

- `load_gate_data()` và `load_llm_predictions()` lưu record vào dictionary theo ID; duplicate ID có thể bị overwrite.
- `build_canonical_table()` dùng giao của hai tập ID (`matched_ids`) thay vì fail khi thiếu/thừa IDs.
- Khi nạp NPZ, code ghép theo ID nhưng chưa đối chiếu `code_sha256` của NPZ với hash ở join.
- `_export_canonical_csv()` chỉ ghi `id,y,p_gate,s_llm,valid`; không xuất group và code hash nên canonical CSV tự thân chưa đủ để tái tạo cluster bootstrap hoặc kiểm tra identity.

Các file nguồn Step 0 trong gói hiện đã được đối chiếu riêng và không có duplicate/missing IDs/hash mismatch. Vì vậy đây là **rủi ro của code path khi dùng dữ liệu mới**, chưa phải bằng chứng các dòng hiện tại đã bị join sai. Dù vậy, trước lượt xác nhận nên dùng adapter strict trong `GRACE_research_kit` hoặc bổ sung fail-fast checks tương đương.

### 4.4. Routing chưa có paired CI cho contrast chính

Các report có point estimates của benefit, confidence và random tại q=5/10/25%, nhưng chưa thấy CI ghép cặp cho:

- benefit − confidence tại q=10% (ΔBA chính, ΔMCC phụ);
- benefit − random tại cùng budget.

Đề cương yêu cầu contrast chính và CI; không nên lấy việc một policy có point estimate cao hơn làm kết luận thắng. Cần export prediction/mask của từng policy và tính paired CI trên cùng target IDs. Random nên giữ 20 seeds như protocol.

### 4.5. Model identity và tài liệu chưa nhất quán

Các mô tả model trong `AUDIT_README.md`, `PROGRESS.md`, manifest và records không đồng nhất. Ngoài tên model, cần pin hash/revision của model file, tokenizer, quantization, llama.cpp/vLLM version, chat template và inference config. Manifest hiện có alias nhưng chưa đủ định danh artifact model để một người khác tái lập chính xác.

### 4.6. Canonical outputs cần giữ provenance đầy đủ

Với các lượt mới, mỗi dòng prediction cần giữ tối thiểu:

- `record_id`, `code_sha256`, `prompt_sha256`, `run_config_hash`;
- `dataset`, `split`, `group`, label chỉ ở file evaluation;
- model/provider/revision, engine/version, tokenizer/template hash;
- raw response, parsed verdict, score và `score_status` tách biệt;
- request status, retry, fallback, token usage, latency.

Không dùng `gate_score` làm score cho expert hoặc stacker. Không biến nhãn nhị phân thành xác suất continuous.

---

## 5. Test đã chạy trong lần audit này

| Bộ test | Cách chạy | Kết quả |
|---|---|---:|
| `GRACE_research_kit.zip` | `python -m unittest discover -s tests -v` | 59/59 PASS |
| `grace_diag_kit.zip` | `PYTHONPATH=src pytest -q tests` | 30/30 PASS |
| Adapter Step 0 trong audit package | `PYTHONPATH=grace_diag_kit/src pytest -q tests/test_step0_offline_diagnostic.py` | 8/8 PASS |

**Phạm vi của kết quả test:** các test trên xác nhận các module và fixture/kịch bản kỹ thuật tương ứng. Chúng không chứng minh toàn bộ pipeline inference trên model thật đã chạy end-to-end từ repository, và không chứng minh hiệu quả benchmark. Không gộp 59 + 30 + 8 thành một con số “toàn repo đã pass”.

Trong hồ sơ có nhiều con số test khác nhau (ví dụ 57, 111, 645); chưa có một bản test report duy nhất, có command/log/version thống nhất để xác nhận các tuyên bố đó. Khi gửi thầy, chỉ nên nêu chính xác ba nhóm test đã chạy lại ở bảng trên.

---

## 6. Đủ điều kiện gửi thầy đến mức nào?

| Mục đích | Verdict |
|---|---|
| Xin thầy duyệt hướng nghiên cứu tổng hợp | **Có thể gửi ngay** |
| Báo cáo tiến độ, kết quả Step 0 và pilot B0/B2 | **Có thể gửi, phải ghi rõ exploratory/limitations** |
| Khẳng định LLM đã chứng minh có giá trị bổ sung | **Chưa đủ** |
| Khẳng định LLM hoàn toàn không có giá trị bổ sung | **Chưa đủ** |
| Nộp như kết quả xác nhận hoàn chỉnh của đề cương tổng hợp | **Chưa đủ** |
| Công bố gói tái lập end-to-end đã kiểm chứng | **Chưa đủ** |

### Cách trình bày an toàn khi gửi thầy

Nên dùng một đoạn kết luận theo tinh thần sau:

> Nhóm đã chuyển trọng tâm sang đánh giá giá trị bổ sung của nhánh LLM so với classifier nền. Phân tích offline P_pre/P_post trên artifact H3-B hiện có cho thấy Devign chưa đạt biên lợi ích MCC đã đặt, còn ReVeal cho kết quả dương theo điểm nhưng chưa đủ bằng chứng thống kê. Phân tích routing bước đầu chưa cho thấy benefit-router vượt confidence ở ngân sách 10%. Ngoài ra, nhóm đã có pilot B0/B2 với Qwen3 trên Devign, nhưng chênh lệch MCC/AUROC còn inconclusive. Các kết quả hiện tại là bằng chứng thăm dò do test đã được tiếp xúc trong các vòng trước, expert lịch sử dùng nhãn nhị phân và validation/test có khác biệt provider. Nhóm đang hoàn thiện group-aware OOF, đồng nhất serving contract, paired CI cho routing và cohort xác nhận ngoài trước khi đưa ra kết luận xác nhận.

Không nên viết “đã chứng minh GRACE thất bại”, “LLM không có giá trị”, “benefit-router không có tác dụng” hoặc “thực nghiệm đã hoàn tất”.

---

## 7. Việc cần làm tiếp theo — ưu tiên tối thiểu, không overtesting

### P0 — cần làm trước lượt xác nhận chính

1. **Khóa nguồn expert thống nhất:** cùng model revision, provider/serving path, tokenizer, prompt contract, parser và parameters cho development và confirmation. Nếu giữ kết quả DeepSeek cũ, ghi rõ `binary_prediction_proxy` và provider shift; không coi đó là serving-consistent confirmation.
2. **Sửa OOF sang group-aware folds:** cùng fold assignment cho P_pre/P_post; lưu fold manifest và chứng minh scaler chỉ fit trên fold train.
3. **Siết canonical join:** fail khi duplicate/missing/extra ID; kiểm tra code hash, split, group và feature IDs; export các trường này trong canonical artifact.
4. **Sửa candidate scorer:** cần đủ cả candidate `0` và `1`; thiếu candidate thì score missing, không tự gán xác suất 0.
5. **Hoàn thiện routing comparison:** tại q=10%, xuất mask/predictions và paired CI cho benefit − confidence (ΔBA chính, ΔMCC phụ); random 20 seeds làm đối chứng.
6. **Khóa một cohort xác nhận ngoài:** ưu tiên PrimeVul theo đề cương; kiểm exact/near overlap với train, validation, donor bank và test lịch sử; lưu sampling weights và group metadata. Nếu cohort đã được dùng chọn phương án, không gọi nó là holdout mới.

### P1 — hoàn thiện tính tái lập và trình bày

- Đồng nhất README/PROGRESS/manifest và model artifact identity; sửa khác biệt Qwen2.5-7B vs Qwen3-30B.
- Giữ raw verdict, candidate score, binary proxy, `valid`, `score_status` và fallback thành trường riêng.
- Xuất kết quả từ script duy nhất; không chép tay số vào bảng.
- Giữ các run Devign/ReVeal cũ là exploratory/sensitivity evidence; không chạy lại toàn bộ graph/demo matrix nếu chưa có câu hỏi cụ thể cần nó.

### Chưa cần làm ngay

- Không cần mở thêm hàng loạt model/backbone hoặc hàng chục arm prompt.
- Không cần mở rộng H2 guarded nếu chưa có case evidence cho thấy thiếu guard/evidence là nguyên nhân chính.
- Không cần lặp toàn bộ B0/B1/B2 trên mọi dataset trước khi sửa protocol và xác nhận hai phép so chính.

---

## 8. Checklist ngắn trước khi bấm gửi email/báo cáo

- [ ] Tiêu đề ghi “Báo cáo tiến độ / kết quả thăm dò”, không ghi “kết quả xác nhận cuối cùng”.
- [ ] Phân biệt hai nhánh: Step 0 DeepSeek lịch sử và B0/B2 Qwen3 pilot.
- [ ] Báo P_pre/P_post và Δ/CI cùng verdict, không chỉ báo MCC đơn lẻ.
- [ ] Ghi rõ `s_llm` của Step 0 là nhãn 0/1, không phải logprob.
- [ ] Ghi provider shift validation/test và test exposure lịch sử.
- [ ] Ghi rõ benefit-router hiện chưa vượt confidence theo point estimate ở q=10%; paired CI còn thiếu.
- [ ] Không lấy McNemar p-value để kết luận MCC/AUROC tăng.
- [ ] Đính kèm hoặc link đúng manifest, prediction artifact, report và phiên bản code; loại API key/secret khỏi gói.

---

## 9. Kết luận cuối

**Nên gửi thầy ngay dưới dạng báo cáo tiến độ.** Hiện đã có lượng bằng chứng thực nghiệm đủ để thầy đánh giá hướng nghiên cứu và góp ý thiết kế bước xác nhận: P_pre/P_post trên cả Devign và ReVeal, repair/harm theo lớp, routing curves và một pilot B0/B2 có logprob.

**Không nên gửi như một nghiên cứu đã hoàn tất.** Lý do quyết định không phải vì thiếu thêm hàng loạt thí nghiệm, mà vì một số điều kiện nền của phép xác nhận chưa đảm bảo: provider shift trong expert history, group folds chưa được thực thi, routing chưa có paired CI của contrast chính, test đã có exposure lịch sử và chưa có cohort ngoài.

Bước đi hợp lý nhất là gửi thầy các kết quả hiện tại với nhãn exploratory, xin thống nhất một lượt xác nhận nhỏ nhưng đúng protocol; không mở rộng ma trận overtesting.
