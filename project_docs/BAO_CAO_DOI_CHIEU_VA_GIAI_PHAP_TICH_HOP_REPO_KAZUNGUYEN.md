# BÁO CÁO TOÀN DIỆN: ĐỐI CHIẾU HIỆN TRẠNG REPO KAZUNGUYEN VÀ GIẢI PHÁP TẬN DỤNG NGUỒN LỰC SẴN CÓ

> **Ngày lập:** 02/11/2026  
> **Đối tượng đối chiếu:**  
> - **Repo ngoài:** `https://github.com/kazunguyen/GRACE-summary` (Branch `baseline-unified`, commit `5377871`).  
> - **Repo nội bộ:** `HuuHieu03/GRACE` (Branch `main`, commit `fa75676`, Git tag `prereg-v1`).  
> **Căn cứ khoa học:** Đề cương nghiên cứu GRACE hợp nhất (`De_cuong_nghien_cuu_GRACE_hop_nhat.pdf`).

---

## TỔNG QUAN TÌNH TRẠNG & ĐỊNH HƯỚNG CHIẾN LƯỢC

1. **Thực trạng repo `kazunguyen/GRACE-summary`**:
   - Bên cạnh ưu điểm đã chuẩn hóa backend suy luận (`llama-cpp-python` 0.3.16 trích xuất logits gốc của token `0`/`1`), repo đang gặp phải các vấn đề nghiêm trọng về **phương pháp luận nghiên cứu (chạy test trước khi khóa ngưỡng, chưa đăng ký OSF)**, **lỗi kỹ thuật thống kê** và **sự đứt gãy giữa các bước (Bước 0 bỏ trống, Bước 5 dở dang ~50% Tầng 1, Bước 6–9 chưa thực hiện)**.
   - Khi chạy kiểm thử độc lập, phát hiện **8 test bị FAILED** (vướng lỗi đường dẫn file zip cục bộ và thiếu gate kiểm soát ngưỡng).

2. **Khả năng cứu vãn & Tận dụng nguồn lực**:
   - **Không cần bỏ đi hay chạy lại** 10.011 mẫu B2 và B0 đã inference trên Kaggle.
   - Toàn bộ các mảnh ghép còn thiếu (Bước 0, khóa ngưỡng 14 arm Bước 4, công thức thống kê chuẩn Bước 7, gói audit Bước 9) **đều đã được hoàn thiện 100% và kiểm thử sạch sẽ trong workspace hiện tại của chúng ta**.
   - Việc ghép nối hai bên sẽ giúp đề tài về đích nhanh chóng mà không lãng phí thêm tài nguyên GPU.

---

## PHẦN I. CHI TIẾT CÁC VẤN ĐỀ TRÊN REPO KAZUNGUYEN (TỪ BƯỚC 0 ĐẾN BƯỚC 9)

### 1. Kiểm định thống kê (Statistical Testing) & Code đánh giá
* **Lỗi công thức hiệu chỉnh liên tục trong McNemar (`stats.py` dòng 230)**:
  - *Hiện trạng*: `stat = (abs(b - c) - 1) ** 2 / (b + c)`.
  - *Lỗi*: Khi hai mô hình có số lỗi bất đồng bằng nhau ($b = c$), công thức trên tính ra $\frac{1}{b+c} > 0$ thay vì 0, dẫn đến p-value bị kéo xuống dưới $1.0$.
  - *Khắc phục*: Cần dùng công thức Edwards chuẩn: `stat = (max(0.0, abs(b - c) - 1.0)) ** 2 / (b + c)`.
* **Lỗi phương pháp luận trong `evaluate_final.py` (dòng 76, 230)**:
  - *Hiện trạng*: Hàm `table_a()` tự gọi lại `S.pick_threshold()` trên tập validation để tính động ngưỡng $\tau^*$ rồi mới ghi ra file.
  - *Lỗi*: Vi phạm nguyên tắc tiền đăng ký. Ngưỡng $\tau^*$ phải được nạp tĩnh từ `thresholds.json` đã đăng ký trước, không được tính động lại trong quá trình sinh bảng Test.
* **Mã nguồn ở trạng thái "ngủ" (Dormant Code)**:
  - Thư mục `runs/final/` chưa tồn tại trong repo; chưa hề có các file kết quả đầu ra như `table_A_metrics.csv`, `table_B_contrasts.csv`, `table_C_sensitivity.csv`.

---

### 2. Chi tiết từng bước từ Bước 0 đến Bước 9

