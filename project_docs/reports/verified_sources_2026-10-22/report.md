---
version: "1.0.0"
date: "2026-10-22"
type: "report"
status: "COMPLETED"
summary: "Đối soát nguồn số liệu; chỉ xác nhận trong phạm vi bằng chứng còn lưu."
---

# Nguồn số liệu được đối soát

Đây là bảng tiến độ có giới hạn truy vết, không phải nghiệm thu cải tiến. Script tái tính metric B3 từ toàn bộ IDs/labels, so với JSON bản tải về và đối chiếu CSV. Các nguồn đầu vào có SHA-256 trong source_registry.json.

| Run | N | F1 | MCC | Balanced accuracy | Raw / actual prompt |
|---|---:|---:|---:|---:|---|
| stage3_devign_ver03 | 100 | 0.5500 | -0.1118 | 0.4469 | unavailable_in_export / unavailable_in_export |
| stage3_reveal_ver04 | 100 | 0.5176 | 0.1887 | 0.5900 | unavailable_in_export / unavailable_in_export |
| stage3_devign_nodiff_ver05 | 100 | 0.5138 | -0.0686 | 0.4658 | unavailable_in_export / unavailable_in_export |
| stage2_devign_original_b2 | 100 | 0.3415 | -0.0500 | 0.4775 | available_300_responses / unavailable_in_export |

`verified_metrics.csv` cung cấp đầy đủ TP/TN/FP/FN, precision/recall, coverage/invalid, predicted vulnerable rate và hai trivial baselines trên cùng IDs; JSON giữ metric cấu trúc và hash nguồn. Bảng rút gọn trên không thay thế các chỉ số đó.

B2 aggregate và paired CI trong Stage 3 được giữ ở registry dưới nhãn reported-only vì thiếu export per-ID B2 của chính run. Stage2 B2 là run khác, không tự thay thế Stage3 B2.

Các CI ΔMCC/ΔBA đã báo chứa 0; chưa đủ bằng chứng lợi ích. Không dùng các tỷ lệ order-swap để kết luận label sensitivity giảm. Full–NoDiff không chứng minh đóng góp nhân quả theo phần trăm.

## Các bảng lịch sử

- `output/stage3/b3_vs_b2_comparison_report.csv`: **consistent_with_json**, 0 sai lệch metric được phát hiện.
- `output/stage3/reveal_b3_vs_b2_comparison_report.csv`: **consistent_with_json**, 0 sai lệch metric được phát hiện.
- `output/stage3/ablation_nodiff_comparison_report.csv`: **consistent_with_json**, 0 sai lệch metric được phát hiện.
- `output/stage3/b3_vs_b2_comparison_summary.csv`: **EXCLUDED_CONFLICT**, 14 sai lệch metric được phát hiện.

CSV summary mâu thuẫn được giữ nguyên để truy vết nhưng loại khỏi nguồn dùng cho bảng/slide. Không suy đoán nguồn sinh của nó.

## Phần chưa nghiệm thu

- Split/UID/leakage và code/identity trong bộ chấm ReVeal còn lỗi đã nêu trong review lần hai.
- Chưa xác nhận hai người chấm mù độc lập; không dùng kappa/confirmed CSV để tuyên bố ưu thế retrieval.
- H2 là kết quả selection R1 đổi 0/100, chưa xác nhận relevance hoặc detection quality.

Tái lập: `python scripts/reconcile_experiment_sources.py`. Script không gọi API hoặc sửa artifact gốc.
