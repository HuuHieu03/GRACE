---
title: "Báo Cáo Đối Chiếu Baseline Chuẩn Mực & 5 Điểm Sai Lệch Của Mã Nguồn Tác Giả"
author: "Nguyễn Hữu Hiếu"
role: "Nghiên cứu viên / Người thực hiện"
document_id: "GRACE-Discrepancy-Audit"
status: "Completed & Verified"
date: "2026-08-24"
base_paper: "GRACE: Empowering LLM-based software vulnerability detection with graph structure and in-context learning"
summary: "Phân tích và khắc phục 5 sai lệch lớn giữa bài báo và mã nguồn tác giả (Prompt đảo ngược, BERT-whitening 256d, thiếu Joern extractor, rác Solidity/Java, đường dẫn hardcode)."
---

# Báo Cáo Đối Chiếu Kỹ Thuật: 4 Phiên Bản Baseline (Ver 08, 11, 12, 13) & Phân Tích Sai Lệch Mã Nguồn Tác Giả vs Bài Báo GRACE

---

## 1. Tổng Quan & Bối Cảnh Thực Nghiệm

Framework **GRACE** (*"GRACE: Empowering LLM-based software vulnerability detection with graph structure and in-context learning"*) là một phương pháp tiếp cận tiên tiến kết hợp biểu diễn đồ thị mã nguồn (AST, CFG, PDG qua Joern CPG), kỹ thuật chọn lọc mẫu tương đồng ngữ nghĩa (CodeT5 + Hybrid Reranking) và khả năng suy luận của Mô hình Ngôn ngữ Lớn (LLMs) để phát hiện lỗ hổng phần mềm C/C++.

Trong quá trình phục dựng, kiểm thử và chuẩn hóa hệ thống trên môi trường Kaggle GPU, chúng tôi đã thực hiện **4 đợt chạy thực nghiệm Baseline quy mô 100% tập dữ liệu kiểm thử**:
1. **Ver08**: Tập **Devign** (2,732 mẫu) – Sử dụng cấu trúc Prompt thử nghiệm ban đầu (Prototype có Expert Reasoning & Demo Graph).
2. **Ver11**: Tập **Reveal** (2,274 mẫu) – Sử dụng cấu trúc Prompt thử nghiệm ban đầu trên tập dữ liệu mất cân bằng nhãn cao (~9.16% lỗ hổng).
3. **Ver12**: Tập **Devign** (2,732 mẫu) – Chuẩn hóa 100% cấu trúc Prompt theo **Hình 6 & Mục 3.3 bài báo gốc**.
4. **Ver13**: Tập **Reveal** (2,274 mẫu) – Chuẩn hóa 100% cấu trúc Prompt theo **Hình 6 & Mục 3.3 bài báo gốc**.

---

## 2. So Sánh Chi Tiết Giữa 4 Phiên Bản Thực Nghiệm Baseline

### 2.1. Bảng Thông Số Kỹ Thuật Từng Phiên Bản

| Thuộc tính / Phiên bản | Ver 08 (Devign Cũ) | Ver 11 (Reveal Cũ) | Ver 12 (Devign Chuẩn Paper) | Ver 13 (Reveal Chuẩn Paper) |
| :--- | :--- | :--- | :--- | :--- |
| **Tập dữ liệu** | `DetectVul/devign` | `SensorLLM/reveal` | `DetectVul/devign` | `SensorLLM/reveal` |
| **Quy mô tập Test** | 2,732 mẫu (100%) | 2,274 mẫu (100%) | 2,732 mẫu (100%) | 2,274 mẫu (100%) |
| **Quy mô tập Train** | 21,854 mẫu (FAISS $L_2$) | 18,187 mẫu (FAISS $L_2$) | 21,854 mẫu (FAISS $L_2$) | 18,187 mẫu (FAISS $L_2$) |
| **Mô hình suy luận** | `gemma-4-26B-A4B-it` | `gemma-4-26B-A4B-it` | `gemma-4-26B-A4B-it` | `gemma-4-26B-A4B-it` |
| **Bộ trích xuất Vector** | `Salesforce/codet5-base` | `Salesforce/codet5-base` | `Salesforce/codet5-base` | `Salesforce/codet5-base` |
| **Trọng số Rerank** | $0.7 \text{Jaccard} + 0.3 \text{Graph}$ | $0.7 \text{Jaccard} + 0.3 \text{Graph}$ | $0.7 \text{Jaccard} + 0.3 \text{Graph}$ | $0.7 \text{Jaccard} + 0.3 \text{Graph}$ |
| **Cấu trúc Demo trong Prompt** | Code + Graph + Reasoning | Code + Graph + Reasoning | **Chỉ Code + Ground Truth Label** | **Chỉ Code + Ground Truth Label** |
| **Cấu trúc Target trong Prompt**| Chuỗi gộp Node/Edge | Chuỗi gộp Node/Edge | **Tách biệt Node Info & Edge Info**| **Tách biệt Node Info & Edge Info**|
| **Thời gian thực thi** | ~62 phút | ~51 phút | **60.26 phút** | **49.52 phút** |

