# So sánh kết quả ablation — Ablation V2

## Kết quả mới — Reproduced-Code-Based và Ablation V2

Các run dưới đây dùng pipeline Reproduced-Code-Based và các arm test_v2. Baseline Reproduced-Code-Based đã inference xong trên Devign (2.732 mẫu) và Reveal (2.274 mẫu). Đây là baseline theo profile Code với các điều chỉnh được khai báo trong run_manifest, không phải reproduction nguyên xi. Các arm có trạng thái complete đều có evaluation artifact; trạng thái complete không có nghĩa mọi phản hồi đều hợp lệ.

**Điều kiện đưa vào so sánh:** chỉ dùng kết quả mới từ notebook đã chuyển sang nền Reproduced-Code-Based. Khi rà ngày 2026-10-16, cả 32 notebook ablation đều gọi code_based_runner; cả 32 run_manifest trong test_v2 đều có schema code_based_ablation_v2, profile code và source_run_manifest_sha256 khớp baseline Code-Based của dataset tương ứng. Notebook chưa chuyển đổi phải được sửa trước, rồi chạy lại để có kết quả mới. Kết quả test/ của pipeline cũ không được đưa vào bảng hoặc dùng để kết luận hiệu quả component.

**Thiết lập và giới hạn cần đọc cùng bảng:**

- Embedding dùng CodeT5 pooling CLS, whitening fit chỉ trên train và cùng candidate pool/retrieval contract. Devign có hash checkpoint trong manifest nhưng không có model revision gốc để đối chiếu. Reveal tái sử dụng cache embedding CLS có thứ tự code hash đã xác minh; manifest ghi model equivalence là giả định cho run này và model revision chưa xác minh độc lập.
- CPG dùng graph Joern đã được kiểm tra theo record_id và code_sha256; graph coverage trong baseline là **95,61% Devign** và **95,12% Reveal**. Baseline dùng whole CPG theo contract 40 node/80 edge. Với C6, run dùng PDG có sẵn để slicing; nguồn biểu diễn graph này khác whole CPG baseline và là một giới hạn khi diễn giải riêng tác động C6.
- Các metric dựa trên phản hồi hợp lệ (N hợp lệ); cột Invalid cho biết số và tỷ lệ phản hồi bị evaluator loại. Vì vậy không xếp hạng arm chỉ bằng MCC/F1 khi tỷ lệ Invalid cao. Accuracy giữa hai dataset cũng không so trực tiếp. Δ MCC là MCC của hàng trừ baseline Reproduced-Code-Based cùng dataset.
- Devign hiện có evaluation cho **13/16 arm**: Full-cai-tien, Grace-baseline và No-C8 mới ở trạng thái chuẩn bị, chưa có inference hoàn tất. Reveal có evaluation cho **14/16 arm**; Full-cai-tien và Grace-baseline mới chuẩn bị. Baseline reproduced được báo cáo riêng trong bảng, không thay thế các arm thiếu này.

### Devign

