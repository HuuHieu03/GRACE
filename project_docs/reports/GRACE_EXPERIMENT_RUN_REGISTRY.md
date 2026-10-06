# GRACE Experiment Run Registry (Bảng Quản Lý Thực Nghiệm Chung)

Bảng quản lý tập trung toàn bộ các lần chạy benchmark theo yêu cầu tại **STEP 3 của GRACE Immediate Action Plan** và mục 1.1 thư phản hồi của GVHD.
Mỗi run là một dòng định danh độc nhất, lưu vết chi tiết từ Commit Git, Dataset Split, Backbone LLM, Tham số suy luận, đến đường dẫn tệp kết quả thô.

---

## 1. Bảng Tổng Hợp Các Lần Chạy Thực Nghiệm (Run Registry Matrix)

| Run ID | Owner | Git Commit | Dataset | Test Size (Total / Vuln / Safe) | Retrieval Bank Pool | Backbone Model / Provider | Inference Config (Temp / MaxTok) | Prompt Mode | Retrieval Mode | Candidate Top-N | Prediction & Raw Response File | Ghi chú / Trạng thái Đối soát |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `run_devign_origin_baseline_v12` | Hieu | `b7e8096` | `DetectVul/devign` | 2,732 (1,255 / 1,477) | Full Train (21,854) | `gemma-4-26B-A4B-it` (FPT AI) | Temp=0.0, MaxTokens=256 | `standard_1shot` (Figure 6) | GRACE Baseline (CodeT5 + Jaccard/GraphSim) | Top-5 | `kaggle_notebooks/.../Ver12` / `kaggle.log` | Baseline chuẩn bài báo gốc; Chạy 100% test set |
| `run_reveal_origin_baseline_v13` | Hieu | `b7e8096` | `SensorLLM/Reveal` | 2,274 (230 / 2,044) | Full Train (18,187) | `gemma-4-26B-A4B-it` (FPT AI) | Temp=0.0, MaxTokens=256 | `standard_1shot` (Figure 6) | GRACE Baseline (CodeT5 + Jaccard/GraphSim) | Top-5 | `kaggle_notebooks/.../Ver13` / `kaggle.log` | Baseline chuẩn bài báo gốc trên ReVeal |
| `run_devign_contrastive_v4` | Hieu | `b7e8096` | `DetectVul/devign` | 2,732 (1,255 / 1,477) | Full Train (21,854) | `gemma-4-26B-A4B-it` (FPT AI) | Temp=0.0, MaxTokens=256 | `contrastive_2shot` (Counterexample) | Security-Aware + Contrastive Pair | Top-50 (SecSim) | `kaggle_notebooks/.../Ver 4_1st time` | Stage 5 Contrastive ICL chính; Bắt thêm +97 lỗ hổng |
| `run_reveal_contrastive_v4` | Hieu | `b7e8096` | `SensorLLM/Reveal` | 2,274 (230 / 2,044) | Full Train (18,187) | `gemma-4-26B-A4B-it` (FPT AI) | Temp=0.0, MaxTokens=256 | `contrastive_2shot` (Counterexample) | Security-Aware + Contrastive Pair | Top-50 (SecSim) | `kaggle_notebooks/.../Ver 4_1st time` | Stage 5 Contrastive ICL trên ReVeal |
| `ablation_devign_zero_shot` | Hieu | `b7e8096` | `DetectVul/devign` | 272 (125 / 147) | N/A (No demo) | `gemma-4-26B-A4B-it` (FPT AI) | Temp=0.0, MaxTokens=256 | `zero_shot` | Không dùng Demonstration | N/A | `kaggle_notebooks/.../Ver 4_1st time` | Ablation 10% Devign; train_sample_ratio vô tình bị rút xuống 10% |
| `ablation_devign_grace_baseline`| Hieu | `b7e8096` | `DetectVul/devign` | 272 (125 / 147) | Train 10% (2,184) | `gemma-4-26B-A4B-it` (FPT AI) | Temp=0.0, MaxTokens=256 | `standard_1shot` | GRACE Baseline | Top-5 | `kaggle_notebooks/.../Ver 4_1st time` | Ablation 10% Devign |
| `ablation_devign_security_aware`| Hieu | `b7e8096` | `DetectVul/devign` | 272 (125 / 147) | Train 10% (2,184) | `gemma-4-26B-A4B-it` (FPT AI) | Temp=0.0, MaxTokens=256 | `standard_1shot` | Security-Aware Reranker | Top-50 | `kaggle_notebooks/.../Ver 4_1st time` | Ablation 10% Devign |
| `ablation_devign_contrastive`   | Hieu | `b7e8096` | `DetectVul/devign` | 272 (125 / 147) | Train 10% (2,184) | `gemma-4-26B-A4B-it` (FPT AI) | Temp=0.0, MaxTokens=256 | `contrastive_2shot` | Security-Aware + Contrastive Pair | Top-50 | `kaggle_notebooks/.../Ver 4_1st time` | Ablation 10% Devign |
| `dung_v1_c1_c2_c4_devign` | Dung | *(Cần Dũng điền)* | `Devign` | ~2,700 *(Cần chốt ID)* | *(Cần chốt)* | `Qwen3-Coder` | *(Cần chốt)* | *(Cần chốt)* | C1+C2+C4 | *(Cần chốt)* | *(Cần file dự đoán mẫu)* | Dùng backbone khác Hiếu, cần chốt contract chung |
| `dung_v1_c1_c2_c4_reveal` | Dung | *(Cần Dũng điền)* | `ReVeal` | *(Cần chốt)* | *(Cần chốt)* | `Qwen3-Coder` | *(Cần chốt)* | *(Cần chốt)* | C1+C2+C4 | *(Cần chốt)* | *(Cần file dự đoán mẫu)* | Tín hiệu tăng MCC nhẹ lên 0.07 |

---

## 2. Quy Định Quản Lý Dữ Liệu Thực Nghiệm (Contract Guidelines)
1. **Mọi run so sánh trực tiếp** phải dùng chung `dataset_split_ids.json` và cùng `retrieval_pool_hash`.
2. **Backbone chung**: Trước khi so sánh phương pháp của Hiếu và Dũng, phải chạy thử nghiệm trên cùng 1 mô hình backbone (hoặc `gemma-4-26B-A4B-it`, hoặc `Qwen-2.5-Coder-32B/7B`) với cùng inference parameter (Temperature=0.0, seed=42).
3. **Mọi bảng kết quả** phải được xuất tự động từ `src/common_evaluator.py`, không sao chép thủ công.
