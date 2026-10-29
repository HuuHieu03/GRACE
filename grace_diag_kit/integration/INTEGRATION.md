# Hướng dẫn tích hợp vào phần mềm thực nghiệm hiện có

Có hai bản mã đang dùng trong nhóm. Gói `grace_diag_kit` không thay thế chúng; nó nối vào ở ba
điểm: (1) lấy `prompt_spec` đã đóng băng từ repo tái triển khai, (2) thay lớp gọi API bằng
backend tự host có logprob, (3) đưa điểm số s và đặc trưng nền của H3-B vào phân tích giá trị
bổ sung. Dưới đây là từng chỗ cần sửa, theo thứ tự nên làm.

## A. Repo tái triển khai (thư mục `src/`, `scripts/`)

### A1. Lấy specs từ plan "verified protocol" (không sửa mã cũ)

`scripts/prepare_verified_plan.py` hiện sinh plan schema v2 với `items[].prompt_spec`
(`query_code`, `nodes`, `edges`, `demonstrations`, `security_difference`). Dùng nguyên plan đó:

```bash
python scripts/prepare_verified_plan.py --draft drafts/devign_validation.json --output output/plans/devign_validation.json
python grace_diag_kit/scripts/convert_verified_plan.py --plan output/plans/devign_validation.json \
    --out data/specs/devign_validation.jsonl --h2 data/h2/devign_validation_evidence.jsonl
```

`convert_verified_plan.py` gộp demo của arm `b2` (1 demo) và `b3` (2 demo + `security_difference`)
theo id và chỉ ghi nhãn vào trường `label` (được tách ra trước khi dựng prompt). Lưu ý: plan hiện
chỉ có `prompt_spec` cho validation/test đang chạy; cần chạy `prepare_verified_plan.py` cho cả
official validation (chọn ngưỡng) và test (kết luận).

### A2. Kho donor cho B2-rand và B1-shuf

Từ `*_train_compact_cpg.json.gz` (kho retrieval) xuất JSONL `{id, func, target, nodes, edges}` rồi:

```bash
python grace_diag_kit/scripts/build_manifests.py --train raw/devign_train.jsonl \
    --validation raw/devign_validation.jsonl --test raw/devign_test.jsonl --dataset devign --out data/manifests
```

File `devign_donors.jsonl` chỉ chứa hàm train không trùng chính xác với validation/test và không
thuộc nhóm nhãn mâu thuẫn — đúng kho đã khử trùng mà B2 dùng để truy hồi.

### A3. Backend tự host trong `src/evaluator.py` (nếu muốn chạy bằng runner cũ)

Đường ngắn nhất là dùng `grace_diag_kit/scripts/run_matrix.py` (đã có journal, resume, cache) và
giữ `run_verified_experiment.py` cho các lượt API lịch sử. Nếu muốn một runner duy nhất, sửa ba chỗ:

1. `make_request_payload(inference, prompt)`: thêm

   ```python
   if inference["provider"] in ("vLLM", "llama.cpp"):
       payload.update(logprobs=True, top_logprobs=inference.get("top_logprobs", 5), seed=inference["seed"])
       if inference.get("guided_choice"):
           payload["extra_body"] = ({"guided_choice": ["0", "1"]} if inference["provider"] == "vLLM"
                                    else {"grammar": 'root ::= "0" | "1"'})
   ```

2. `LLMEvaluator.__init__`: nhánh provider mới `_init_local_client()` với
   `openai.OpenAI(base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:8000/v1"), api_key="EMPTY", max_retries=0)`.

3. `LLMEvaluator.generate_response`: sau khi có `choice`, lưu
   `metadata["top_logprobs"] = {t.token: t.logprob for t in choice.logprobs.content[0].top_logprobs}`
   (bọc trong `try` vì Vertex không trả trường này).

### A4. Parser logprob trong `scripts/run_verified_experiment.py`

- `validate_plan`: cho phép `inference["provider"] in ("Vertex AI", "vLLM", "llama.cpp")` và
  `plan["parser_policy"] in ("strict_binary_v1", "logprob_binary_v1")`.
- `execute`: khi `parser_policy == "logprob_binary_v1"`:

  ```python
  from grace_diag.llm_backend import parse_top_logprobs
  parsed = parse_top_logprobs(metadata.get("top_logprobs", {}))
  prediction, valid, method = parsed["pred_argmax"], parsed["valid"], "logprob_binary_v1"
  record.update(s=parsed["s"], p0=parsed["p0"], p1=parsed["p1"], top5=metadata.get("top_logprobs"))
  ```

  Mọi trường cũ (`llm_raw_response`, `finish_reason`, `usage`) giữ nguyên để `common_evaluator.py`
  vẫn reparse được.