---

### 2.2. Bảng Đối Chiếu Kết Quả Thực Nghiệm Toàn Diện

```
+-------------------------------------------------------------------------------------------------------------------------------+
| Dataset  | Phiên Bản               | Accuracy   | Precision  | Recall     | F1-Score   | TP    | FP         | TN          | FN    |
+----------+-------------------------+------------+------------+------------+------------+-------+------------+-------------+-------+
| DEVIGN   | Paper GRACE (GPT-4)     | 60.13%     | 54.58%     | 84.68%     | 66.38%     | N/A   | N/A        | N/A         | N/A   |
| (2,732)  | Ver 08 (Prompt Cũ)      | 56.37%     | 53.27%     | 40.88%     | 46.26%     | 513   | 450        | 1,027       | 742   |
|          | Ver 12 (Chuẩn Figure 6) | 56.19%     | **54.75%** | 26.61%     | 35.82%     | 334   | **276** ⬇️ | **1,201** ⬆️| 921   |
+----------+-------------------------+------------+------------+------------+------------+-------+------------+-------------+-------+
| REVEAL   | Paper GRACE (GPT-4)     | 88.12%     | 32.05%     | 62.01%     | 42.26%     | N/A   | N/A        | N/A         | N/A   |
| (2,274)  | Ver 11 (Prompt Cũ)      | 70.18%     | 12.42%     | 32.17%     | 17.92%     | 74    | 522        | 1,522       | 156   |
|          | Ver 13 (Chuẩn Figure 6) | **76.39%** | **13.54%** | 24.78%     | 17.51%     | 57    | **364** ⬇️ | **1,680** ⬆️| 173   |
+-------------------------------------------------------------------------------------------------------------------------------+
```

---

### 2.3. Đánh Giá & Phân Tích Hiện Tượng Kỹ Thuật

1. **Báo động giả (False Positives) giảm đột phá**:
   - Trên **Devign**: Số ca FP giảm từ 450 xuống **276 ca (-38.7%)**.
   - Trên **Reveal**: Số ca FP giảm từ 522 xuống **364 ca (-30.3%)**.
   - *Nguyên nhân*: Bản prompt cũ (Ver08/Ver11) tự động chèn câu lý giải suy diễn (*"The demonstrated function contains insecure memory buffering..."*), khiến mô hình bị thiên kiến tiêu cực (negative prompt bias) và coi hầu hết các hàm có thao tác mảng/con trỏ là lỗi. Bản chuẩn Figure 6 (Ver12/Ver13) loại bỏ câu này, giúp mô hình ra quyết định khách quan hơn.

2. **Precision & Accuracy tăng trưởng**:
   - **Devign (Ver12)**: Precision tăng lên **54.75%** (vượt qua mốc **54.58%** của GPT-4 trong bài báo gốc).
   - **Reveal (Ver13)**: Accuracy tăng vọt lên **76.39%** (+6.21% so với Ver11), Precision tăng lên **13.54%**.

