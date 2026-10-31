# H3-B validation — Kaggle DeepSeek V4.1 — 2026-10-24

Lượt validation do **Hiếu chạy** trên Kaggle bằng Vertex AI, dùng model
`deepseek-ai/deepseek-v4.1-flash-maas`, context 8.192 UTF-8 bytes, temperature
0, seed 42 và `max_tokens=256`.

Đây là lần chạy lại trên đúng cohort prompt H3-B `baseline_whitening` / `validation`:

- Devign: 2.724/2.724 prediction hợp lệ; metric P/R/F1 = 48,11/33,28/39,34%, MCC 0,0614.
- ReVeal: 2.196/2.196 prediction hợp lệ; metric P/R/F1 = 14,44/7,47/9,85%, MCC 0,0499.
- ID, `code_sha256`, `prompt_sha256` trong prediction giữ nguyên thứ tự và khớp toàn cohort prompt đã đóng băng. Prompt gốc được liên kết trong bảng quản lý run.
- Mỗi dataset có prediction, raw response, evaluation và manifest. Báo cáo gộp ở `baseline_comparison_report.json`.
- ZIP kết quả không chứa notebook Kaggle đã thực thi. Prediction không lưu ground truth dùng được; metric được giữ nguyên trong `evaluation.json`.

## Nguồn

- ZIP nguồn: `D:/JUNIOR/LabThayTho/SHARE_BASELINE_WHITENING_DEVIGN_REVEAL_VALIDATION_CONTEXT8192_20261023/H2_vertex_validation_kaggle_results.zip`
- SHA-256 ZIP: `17E8829944E927C4F2AAF77B1A6D76C818D075CB68350FEEC133CAE96CE57E43`
- Cohort Devign xuất phát từ H3-B run `f79c31718971e534`; prompt SHA-256: `58a0296e7c610f3fe7e3b8ab8e96d74489a437873f72b71956e90dbb6706b743`.
- Cohort ReVeal xuất phát từ H3-B run `27ee63ea9ec23f93`; prompt SHA-256: `e80d9e19359b65c39979b93bf02260b07658c80ec37ad4ada49d497dab9f2d36`.
- Chi tiết nguồn máy và cấu hình được lưu trong [`provenance.json`](provenance.json).

Đây là run ưu tiên cho hai cohort validation trên. Các dòng mixed Qwen/DeepSeek
cũ vẫn được giữ trong bảng làm lịch sử. Không gộp hai lần chạy thành một run.
