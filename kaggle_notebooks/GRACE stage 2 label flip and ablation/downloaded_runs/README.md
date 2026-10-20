# 📥 Kaggle Executed Runs & Artifacts

Thư mục này được sử dụng để lưu trữ các phiên bản notebook (`.ipynb`) và kết quả đầu ra (`output/`) tải về từ Kaggle sau khi chạy thực nghiệm.

### Lệnh tải kết quả về thư mục này bằng Kaggle CLI:

```powershell
# 1. Tải toàn bộ file kết quả (Báo cáo JSON/CSV) về thư mục output/stage2/label_flip/
$env:PYTHONUTF8="1"; kaggle kernels output huuhieu3333/grace-stage-2-label-flip-and-ablation -p ./output/stage2/label_flip

# 2. Tải bản Notebook (.ipynb) đã chạy đầy đủ log từng ô code về thư mục này
$env:PYTHONUTF8="1"; kaggle kernels pull huuhieu3333/grace-stage-2-label-flip-and-ablation -p "./kaggle_notebooks/GRACE stage 2 label flip and ablation/downloaded_runs/Ver01_Label_Flip" -m
```
