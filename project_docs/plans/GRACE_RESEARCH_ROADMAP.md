# GRACE Research Roadmap — Kế hoạch nghiên cứu theo từng phase

## 0. Mục tiêu chung

Từ thời điểm này, mục tiêu không phải là tiếp tục thêm feature ngay, mà là:

1. Làm sạch nền thực nghiệm để có thể tin được vào kết quả.
2. Thống nhất điều kiện so sánh giữa hai hướng nghiên cứu.
3. Tách riêng tác dụng của từng thành phần:
   - baseline retrieval;
   - security-aware reranking;
   - balanced two-demo retrieval;
   - contrastive pair selection;
   - graph / prompt / instruction.
4. Chỉ khi một thành phần cho tín hiệu đáng tin cậy mới mở rộng benchmark và tối ưu tiếp.
5. Kết luận dựa trên MCC / Balanced Accuracy / F1 / confusion matrix và khoảng tin cậy, không dựa trên một metric đơn lẻ.

---

# PHASE 1 — Chuẩn hóa nền thực nghiệm

## 1.1. Thống nhất experimental contract giữa Hiếu và Dũng

### Dataset / split
- Dataset chính vòng đầu: ưu tiên Devign.
- Dataset xác nhận sau: ReVeal.
- Dùng cùng danh sách train/dev/test IDs.
- Lưu split cố định, có hash/version.
- Không thay split giữa các method được đem ra so trực tiếp.

### Retrieval pool
- Retrieval pool mặc định = full train set.
- Khi giảm chi phí:
  - giữ `train_sample_ratio = 1.0`;
  - chỉ giảm `test_sample_ratio`.
- Các method trong một ablation phải nhận cùng candidate pool nếu mục tiêu là đo tác dụng reranking/selector.

### Backbone
- Dùng cùng một LLM backbone/provider cho comparison trực tiếp.
- Chốt model, provider, temperature, max_tokens, retry policy, seed nếu có.
- Nếu hai người dùng model khác nhau thì chỉ được phân tích riêng, không kết luận hướng nào tốt hơn.

### Prompt / context policy
- Chốt rõ code-only hay code+graph, có demonstration hay không, số demo, graph truncation, context limit, demo order và instruction.
- Mọi run phải log prompt thực tế gửi cho model.

### Evaluation
Mọi run dùng chung evaluator và báo cáo:
- TP / TN / FP / FN;
- Accuracy;
- Precision;
- Recall;
- F1;
- MCC;
- Balanced Accuracy;
- predicted-positive rate;
- invalid/error rate;
- always-vulnerable baseline;
- always-non-vulnerable baseline.

### Run tracking
Mỗi run lưu:
- run_id;
- commit hash;
- model/provider;
- dataset/split hash;
- retrieval pool hash;
- prompt mode;
- retrieval config;
- number of candidates;
- demo IDs;
- target IDs;
- raw response;
- parsed prediction;
- parse method;
- token count;
- phần context bị truncate.

---

## 1.2. Sửa parser và re-evaluate các run cũ

### Vấn đề
Parser hiện có nguy cơ:
- parse `Non-vulnerable (0)` thành `1`;
- response không parse được bị mặc định thành `0`.

### Việc cần làm
- Viết test cho `0`, `1`, `Vulnerable`, `Non-vulnerable`, `Non-vulnerable (0)`, `Label: Non-vulnerable (0)`, empty, malformed và contradictory response.
- Invalid output phải có trạng thái riêng, không ép thành `0`.
- Reparse raw responses đã lưu.
- Không gọi lại LLM ở bước này.
- Báo cáo số prediction bị đổi, thay đổi theo ground truth, phân phối parse_method và metric trước/sau.

### Kết quả mong đợi
Có một bộ metric mới đáng tin cậy làm baseline thực nghiệm.

---

## 1.3. Xây evaluator chung

Một script duy nhất đọc prediction-level records và tính:
- confusion matrix;
- Accuracy;
- Precision;
- Recall;
- F1;
- MCC;
- Balanced Accuracy;
- predicted-positive rate;
- invalid rate;
- trivial baselines.

Quy định:
- positive label = vulnerable;
- invalid không được ngầm bỏ khỏi mẫu số;
- nếu đánh giá valid-only phải báo coverage.

---

## 1.4. Sửa sampling

Tách:

```text
train_sample_ratio
test_sample_ratio
```

