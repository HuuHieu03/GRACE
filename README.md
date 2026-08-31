---
project: "GRACE: Vulnerability-Aware Contrastive Demonstration Retrieval"
author: "Nguyễn Hữu Hiếu"
role: "Nghiên cứu viên / Người thực hiện"
domain: "LLM-based Software Vulnerability Detection (C/C++ functions)"
base_paper:
  title: "GRACE: Empowering LLM-based software vulnerability detection with graph structure and in-context learning"
  core_approach: "CodeT5 Vector Embedding + Joern CPG Graph Similarity + In-Context Learning"
enhancement_breakthrough:
  name: "Stage 5: Vulnerability-Aware Contrastive Demonstration Retrieval (VAC-Retrieval)"
  technique: "Contrastive ICL (Pairing 1 Vulnerable + 1 Safe demonstration with security boundary analysis)"
datasets:
  - name: "Devign"
    total_test: 2732
    vulnerable_ratio: "45.7%"
  - name: "ReVeal"
    total_test: 2274
    vulnerable_ratio: "10.1% (Severe Imbalance)"
models_used:
  embedder: "Salesforce/codet5-base (768d latent space)"
  similarity_search: "Meta FAISS Flat L2 Index"
  graph_extractor: "Joern CLI v2.0 (AST, CFG, PDG)"
  llm_evaluator: "gemma-4-26B-A4B-it (via FPT AI Platform)"
execution_environment:
  platform: "Kaggle GPU (Tesla T4)"
  os: "Linux / Ubuntu"
  python_version: "3.10 - 3.12"
date_created: "2026-08-31"
status: "Completed & Fully Verified"
---

# GRACE: Nghiên Cứu Phục Dựng Baseline, Khắc Phục Sai Lệch & Đột Phá Với Vulnerability-Aware Contrastive Retrieval (Stage 5)

Kho lưu trữ này tổng hợp toàn bộ công trình phục dựng chuẩn hóa bài báo khoa học **GRACE**, phân tích định lượng nguyên nhân thất bại của cơ chế truy xuất tương đồng bề mặt, và triển khai giải pháp cải tiến đột phá **Vulnerability-Aware Contrastive Demonstration Retrieval (VAC-Retrieval)** phục vụ bài toán phát hiện lỗ hổng phần mềm bằng mô hình ngôn ngữ lớn (LLM).

---

## 1. Tóm Tắt Đóng Góp Cốt Lõi Của Nghiên Cứu

### A. Vấn đề của bài báo GRACE gốc (The Superficial Similarity Trap)
Bài báo gốc dựa trên giả định: *Đoạn mã có cấu trúc tương đồng (Jaccard + GraphSim) sẽ có đặc tính an ninh tương đồng*.  
Tuy nhiên, trong thực tế an toàn phần mềm, **hai hàm C/C++ có thể giống nhau đến 95% về cấu trúc nhưng một bên an toàn và một bên chứa lỗ hổng chết người** chỉ vì sự xuất hiện của đúng 1 dòng kiểm tra biên (*bounds check*) hoặc kiểm tra con trỏ (*NULL check*).

### B. Khảo sát định lượng trên 5,006 mẫu kiểm thử (`analyze_retrieval_failures.py`)
Khi đối soát thực tế, chúng tôi phát hiện những con số báo động về cơ chế truy xuất của GRACE gốc:
* **47.58% (Devign)** và **71.43% (ReVeal)** các hàm chứa lỗ hổng lại bị gán cho một ví dụ an toàn (ngược nhãn).
* Hiện tượng này gây ra **thiên kiến ngữ cảnh (In-Context Bias)** nghiêm trọng, khiến LLM lầm tưởng hàm mục tiêu là an toàn và **bỏ sót lỗ hổng hàng loạt (Tỷ lệ False Negatives lên tới hơn 70%)**.

### C. Đột phá Stage 5: Vulnerability-Aware Contrastive Demonstration Retrieval (VAC-Retrieval)
Thay vì đưa 1 ví dụ đơn lẻ dễ gây thiên kiến, phương pháp Stage 5 đề xuất:
1. **Truy xuất cặp mẫu đối sánh tương phản (Contrastive Pair: 1 Vulnerable + 1 Safe)** có cùng ngữ cảnh nghiệp vụ nhưng khác nhau ở ranh giới bảo vệ (*security boundary*).
2. **Cấu trúc lại Prompt ICL chuẩn mực**: Đưa cặp mẫu đối sánh lên đầu làm tiền đề so sánh vi sai (*differential analysis*), buộc LLM phải phân tích: *"Hàm này thiếu kiểm tra biên như mẫu lỗi hay đã được bảo vệ an toàn như mẫu sạch?"*.

---

## 2. Bảng Ma Trận So Sánh Hiệu Năng Thực Nghiệm (Performance Matrix)

Dữ liệu được trích xuất trực tiếp từ cell outputs của các Jupyter Notebooks chạy trên **100% Test Set** (Kaggle GPU Tesla T4, mô hình `gemma-4-26B-A4B-it`):