| Arm | Trạng thái | N mục tiêu | N hợp lệ | Accuracy | Balanced Acc. | Precision | Recall | F1 | MCC | Δ MCC vs Code-Based | Invalid |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Reproduced-Code-Based (baseline) | complete | 2732 | 2732 | 54.76% | 52.70% | 51.42% | 27.41% | 35.76% | 0.0627 | +0.0000 | 0/2732 (0.00%) |
| Full cải tiến (C1–C8) | đã prepare, chưa inference | 2732 | — | — | — | — | — | — | — | — | — |
| Grace-baseline | đã prepare, chưa inference | 2732 | — | — | — | — | — | — | — | — | — |
| Bỏ C1 — hybrid retrieval | complete | 2732 | 2732 | 54.98% | 53.00% | 51.80% | 28.61% | 36.86% | 0.0686 | +0.0060 | 0/2732 (0.00%) |
| Bỏ C2 — stratified demo selection | complete | 2732 | 2726 | 54.26% | 52.19% | 50.45% | 26.66% | 34.88% | 0.0510 | -0.0116 | 6/2732 (0.22%) |
| Bỏ C3 — GEPA prompt optimization | complete | 2732 | 2732 | 55.31% | 52.96% | 52.98% | 24.06% | 33.10% | 0.0726 | +0.0099 | 0/2732 (0.00%) |
| Bỏ C5 — graph verbalization | complete | 2732 | 2732 | 55.71% | 53.70% | 53.30% | 28.92% | 37.50% | 0.0852 | +0.0225 | 0/2732 (0.00%) |
| Bỏ C6 — graph slicing | complete | 2732 | 2732 | 55.09% | 52.58% | 52.70% | 21.75% | 30.80% | 0.0657 | +0.0030 | 0/2732 (0.00%) |
| Bỏ C7 — security cot | complete | 2732 | 2731 | 55.25% | 53.47% | 52.18% | 31.47% | 39.26% | 0.0774 | +0.0147 | 1/2732 (0.04%) |
| Bỏ C8 — MMR demo selection | đã prepare, chưa inference | 2732 | — | — | — | — | — | — | — | — | — |
| Chỉ bật C1 — tri signal retrieval | complete | 2732 | 2732 | 54.80% | 52.88% | 51.40% | 29.32% | 37.34% | 0.0653 | +0.0026 | 0/2732 (0.00%) |
| Chỉ bật C2 — stratified demos | complete | 2732 | 2728 | 56.67% | 54.79% | 54.81% | 31.87% | 40.30% | 0.1079 | +0.0453 | 4/2732 (0.15%) |
| Chỉ bật C3 — GEPA prompt | complete | 2732 | 2603 | 54.90% | 52.47% | 52.00% | 22.85% | 31.74% | 0.0614 | -0.0012 | 129/2732 (4.72%) |
| Chỉ bật C5 — graph verbalization | complete | 2732 | 2267 | 54.21% | 52.13% | 51.22% | 23.90% | 32.60% | 0.0517 | -0.0110 | 465/2732 (17.02%) |
| Chỉ bật C6 — graph slicing | complete | 2732 | 2730 | 54.25% | 52.63% | 50.31% | 32.70% | 39.63% | 0.0572 | -0.0054 | 2/2732 (0.07%) |
| Chỉ bật C7 — security cot | complete | 2732 | 2627 | 54.59% | 51.73% | 53.55% | 13.66% | 21.77% | 0.0535 | -0.0091 | 105/2732 (3.84%) |
| Chỉ bật C8 — MMR selection | complete | 2732 | 1481 | 55.77% | 54.29% | 55.04% | 30.69% | 39.41% | 0.0975 | +0.0348 | 1251/2732 (45.79%) |

### Reveal

