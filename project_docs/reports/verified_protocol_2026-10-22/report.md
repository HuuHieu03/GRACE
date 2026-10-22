---
version: "2.0.0"
date: "2026-10-22"
type: "report"
status: "COMPLETED"
target_component: "New execution, evaluation and prompt protocol"
tags: ["tracking", "evaluation", "prompt", "offline_validation"]
summary: "Đã triển khai và kiểm thử đường chạy mới có journal, strict parser, schema adapter, graph closure và controls; 586 tests đạt. Chưa gọi LLM thật, chưa xác nhận cải thiện mô hình."
---

# Bàn giao phần kỹ thuật việc 4–5

Đã hoàn tất triển khai và kiểm thử offline. **Không đồng nghĩa đã chạy thực nghiệm xác nhận hoặc hoàn thành chấm độc lập.** Toàn suite: `586 passed in 22.10s`; smoke synthetic: 20 condition, **0 API calls**. Chi tiết tại `mock_smoke_summary.json`. Nhãn synthetic là dữ liệu kiểm thử tự tạo, không phải gold security labels.

## Đường chạy mới

- `scripts/prepare_verified_plan.py`: dựng plan từ lựa chọn đã đóng băng và prompt specs; không retrieve lại demo giữa các controls, không gọi API.
- `scripts/run_verified_experiment.py`: mặc định chỉ validate; chỉ thực thi khi có `--execute`, output riêng. Không tự nạp baseline run khác. Plan chứa đủ mọi ID/arm/condition và nhãn evaluation nằm ngoài inference items.
- `src/experiment_tracking.py`: manifest đầy đủ plan/config/source hashes/Git commit/SDK version; fsync payload trước SDK, lưu raw completion, usage, finish reason và attempts. Không ghi auth token/header. Resume sai identity, journal hỏng hoặc request dở dang bị từ chối; lỗi ghi đĩa không dẫn tới retry trả phí.
- SDK retries được tắt; vòng ngoài tối đa5 attempts, backoff5/10/20/40, exhausted vẫn invalid trong coverage. Mock/real được gắn nhãn riêng. Usage thiếu ghi null, không tự suy chi phí.
- Run hoàn tất có thể đọc lại mà không khởi tạo/authenticate client. Run directory có execution lock; không xóa lock/request dở dang để cố resume khi chưa kiểm tra nhật ký.
- Stage3 real runner cũ bị chặn để tránh tạo thêm run mất B2/raw/prompt. Mock regressions và artifact lịch sử vẫn giữ nguyên. Runner/notebook legacy khác không được chứng nhận như đường chạy xác nhận v2.

## Evaluator và parser

- `src/record_schema.py` đọc Stage2 A/B/C, Stage3 B3 và schema records v2; chọn từng arm/condition, không gộp nhiều lần gọi thành mẫu số lớn hơn.
- `src/common_evaluator.py` không biến raw lịch sử thiếu thành response rỗng giả. Reparse lưu riêng raw unavailable và số thực sự reparse. Split match dùng đầy đủ IDs/labels, không fuzzy alias theo số.
- Run mới dùng `strict_binary_v1`: chỉ final content0/1; truncated finish=`length` là invalid. Reasoning được lưu riêng, không lấy thay final answer. Parser semantic cũ chỉ dành cho công cụ đọc/reparse lịch sử, không phải parser của run xác nhận mới.
- Reparse Stage2 original bằng adapter mới:100/100 raw,0 nhãn đổi. Stage3 thiếu raw không được tuyên bố đã reparse thành công.
- Records giữ đủ invalid; metric/baseline được tính cùng target IDs của từng condition. Paired inference thống kê xác nhận phải dùng records mới của cả hai arm; không phục dựng B2 lịch sử từ aggregate.

## Payload và controls

- `src/prompt_contract.py` dựng prompt có headings trung lập, không đưa query label vào renderer; label-flip chỉ đổi nhãn hiển thị do template sinh, không replace nội dung code.
- Có original, label_flip, order_swap, repeat_original, graph_omitted, no_difference. Repeat giữ prompt giống hệt; mọi condition cùng arm phải giữ cùng code/demo/graph/clues/candidate pool. Graph/no-diff ablation rỗng bị từ chối.
- Chọn tối đa25 nodes rồi chỉ giữ edges có đủ endpoints, tối đa25 edges; lưu số cắt/bỏ và graph hash. Không dựng graph giả khi graph thiếu.
- Target3000chars, demo1500/1200chars tùy one/two-shot; giữ phần code bị cắt trong evidence. Không cắt riêng một arm để lọt budget.
- Budget8192 gồm chat-template prompt tokens + max output + reserve64. Mock counter chỉ dành cho synthetic. Real yêu cầu tokenizer local ghim revision/file hashes, chat template và bằng chứng model-binding; `local_files_only=True`, không tự tải model hoặc fallback bộ đếm gần đúng.
- Real còn buộc50 candidates duy nhất từ cùng full train manifest, code/label/UID khớp, query overlap bị quarantine không được dùng; selections phải khớp artifact đóng băng. Graph thật phải có pinned export/source hash/version, không chứng nhận chỉ từ nonempty nodes/edges.

## Các giới hạn phải giải quyết trước run thật

1. Chốt lựa chọn retrieval mới và study design trên development; không gọi nó là phục hồi run Ver03/Ver04.
2. Cung cấp tokenizer/model binding và graph export provenance đúng yêu cầu. Hiện chưa tạo một real plan đủ điều kiện hoặc thử kết nối provider; các kiểm thử dispatch dùng fake SDK.
3. Ghi phạm vi near-clone/nhãn còn chưa xác minh và exposure; không coi canonical100 đã dùng audit là final test mới.
4. Sau khi có run thật lưu đủ B2/B3 mới dựng packet full code, hai người chấm riêng, khóa phiếu và đối soát. Chưa có phiếu hoặc Kappa mới được tạo.

## Lệnh sử dụng

```text
python scripts/prepare_verified_plan.py --draft <frozen-draft.json> --output <new-plan.json>
python scripts/run_verified_experiment.py --plan <new-plan.json>
python scripts/run_verified_experiment.py --plan <new-plan.json> --output <new-run-directory> --execute
python src/common_evaluator.py --input <report.json> --arm b2 --condition original --reparse
python scripts/smoke_verified_protocol.py --output <new-mock-directory>
```

Draft gồm execution_mode, inference, identity/input pins, evaluation_labels, design và frozen_selections. Mỗi frozen selection giữ id, ordered candidate_ids và prompt_specs cho từng arm. Real plan cần input roles pool_manifest/query_manifest/selection_plan; tokenizer pins và graph exports được kiểm lại trước thực thi. Không dùng draft/mock fixture làm real plan.
