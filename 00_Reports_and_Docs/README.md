---
category: "Reports & Academic Documentation"
author: "Nguyễn Hữu Hiếu"
role: "Nghiên cứu viên / Người thực hiện"
parent_project: "GRACE Enhancement Study"
last_updated: "2026-08-31"
---

# 00_Reports_and_Docs: Danh Mục Báo Cáo Nghiên Cứu Khoa Học GRACE

Thư mục này tập trung toàn bộ các báo cáo khoa học, dữ liệu đối chứng và bài báo gốc của đề tài nghiên cứu cải tiến phương pháp **GRACE (Graph Structure and In-Context Learning for Vulnerability Detection)**.

## 1. Báo Cáo Khoa Học Tinh Hoa
- 📄 [`01_Stage5_Contrastive_Benchmark_Report.md`](01_Stage5_Contrastive_Benchmark_Report.md) *(28.5 KB)*:
  * **Báo cáo nghiên cứu quan trọng nhất (Stage 5)**: Đột phá phương pháp *Vulnerability-Aware Contrastive Demonstration Retrieval (VAC-Retrieval)* trên 100% Test set của 2 bộ benchmark bảo mật (2,732 mẫu Devign & 2,274 mẫu ReVeal).
  * **Thành tựu**: Devign Recall tăng vọt **+7.73%** (26.61% -> 34.34%), F1 tăng **+5.84%** (35.82% -> 41.66%), bắt trúng thêm **+97 lỗ hổng thực tế**.
- 📄 [`02_Baseline_Reproduction_and_Discrepancy_Report.md`](02_Baseline_Reproduction_and_Discrepancy_Report.md) *(14.8 KB)*:
  * Phục dựng baseline chuẩn mực và đối chiếu vạch trần **5 sai lệch & lỗi nghiêm trọng trong mã nguồn gốc của tác giả** (đảo ngược prompt, ép vector 256d, thiếu công cụ Joern, mã rác Solidity/Java).
- 📄 [`03_Retrieval_Failure_Analysis_Report.md`](03_Retrieval_Failure_Analysis_Report.md) *(7.2 KB)*:
  * Khảo sát định lượng chứng minh sự thất bại của giả định tương đồng bề mặt: **47.58% (Devign)** và **71.43% (ReVeal)** các ca truy xuất bị ngược nhãn, khiến LLM bỏ sót lỗ hổng.
- 📄 [`04_Vulnerability_Aware_Contrastive_Design.md`](04_Vulnerability_Aware_Contrastive_Design.md) *(17.8 KB)*:
  * Bản thiết kế kiến trúc và giải tích toán học của cơ chế chọn cặp ví dụ tương phản (Contrastive ICL Pair Selection).

## 2. Dữ Liệu Thực Nghiệm Chi Tiết & Bài Báo Gốc
- 📊 [`retrieval_failure_analysis_devign.csv`](retrieval_failure_analysis_devign.csv) *(242 KB)*: Dữ liệu phân loại chi tiết lỗi truy xuất trên 2,732 hàm Devign.
- 📊 [`retrieval_failure_analysis_reveal.csv`](retrieval_failure_analysis_reveal.csv) *(204 KB)*: Dữ liệu phân loại chi tiết lỗi truy xuất trên 2,274 hàm ReVeal.
- 📕 [`GRACE_Empowering_LLM_Original_Paper.pdf`](GRACE_Empowering_LLM_Original_Paper.pdf) *(1.41 MB)*: Bản PDF bài báo khoa học gốc công bố phương pháp GRACE.