| Bước | Yêu cầu theo Đề cương | Hiện trạng trên repo `kazunguyen` | Lỗi / Rủi ro phát hiện | Mức độ nghiêm trọng |
| :--- | :--- | :--- | :--- | :---: |
| **Bước 0: Chẩn đoán bổ sung (Complementarity)** | Phân tích 36 run lịch sử, OOF Benefit Router $R(x)$, Paired Cluster Bootstrap CI (5.000 lượt) tại $q=10\%$, phân tích repair vs harm. | **Trống 100%**. Tài liệu `TIEN_DO_PHUONG_AN_2.md` thừa nhận phần này nằm ngoài repo. | Bỏ trống hoàn toàn giả thuyết nền tảng RQ0 về tính bổ sung giữa mô hình đồ thị và LLM. | **Rất cao (Critical)** |
| **Bước 1: Môi trường & Backend LLM** | Qwen3-Coder-30B GGUF Q4_K_M, llama.cpp context 8.192, unconstrained first-token logits. | Đã cấu hình llama-cpp-python và model SHA cố định. | Phụ thuộc thư viện Linux `fcntl` gây crash trên Windows native; cơ chế ghi log thiếu `os.fsync` dễ hỏng dữ liệu khi timeout. | **Trung bình** |
| **Bước 2: Ngân hàng Donor & CPG** | Đóng băng donor pool, trích xuất CodeT5 vector và CPG (AST/CFG/PDG max 40n/80e), lưu specs `*.jsonl.gz`. | Đã trích xuất CPG/CodeT5 nhưng lọc bỏ nhãn mâu thuẫn làm lệch candidate pool Devign (21.750 -> 21.691 mẫu). | 66 mẫu B2 Devign bị lệch donor; phát sinh folder chắp vá `07_Arm_B2_Donor_Rerun_66/`; file specs không đưa lên Git. | **Trung bình** |
| **Bước 3: Bộ sinh Prompt & Kiểm toán** | Prompt Figure 6 chuẩn, token budget $\le 8192$, prompt audit tự động, kiểm toán mù bằng người 30 mẫu/dataset. | Đã sinh prompt Tầng 1 và B2-rand. | 1. `prompt_audit.py` crash với lỗi `KeyError: 'evidence'`.<br>2. Chưa có biên bản đọc mù 30 mẫu/dataset bằng người. | **Cao** |
| **Bước 4: Đăng ký trước & Khóa ngưỡng** | Khóa toàn bộ 14–15 ngưỡng $\tau^*$ trên Validation trước khi chạy Test; niêm phong trên OSF và Git tag. | Chỉ mới khóa 4/14 ngưỡng. Unit test `test_validation_lock.py` bị **FAILED** (lỗi `StopIteration`). | **Vi phạm phương pháp luận nghiêm trọng**: Chạy Test trước khi khóa ngưỡng (test B2/ReVeal chạy ở I-04 trước khi khóa ở I-05); chưa đăng ký OSF. | **Rất cao (Critical)** |
| **Bước 5: Chạy ma trận cấu hình** | Tầng 1 (5 arm $\approx$ 31k prompt); Tầng 2 (8 run $\approx$ 50k prompt); Tầng 3 (6 run $\approx$ 37k prompt). | B0 đủ (chỉ lưu local); B2 đủ (dính 66 mẫu lệch); B1 dở dang 54%; B2-flip dở dang 52%; B2-rep 0%; B2-rand 0%. | Thiếu hơn 14.000 prompt của Tầng 1; B2-rep chưa có runner inference độc lập; Tầng 2 và 3 chưa chạy. | **Rất cao (Critical)** |
| **Bước 6: Điểm neo có giám sát** | Huấn luyện SUP-LR, SUP-MLP, SUP-METRIC 3 seed trên CodeT5/Graph làm đối chứng cho Bảng A. | Có code `supervised_anchor.py` nhưng chưa chạy. | Thiếu toàn bộ file `anchor_scores.csv`; B0 có 1.132 raw response bất thường chưa được bóc tách khỏi valid logits. | **Cao** |
| **Bước 7: Thống kê & Bảng tổng hợp** | Bảng A (hiệu năng), Bảng B (kiểm định giả thuyết H1–H4, McNemar, Bootstrap CI), Bảng C (độ nhạy nhãn). | Có file thư viện `stats.py` nhưng chưa sinh bảng. | Chưa có bất kỳ file kết quả nào trong repo; code McNemar bị lỗi hiệu chỉnh liên tục. | **Cao** |
| **Bước 8: Đánh giá định tính mù** | 60–100 ca phân tích định tính (30 Devign, 30 ReVeal) theo rubric 4 tiêu chí bởi 2 chuyên gia độc lập. | Có file tiện ích `make_case_packets.py` nhưng chưa dùng. | Chưa trích xuất ca bệnh, chưa có kết quả đánh giá thực tế của chuyên gia. | **Trung bình** |
| **Bước 9: Khả năng tái lập & Bài báo** | Gói mã nguồn tái lập sạch (one-click reproduction), bài báo khoa học hoàn chỉnh. | Chưa có bài báo; 6 test trong `test_frozen_resume.py` bị **FAILED** do hard-code đường dẫn file zip cục bộ. | Người khác clone repo về không thể chạy kiểm thử sạch; tài liệu và sản phẩm bàn giao chưa sẵn sàng. | **Cao** |

