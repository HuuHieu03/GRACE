# GRACE Immediate Action Plan — Những việc cần làm ngay bây giờ

## Mục tiêu của đợt này

Trong đợt gần nhất:
- không phát triển feature mới;
- chưa chạy lại toàn bộ benchmark.

Mục tiêu là tạo một nền thực nghiệm chung đủ sạch để Hiếu và Dũng:
1. so sánh công bằng;
2. biết kết quả cũ có bị parser/config/sampling làm sai không;
3. chọn đúng một hypothesis để chạy tiếp.

---

# STEP 1 — Chốt experimental contract với teammate

## 1.1. Chốt dataset và split

Hai người cần xác nhận bằng file:
- Devign train IDs;
- Devign dev IDs;
- Devign test IDs;
- ReVeal train/dev/test nếu dùng;
- số sample mỗi class;
- hash/version của split.

Cần trả lời:
- Hiếu và Dũng hiện có dùng cùng test IDs không?
- Nếu không: chọn một split chuẩn mới.
- Split này từ giờ không thay trong comparison chính.

Output đề xuất:

```text
splits/
  devign_train_ids.json
  devign_dev_ids.json
  devign_test_ids.json
  reveal_*.json
```

---

## 1.2. Chốt retrieval pool

Quy định:
- demonstration chỉ lấy từ train split;
- cùng retrieval pool cho các method được so trực tiếp;
- mặc định dùng full train pool.

Lưu:
```text
retrieval_pool_name
retrieval_pool_size
retrieval_pool_hash
class_distribution
```

---

## 1.3. Chốt backbone / inference config

Chọn một backbone chung cho vòng comparison đầu tiên.

Cần chốt:
- model;
- provider;
- temperature;
- max_tokens;
- retry;
- seed nếu có;
- timeout;
- output format.

Nếu chưa thống nhất model:
- vẫn audit riêng pipeline cũ;
- không so trực tiếp Hiếu vs Dũng.

---

## 1.4. Chốt metric

Mọi bảng kết quả từ giờ phải có:

```text
TP TN FP FN
Accuracy
Precision
Recall
F1
MCC
Balanced Accuracy
Predicted Vulnerable Rate
Invalid Rate
Always-Vulnerable Baseline
Always-Non-Vulnerable Baseline
```

Metric chính để nói “có improvement”:
- MCC;
- Balanced Accuracy;
- đọc cùng confusion matrix.

F1 vẫn báo để đối chiếu với paper.

---

# STEP 2 — Sửa evaluator/parser trước khi chạy model

## 2.1. Fix parser

Test ít nhất:

```text
0
1
Vulnerable
Non-vulnerable
Non-vulnerable (0)
Label: Non-vulnerable (0)
empty
malformed
contradictory
```

Quy tắc:
- `Non-vulnerable` → 0;
- invalid → trạng thái riêng;
- không default invalid → 0.

---

## 2.2. Reparse raw responses cũ

Không gọi lại LLM.

Với từng run chính:
- load raw response;
- parse bằng parser mới;
- lưu prediction mới;
- so với prediction cũ.

Báo cáo:
- tổng số label đổi;
- 0→1 bao nhiêu;
- 1→0 bao nhiêu;
- thay đổi theo ground truth;
- invalid bao nhiêu;
- metric trước/sau.

---

## 2.3. Tạo common evaluator

Một script duy nhất cho cả hai người.

Input tối thiểu:

```text
sample_id
ground_truth
prediction
parse_status
```

Output:
- toàn bộ metric đã thống nhất;
- trivial baselines;
- confusion matrix.

Không copy/paste metric thủ công vào report nữa.

---

# STEP 3 — Tạo bảng quản lý run

Mỗi run là một dòng.

Template:

| Field | Nội dung |
|---|---|
| run_id | ID duy nhất |
| owner | Hieu / Dung |
| commit | Git commit |
| dataset | Devign/ReVeal |
| split_hash | hash split |
| test_size | tổng target |
| positive_count | vulnerable |
| negative_count | safe |
| retrieval_pool_hash | pool |
| retrieval_pool_size | size |
| model | backbone |
| provider | API |
| temperature | inference |
| max_tokens | inference |
| prompt_mode | zero/baseline/contrastive/... |
| graph_mode | yes/no |
| retrieval_mode | baseline/security/... |
| top_n | candidate count |
| num_demo | 0/1/2/... |
| prediction_path | file |
| raw_response_path | file |
| prompt_log_path | file |
| notes | thiếu gì ghi rõ |

---

# STEP 4 — Tách sampling train/test

Sửa:

```text
sample_ratio
```

thành:

```text
train_sample_ratio
test_sample_ratio
```

Quy ước vòng tiếp theo:

```text
train_sample_ratio = 1.0
test_sample_ratio  = 0.1 hoặc 0.2
```

nếu cần tiết kiệm chi phí.

