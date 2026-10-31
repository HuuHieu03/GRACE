# B0_offline — nội dung và provenance

> Đính chính 30/10/2026: các JSON complementarity đã được chạy lại và ZIP FINAL đã được cập nhật. Xem `CORRECTION_20261030.md`.

> Ngưỡng chính theo B3 là train OOF: dùng `runs/complementarity_<dataset>.train_oof.json`. Các JSON không có hậu tố là mốc gate_tuned trên validation. Xem `THRESHOLD_POLICIES_20261030.md`.

Bộ đầu ra chính cho Bước 0. Bản canonical có 36 run lịch sử, 90.108 target rows; metric tái tính so với file evaluation có sai khác tối đa 5.56e-17. H3-B dùng checkpoint đã khóa `a93a831ac8416426a1d4` (Devign) / `b4564696e647259a09b9` (ReVeal), gate thresholds 0.53/0.14.

- `xpre_{validation,test}_{devign,reveal}.npz` và các CSV `*_gate_*_exact.csv`, `*_join_*.csv`: bản chuẩn theo checkpoint đã khóa.
- `canonical_historical_36.csv`, `metric_reproduction_historical_36.{json,csv}`: lịch sử per-item và kiểm tra metric.
- `section2_1_full_reproduction.json`: audit per-item H1/H2/H3-A/H3-B, cùng registry hash nguồn.
- `runs/complementarity_{devign,reveal}.json`: phân tích H3-B có provenance.
- `fpt_v41_validation_fill_*` và `validation_missing_ids_resolved.csv`: 85 validation ID được gọi bổ sung; mỗi dòng ghi nguồn FPT. Validation cohort mixed-provider.

Các tóm tắt dựa trên chấm mù cần phiếu từng người chấm để tái tạo. Không suy ra phiếu cá nhân từ tổng kết. Chi tiết xem `B0_EXPORT_GUIDE_FINAL.md` ở thư mục gốc của gói.