### A5. Thứ tự khối prompt

`prompt_contract.render_control` đặt demonstration TRƯỚC target (demo-first) và cắt theo ký tự.
Lượt xác nhận dùng `grace_diag.probes.render_arm` (demo SAU graph, cắt theo token). Không sửa
`render_control` — giữ nó để tái lập các run lịch sử; trong bài ghi rõ hai bản có thứ tự khác nhau.
Nếu muốn `validate_payload_plan` kiểm tra lại prompt của lượt mới, thêm một nhánh:

```python
if plan.get("payload_contract", {}).get("renderer") == "figure6_v2":
    from grace_diag.probes import render_arm
    rendered = render_arm(spec, item["arm"], item["seed"], counter, donors, budget=plan["token_budget"])
```

### A6. Kiểm thử

Chép `grace_diag_kit/tests/test_probes.py` vào `tests/` của repo (đã có `conftest.py`) để mọi lần
sửa prompt builder đều chạy lại kiểm tra "mỗi arm khác arm gốc đúng một khối".

## B. Gói H3-B (`grace_h3v2`)

### B1. Xuất đặc trưng nền và p_gate

Trong `grace_h3v2/meta.py`, hàm `fit_meta` đã tính `scores` (5 view) và `probability` (winner).
Thêm hai dòng sau khi tính `pre = pre_features(rows, scores, probability)`:

```python
np.savez(root / base["folder"] / f"xpre_{split}.npz", X=pre, ids=np.array([r["record_id"] for r in rows]))
write_csv(root / base["folder"] / f"gate_{split}.csv", ["id", "y", "p_gate"], zip(ids, y, probability))
```

Làm cho cả validation và test (test chỉ có `p_gate`, không dùng nhãn để fit).

### B2. Thay expert 0/1 bằng điểm số s

`expert_records` hiện lấy `prediction` 0/1 từ API. Với lượt mới, đọc `records.jsonl` của
`run_matrix.py` (arm B2, seed 42) và lấy `s`, `valid`. Ghép hai nguồn thành CSV
`id,y,p_gate,s_llm,valid[,group]` cho mỗi split rồi chạy:

```bash
python -m grace_diag.complementarity --val devign_val.csv --test devign_test.csv \
    --xpre-val xpre_validation.npz --xpre-test xpre_test.npz --tau <τ của gate chung> --out runs/complementarity_devign.json
```

Kết quả gồm: `repair_harm_test` (R_y, H_y theo lớp), `reference_experts_test` (ALL-0, ALL-1,
RANDOM cùng tỷ lệ đoán 1), `oracle_test`, cặp `pre_post_*` (ΔMCC, CI, kết luận theo δ = 0,02) và
`routing_test` (random × 20 seed, confidence, benefit, oracle tại q = 5/10/25 %).

### B3. Một ngưỡng chung

Mọi policy trong bảng so sánh dùng cùng nhãn `h` từ cùng gate và cùng τ (ngưỡng chọn trên train
OOF như `base['winner']` đang làm). `gate_tuned` (ngưỡng chọn trên validation) chỉ được báo thêm
dưới tên riêng, không trộn vào cặp so sánh. Không chọn lại winner bằng test (ví dụ `gate_0_5`
có MCC cao hơn trên Devign nhưng winner đã khóa vẫn giữ).

### B4. Phân rã sửa–hỏng đúng chiều

Chiều chuẩn là classifier → expert: R = classifier sai & expert đúng, H = classifier đúng & expert
sai. Bảng đối soát cũ tính theo chiều ngược (full GRACE → gate); khi dùng lại phải đổi chiều và
luôn kèm hàng đối chứng expert hằng/ngẫu nhiên do `reference_experts` sinh.

## C. Định dạng file trao đổi

| File | Cột / trường | Ai tạo |
| --- | --- | --- |
| `data/specs/<dataset>_<split>.jsonl` | id, query_code, nodes, edges, demonstrations, demonstrations_pair, security_difference, h2_evidence, label, group | convert_verified_plan.py |
| `data/manifests/<dataset>_donors.jsonl` | function_uid, func, target, nodes, edges | build_manifests.py |
| `runs/final/<dataset>/<split>/<arm>/<seed>/records.jsonl` | schema B.2 (+ s, p0, p1, top5, valid, tokens_*, truncated, group) | run_matrix.py |
| `runs/anchor/anchor_scores.csv` | id, dataset, split, arm, seed, score | supervised_anchor.py |
| `<dataset>_<split>.csv` cho complementarity | id, y, p_gate, s_llm, valid, group | ghép từ H3-B + records |
| `runs/tables/table_{A,B,C}.csv/.tex`, `fig_*.png` | — | evaluate_final.py |