Phải lưu target IDs và dùng đúng cùng subset cho các method được so.

---

# STEP 5 — Instrument contrastive fallback

Chưa sửa algorithm ngay. Trước tiên đo mức độ ảnh hưởng.

Với mỗi target log:

```text
target_id
fallback_triggered
missing_label
top_n_label_counts
fallback_candidate_ids
final_selected_fallback_id
```

Tính:

## 5.1. FallbackRate
```text
# target fallback / total target
```

## 5.2. Dataset comparison
```text
Devign fallback rate
ReVeal fallback rate
```

## 5.3. Missing label distribution
```text
missing vulnerable
missing safe
```

## 5.4. Repeated fallback IDs
Kiểm tra một vài train IDs có bị chọn cho rất nhiều target không.

Quyết định:
- fallback hiếm → có thể giữ tạm nhưng phải báo;
- fallback cao → sửa trước contrastive benchmark.

---

# STEP 6 — Audit Security Signature

## 6.1. Thống kê empty signature

Theo từng dataset và feature:

```text
% empty sink
% empty sanitizer
% empty clue
% all memory flags false
```

## 6.2. Đo random-pair SecSim

Random target-demo pairs từ retrieval pool.

Báo:
- mean;
- median;
- distribution.

So với retrieved pairs.

Nếu random pairs cũng SecSim cao thì current SecSim đang inflate.

## 6.3. Synthetic unit cases

### Case A — correct guard
```c
if (len <= dst_size)
    memcpy(dst, src, len);
```

### Case B — irrelevant comparison
```c
if (retry > 0)
    memcpy(dst, src, len);
```

### Case C — guard after sink
```c
memcpy(dst, src, len);
if (len <= dst_size) ...
```

### Case D — wrong variable null check
```c
if (other != NULL)
    use(ptr);
```

Extractor phải cho thấy nó phân biệt được gì và chưa phân biệt được gì.

---

# STEP 7 — Chốt comparison đầu tiên sẽ chạy

Chỉ chọn một câu hỏi:

> Security-aware reranking có thực sự tốt hơn baseline reranking khi giữ mọi điều kiện khác cố định không?

Chạy:

```text
B2: baseline rerank + 1 demo
B3: security-aware rerank + 1 demo
```

Giữ nguyên:
- target IDs;
- full retrieval pool;
- initial candidate list;
- model;
- prompt;
- graph;
- num_demo;
- inference config.

Không chạy B5/B6 trước khi B2/B3 được thiết kế sạch.

---

# STEP 8 — Sau B2/B3 mới sang Contrastive

Nếu security-aware có tín hiệu:

```text
B4 = 1 vuln + 1 safe, baseline independent selection
B5 = 1 vuln + 1 safe, security-aware independent selection
B6 = same as B5 nhưng contrastive pair selector
```

Comparison chính:

```text
B5 vs B6
```

để trả lời:
> Pair-selection algorithm có lợi ích riêng ngoài việc đưa một example mỗi label không?

---

# Phân công ngay

## Hiếu

Làm ngay:
1. sửa parser;
2. reparse raw outputs;
3. common evaluator draft;
4. tách train/test sampling;
5. instrument fallback;
6. security signature diagnostics.

Sau đó:
7. chuẩn bị B2/B3;
8. chuẩn bị B5/B6 khi đủ điều kiện.

## Dũng

Làm ngay:
1. export danh sách run V1/V2;
2. cung cấp commit, model, split IDs, retrieval pool, prediction per sample, raw response, prompt/config;
3. xác nhận component nào bật ở từng run;
4. chuyển output sang format evaluator chung.

Sau khi common framework chốt:
5. rerun hypothesis trong cùng split/model/pool;
6. mỗi run chỉ thay một component.

## Cả hai cùng làm
1. chốt split;
2. chốt retrieval pool;
3. chốt backbone;
4. chốt evaluator;
5. chốt run registry;
6. review chéo parser/evaluator;
7. thống nhất run đầu tiên B2/B3.

---

# Thứ tự ưu tiên ngay

```text
1. Chốt experimental contract
2. Fix parser
3. Reparse run cũ
4. Common evaluator
5. Run registry
6. Tách sample ratio
7. Instrument fallback
8. Audit SecSim
9. Thiết kế B2/B3
10. Chỉ sau đó mới chạy LLM lại
```

---

# Definition of Done cho đợt hiện tại

- [ ] split IDs chung;
- [ ] retrieval pool chung;
- [ ] backbone/config chung cho comparison;
- [ ] parser mới + unit tests;
- [ ] reparse report;
- [ ] evaluator chung;
- [ ] run registry;
- [ ] train/test sampling tách riêng;
- [ ] fallback statistics;
- [ ] SecSim diagnostics;
- [ ] spec B2/B3 được chốt trước khi chạy.

Khi đủ các mục trên, nhóm mới nên bắt đầu vòng benchmark mới.