- `train_sample_ratio`: kích thước retrieval bank.
- `test_sample_ratio`: số target được benchmark.

Khi chạy ablation rẻ:

```text
train_sample_ratio = 1.0
test_sample_ratio  = 0.1 hoặc 0.2
```

Không thu nhỏ retrieval pool chỉ để giảm số lần gọi LLM.

---

## 1.5. Sửa checkpoint / mock / reproducibility

### Checkpoint
Checkpoint key phải phụ thuộc ít nhất vào:
- dataset/split;
- model;
- inference config;
- prompt;
- retrieval config.

Không restore nếu config/hash không khớp.

### Mock
- Thiếu API key/model/data phải fail rõ ràng.
- Không silent fallback sang mock trong benchmark thật.

---

# PHASE 2 — Audit retrieval độc lập với LLM

## 2.1. Đo random retrieval baseline

Con số như `47.58% vulnerable target lấy safe demo` không tự chứng minh retrieval thất bại.

Cần đo cùng metric với random retrieval trên đúng retrieval pool:
- Label Agreement@1;
- Vulnerable Target Correct Demo Rate;
- tỷ lệ vulnerable target lấy safe demo.

Mục tiêu:
- biết GRACE retrieval cao hơn random bao nhiêu;
- phân biệt label mismatch do class distribution với retriever thực sự có/không có tín hiệu.

---

## 2.2. Đánh giá fallback của contrastive selector

Với mỗi dataset đo:

1. `FallbackRate`: bao nhiêu target có Top-N thiếu một label.
2. `MissingLabelDistribution`: thiếu vulnerable hay thiếu safe.
3. `FallbackCandidateIDs`: các sample được bổ sung.
4. `FinalFallbackSelectedID`: sample fallback cuối cùng được chọn.
5. `RepeatedFallbackBias`: một vài fallback ID có bị dùng lặp lại cho rất nhiều target không.

### Nếu fallback rate cao
Phải sửa fallback trước khi kết luận về contrastive selector.

### Hướng sửa
Không lấy 5 sample đầu tiên theo label. Thay bằng retrieval bổ sung có tiêu chí:
- search sâu hơn;
- search riêng trong subset của label thiếu;
- hoặc candidate expansion vẫn dựa trên target similarity.

---

## 2.3. Kiểm tra Security Signature

Hiện feature gồm:
- Sink;
- Sanitizer;
- Memory;
- Clue.

### Vấn đề cần kiểm tra
- empty set vs empty set có thể cho similarity = 1;
- memory flags cùng `False` được tính là match;
- `bounds_check` quá rộng;
- `null_check` quá rộng;
- feature mới phản ánh dấu hiệu, chưa chứng minh guard liên quan đúng sink.

### Synthetic test cases
Tạo mini-function có đáp án rõ:
1. check đúng biến trước sink;
2. check biến không liên quan;
3. check sau sink;
4. check chỉ bảo vệ một branch;
5. sink giống nhưng sanitizer khác;
6. sanitizer giống nhưng bảo vệ sink khác.

### Random-pair SecSim baseline
Ghép ngẫu nhiên target-demo và tính SecSim.

Nếu random pairs cũng có score rất cao thì current SecSim chưa đủ discriminative.

---

## 2.4. Manual retrieval audit

Tập thăm dò:
- 50 Devign;
- 50 ReVeal;
- có cả hai label.

Với mỗi target-demo pair, chấm:
- sensitive operation;
- relevant variable;
- guard/condition;
- guard có thực sự bảo vệ operation không;
- evidence line;
- security mechanism.

Hai thành viên chấm độc lập trước khi thống nhất.

---

# PHASE 3 — Ablation có kiểm soát

## 3.1. Câu hỏi 1: Security-aware reranking có thực sự giúp?

### B2
- code + graph;
- 1 demo;
- baseline reranking.

### B3
- y hệt B2;
- chỉ thay reranking bằng security-aware.

Giữ cố định:
- candidate set;
- number of candidates;
- number of demos;
- prompt;
- model;
- target IDs;
- inference config;
- context policy.

Metric chính:
- MCC;
- Balanced Accuracy;
- F1;
- Recall;
- Precision;
- confusion matrix.

Chỉ coi security-aware có tín hiệu nếu metric độc lập cải thiện, không chỉ security similarity tăng.

---

## 3.2. Câu hỏi 2: Balanced two-demo có giúp?

