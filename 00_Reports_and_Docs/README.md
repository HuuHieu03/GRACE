---
category: "Reports & Academic Documentation (Official Submission)"
author: "Nhóm nghiên cứu sinh viên (Nguyễn Hữu Hiếu & Trần Tiến Dũng)"
role: "Nghiên cứu viên / Người thực hiện"
parent_project: "GRACE Enhancement Study"
last_updated: "2026-10-24"
status: "OFFICIAL_SUBMISSION_FOLDER"
---

# 00_Reports_and_Docs: Thư Mục Báo Cáo Nghiệm Thu Chính Thức Gửi Thầy Hướng Dẫn

> 📌 **CHỈ DẪN CHO THẦY HƯỚNG DẪN & HỘI ĐỒNG NGHIỆM THU**:  
> Thư mục `00_Reports_and_Docs/` là **thư mục chính thức duy nhất** lưu trữ các báo cáo khoa học học thuật, tài liệu tổng kết, kết quả nghiệm thu và dữ liệu đối chứng của đề tài **GRACE**. Thầy và người đọc vui lòng đọc trực tiếp báo cáo tiến độ và nghiệm thu tại thư mục này.  
> *(Ghi chú: Thư mục `project_docs/` là không gian làm việc cá nhân / nội bộ của nhóm sinh viên Hiếu & Dũng, chứa ghi chú làm việc, kế hoạch kỹ thuật chi tiết, log thực thi và bảng chấm nháp).*

---

## 1. Báo Cáo Tiến Độ & Nghiệm Thu Chính Thức Mới Nhất

- 🎯 📄 [`bao_cao_chung_Dung_Hieu_gui_thay.md`](bao_cao_chung_Dung_Hieu_gui_thay.md) *(BÁO CÁO TIẾN ĐỘ CHUNG DŨNG & HIẾU - CẬP NHẬT 25/10/2026)*:
  * Tổng hợp đối soát nền thực nghiệm Đợt 1, kết quả thăm dò Đợt 2 của cả hai bạn, rà soát các giới hạn kỹ thuật (Over-sensitization, FP/recall trade-off) và đề xuất kế hoạch thực hiện Đợt 3.
  * Kèm theo: 📄 [`cac_diem_can_thong_nhat_Dung_Hieu.md`](cac_diem_can_thong_nhat_Dung_Hieu.md) *(Bảng 6 điểm kỹ thuật cần thống nhất giữa Dũng và Hiếu trước khi chạy Test Set)*.

- 🎯 📄 [`BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md`](BAO_CAO_TIEN_DO_NGHIEM_THU_GRACE_20261022.md) *(BÁO CÁO TOÀN DIỆN & ĐỐI SOÁT CHI TIẾT - PHÍA HIẾU)*:
  * **BÁO CÁO TIẾN ĐỘ TOÀN DIỆN VÀ KẾT QUẢ THỰC NGHIỆM ĐỀ TÀI GRACE (KIỂM ĐỊNH ĐỘC LẬP TÍNH ĐÁNG TIN CẬY KHOA HỌC & BÓC TÁCH KỸ THUẬT)**
  * **Trọng tâm đối soát & nghiệm thu**:
    1. **Stage 2 Label-Flip Control Test trên Baseline B2**: Net Sensitivity = 31.0%, Natural Variance = 4.0%, F1 = 0.3415 trên `devign_dev_clean_100_ids.json`.
    2. **Stage 3 Đối đầu B3 (Contrastive) vs B2 (1-shot) trên Devign**: Recall tăng gấp 2.2 lần (27.8% lên 61.1%, +18 lỗ hổng nguy hiểm), F1 tăng từ 36.1% lên 55.0% (+18.9%, Paired Bootstrap 95% CI `[+0.0710, +0.3093]`).
    3. **Stage 3 Cross-dataset trên ReVeal**: F1 tăng từ 38.9% lên 51.8%, Recall tăng từ 28.0% lên 44.0%, MCC dương +0.1887; lát cắt mở rộng ghi nhận F1 tăng từ 33.3% lên 46.2%, Recall tăng từ 20.0% lên 60.0%.
    4. **Ablation B3-NoDiff**: Bóc tách định lượng đóng góp của Cặp tương phản 1:1 (82.6% mức tăng F1, nền tảng chống lệch nhãn) và khối Core Security Difference (17.4% mức tăng F1, cứu thêm 5 lỗi tinh vi, kiểm soát FP).
    5. **Blind Human Review 100 mẫu (50 Devign + 50 ReVeal)**: Do Hiếu và Dũng trực tiếp đọc mã C bằng mắt độc lập, hòa giải kỹ thuật (Adjudication) trên dòng code C cụ thể (Sink, Guard, Variable). Giữ nguyên hệ số Cohen's Kappa trước hòa giải: Devign $\kappa = 0.315$ (0.3151), ReVeal $\kappa = 0.340$ (0.3271 thô), $P_o = 48.0\%$.
    6. **Khắc phục triệt để mapping canonical C**: 50/50 mẫu ReVeal khớp 100% file canonical C trên đĩa và split sạch.
    7. **Minh bạch hạ tầng**: Giải trình sự cố đối tác Google Cloud đóng endpoint Qwen3-Coder MaaS sau 21/10 và đề xuất di chuyển sang Gemini 1.5 Flash/Pro.

