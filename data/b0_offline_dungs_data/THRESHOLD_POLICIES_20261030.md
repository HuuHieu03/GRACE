# Đính chính ngưỡng cho phân tích Bước 0

Phân tích chính theo B3 của đề cương và INTEGRATION.md dùng một gate chung với ngưỡng của base winner chọn trên train nested OOF, không chọn trên test. Nguồn: `GRACE-H3-BenchmarkEnsemble/artifacts/h3v2/base/<dataset>/42/<checkpoint>/manifest.json`, trường `winner.name` và `winner.threshold`.

| Dataset | Checkpoint | Base winner | Train OOF τ | Kết quả phân tích chính | Gate tuned τ |
|---|---|---|---:|---|---:|
| Devign | a93a831ac8416426a1d4 | fusion_all | 0.36 | `runs/complementarity_devign.train_oof.json` | 0.53 |
| ReVeal | b4564696e647259a09b9 | fusion_semantic_lexical | 0.17 | `runs/complementarity_reveal.train_oof.json` | 0.14 |

Ngưỡng validation 0.53/0.14 là mốc lịch sử `gate_tuned` đã được khóa và công bố trong Mục 2.1; kết quả của nó giữ ở `runs/complementarity_<dataset>.json` như phân tích tham chiếu riêng. Không gọi các file này là phân tích chính theo B3 và không so chính sách router dùng train OOF với mốc gate_tuned mà không nêu sự khác biệt.

Test train OOF: Devign repair 694, harm 858, oracle accuracy 0.8656661786; ReVeal repair 180, harm 197, oracle accuracy 0.9406332454. Nhãn dự đoán trên test ở cả hai dataset khớp 100% với run `notebook_sessions/deepseek_v41_hieu_8192_seed42/test/<dataset>/42/gate_train_threshold.jsonl`, theo từng record ID. Một run `5fc21bd...` khác dùng checkpoint khác, không được thay thế cho checkpoint đã khóa.

P_pre/P_post là cặp meta-model với ngưỡng của riêng chúng chọn trên validation OOF; so sánh P_pre/P_post không thay đổi khi thay ngưỡng gate trong lần chạy này. Routing và sửa–hỏng dùng ngưỡng gate đã nêu. Toàn bộ phân tích là thăm dò: expert lịch sử chỉ có nhãn 0/1 và validation trộn provider.

Tái tạo: `.venv-b0-312/Scripts/python.exe B0_offline/rebuild_complementarity_locked.py devign train_oof` (tương tự `reveal`). Kiểm tra bằng `B0_offline/audit_threshold_policies.py`. Không đổi các prediction hoặc metric gốc của H3-B.
