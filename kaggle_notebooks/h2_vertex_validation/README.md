# 🚀 GRACE H2: Đánh Giá Tập Validation Trên Vertex AI (DeepSeek-V4.1-Flash) Qua Kaggle Cloud

Thư mục này chứa toàn bộ tài nguyên đóng gói cho thực nghiệm đánh giá **H2 GuardedEvidence v3** trên tập **Validation** (Devign & ReVeal) sử dụng mô hình **DeepSeek-V4.1-Flash** qua **Google Cloud Vertex AI MaaS (Model-as-a-Service)** trên nền tảng **Kaggle Cloud**.

---

## 📌 1. Cấu Trúc Gói Thực Nghiệm Kaggle

```
kaggle_notebooks/h2_vertex_validation/
├── kernel-metadata.json                # Metadata cấu hình kernel (id: huuhieu3333/grace-h2-vertex-deepseek-validation)
├── h2_vertex_validation_kaggle.ipynb   # Notebook thực thi hoàn chỉnh (Secret setup, Smoke test, 100% Real Validation Prompts, Guard Assertions, Metrics)
├── push_kernel.ps1                     # Script tự động stage dataset (nếu thiếu), đẩy dataset và kernel lên Kaggle, theo dõi trạng thái
├── dataset_staging/                    # Thư mục staging chứa dataset validation (kèm dataset-metadata.json, runner.py nếu có)
└── README.md                           # Hướng dẫn chi tiết quy trình vận hành và kiểm thử
```

### ⚙️ Thông Số Kỹ Thuật (Tuân thủ `evaluation_contract.yaml`):
- **Kernel ID**: `huuhieu3333/grace-h2-vertex-deepseek-validation`
- **Dataset ID**: `huuhieu3333/grace-h2-vertex-validation`
- **Môi trường**: Kaggle VM (Standard CPU, `enable_gpu: false`, `enable_internet: true`)
- **Backbone LLM**: `deepseek-ai/deepseek-v4.1-flash-maas` (Location: `global`)
- **GCP Project**: `grace-research-2903`
- **Inference Params**: `temperature=0.0`, `seed=42`, `max_tokens=256`, `stream=false`
- **Context Limit**: 8,192 UTF-8 bytes truncation guard
- **Parser**: Canonical `ExactLastLineBinaryParser` từ `strict_parser.py` (chỉ chấp nhận dòng cuối là `0` hoặc `1`)
- **Tập Dữ Liệu**: Validation Split của Devign & ReVeal

---

## 🛡️ 2. Các Ràng Buộc Kỹ Thuật Tuyệt Đối (Lessons Learned)

1. **KHÔNG chạy `pip install -q --upgrade ...`**:
   - Môi trường Kaggle đã có sẵn `requests`, `google-auth`, `pandas`, `scikit-learn`, `numpy`, `tqdm`.
   - Tránh triệt để xung đột pip dependency resolver (từng gây lỗi với `google-genai`, `google-colab`, `cudf`).
2. **Dùng Parser Canonical từ `strict_parser.py`**:
   ```python
   last_line = next((line.strip() for line in reversed(raw_text.splitlines()) if line.strip()), "")
   if last_line == "1": return 1, "valid"
   if last_line == "0": return 0, "valid"
   return None, "invalid"
   ```
   - Không lồng chuỗi regex phức tạp có ngoặc kép/nháy đơn trong JSON cell để bảo đảm 0 lỗi cú pháp (`SyntaxError`).
3. **Nạp ĐẦY ĐỦ 100% Prompt Thật**:
   - Tuyệt đối không dùng mock/synthetic prompts rút gọn (như 4 mẫu anchor ở lượt trước).
   - Notebook tự động quét đệ quy các thư mục `/kaggle/input`, `/kaggle/working`, và unpacked archives để nạp đúng file `prompts.jsonl` hoặc `prompts.jsonl.gz` cho cả Devign và ReVeal.
   - Chuẩn hóa các trường đầu vào: `"prompt_text"`, `"prompt"`, `"input"` và `"ground_truth"`, `"target"`, `"label"`.
   - Nếu thiếu tệp dataset thật, notebook dừng ngay lập tức với lỗi `FileNotFoundError` rõ ràng.
