# 🚀 GRACE H2: Đánh Giá Vertex AI (DeepSeek-V4.1-Flash) Trên Kaggle Cloud

Thư mục này chứa toàn bộ tài nguyên đóng gói cho thực nghiệm **H2 GuardedEvidence v3** trên mô hình **DeepSeek-V4.1-Flash** qua **Google Cloud Vertex AI MaaS (Model-as-a-Service)** trên nền tảng **Kaggle Cloud**.

---

## 📌 1. Cấu Trúc Gói Thực Nghiệm Kaggle

```
kaggle_notebooks/h2_vertex_eval/
├── kernel-metadata.json          # Metadata cấu hình kernel (id: huuhieu3333/grace-h2-vertex-deepseek-evaluation)
├── h2_vertex_eval_kaggle.ipynb   # Notebook thực thi hoàn chỉnh (Secret setup, Smoke test, Apple-to-Apple Latency Profiler, Eval)
├── push_kernel.ps1               # Script tự động đẩy kernel và kiểm tra trạng thái
└── README.md                     # Hướng dẫn chi tiết vận hành và phân tích tốc độ
```

### ⚙️ Thông Số Kỹ Thuật (Conforming to `evaluation_contract.yaml`):
- **Kernel ID**: `huuhieu3333/grace-h2-vertex-deepseek-evaluation`
- **Môi trường**: Kaggle VM (Standard CPU, `enable_gpu: false`, `enable_internet: true`)
- **Backbone LLM**: `deepseek-ai/deepseek-v4.1-flash-maas` (Location: `global`)
- **GCP Project**: `grace-research-2903`
- **Inference Params**: `temperature=0.0`, `seed=42`, `max_tokens=256`, `stream=false`
- **Context Limit**: 8,192 UTF-8 bytes truncation guard
- **Parser**: `exact_last_line_binary` (chỉ chấp nhận dòng cuối là `0` hoặc `1`)

---

## 🔑 2. Cấu Hình Kaggle User Secret (Bắt Buộc)

Notebook sử dụng module `kaggle_secrets` để bảo mật tuyệt đối Service Account Key của Google Cloud:
1. Mở notebook trên giao diện Kaggle.
2. Vào menu **Add-ons** ➔ **Secrets**.
3. Thêm secret mới:
   - **Label**: `GCP_SA_KEY`
   - **Value**: Dán toàn bộ nội dung file JSON của Google Cloud Service Account (tương ứng với file `.gcp_key.json` của dự án).
4. Nhấn **Save** và kích hoạt secret cho notebook.

---

## 🚀 3. Hướng Dẫn Vận Hành Qua Kaggle CLI

> **Lưu ý Quan Trọng**: Lệnh đẩy lên Kaggle hoàn toàn độc lập, **tiến trình đang chạy cục bộ trên máy local vẫn tiếp tục hoạt động bình thường, tuyệt đối không bị ảnh hưởng hay gián đoạn.**

### Bước 3.1: Đẩy Kernel Lên Kaggle
Chạy trực tiếp script PowerShell hoặc lệnh CLI tại thư mục kernel:
```powershell
# Cách 1: Sử dụng script tự động
.\kaggle_notebooks\h2_vertex_eval\push_kernel.ps1

# Cách 2: Chạy trực tiếp lệnh Kaggle CLI
cd "kaggle_notebooks/h2_vertex_eval"
$env:PYTHONUTF8="1"; kaggle kernels push -p .
```

### Bước 3.2: Theo Dõi Trạng Thái Khởi Chạy
Kiểm tra trạng thái thực thi của kernel:
```powershell
kaggle kernels status huuhieu3333/grace-h2-vertex-deepseek-evaluation
```
Các trạng thái:
- `queued`: Đang xếp hàng chờ cấp phát máy ảo.
- `running`: Đang thực thi evaluation và đo lường latency.
- `complete`: Đã hoàn tất toàn bộ chu trình đánh giá.

### Bước 3.3: Tải Kết Quả Về Máy Sau Khi Hoàn Tất
Khi trạng thái chuyển sang `complete`, tải toàn bộ artifact về thư mục output độc lập:
```powershell
$env:PYTHONUTF8="1"; kaggle kernels output huuhieu3333/grace-h2-vertex-deepseek-evaluation -p ../../output/h2_vertex_deepseek_v41_kaggle/
```

---

## ⚡ 4. Phân Tích & So Sánh Tốc Độ Chuẩn Xác (Apple-to-Apple Latency Benchmark)