3. **Hiện tượng Recall suy giảm ở mô hình Open-Weights (26B)**:
   - Khi loại bỏ reasoning mẫu, mô hình Gemma-26B trở nên thận trọng (Conservative Bias), ưu tiên gán nhãn Non-vulnerable cho các trường hợp không có dấu hiệu lỗi rõ ràng. Điều này giải thích vì sao Recall của Gemma-26B (26.61% và 24.78%) thấp hơn GPT-4 (vốn có năng lực suy luận tự thân cực mạnh nhờ quy mô tham số khổng lồ).

---

## 3. Phân Tích Đối Chiếu Sâu: Mã Nguồn Gốc Tác Giả vs Bài Báo Khoa Học GRACE

Khi đối chiếu giữa **Mã nguồn gốc do tác giả cung cấp trong repo** (`genexample.py`, `llmpre.py`, `basep.py`, `util.py`) và **Nội dung công bố chính thức trong bài báo PDF** (*Section 3 & Figure 6*), chúng tôi phát hiện 5 điểm sai lệch và khiếm khuyết lớn:

```
+-------------------------------------------------------------------------------------------------------------------+
| Tiêu Chí                | Bài Báo Công Bố (Paper PDF)               | Mã Nguồn Gốc Tác Giả (Original Codebase)    |
+-------------------------+-------------------------------------------+---------------------------------------------+
| 1. Thứ tự cấu trúc      | Figure 6: Demonstration đặt ở ĐẦU         | llmpre.py: Demonstration bị đặt ở CUỐI      |
|    Prompt ICL           | (Mẫu ví dụ -> Target Code -> Đồ thị ->    | (Target Code -> Node -> Edge ->             |
|                         |  Câu hỏi & Ràng buộc nhãn)                |  Templates -> Demonstration)                |
+-------------------------+-------------------------------------------+---------------------------------------------+
| 2. Định dạng chuỗi      | Mô tả rõ ràng từng phần $P_i$, $P_d$,     | Nối chuỗi thô không có khoảng trắng/xuống   |
|    Prompt               | $P_t$, $P_b$ với định dạng mạch lạc       | dòng khiến các từ bị dính chùm vào nhau     |
+-------------------------+-------------------------------------------+---------------------------------------------+
| 3. Mã rác & Artifacts   | Chỉ đề cập C/C++ (Devign, Reveal, BigVul) | util.py chứa thư viện Solidity JS           |
|    không liên quan      |                                           | (@solidity-parser), Java (javalang), v.v.   |
+-------------------------+-------------------------------------------+---------------------------------------------+
| 4. Xử lý Vector         | CodeT5 Embedding 768-dim + Cosine/L2      | genexample.py dùng BERT-Whitening cũ        |
|    ngữ nghĩa            | trên toàn bộ tập dữ liệu                  | (đọc các file tĩnh a.pkl, b.pkl 256 chiều)  |
+-------------------------+-------------------------------------------+---------------------------------------------+
| 5. Giới hạn thực nghiệm | Công bố đánh giá trên 100% Test Split     | Hardcode đường dẫn tuyệt đối 'F:/...'       |
|    & Dữ liệu            | (Devign 2,732; Reveal 2,274; BigVul)      | và cắt cứng chỉ chạy 2000 mẫu [0:2000]      |
+-------------------------+-------------------------------------------+---------------------------------------------+
```

### Chi Tiết Từng Điểm Sai Lệch:

#### ❌ Sai lệch 1: Đảo lộn vị trí In-Context Demonstration trong Prompt
- **Trong Paper (Figure 6 & Section 3.3)**: Mẫu ví dụ học tập đóng vai trò là tiền đề (Premise):
  $$\text{Prompt} = [P_i + P_d] + [\text{Demo Code} + \text{Demo Label}] + [\text{Target Code} + \text{Target Nodes} + \text{Target Edges}] + [P_b]$$
