# Nhật Ký Thay Đổi Sau Đăng Ký Trước (Changes After Preregistration)

Tài liệu này ghi nhận mọi điều chỉnh, bổ sung hoặc sửa đổi đối với giao thức nghiên cứu sau thời điểm khóa phiên bản `prereg-v1` (ngày 2026-10-31).

Mọi thay đổi cần được ghi rõ:
1. Ngày thực hiện.
2. Mục / tệp bị ảnh hưởng.
3. Bản chất thay đổi.
4. Lý do kỹ thuật / khoa học khách quan.
5. Tác động tới các giả thuyết nghiên cứu (H1.1–H6.1) và cam kết không thiên vị (unbiasedness commitment).

---

## Nhật Ký Phiên Bản

### [prereg-v1] — 2026-10-31
- **Trạng thái:** Bản gốc đăng ký trước chính thức (Original Preregistered Protocol).
- **Git Commit / Tag:** `prereg-v1`
- **Mã băm Manifest:**
  - Devign: `5a084a10e5c191039e56e351bf8d722fe017424f159a84d6b92be86a1d0f4952`
  - ReVeal: `59498c4a4ab038babe558675c183c2b104b0145590fb0accf8b02cd5440d57f7`
- **Ghi chú kỹ thuật bổ sung:**
  - Sao chép bản sao tệp cấu hình `configs/arms.yaml` (từ `grace_diag_kit/configs/arms.yaml`) ra thư mục gốc `configs/` để bảo đảm độ tương thích 100% với đường dẫn `arms_file: configs/arms.yaml` trong `configs/protocol.yaml` (theo khuyến nghị của Báo cáo kiểm toán độc lập).
  - Không làm thay đổi bất kỳ định nghĩa arm, giả thuyết hay mã băm manifest nào.

### [step5-threshold-locking] — 2026-10-31
- **Mục tiêu:** Thực hiện Bước 5: Tối ưu hóa và Khóa ngưỡng $\tau^*$ trên tập Validation chính thức.
- **Tệp bị ảnh hưởng:**
  - `configs/thresholds.json` (tạo mới): Khóa 14 ngưỡng tối ưu $\tau^*$ được chọn 100% trên Validation. Cam kết Zero-Test-Exposure.
  - `scripts/run_step5_matrix.py` (tạo mới): Bộ điều phối suy luận ma trận 15 arm theo 3 tầng (Tiers 1, 2, 3), kèm rào chắn cấm chạy split Test nếu chưa khóa ngưỡng.
  - `grace_diag_kit/src/grace_diag/llm_backend.py`: Cập nhật `FirstTokenScorer` tuân thủ chính sách Retry tối đa 5 lần với exponential backoff theo Hợp đồng thực nghiệm (`evaluation_contract.yaml`).
  - `grace_diag_kit/src/grace_diag/evaluate_final.py`: Bảo tồn nguyên vẹn metadata và chữ ký băm trong `thresholds.json`.
- **Tác động tới các giả thuyết H1.1–H6.1:** Hoàn toàn độc lập và trung lập; ngưỡng được khóa trước khi mở tập Test, ngăn chặn tuyệt đối thiên vị rò rỉ dữ liệu (p-hacking).

### [step5-v10-kaggle-optimization] — 2026-11-01
- **Mục tiêu:** Khắc phục lỗi tràn context và lãng phí GPU retry ở Version 9, tối ưu thông lượng cho Version 10.
- **Tệp bị ảnh hưởng:**
  - `grace_diag_kit/src/grace_diag/llm_backend.py`: Bổ sung cơ chế fail-fast (0 retry) khi gặp lỗi HTTP 400 Bad Request / context length exceeded (tránh lãng phí 2.5h GPU cho 120 mẫu), tích hợp connection pool `httpx.Limits(max_keepalive_connections=50, max_connections=100)` duy trì persistent HTTP socket.
  - `kaggle_notebooks/host_llm/host_llm_kaggle_server.ipynb` & `kaggle_notebooks/host_llm_kaggle_server.ipynb`: Nâng `--n_ctx 8192` và `--ctx-size 8192` (khớp hoàn toàn với ngân sách prompt của `TokenBudgetManager`), bổ sung tham số thông lượng `--n_batch 2048`, `--n_ubatch 512` và tự động kích hoạt Flash-Attention.
  - `tests/test_step5_matrix_execution.py`: Bổ sung unit test `test_backend_fail_fast_on_bad_request_or_context_exceeded`.
- **Tác động tới các giả thuyết H1.1–H6.1:** Không thay đổi bất kỳ giả thuyết hay phân bổ ngân sách nào; đưa tỷ lệ invalid_rate trên Devign B2 từ 4.39% về 0.0%, bảo toàn 100% 2,732 cặp mẫu cho các phép kiểm định thống kê H1.1 (McNemar, Paired Bootstrap).