### A. Tập Kiểm Thử Devign Benchmark (2,732 Mẫu Toàn Diện)
| Chỉ Số Đánh Giá | GRACE Baseline (Phục dựng Paper) | GRACE Stage 5 (Cải Tiến VAC) | Mức Độ Cải Thiện (Delta) | Ý Nghĩa Kỹ Thuật |
| :--- | :---: | :---: | :---: | :--- |
| **Recall (Độ phủ bắt lỗi)** | 26.61% | **34.34%** | 🟢 **+7.73% Tuyệt đối** | **Bắt trúng thêm nhiều mã độc** 🎯 |
| **F1-Score (Chỉ số tổng hòa)** | 35.82% | **41.66%** | 🟢 **+5.84% Tuyệt đối** | **Thiết lập đỉnh cao mới của đề tài** 🚀 |
| **True Positives (Bắt trúng lỗi)** | 334 | **431** | 🟢 **+97 Lỗ hổng thực tế** | Cứu vãn 97 ca nguy hiểm bị bỏ sót |
| **False Negatives (Bỏ sót lỗi)** | 921 | **824** | 🟢 **-97 Ca bỏ sót** | Giảm thiểu rủi ro bảo mật nghiêm trọng |
| **Accuracy (Độ chính xác toàn cục)**| 61.16% | **61.35%** | `+0.19%` | Duy trì ổn định |
| **Notebook Thực Nghiệm** | `devign_baseline_reproduce.ipynb` | `stage5_contrastive_demonstration.ipynb` | — | Đã lưu sẵn cell output trong `01_Reproduce_Notebooks/` |

### B. Tập Kiểm Thử ReVeal Benchmark (2,274 Mẫu - Imbalance Cực Đoan 10% Lỗi)
| Chỉ Số Đánh Giá | GRACE Baseline (Phục dựng Paper) | GRACE Stage 5 (Cải Tiến VAC) | Mức Độ Cải Thiện (Delta) | Ý Nghĩa Kỹ Thuật |
| :--- | :---: | :---: | :---: | :--- |
| **Recall (Độ phủ bắt lỗi)** | 24.78% | **27.39%** | 🟢 **+2.61% Tuyệt đối** | Bắt thêm các lỗ hổng ẩn sâu |
| **F1-Score (Chỉ số tổng hòa)** | 17.51% | **18.69%** | 🟢 **+1.18% Tuyệt đối** | Cải thiện trên tập siêu mất cân bằng |
| **True Positives (Bắt trúng lỗi)** | 57 | **63** | 🟢 **+6 Lỗ hổng thực tế** | Bắt thêm 6 ca lỗ hổng thực tế |
| **False Negatives (Bỏ sót lỗi)** | 173 | **167** | 🟢 **-6 Ca bỏ sót** | Giảm thiểu bỏ sót |
| **Notebook Thực Nghiệm** | `reveal_baseline_reproduce.ipynb` | `stage5_contrastive_demonstration.ipynb` | — | Đã lưu sẵn cell output trong `01_Reproduce_Notebooks/` |

---

## 3. Bảng Đối Chiếu: Mã Nguồn Tác Giả vs Hệ Thống Phục Dựng Chuẩn Hóa

| Tiêu Chí Kỹ Thuật | Mã Nguồn Gốc Tác Giả Cung Cấp | Hệ Thống Phục Dựng Của Chúng Ta |
| :--- | :--- | :--- |
| **Cấu trúc Prompt ICL** | ❌ **Sai vị trí**: Đẩy Demonstration xuống cuối cùng sau code mục tiêu (`llmpre.py`). | ✅ **Chuẩn Figure 6**: Demonstration đặt ở đầu làm tiền đề học tập ngữ cảnh. |
| **Biểu diễn Vector** | ❌ **Thoái hóa**: Dùng BERT-whitening ép xuống 256 chiều làm mất thông tin. | ✅ **Chuẩn Paper**: `Salesforce/codet5-base` 768 chiều nguyên bản + FAISS Index Flat $L_2$. |
| **Pipeline Đồ thị CPG** | ❌ **Thiếu hoàn toàn**: Hardcode đường dẫn `F:/pycharmfile/...`, không có script trích xuất. | ✅ **Tự động hóa 100%**: `batch_joern_extractor.py` trích xuất CPG cho 47,779 hàm C/C++. |
| **Chất lượng Codebase** | ❌ **Mã rác**: Import `@solidity-parser`, `javalang` không liên quan đến C/C++. | ✅ **Tối ưu & Chuyên biệt**: Loại bỏ 100% mã rác, tích hợp 29 unit tests tự động (`tests/`). |

---

## 4. Cấu Trúc Thư Mục Dự Án (Directory Hierarchy)