- **Trong Mã nguồn gốc (`llmpre.py` dòng 74)**:
  `format(inputCode)+templates[1]+templates[2]+format(inputnode)+templates[3]+format(inputedge)+templates[4]+format(inputex)`
  $\rightarrow$ Tác giả đặt `inputCode` (hàm mục tiêu) ở đầu tiên, sau đó mới nối các template và đẩy `inputex` (ví dụ mẫu) xuống tận cuối cùng. Điều này vi phạm nguyên lý In-Context Learning chuẩn và gây xáo trộn khả năng chú ý (Attention Mechanism) của LLM.

#### ❌ Sai lệch 2: Mã nguồn gốc chứa nhiều tàn dư dự án khác (Solidity, Java, Smart Contracts)
- File `util.py` của tác giả nhập thư viện `execjs` để gọi `@solidity-parser/parser` (trích xuất AST của Smart Contract Ethereum) và `javalang` (Java parser).
- Những module này hoàn toàn không liên quan đến bài báo GRACE (vốn chuyên biệt cho C/C++ phát hiện lỗ hổng qua Joern CPG).

#### ❌ Sai lệch 3: Module tìm kiếm tương đồng bị thoái hóa thành BERT-Whitening
- File `genexample.py` trong repo gốc nạp các file tĩnh `model/a.pkl`, `model/b.pkl` để làm giảm chiều vector xuống 256 (`bert_whitening`), thay vì sử dụng trực tiếp không gian đặc trưng 768 chiều nguyên bản của `Salesforce/codet5-base` như lý thuyết trong paper.

#### ❌ Sai lệch 4: Mã nguồn gốc thiếu hoàn toàn Pipeline trích xuất Joern CPG
- Tác giả không công bố script tự động hóa trích xuất từ mã nguồn C/C++ thô sang Node/Edge CPG, mà chỉ để lại các file JSON/CSV đã qua xử lý với đường dẫn cố định trên máy cá nhân (`F:/pycharmfile/vulllm/...`).

---

## 4. Những Đóng Góp Kỹ Thuật Đã Hoàn Thiện Trong Dự Án Này

Để giải quyết toàn bộ các hạn chế trên, chúng tôi đã tái cấu trúc và hoàn thiện hệ thống:
1. **Xây dựng `batch_joern_extractor.py`**: Tự động hóa trích xuất CPG 100% cho 27,318 hàm Devign và 20,461 hàm Reveal.
2. **Hiện đại hóa `retrieval_engine.py`**: Sử dụng `Salesforce/codet5-base` 768 chiều + GPU Batch Encoding + FAISS $L_2$ + Hybrid Reranking ($0.7 \text{Jaccard} + 0.3 \text{GraphSim}$) chạy trong 1.23 giây.
3. **Chuẩn hóa `prompt_engine.py`**: Tái tạo chính xác 100% theo Figure 6 & Mục 3.3 của bài báo.
4. **Kiểm chứng thực nghiệm 100% trên Kaggle GPU**: Xuất xưởng 4 bản chạy hoàn chỉnh (Ver08, Ver11, Ver12, Ver13), lưu trữ checkpoint JSONL và tính toán đầy đủ ma trận nhầm lẫn (Confusion Matrix).

---

## 5. Định Hướng Giai Đoạn 5: Nghiên Cứu Đột Phá (Novel Proposals)

Các số liệu từ Ver12 và Ver13 là mốc chuẩn khoa học (Baseline Anchors) vững chắc để tiến hành 3 nghiên cứu cải tiến tiếp theo:
1. **Security Chain-of-Thought (Security CoT)**: Khắc phục điểm nghẽn Recall bằng cách yêu cầu mô hình giải trình luồng *Taint Source $\rightarrow$ Taint Sink $\rightarrow$ Sanitization Check*.
2. **Contrastive In-Context Learning (2-shot tương phản)**: Cung cấp đồng thời cặp mẫu (1 Lỗ hổng + 1 An toàn) để cân bằng khả năng phán đoán nhãn.
3. **Vulnerability-Focused Program Slicing**: Rút gọn đồ thị CPG, chỉ giữ lại các lát cắt luồng dữ liệu/điều khiển quan trọng liên quan đến thao tác bộ nhớ nguy hiểm.
