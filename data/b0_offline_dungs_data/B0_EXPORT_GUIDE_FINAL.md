# Bước 0 — hướng dẫn và trạng thái export cuối

## Kết quả hiện có

Đã xuất xpre 34 chiều, gate và join đầy đủ cho cả hai dataset:

- `xpre_validation_devign.npz`, `xpre_test_devign.npz`
- `xpre_validation_reveal.npz`, `xpre_test_reveal.npz`
- `devign_gate_validation_exact.csv`, `devign_gate_test_exact.csv`
- `reveal_gate_validation_exact.csv`, `reveal_gate_test_exact.csv`
- `devign_validation_join_with_fpt.csv` (2.732 dòng), `devign_test_join_exact.csv` (2.732 dòng)
- `reveal_validation_join_with_fpt.csv` (2.273 dòng), `reveal_test_join_exact.csv` (2.274 dòng)
- `complementarity_devign_fpt_mixed.json`, `complementarity_reveal_fpt_mixed.json`

`X[:,5]` là p_gate; score test đã khớp file gate của H3-B run `5fc21bd7cafff9846aff` với sai số tuyệt đối nhỏ hơn 1e-5. Join CSV theo đúng thứ tự ID của xpre, ID/hash đã đối chiếu; Devign tau=0.39, ReVeal tau=0.19.

## 85 bản ghi đã bổ sung

Lý do thiếu ban đầu: lượt validation cũ tạo prompt cho 2.724 Devign và 2.196 ReVeal; 8 và 77 ID còn lại không có trong prompt cohort, chứ không phải request LLM thất bại. Đã chạy lại pipeline tạo prompt cho đúng các ID thiếu và gọi FPT AI Factory, model `DeepSeek-V4.1-Flash`, temperature=0, seed=42, max_tokens=256, thinking=false. Cả 85/85 phản hồi parse được nhãn 0/1.

- `fpt_v41_validation_fill_raw.jsonl`: raw response, prompt hash, trạng thái request/parse, usage và provenance.
- `fpt_v41_validation_fill_predictions.jsonl`: prediction parse cho 85 ID.
- `fpt_v41_validation_fill_manifest.json`: cấu hình và số lượng.
- `validation_missing_ids_resolved.csv`: mapping ID/hash/nhãn với prediction và checksum phản hồi.
- Prompt/retrieval/graph index mới được lưu dưới các thư mục `runs/...` trong B0_offline và có trong ZIP.

85 dòng mới được đánh dấu nguồn `FPT AI Factory / DeepSeek V4.1 Flash`; các dòng cũ vẫn là `Vertex AI MaaS / DeepSeek V4.1 Flash`. Vì vậy validation và complementarity là cohort mixed-provider; không coi kết quả là một benchmark đồng nhất provider. Với 77 prompt ReVeal mới, graph coverage là 77,9%; prompt vẫn ghi rõ graph unavailable ở những mẫu Joern không trích được graph. Devign coverage là 100%.

## File phân tích

Hai `complementarity_*_fpt_mixed.json` có repair/harm theo lớp, ALL-0/ALL-1/RANDOM, oracle ceiling, validation OOF P_pre/P_post, CI trên test và routing theo ngân sách. Đã sửa lỗi CLI bootstrap group; dùng script đóng gói `complementarity_fixed_v2.py` cùng source `grace_diag`.

Việc đối chiếu toàn bộ metric lịch sử của mục 2.1 trong đề cương với sai khác <=0.001 chưa được ghi nhận ở lượt này; các JSON trên là đầu ra complementarity dùng cohort mixed-provider.

## Tái tạo xpre

Checkpoint/model metadata yêu cầu Python 3.12.13, joblib 1.6.0, NumPy 2.5.4, scikit-learn 1.9.1, SciPy 1.18.1. Môi trường riêng tại `D:\JUNIOR\LabThayTho\.venv-b0-312`; source/data/cache/checkpoint đã dựng trong staging `D:\JUNIOR\LabThayTho\tmp\b0_h3b_exact_sjh9nczr`.

Chạy `export_xpre_test.py` cho dataset `devign`/`reveal` và split `validation`/`test`, với manifest tương ứng:

- Devign: `artifacts/h3v2/base/devign/42/f6d28bb5a30eed5a3201/manifest.json`
- ReVeal: `artifacts/h3v2/base/reveal/42/9e5b6bc3bb5e930e1497/manifest.json`

Không dùng in-sample train features cho meta-fit; nếu cần train thì dùng OOF `train_nested_oof.npy` cùng `folds.json`.