| Arm | Trạng thái | N mục tiêu | N hợp lệ | Accuracy | Balanced Acc. | Precision | Recall | F1 | MCC | Δ MCC vs Code-Based | Invalid |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Reproduced-Code-Based (baseline) | complete | 2274 | 2274 | 80.47% | 50.94% | 11.51% | 13.91% | 12.60% | 0.0173 | +0.0000 | 0/2274 (0.00%) |
| Full cải tiến (C1–C8) | đã prepare, chưa inference | 2274 | — | — | — | — | — | — | — | — | — |
| Grace-baseline | đã prepare, chưa inference | 2274 | — | — | — | — | — | — | — | — | — |
| Bỏ C1 — hybrid retrieval | complete | 2274 | 2128 | 81.20% | 52.24% | 13.23% | 16.11% | 14.53% | 0.0411 | +0.0238 | 146/2274 (6.42%) |
| Bỏ C2 — stratified demo selection | complete | 2274 | 1261 | 76.61% | 50.09% | 9.77% | 17.21% | 12.46% | 0.0014 | -0.0159 | 1013/2274 (44.55%) |
| Bỏ C3 — GEPA prompt optimization | complete | 2274 | 1344 | 82.66% | 53.14% | 15.71% | 16.06% | 15.88% | 0.0622 | +0.0449 | 930/2274 (40.90%) |
| Bỏ C5 — graph verbalization | complete | 2274 | 1238 | 83.36% | 54.41% | 16.67% | 18.64% | 17.60% | 0.0839 | +0.0667 | 1036/2274 (45.56%) |
| Bỏ C6 — graph slicing | complete | 2274 | 2273 | 83.06% | 53.54% | 16.45% | 16.52% | 16.49% | 0.0706 | +0.0533 | 1/2274 (0.04%) |
| Bỏ C7 — security cot | complete | 2274 | 2272 | 78.43% | 52.12% | 12.64% | 19.13% | 15.22% | 0.0355 | +0.0183 | 2/2274 (0.09%) |
| Bỏ C8 — MMR demo selection | complete | 2274 | 1699 | 81.05% | 52.43% | 12.22% | 17.42% | 14.36% | 0.0416 | +0.0243 | 575/2274 (25.29%) |
| Chỉ bật C1 — tri signal retrieval | complete | 2274 | 1340 | 78.58% | 48.91% | 9.20% | 11.03% | 10.03% | -0.0202 | -0.0375 | 934/2274 (41.07%) |
| Chỉ bật C2 — stratified demos | complete | 2274 | 2274 | 84.04% | 52.73% | 15.90% | 13.48% | 14.59% | 0.0587 | +0.0415 | 0/2274 (0.00%) |
| Chỉ bật C3 — GEPA prompt | complete | 2274 | 1905 | 79.58% | 52.60% | 13.33% | 18.85% | 15.62% | 0.0447 | +0.0275 | 369/2274 (16.23%) |
| Chỉ bật C5 — graph verbalization | complete | 2274 | 2092 | 80.40% | 51.20% | 12.02% | 14.49% | 13.14% | 0.0221 | +0.0048 | 182/2274 (8.00%) |
| Chỉ bật C6 — graph slicing | complete | 2274 | 2134 | 76.94% | 50.37% | 10.63% | 16.97% | 13.07% | 0.0061 | -0.0112 | 140/2274 (6.16%) |
| Chỉ bật C7 — security cot | complete | 2274 | 1116 | 85.22% | 54.58% | 19.57% | 16.51% | 17.91% | 0.0989 | +0.0816 | 1158/2274 (50.92%) |
| Chỉ bật C8 — MMR selection | complete | 2274 | 1479 | 80.73% | 51.46% | 12.15% | 14.86% | 13.37% | 0.0267 | +0.0094 | 795/2274 (34.96%) |

### Nhận xét về kết quả mới

- Trong các arm có evaluation, Devign có MCC cao nhất ở Chỉ bật C2 (0.1079; 4/2.732 invalid). Reveal cao nhất ở Chỉ bật C7 (0.0989), nhưng arm này có 1.158/2.274 invalid; trong các arm có ít nhất 99% phản hồi hợp lệ, Bỏ C6 có MCC cao nhất (0.0706; 1 invalid). Đây là mô tả kết quả hiện có, chưa phải kiểm định ý nghĩa thống kê.
- Tỷ lệ invalid cao ở một số arm làm metric valid-only có thể lệch. Các kết quả đó cần được sửa/đánh giá lại trước khi kết luận hiệu quả của component.

### Notebook còn cần chạy inference

Cả năm notebook đã có retrieval, prompts và freeze trong test_v2; hiện chưa có output inference/evaluation. Chọn kernel WSL, Restart Kernel rồi Run All; RUN_INFERENCE hiện đã đặt True.

| Dataset | Arm | Notebook |
|---|---|---|
| Devign | Full cải tiến | [full_cai_tien_devign.ipynb](Devign/Ablations/Full-cai-tien/full_cai_tien_devign.ipynb) |
| Devign | Grace-baseline | [grace_baseline_devign.ipynb](Devign/Ablations/Grace-baseline/grace_baseline_devign.ipynb) |
| Devign | Bỏ C8 | [no_c8_mmr_demo_selection_devign.ipynb](Devign/Ablations/No-C8-mmr-demo-selection/no_c8_mmr_demo_selection_devign.ipynb) |
| Reveal | Full cải tiến | [full_cai_tien_reveal.ipynb](Reveal/Ablations/Full-cai-tien/full_cai_tien_reveal.ipynb) |
| Reveal | Grace-baseline | [grace_baseline_reveal.ipynb](Reveal/Ablations/Grace-baseline/grace_baseline_reveal.ipynb) |

Nguồn số liệu: Reproduced-Code-Based/{devign,reveal}/test/completion.json và {Devign,Reveal}/Ablations/*/test_v2/evaluation/evaluation.json. Cache và artifact lịch sử vẫn nằm tại test/; các bảng lịch sử đã được loại khỏi báo cáo này để tuân thủ điều kiện so sánh ở trên.