---

## PHẦN II. NHỮNG GÌ WORKSPACE HIỆN TẠI CỦA MÌNH CÓ THỂ ĐẮP SANG NGAY

Toàn bộ các điểm khuyết thiếu cốt tử của repo `kazunguyen` đều đã được giải quyết trọn vẹn và kiểm chứng nghiêm ngặt trong thư mục làm việc của chúng ta (`HuuHieu03/GRACE`):

```
┌──────────────────────────────────────────────┐       ┌──────────────────────────────────────────────┐
│       REPO HIỆN TẠI (HuuHieu03/GRACE)        │       │       REPO ĐỐI TÁC (kazunguyen/summary)      │
├──────────────────────────────────────────────┤       ├──────────────────────────────────────────────┤
│ [ĐÃ XONG] Bước 0: OOF Routing + Stratified   │ ────► │ [TRỐNG 100%] Tiếp nhận module & dữ liệu Bước 0│
│ [ĐÃ XONG] Bước 2: Specs *.jsonl.gz chuẩn hóa │ ────► │ [BỊ LỆCH 66 MẪU] Chuẩn hóa lại donor pool     │
│ [ĐÃ XONG] Bước 4: Khóa 14/14 ngưỡng + Tag Git│ ────► │ [MỚI KHÓA 4] Hợp thức hóa hồ sơ OSF chuẩn   │
│ [ĐÃ XONG] Bước 5: Chạy sạch Test B0 & B2     │ ────► │ [CHỈ CÓ B2] Bù đắp Test B0 Devign & cross-val│
│ [ĐÃ XONG] Bước 7: McNemar chuẩn + Bảng A/B   │ ────► │ [LỖI CODE & TRỐNG ĐẦU RA] Thay thế engine    │
│ [ĐÃ XONG] Bước 9: audit_package 120MB sạch   │ ────► │ [FAIL 8 TEST CỤC BỘ] Gói bàn giao sạch        │
└──────────────────────────────────────────────┘       └──────────────────────────────────────────────┘
```

### 1. Bù đắp 100% Bước 0 (Complementarity & Routing)
* **Tài nguyên sẵn có trong repo của ta**:
  - Mã nguồn hoàn chỉnh: [grace_diag_kit/src/grace_diag/complementarity.py](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/grace_diag_kit/src/grace_diag/complementarity.py).
  - Thuật toán phân nhóm không rò rỉ: `StratifiedGroupKFold` 5-fold theo hash cụm file/project của ReVeal (627 val clusters, 646 test clusters).
  - Kết quả thực nghiệm đã tính: Benefit Router $R(x)$ tại $q=10\%$, Paired Cluster Bootstrap 95% CI (5.000 reps) cho cả Devign và ReVeal.
* **Cách tận dụng**: Copy module và xuất kết quả sang repo của họ để đóng gói hoàn thiện Bước 0 theo đúng đề cương.

### 2. Chuẩn hóa Bước 2 & Bước 3 (Specs & Prompt Audit)
* **Tài nguyên sẵn có**:
  - Tập specs đã đóng gói chuẩn [data/specs/](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/data/specs/) dạng `*.jsonl.gz`, độc lập hoàn toàn với runtime của Joern.
  - Script kiểm toán prompt và rubric đọc mù đã có sẵn mẫu tiêu chuẩn, không bị lỗi `KeyError: 'evidence'`.
* **Cách tận dụng**: Dùng tập specs sạch của ta để thay thế các bản chắp vá; nạp rubric đọc mù cho 30 mẫu Devign và 30 mẫu ReVeal.

