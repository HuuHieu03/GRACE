# grace_diag_kit — bộ công cụ cho lượt chạy xác nhận "tái lập có chẩn đoán" GRACE

Gói này bổ sung cho hai bản mã hiện có của nhóm (repo tái triển khai với `prompt_contract.py`,
`run_verified_experiment.py`; và gói H3-B `grace_h3v2`) đúng những phần còn thiếu của đề cương:

| Phần | File | Trả lời cho |
| --- | --- | --- |
| Bộ dựng prompt theo Hình 6 + 15 arm/probe thay-một-thành-phần | `src/grace_diag/probes.py`, `configs/arms.yaml` | RQ1–RQ3 |
| Ngân sách context bằng token của tokenizer model | `src/grace_diag/token_budget.py` | Mục 6.4 |
| Gọi LLM tự host (vLLM / llama.cpp) và lấy điểm số s từ logprob token đầu | `src/grace_diag/llm_backend.py`, `configs/backend_*.yaml` | RQ4 |
| Kiểm tra toàn vẹn prompt trước khi gọi LLM | `src/grace_diag/prompt_audit.py` | Bước 3 |
| Mốc có giám sát SUP-LR / SUP-MLP / SUP-METRIC | `src/grace_diag/supervised_anchor.py` | RQ5 |
| Giá trị bổ sung: P_pre/P_post, sửa–hỏng theo lớp với đối chứng expert hằng/ngẫu nhiên, trần oracle, routing theo ngân sách | `src/grace_diag/complementarity.py` | RQ5b |
| Bootstrap ghép cặp (từng mẫu hoặc theo cụm), McNemar, Holm, biên δ và quy tắc kết luận 4 ô, độ nhạy nhãn | `src/grace_diag/stats.py` | Mục 6.6 |
| Sinh bảng A/B/C + hình từ `runs/final` | `src/grace_diag/evaluate_final.py` | Bước 7 |
| Chạy ma trận có journal/resume/cache; smoke test; manifest; gói ca chấm mù | `scripts/*.py` | Bước 1, 2, 5, 8 |
| Giao thức đăng ký trước dạng máy đọc được | `configs/protocol.yaml` | Bước 4 |

## Cài đặt

```bash
pip install -e grace_diag_kit            # numpy, scipy, scikit-learn, pyyaml, openai
pip install transformers                 # tokenizer của model (bắt buộc cho lượt chạy thật)
pip install matplotlib pytest            # hình và kiểm thử
python -m pytest grace_diag_kit/tests    # 29 test phải xanh trước khi dùng
```

## Thứ tự chạy (tóm tắt; chi tiết ở Mục 7–8 của đề cương)

```bash
# 0. (3 ngày đầu) phân tích offline từ dự đoán đã có — không cần GPU
python -m grace_diag.complementarity --val val.csv --test test.csv --tau 0.53 --out runs/complementarity_devign.json

# 1. server LLM + smoke test
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct --max-model-len 8192 --seed 42 --enable-prefix-caching --port 8000
python scripts/run_matrix.py --dataset devign --split validation --specs data/specs/devign_validation.jsonl \
    --donors data/manifests/devign_donors.jsonl --arms B2 --dry-run --out runs/dryrun
python scripts/smoke_test_backend.py --backend configs/backend_vllm.yaml --prompts runs/dryrun/prompts_devign_validation.jsonl

# 2. đóng băng dữ liệu
python scripts/build_manifests.py --train raw/devign_train.jsonl --validation raw/devign_validation.jsonl \
    --test raw/devign_test.jsonl --dataset devign --out data/manifests
python scripts/convert_verified_plan.py --plan <plan schema v2 của repo> --out data/specs/devign_validation.jsonl

# 3. audit prompt (mọi arm, split validation) rồi mới đăng ký trước
python scripts/run_matrix.py ... --arms $(python -c "import yaml;print(' '.join(a['name'] for a in yaml.safe_load(open('configs/arms.yaml'))['arms']))") --dry-run --out runs/dryrun
python -m grace_diag.prompt_audit --prompts runs/dryrun/prompts_devign_validation.jsonl --out-dir runs/dryrun/audit

# 5. ma trận: validation trước (chọn τ*), test một lần
python scripts/run_matrix.py --dataset devign --split validation --specs ... --donors ... --arms B0 B1 B2 B2-flip B2-rep --seeds 42 --backend configs/backend_vllm.yaml --out runs/final
python scripts/run_matrix.py --dataset devign --split test       --specs ... --donors ... --arms B0 B1 B2 B2-flip B2-rep --seeds 42 --backend configs/backend_vllm.yaml --out runs/final

# 6. mốc có giám sát
python -m grace_diag.supervised_anchor --dataset devign --emb-train ... --emb-val ... --emb-test ... --code-train ... --code-val ... --code-test ... --out-dir runs/anchor

# 7. bảng và hình
python -m grace_diag.evaluate_final --runs runs/final --protocol configs/protocol.yaml --anchor-csv runs/anchor/anchor_scores.csv --out runs/tables

# 8. gói ca chấm mù phân tầng
python scripts/make_case_packets.py --records runs/final/devign/test/B2/42/records.jsonl --anchor runs/anchor/anchor_scores.csv --tau 0.53 --code raw/devign_test.jsonl --out packets/devign_B2
```

Định dạng dữ liệu vào/ra, cách nối với mã hiện có và các chỗ cần sửa trong repo được mô tả
trong `integration/INTEGRATION.md`.

## Nguyên tắc mã

- Nhãn của target không bao giờ đi vào `render_arm` (hàm từ chối khi thấy trường `target`/`label`).
- Mỗi arm khác arm gốc đúng một khối; `tests/test_probes.py` kiểm tra điều này bằng `diff_blocks`.
- Mọi lượt gọi LLM được cache theo `sha256(prompt | model | tham số | parser_version)`; đổi model
  hay tham số là một cache khác.
- Metric không xác định (MCC của predictor hằng, AUROC khi thiếu một lớp) trả `None`/`N/A`, không ép 0;
  số lượt bootstrap suy biến được báo cáo cùng CI.
- Kết luận đọc từ CI và biên δ đã khai báo: `benefit`, `no_meaningful_benefit`, `harm`, `inconclusive`.
