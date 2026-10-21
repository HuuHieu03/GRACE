# 🚀 GRACE Stage 3: Head-to-Head Comparison (B3 vs B2) trên Kaggle

Thư mục này chứa toàn bộ tài nguyên đóng gói cho thực nghiệm **Đợt 3 (Stage 3: B3 vs B2)** trên Kaggle GPU:
- **Notebook**: `stage3_b3_vs_b2_kaggle.ipynb`
- **Metadata**: `kernel-metadata.json`

### 1. Hướng dẫn đẩy Kernel lên Kaggle (Kaggle CLI):
```powershell
# Chuyển vào thư mục notebook Đợt 3
cd "kaggle_notebooks/stage3_b3_vs_b2"

# Đẩy mã nguồn và khởi chạy kernel trên Kaggle GPU
$env:PYTHONUTF8="1"; kaggle kernels push -p .
```

### 2. Kiểm tra tiến độ chạy thực nghiệm:
```powershell
kaggle kernels status huuhieu3333/grace-stage-3-b3-vs-b2-contrastive
```

### 3. Tải kết quả báo cáo sau khi hoàn tất:
```powershell
# Tải kết quả về thư mục output/stage3/
$env:PYTHONUTF8="1"; kaggle kernels output huuhieu3333/grace-stage-3-b3-vs-b2-contrastive -p ../../output/stage3/
```
