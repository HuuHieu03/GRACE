# Tóm Tắt Phiên Làm Việc (Session Summary): 2026-10-15

## 1. Mục Tiêu Chính
- Tiếp thu toàn bộ chỉ đạo học thuật từ Giảng viên Hướng dẫn theo tài liệu `project_docs/docs/yeu_cau_cua_thay_cho_Dung_va_Hieu.md`.
- Xây dựng và thực thi Kế hoạch Hành Động Chi Tiết Đợt 1 (`PLAN_SUPERVISOR_REQUIREMENTS_EXECUTION_20261014.md`).
- Giải quyết triệt để 4 chốt chặn kỹ thuật, khắc phục vấn đề thước đo giả tạo bằng Synthetic Ground-Truth Suite, kiểm toán rò rỉ dữ liệu và reparse dữ liệu cũ.
- Đồng bộ toàn bộ tài liệu học thuật và mã nguồn vào `project_docs/` và đẩy lên GitHub.

---

## 2. Công Việc Đã Thực Hiện & Kết Quả Đạt Được

1. **Khắc phục 4 chốt chặn kỹ thuật lõi**:
   - Loại bỏ cơ chế fail-to-mock âm thầm trong `src/evaluator.py`, ném `RuntimeError` khi thiếu API key.
   - Thêm mã băm Config Integrity Hash (SHA-256) khóa chặt cấu hình vào Checkpoint JSONL.
   - Sửa quy ước toán học Jaccard cho 2 tập rỗng về `0.0` thay vì `1.0` trong `src/security_signature/similarity.py`, triệt tiêu SecSim Inflation.
   - Bổ sung Telemetry theo dõi phân nhánh fallback trong `src/contrastive_selector.py`.

2. **Triệt tiêu "Vừa đá bóng vừa thổi còi" & Synthetic Ground-Truth**:
   - Thiết lập Khung đánh giá 3 Chân Kiềng (Triangulation: Downstream MCC, Blind Human Review, Synthetic Ground-Truth). Tạm hoãn CWE-alignment do Devign/ReVeal thiếu nhãn CWE chuẩn.
   - Nâng cấp parser ngoặc lồng nhau và thuật toán liên kết Guard - Sink (`is_effective`, `controlled_vars`).
   - Xây dựng bộ Synthetic Ground-Truth Suite (10 ca) và script `scripts/run_synthetic_ground_truth_eval.py`: Đạt 10/10 ca PASSED (100.0%), Average Margin đạt **+0.3304**.

3. **Kiểm toán rò rỉ mã nguồn (Code Leakage Audit)**:
   - Xây dựng script `scripts/audit_code_leakage.py` quét trên toàn bộ 45,050 mẫu thật của Devign và ReVeal.
   - Đo lường 3 mức độ: Exact (Devign: 3.95%, ReVeal: 2.29%), Normalized (Devign: 6.00%, ReVeal: 3.83%), Token Stream (Devign: 6.66%, ReVeal: 4.22%).
   - Phát hiện 26 ca nhãn mâu thuẫn (Contradictory Labels: 19 Devign, 7 ReVeal) giữa Train và Test, xác thực cảnh báo của Thầy về hiện tượng nhiễu nhãn (Label Noise) trong benchmark công khai.

4. **Đối soát & Reparse kết quả cũ**:
   - Sử dụng `src/common_evaluator.py` quét lại `output/results_grace_exp.json` (26 mẫu `gpt-oss-20b`).
   - Vạch trần 8/26 mẫu (30.77%) bị rỗng phản hồi nhưng parser cũ đã tự động ép về 0 (Safe), trong đó có 5 ca là lỗ hổng thật (GT=1).
   - Khôi phục Recall thực chất đạt 71.43% và F1 đạt 0.50, nhưng MCC thực chất chỉ là -0.0141 với Predicted Vulnerable Rate = 72.22% (chứng minh mô hình bị thiên vị đoán 1 chứ chưa phân biệt được code).

5. **Kiểm thử tự động & Đồng bộ Git**:
   - 100% các unit tests trong 9 modules `tests/` đều PASS hoàn hảo (24+ tests).
   - Đã rebase mượt mà với commit của Dũng (`chore: finalize shared inference evaluation contract`) và push lên remote `origin/main` (commit `1e45628`).

---

## 3. Trạng Thái & Hướng Đi Tiếp Theo
- **Trạng thái**: Đợt 1 đã chính thức hoàn thành 100% và được nghiệm thu toàn diện.
- **Kế hoạch tiếp theo (Đợt 2)**:
  1. Thí nghiệm 2.1: Xây dựng script `scripts/run_label_flip_test.py` (Label-Flip Control Test).
  2. Thí nghiệm 2.3: Chuẩn bị bảng chấm mù độc lập (Human Blind Review 50 Devign + 50 ReVeal).
  3. Thí nghiệm 2.2: Chạy thực nghiệm đối chứng cô lập B2 (BM25) vs B3 (Security Reranker) trên Dev Set 100–200 mẫu sạch.