### 📊 Dữ Liệu Đo Đạc Thực Tế Trên Máy Local (Đợt Chạy Hiện Tại):
Từ file kết quả `raw_responses.jsonl` được ghi nhận trên máy local (Việt Nam) gửi tới Vertex AI endpoint:
- **Mẫu 1 (devign:test:3)**: 2,304 tokens | 2,265.2 ms
- **Mẫu 2 (devign:test:12)**: 2,275 tokens | 1,698.9 ms
- **Mẫu 3 (devign:test:35)**: 1,346 tokens | 1,075.4 ms
- **Mẫu 4 (devign:test:43)**: 2,063 tokens | 824.5 ms
- **Thời Gian Phản Hồi Trung Bình (Local Mean Latency)**: **~1,466.0 ms (~1.47 giây / request)**
- **Thời Gian Trung Vị (Local Median P50)**: **~1,387.2 ms**
- **Thông Lượng (Throughput)**: **~0.68 request / giây**

### 🌐 Tại Sao Chạy Trên Kaggle Cloud Nhanh Hơn Rõ Rệt?
1. **Định Tuyến Nội Bộ Mạng Google Cloud (Intra-GCP Backbone)**:
   - Các máy ảo Kaggle được lưu trữ trực tiếp tại trung tâm dữ liệu của Google Cloud (vùng `us-central1` - Iowa hoặc Oregon).
   - Khi Kaggle gọi tới Vertex AI OpenAPI endpoint (`https://aiplatform.googleapis.com/...`), luồng dữ liệu di chuyển hoàn toàn trên mạng cáp quang nội bộ tốc độ cao của Google Cloud với độ trễ vòng lặp (Network RTT) cực thấp (**< 5 ms**).
2. **Loại Bỏ Độ Trễ Xuyên Đại Dương Của Mạng Dân Dụng (Local Machine)**:
   - Trên máy local tại Việt Nam, mỗi request phải đi qua mạng ISP dân dụng và các tuyến cáp quang biển quốc tế (AAG/APG/IA) tới các trạm Google Front End tại Mỹ/Châu Âu, tiêu tốn **150 - 250 ms RTT** chỉ riêng cho quá trình bắt tay TCP + TLS handshake.
3. **Giảm Thiểu Jitter & Connection Timeout**:
   - Mạng đám mây Kaggle có băng thông đối xứng hàng chục Gbps, hầu như không bị rớt gói (packet loss) hay biến động ping, giúp quá trình streaming và nhận completion tokens đạt tốc độ tối đa của mô hình `deepseek-v4.1-flash-maas`.
4. **Ước Tính Tốc Độ Gia Tăng (Speedup Ratio)**:
   - Dự kiến độ trễ trung bình trên Kaggle Cloud giảm xuống còn **~800 ms - 1,050 ms / request** (tăng tốc độ xử lý thêm **~30% - 45%**, tương đương tốc độ nhanh hơn **1.4x - 1.8x** so với chạy cục bộ).

---

## 🛡️ 5. Đối Chiếu Kết Quả Với Baselines Của Đề Tài

| Metric | B2 (1-shot CodeT5+GraphSim) | B3 (2-shot Contrastive Selection) | H2 GuardedEvidence v3 (Vertex AI) |
| :--- | :---: | :---: | :---: |
| **Accuracy** | 0.4700 | 0.4600 | *Đang đánh giá đối chiếu* |
| **Precision** | **0.5172** | 0.5000 | *Đang đánh giá đối chiếu* |
| **Recall** | 0.2778 | **0.6111** | *Đang đánh giá đối chiếu* |
| **F1-Score** | 0.3614 | **0.5500** | *Đang đánh giá đối chiếu* |
| **MCC** | -0.0292 | -0.1118 | *Đang đánh giá đối chiếu* |
| **Balanced Accuracy** | 0.4867 | 0.4469 | *Đang đánh giá đối chiếu* |

---

## 🔒 6. Tính Toàn Vẹn & Khép Kín Của Tiến Trình Local

Tiến trình đánh giá cục bộ trên máy local vẫn được giữ nguyên vẹn 100%:
- Không có bất kỳ tiến trình local nào bị tạm dừng, tắt hay ghi đè.
- Thư mục output của Kaggle được phân tách độc lập (`output/h2_vertex_deepseek_v41_kaggle/`), đảm bảo đối sánh song song độc lập và trung thực khoa học.
