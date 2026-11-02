# Tóm Tắt Phiên Làm Việc (Session Summary): 2026-11-02

## 1. Mục Tiêu Chính
- Nghiệm thu kết quả đợt chạy suy luận ma trận trên Kaggle GPU (Version 10) cho tập kiểm thử Devign Test ($N = 2,732$ mẫu).
- Kiểm toán toàn diện từng cell trong Notebook Kaggle nhằm bảo đảm không có lỗi dây chuyền làm sai lệch số liệu.
- Đối soát các chỉ số khoa học chính thức: Bảng A (Hiệu năng tại ngưỡng khóa $\tau^*$), Bảng B (Kiểm định tương phản H1.1, McNemar test, Cluster Bootstrap 95% CI).
- Đóng gói toàn bộ mã nguồn sạch, tài liệu của Thầy và kết quả thực nghiệm thành một gói lưu trữ kiểm toán độc lập (`audit_package_grace.zip`) loại bỏ hoàn toàn các thành phần dư thừa.
- Cập nhật đầy đủ hệ thống tài liệu nội bộ trong `project_docs/` và đồng bộ lên GitHub.

---

## 2. Công Việc Đã Thực Hiện & Kết Quả Đạt Được

1. **Nghiệm thu thành công Version 10 trên Kaggle 2× Tesla T4 GPU**:
   - Khắc phục triệt để lỗi tràn context bằng cờ `--n_ctx 8192` trong `llama-server`.
   - Đạt tỷ lệ hợp lệ **100.0% (`invalid_rate = 0.00%`)** trên toàn bộ 5,464 requests (2,732 cho Arm B0 và 2,732 cho Arm B2).
   - Tối ưu hóa pipeline suy luận, rút ngắn thời gian từ 7.5 giờ xuống **3.92 giờ (14,141s - nhanh gấp 2 lần)**.
   - Kiểm toán từng cell trong notebook: Toàn bộ 22 cell đều kết thúc thành công (`exit_code: 0`).

2. **Chốt số liệu Bảng A & Bảng B khoa học chính thức**:
   - **Bảng A** (Tại ngưỡng khóa $\tau_{B0}^* = 0.08, \tau_{B2}^* = 0.98$):
     - Devign Test B0: AUROC = 0.5392, AUPRC = 0.5109, MCC = 0.0484, BA = 0.5238, F1 = 0.5403.
     - Devign Test B2: AUROC = 0.5394, AUPRC = 0.4940, MCC = 0.0743, BA = 0.5358, F1 = 0.4478.
   - **Bảng B** (Tương phản giả thuyết H1.1 B0 vs B2):
     - $\Delta\text{AUROC} = +0.000244$ (95% CI: $[-0.019390, +0.020274]$).
     - $\Delta\text{MCC} = +0.025925$ (95% CI: $[-0.020615, +0.070114]$).
     - Kiểm định McNemar: $b = 438, c = 522, \chi^2 = 7.18, p = 0.007388 < 0.01$ (thay đổi hành vi phân loại có ý nghĩa thống kê cao).
     - Kết luận khoa học: `inconclusive` theo tiêu chuẩn preregistration nghiêm ngặt.

3. **Xây dựng công cụ và đóng gói bộ kiểm toán (`audit_package_grace.zip`)**:
   - Viết script tự động [`scripts/create_audit_package.py`](../../scripts/create_audit_package.py) và tài liệu chỉ dẫn [`AUDIT_README.md`](../../AUDIT_README.md).
   - Bảo toàn 100% tài liệu Thầy gửi trong `00_Reports_and_Docs/` và `project_docs/docs/`.
   - Lưu trữ mã nguồn sạch, các script vận hành, 111 bài kiểm thử pytest (100% Passed), dữ liệu offline Bước 0 chuẩn hóa, specs nén và kết quả Bảng A, Bảng B.
   - Lược bỏ hoàn toàn các thành phần dư thừa: `.git/` (tiết kiệm ~236 MB), cache `runs/**/_cache/` (>4,800 file json), dữ liệu thô Joern (8.9 GB), các file zip cũ dung lượng lớn (473MB, 310MB), và các tệp cấu hình bảo mật.
   - Tệp nén hoàn thành với dung lượng **119.87 MB** (628 tệp), kiểm thử tính toàn vẹn CRC32 đạt 100%.

4. **Đồng bộ hóa tài liệu nội bộ & Git**:
   - Thêm báo cáo kỹ thuật nghiệm thu: `project_docs/reports/v1.0.0_2026-11-02_nghiem_thu_toan_dien_version10_va_goi_audit_report.md`.
   - Thêm báo cáo tiến độ: `project_docs/progress/v1.0.0_2026-11-02_hoan_thanh_step5_va_dong_goi_audit_progress.md`.
   - Thêm nhật ký kỹ thuật: `project_docs/logs/v1.0.0_2026-11-02_step5_kaggle_v10_and_audit_packaging_log.md`.
   - Cập nhật mục lục `project_docs/README.md`.
   - Commit và push toàn bộ lên nhánh `main` của repository GitHub.

---

## 3. Trạng Thái Hiện Tại & Sẵn Sàng Nghiệm Thu
- **Trạng thái**: Đề tài đã hoàn tất trọn vẹn cả 5 Bước theo đúng Đề cương hợp nhất.
- **Hồ sơ bàn giao**: Đã có sẵn tệp `audit_package_grace.zip` kèm `AUDIT_README.md` tại thư mục gốc để bàn giao cho Thầy và Hội đồng kiểm toán bất kỳ lúc nào.