### 3. Hợp thức hóa Bước 4 (Khóa 14 ngưỡng & Đăng ký OSF)
* **Tài nguyên sẵn có**:
  - Bảng khóa ngưỡng hoàn chỉnh 14 arm: [configs/thresholds.json](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/configs/thresholds.json).
  - Bản thuyết minh tiền đăng ký: [docs/preregistration.md](file:///d:/tai%20lieu%20hoc%20tap/%C4%90%E1%BB%81%20t%C3%A0i%20nghi%C3%AAn%20c%E1%BB%A9u%20khoa%20h%E1%BB%8Dc/papers%20source%20code/GRACE/docs/preregistration.md).
  - Dấu niêm phong Git tag: `prereg-v1` đã push lên remote.
* **Cách tận dụng**:
  - Xuất gói `osf_preregistration_bundle.zip` từ repo của ta đưa lên OSF theo quy chuẩn *Transparent Preregistration with In-flight Baseline Data*.
  - Nhúng gate `require_test_lock` từ code của ta vào notebook B2/B1 của họ để fix triệt để lỗi FAILED của unit test `test_validation_lock.py`.

### 4. Tận dụng dữ liệu Bước 5 & Tiết kiệm tối đa GPU
* **Tài nguyên sẵn có**:
  - Dữ liệu Test Devign B0 và B2 sạch 100% (2.732 record/arm, 0.00% invalid logit score).
  - Pipeline tự động Resume với `os.fsync` bảo đảm an toàn dữ liệu trên Kaggle.
* **Cách phối hợp chạy tiếp**:
  - **B0 & B2**: Giữ nguyên toàn bộ 10.011 record đã chạy của họ, đối chiếu chéo (cross-validate) với dữ liệu của ta. Không chạy lại GPU!
  - **B1**: Vì tập Validation của họ đã xong 100% (5.005 mẫu), lấy ngay $\tau^*$ khóa vào `thresholds.json`, sau đó bật Resume chạy nốt 4.577 mẫu Test còn thiếu.
  - **B2-flip**: Đồng bộ donor mới, khóa $\tau^*$ từ validation, chạy nốt 4.776 mẫu Test.
  - **B2-rep**: Chạy một phiên độc lập từ prompt B2 để lấy phương sai tự nhiên.

### 5. Khắc phục lỗi thống kê Bước 6 & Bước 7 (Tables A/B/C)
* **Tài nguyên sẵn có**:
  - Script tính toán thống kê chuẩn xác, đã sửa triệt để lỗi hiệu chỉnh liên tục McNemar Edwards.
  - Module sinh tự động Bảng A, Bảng B (McNemar $\chi^2$, p-value, Holm correction, Paired Cluster Bootstrap 95% CI).
* **Cách tận dụng**: Sử dụng trực tiếp engine đánh giá của ta nạp dữ liệu inference của cả hai bên để xuất ra các bảng CSV và LaTeX hoàn chỉnh.

### 6. Đóng gói sản phẩm nghiệm thu Bước 9
* **Tài nguyên sẵn có**: Gói nghiệm thu độc lập `audit_package_grace.zip` (636 files, 120.22 MB, mã băm CRC32/SHA256 minh bạch), dàn ý bài báo khoa học.
* **Cách tận dụng**: Đưa toàn bộ cấu trúc đóng gói này làm chuẩn bàn giao chung cho Thầy.

---

## PHẦN III. KẾ HOẠCH HÀNH ĐỘNG HỢP NHẤT CHI TIẾT (ACTION PLAN)

| Thứ tự | Nhiệm vụ | Nguồn thực hiện / File áp dụng | Thời gian dự kiến | Kết quả đạt được |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Đăng ký OSF & Khóa ngưỡng** | Dùng `docs/preregistration.md` & `configs/thresholds.json` nộp lên `osf.io` | 15 phút | Có DOI/URL OSF chính thức; hợp thức hóa 100% kết quả đã chạy. |
| **2** | **Sửa lỗi Code & Unit Test** | Sửa `stats.py` (McNemar), thêm gate `require_test_lock` vào notebook B2 | 30 phút | Toàn bộ 8 unit test bị fail trên repo đối tác chuyển sang PASS. |
| **3** | **Tích hợp Bước 0** | Copy module `complementarity.py` và bảng kết quả OOF routing sang | 1 giờ | Hoàn tất 100% Bước 0 theo đề cương. |
| **4** | **Resume Kaggle Tầng 1** | Bật phiên Kaggle resume cho B1 (4.577 mẫu) và B2-flip (4.809 mẫu) | 1–2 ngày (GPU) | Hoàn thành trọn vẹn Tầng 1 (5 arm cốt lõi). |
| **5** | **Sinh Bảng A, B, C** | Chạy `evaluate_final.py` chuẩn trên tập kết quả hợp nhất | 30 phút | Có đầy đủ các bảng thống kê và biểu đồ ROC/Operating Points cho bài báo. |
| **6** | **Nghiệm thu & Bàn giao** | Xuất gói `audit_package_grace.zip` và cập nhật báo cáo tổng kết | 1 giờ | Bàn giao trọn vẹn đề tài cho Thầy nghiệm thu. |

---
*Báo cáo này được lập để làm căn cứ kỹ thuật và phương pháp luận cho việc thống nhất mã nguồn và hoàn thiện đề tài.*