---

## 2. Báo Cáo Chuyên Đề & Thiết Kế Kỹ Thuật Lịch Sử

- 📄 [`01_Stage5_Contrastive_Benchmark_Report.md`](01_Stage5_Contrastive_Benchmark_Report.md) *(28.5 KB)*:
  * Báo cáo nghiên cứu cơ chế *Vulnerability-Aware Contrastive Demonstration Retrieval (VAC-Retrieval)* trên 100% Test set của 2 bộ benchmark (2,732 Devign & 2,274 ReVeal).
- 📄 [`02_Baseline_Reproduction_and_Discrepancy_Report.md`](02_Baseline_Reproduction_and_Discrepancy_Report.md) *(14.8 KB)*:
  * Phục dựng baseline chuẩn mực và đối chiếu chỉ ra 5 lỗi kỹ thuật trong mã nguồn gốc của tác giả (đảo ngược prompt, ép vector 256d, thiếu Joern extractor, mã rác Solidity/Java).
- 📄 [`03_Retrieval_Failure_Analysis_Report.md`](03_Retrieval_Failure_Analysis_Report.md) *(7.2 KB)*:
  * Khảo sát định lượng chứng minh sự thất bại của giả định tương đồng bề mặt: 47.58% (Devign) và 71.43% (ReVeal) các ca truy xuất bị ngược nhãn.
- 📄 [`04_Vulnerability_Aware_Contrastive_Design.md`](04_Vulnerability_Aware_Contrastive_Design.md) *(17.8 KB)*:
  * Bản thiết kế kiến trúc và giải tích toán học của cơ chế chọn cặp ví dụ tương phản (Contrastive ICL Pair Selection).

---

## 3. Dữ Liệu Đối Chứng & Bài Báo Gốc

- 📊 [`retrieval_failure_analysis_devign.csv`](retrieval_failure_analysis_devign.csv) *(242 KB)*: Dữ liệu phân loại chi tiết lỗi truy xuất trên 2,732 hàm Devign.
- 📊 [`retrieval_failure_analysis_reveal.csv`](retrieval_failure_analysis_reveal.csv) *(204 KB)*: Dữ liệu phân loại chi tiết lỗi truy xuất trên 2,274 hàm ReVeal.
- 📕 [`GRACE_Empowering_LLM_Original_Paper.pdf`](GRACE_Empowering_LLM_Original_Paper.pdf) *(1.41 MB)*: Bản PDF bài báo khoa học gốc công bố phương pháp GRACE.