### B2
- 1 demo baseline.

### B4
- 1 vulnerable + 1 safe;
- chọn độc lập bằng baseline retriever.

Nếu cần isolate riêng “2 demo” và “balanced labels”, thêm cấu hình 2 demo tốt nhất nhưng không ép khác label.

---

## 3.3. Câu hỏi 3: Security-aware có giúp khi đã balanced label?

### B4
- 1 vulnerable + 1 safe bằng baseline.

### B5
- 1 vulnerable + 1 safe bằng security-aware;
- vẫn chọn độc lập từng nhóm.

Mục tiêu: tách tác dụng security-aware khỏi contrastive pair selection.

---

## 3.4. Câu hỏi 4: Contrastive pair selector có contribution riêng không?

### B5
- chọn vulnerable và safe độc lập.

### B6
- cùng candidate pool;
- dùng pair objective:

```text
SecSim(T,V)
+ SecSim(T,S)
+ 0.5 * CodeSim(V,S)
```

Giữ nguyên:
- 2 demo;
- label balance;
- prompt wording;
- instruction;
- model.

Comparison chính là B5 vs B6.

Nếu B6 không tốt hơn B5 thì pair-selection algorithm chưa chứng minh contribution riêng.

---

## 3.5. Demo-label flip test

Giữ nguyên target, demo code, order và prompt.
Chỉ đảo label ghi kèm demo.

Đo:
- prediction flip rate;
- correct → wrong;
- wrong → correct.

Chạy thêm repeated same-prompt baseline để biết natural model variability.

---

## 3.6. Demo order test

Contrastive prompt hiện vulnerable trước, safe sau.

Chạy thêm bản đảo:
- safe trước;
- vulnerable sau.

Nếu prediction thay đổi đáng kể thì prompt order đang gây bias.

---

# PHASE 4 — Xác nhận trên phạm vi lớn

Chỉ thực hiện khi Phase 3 có tín hiệu rõ.

## 4.1. Larger / full benchmark
- Devign full test.
- ReVeal làm external confirmation.

## 4.2. Statistical validation
- paired bootstrap 95% CI cho MCC/F1;
- McNemar trên paired errors;
- repeated runs nếu model stochastic.

## 4.3. Error analysis
Theo cùng IDs:
- baseline wrong → new correct;
- baseline correct → new wrong.

## 4.4. Cost analysis
Báo:
- retrieval time;
- preprocessing time;
- token count;
- LLM cost;
- latency.

---

# PHASE 5 — Chốt contribution nghiên cứu

### Nếu Security-aware thắng rõ
Contribution:
> security mechanism-aware reranking improves demonstration retrieval under controlled conditions.

### Nếu Balanced two-demo thắng, pair selector không thắng
Contribution:
> label-balanced ICL helps, nhưng contrastive pair algorithm chưa có lợi ích riêng.

### Nếu B6 thắng B5
Contribution mạnh hơn:
> security-context-aware contrastive pair selection adds value beyond balanced demonstrations.

### Nếu không có tín hiệu
Chuyển trọng tâm sang:
- reproduction study;
- analysis of GRACE implementation gap;
- prompt/model sensitivity;
- graph truncation;
- label noise;
- retrieval-label dependence.

Negative result được kiểm soát tốt vẫn có giá trị nghiên cứu.

---

# Phân công đề xuất

## Công việc chung
- chốt experimental contract;
- chốt split;
- chốt retrieval pool;
- chốt backbone;
- evaluator chung;
- run registry;
- manual retrieval rubric;
- review chéo kết quả.

## Hiếu
Chịu trách nhiệm chính:
- parser;
- checkpoint;
- security signature;
- SecSim synthetic tests;
- random-pair SecSim baseline;
- contrastive selector fallback;
- B5 vs B6;
- prompt order test;
- sửa wording/report cho đúng implementation.

## Dũng
Chịu trách nhiệm chính:
- đối soát V1/V2;
- export prediction-level outputs;
- chuẩn hóa config các component C1/C2/C4...;
- rerun các hypothesis trong common framework;
- mỗi run chỉ thay một component.

---

# Tiêu chí hoàn thành

Một phase chỉ hoàn thành khi:
- có artifact/reproducible output;
- config được lưu;
- target/demo IDs được lưu;
- evaluator chung tạo ra bảng metric;
- kết luận không vượt quá bằng chứng có được.