4. **Guard Chống Nuốt Lỗi (Non-Empty Evaluation Guard)**:
   - Thêm assertion bắt buộc: `assert len(devign_preds) > 0 or len(reveal_preds) > 0`, ngăn chặn hoàn toàn việc notebook kết thúc thành công giả tạo (exit 0) khi không có mẫu nào được đánh giá.
5. **Xác Thực GCP & Tự Động Refresh Token**:
   - Nạp secret `GCP_SA_KEY` từ Kaggle User Secrets (`UserSecretsClient().get_secret("GCP_SA_KEY")`).
   - Tự động bắt HTTP 401 để refresh OAuth2 access token ngay lập tức mà không làm đứt quãng batch request.
6. **Kiểm Tra Tĩnh AST**:
   - Toàn bộ 100% code cells của notebook đã được kiểm tra cú pháp nghiêm ngặt (`ast.parse()`), đảm bảo 0 lỗi `SyntaxError` hoặc `IndentationError`.

---

## 🔑 3. Cấu Hình Kaggle User Secret (Bắt Buộc)

1. Mở giao diện Kaggle Notebook.
2. Chọn menu **Add-ons** ➔ **Secrets**.
3. Thêm secret mới:
   - **Label**: `GCP_SA_KEY`
   - **Value**: Dán toàn bộ nội dung file JSON của Google Cloud Service Account (tương ứng với file `.gcp_key.json` của dự án).
4. Nhấn **Save** và kích hoạt secret cho notebook.

---

## 🚀 4. Hướng Dẫn Vận Hành Qua Kaggle CLI

### Bước 4.1: Tự Động Đẩy Kernel & Dataset Lên Kaggle
Script PowerShell đã được tích hợp logic tự động kiểm tra staging: nếu thư mục `dataset_staging` chưa có, script sẽ tự gọi `scripts/package_validation_dataset.py` từ thư mục `SHARE_H2_VERTEX_DEEPSEEK_V41_CONTEXT8192_20261022\validation` rồi đẩy dataset và kernel lên Kaggle:
```powershell
.\kaggle_notebooks\h2_vertex_validation\push_kernel.ps1
```

### Bước 4.2 (Tùy chọn): Đóng Gói Dataset Thủ Công (Nếu cần tùy biến)
```powershell
python scripts/package_validation_dataset.py --source "D:\tai lieu hoc tap\Đề tài nghiên cứu khoa học\papers source code\SHARE_H2_VERTEX_DEEPSEEK_V41_CONTEXT8192_20261022\validation"
```

### Bước 4.3: Theo Dõi Trạng Thái Thực Thi
```powershell
kaggle kernels status huuhieu3333/grace-h2-vertex-deepseek-validation
```
- `queued`: Đang chờ cấp phát tài nguyên máy ảo.
- `running`: Đang thực thi đánh giá Vertex AI DeepSeek trên tập validation.
- `complete`: Đã hoàn tất và xuất đủ file artifact.

### Bước 4.4: Tải Kết Quả Về Máy Local Sau Khi Hoàn Tất
```powershell
$env:PYTHONUTF8="1"; kaggle kernels output huuhieu3333/grace-h2-vertex-deepseek-validation -p ../../output/h2_vertex_validation_kaggle/
```

---

## 📊 5. Đối Chiếu Kết Quả Với Baselines Của Đề Tài

| Metric | B2 (1-shot CodeT5+GraphSim) | B3 (2-shot Contrastive Selection) | H2 Validation (DeepSeek-V4.1-Flash) |
| :--- | :---: | :---: | :---: |
| **Accuracy** | 0.4700 | 0.4600 | *Ghi nhận sau khi chạy xong* |
| **Precision** | 0.5172 | 0.5000 | *Ghi nhận sau khi chạy xong* |
| **Recall** | 0.2778 | 0.6111 | *Ghi nhận sau khi chạy xong* |
| **F1-Score** | 0.3614 | 0.5500 | *Ghi nhận sau khi chạy xong* |
| **MCC** | -0.0292 | -0.1118 | *Ghi nhận sau khi chạy xong* |
| **Balanced Accuracy** | 0.4867 | 0.4469 | *Ghi nhận sau khi chạy xong* |