```text
GRACE/
│
├── README.md                            # [File này] Metadata YAML, Bảng kết quả & Reproduction Guide
│
├── 00_Reports_and_Docs/                 # Trung tâm tài liệu & báo cáo khoa học học thuật
│   ├── README.md                        # Danh mục và hướng dẫn đọc báo cáo
│   ├── 01_Stage5_Contrastive_Benchmark_Report.md  # Báo cáo 28.5 KB: kết quả đột phá Stage 5
│   ├── 02_Baseline_Reproduction_and_Discrepancy_Report.md # Báo cáo chỉ ra 5 lỗi sai của tác giả gốc
│   ├── 03_Retrieval_Failure_Analysis_Report.md    # Báo cáo khảo sát định lượng lỗi ngược nhãn
│   ├── 04_Vulnerability_Aware_Contrastive_Design.md # Bản thiết kế kỹ thuật cơ chế VAC-Retrieval
│   ├── retrieval_failure_analysis_devign.csv      # File dữ liệu phân tích 2,732 ca Devign
│   ├── retrieval_failure_analysis_reveal.csv      # File dữ liệu phân tích 2,274 ca ReVeal
│   └── GRACE_Empowering_LLM_Original_Paper.pdf    # Bài báo khoa học gốc
│
├── 01_Reproduce_Notebooks/              # Notebooks Kaggle chính thức ĐÃ LƯU CELL OUTPUTS
│   ├── README.md                        # Hướng dẫn mở xem output hoặc chạy lại
│   ├── stage5_contrastive_demonstration.ipynb  # [SOTA Stage 5] Full Devign & ReVeal (1.39 MB)
│   ├── devign_baseline_reproduce.ipynb         # [Baseline] Chạy trên 2,732 mẫu Devign (612.9 KB)
│   └── reveal_baseline_reproduce.ipynb         # [Baseline] Chạy trên 2,274 mẫu ReVeal (514.0 KB)
│
├── baseline code/                       # Lưu trữ mã nguồn phục dựng baseline
│   ├── README.md                        # Giải thích cấu trúc code text và gói bundle
│   └── baseline_code_text/              # Các file mã nguồn Python (.py) phục dựng baseline
│
├── data/                                # Thư mục dữ liệu dùng chung (được ignore trên Git)
│   └── processed/                       # Chứa đồ thị JSON trích xuất (devign_train, reveal_train...)
│
├── security_signature/                  # Module trích xuất chữ ký bảo mật (bounds check, null check)
├── tests/                               # 29 Unit tests kiểm thử hệ thống
│
├── run_pipeline.py                      # Đầu não điều phối dòng lệnh (chạy baseline hoặc contrastive)
├── contrastive_selector.py              # Thuật toán chọn cặp ví dụ tương phản (Stage 5)
├── retrieval_security_engine.py         # Bộ truy xuất có nhận biết bảo mật (Stage 5)
├── retrieval_engine.py                  # Bộ truy xuất CodeT5 768d + FAISS L2 + Hybrid Reranking
├── batch_joern_extractor.py             # Bộ trích xuất đồ thị Joern CPG v2.0
├── prompt_engine.py                     # Bộ tạo prompt ICL chuẩn mực
├── evaluator.py                         # Module suy luận LLM có checkpoint JSONL tự phục hồi
└── metrics.py                           # Module tính toán Accuracy, Precision, Recall, F1-Score
```

---

## 5. HƯỚNG DẪN CÀI ĐẶT & CHẠY LẠI MÃ NGUỒN (REPRODUCTION GUIDE)

### Phương thức 1: Mở xem trực tiếp hoặc chạy trên Kaggle Notebook (Khuyến nghị cho Giảng viên)
Tất cả các tệp notebook trong thư mục [`01_Reproduce_Notebooks/`](01_Reproduce_Notebooks/) đều **đã lưu sẵn toàn bộ Cell Outputs, biểu đồ và kết quả đánh giá**:
1. Giảng viên chỉ cần click vào từng file notebook để xem kết quả thẩm định.
2. Nếu muốn chạy lại từ đầu: Upload notebook lên Kaggle, chọn Accelerator **GPU Tesla T4**, nhập API Key của LLM (FPT AI / OpenAI / vLLM) và nhấn **Run All**.

### Phương thức 2: Chạy kiểm thử đơn vị cục bộ (Unit Testing)
```bash
# 1. Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
pip install pytest faiss-cpu

# 2. Chạy 29 unit tests kiểm tra toàn bộ pipeline
pytest tests/ -v
```

### Phương thức 3: Thực thi toàn bộ quy trình qua dòng lệnh (CLI Pipeline)
Hệ thống hỗ trợ chạy cả phương pháp **Baseline** lẫn **Stage 5 Contrastive**:

```bash
# Thiết lập biến môi trường API Key
export FPT_AI_API_KEY="your_api_key_here"

# 1. Chạy phương pháp cải tiến Stage 5 (VAC-Retrieval) trên tập Devign
python run_pipeline.py --dataset_name DetectVul/devign --sample_ratio 0.05 --retrieval_method contrastive_icl --experiment_name exp_stage5_devign

# 2. Chạy phương pháp phục dựng Baseline trên tập Devign
python run_pipeline.py --dataset_name DetectVul/devign --sample_ratio 0.05 --retrieval_method grace_baseline --experiment_name exp_baseline_devign

# 3. Chạy chế độ Mock Test (Kiểm tra nhanh trên CPU không cần GPU/API)
python run_pipeline.py --use_mock True --retrieval_method contrastive_icl
```
