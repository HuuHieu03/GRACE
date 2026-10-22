---
version: "2.0.0"
date: "2026-10-22"
type: "report"
status: "DRAFT"
target_component: "Supervisor progress report after evidence reconciliation"
tags: ["supervisor", "progress", "limitations", "failure_analysis"]
summary: "Bản tiến độ đã sửa claims và nguồn số liệu, có thể dùng trao đổi với thầy; chưa nghiệm thu cải tiến hoặc independent human review."
---

# Báo cáo tiến độ sau đối soát — 22/10/2026

Nhóm đã chuyển trọng tâm từ tăng F1 sang kiểm tra tính đáng tin của số liệu theo yêu cầu thầy. Công việc kỹ thuật có Codex hỗ trợ. **Hiện chưa đủ bằng chứng kết luận phương pháp cải tiến khả năng phân biệt vulnerable/safe; chưa hoàn tất chấm mù độc lập hợp lệ.** Báo cáo này trình bày tiến độ và failure modes, không phải nghiệm thu toàn bộ đề tài.

## Kết quả còn truy vết được

| Run | N | F1 | MCC | Balanced accuracy | Giới hạn |
|---|---:|---:|---:|---:|---|
| Stage2 Devign B2 original | 100 | 0.3415 | -0.0500 | 0.4775 | Có per-ID/raw; chưa có actual prompt đầy đủ. |
| Stage3 Devign B3 Ver03 | 100 | 0.5500 | -0.1118 | 0.4469 | Metric khớp records; thiếu raw/prompt và B2 per-ID cùng run. |
| Stage3 ReVeal B3 Ver04 | 100 | 0.5176 | 0.1887 | 0.5900 | Tương tự; thêm vấn đề identity/overlap/bộ chấm ReVeal. |
| Devign B3-NoDiff Ver05 | 100 | 0.5138 | -0.0686 | 0.4658 | Có thể đối chiếu Full–NoDiff records; chưa chứng minh block diff có lợi. |

[Nguồn, SHA-256 và metric đầy đủ](verified_sources_2026-10-22/report.md) kèm CSV có confusion matrix, precision/recall, predicted vulnerable rate, coverage và trivial baselines trên cùng IDs. CSV summary mâu thuẫn đã bị loại khỏi nguồn báo cáo; giữ nguyên file để truy vết.

Devign Stage3 B2 aggregate ghi MCC=-0.0292/BA=.4867; B3 giảm xuống-.1118/.4469 dù F1 tăng. ReVeal aggregate có tăng nhẹ MCC/BA nhưng paired95% CI ΔMCC/ΔBA đã báo đều chứa0. Các paired statistics B2–B3 này chỉ còn reported-only vì B2 per-ID mất. Người dùng đã xác nhận B2 chi tiết Ver03/Ver04 không còn/không tồn tại; không lấy Stage2 thay cho baseline cùng run.

Đối chiếu Full–NoDiff trên cùng100 IDs: thêm5TP và6FP; CI ΔF1=[-.0156,.0993], ΔMCC=[-.1672,.0841], đều chứa0. Rút kết luận đóng góp82.6%/17.4% và giảm label sensitivity31%→18%/13%: baseline khác run, B3 đang đo order swap chứ không đo label flip cùng phép đối chứng.

## Đối soát dữ liệu và review

- Sidecar v2 cấp UID riêng cho21.854 Devign/18.187 ReVeal train functions. Đã kiểm source code của40.241 train và200 target với file `.c`; không sửa nhãn/kết quả cũ. ReVeal legacy ID không duy nhất nên không dùng nó một mình để phục dựng demo.
- Devign clean100 thực tế54/46, không phải50/50 như metadata cũ. ReVeal có2target trùng code train nhưng khác nhãn; đã gắn quarantine cho đánh giá mới, chưa tự adjudicate nhãn.
- Lexical token5 Jaccard≥.8 trên full train tìm8candidate pairs Devign và89ReVeal. Đây là các ca cần đọc code, không chứng minh đã loại mọi semantic/renamed clone.
- Phiếu ReVeal cũ không khớp code target/ID; generator cũ chọn B3 theo target label và có baseline thay thế sai. Chưa nghiệm thu independent review100mẫu; các Kappa/tỷ lệ ưu tiên cũ không dùng xác nhận retrieval tốt hơn. Hai phiếu H2 mới vẫn trống.
- H2 replay source/input/vector/top50/score/policy khớp100/100; R1 đổi0/100 demo. Đây là kết quả âm về selection, chưa cho biết relevance hoặc detection quality. Không chạy hai arm LLM giống demo để quy lợi ích cho policy.

## Phần kỹ thuật đã sửa

Đã tạo đường chạy mới có frozen plan và per-ID/per-condition journal: lưu SDK payload trước gọi, raw completion, parse, usage/finish reason và attempts; hash toàn bộ plan/input/source để tránh resume nhầm. Invalid vẫn nằm trong coverage. Parser run mới strict0/1; không dùng reasoning thay final answer. Schema evaluator chung đọc được Stage2/Stage3/v2 và phân biệt raw thiếu với response rỗng thật.

Đã kiểm graph endpoint closure, giới hạn code/demo và token budget theo chat template; controls giữ cố định selections/code/order phù hợp từng phép thử. Real plan thiếu tokenizer binding, graph provenance hoặc manifest tương ứng bị từ chối. Stage3 real runner cũ bị chặn để không tạo thêm run thiếu evidence.

Kiểm thử: **586 tests đạt**; synthetic smoke20conditions, **0 API calls**. Đây là xác nhận hạ tầng, không phải hiệu năng model mới. [Bàn giao kỹ thuật và lệnh tái lập](verified_protocol_2026-10-22/report.md).

## Việc nghiên cứu còn lại

1. Rà candidate near-clones, nguồn nhãn mâu thuẫn và exposure; chốt protocol/development mới, chưa dùng current canonical100 như final test.
2. Chuẩn bị full retrieval selections và tokenizer/graph provenance cho real plan. Chưa có thực nghiệm LLM mới được thực hiện.
3. Chạy đúng một giả thuyết với controls cần thiết, lưu đầy đủ B2/B3 và actual requests; không tự mở benchmark lớn.
4. Tạo packet từ code/UID/demo thật của run mới; hai người chấm riêng, khóa phiếu trước đối soát, giữ bất đồng.
5. Tái tính MCC/BA/confusion matrix/coverage/trivial baselines và paired CI từ cả hai arm. Nếu chưa có tín hiệu, báo failure modes thay vì kết luận cải tiến.

Các nội dung trên phù hợp để báo cáo **tiến độ và vấn đề đang xử lý** với thầy; chưa đạt Definition of Done cho tuyên bố “cải tiến có tác dụng”.
