---
version: "2.0.0"
date: "2026-10-22"
type: "report"
status: "COMPLETED"
target_component: "Versioned function identity and data audit"
tags: ["data_contract", "identity", "leakage", "development"]
summary: "Đã tạo sidecar UID duy nhất, kiểm tra toàn bộ source .c, phân bố thực và lexical near-clone; không sửa dữ liệu hoặc nhãn lịch sử, chưa xác minh gold label/semantic clones."
---

# Contract dữ liệu v2 — kết quả phần kỹ thuật của việc 2

Đã xuất bốn sidecar tại `data/manifests/function_uid_v2/`: train và validation của Devign/ReVeal. Các dataset/split/run cũ giữ nguyên. Đây là dữ liệu development đã được xem trong quá trình audit, không phải final test mới hoặc một lần chạy LLM xác nhận.

## Identity và code

- `function_uid` lấy dataset, split, source path và SHA-256 code; **không lấy nhãn** để tạo UID. `legacy_id` chỉ giữ để truy vết, không dùng làm khóa duy nhất.
- UID train duy nhất: **21.854/21.854 Devign**, **18.187/18.187 ReVeal**. Giữ nguyên thứ tự, code và nhãn; không loại các train row chỉ vì trùng legacy ID.
- Đã đọc kiểm tra **40.241 file train và 200 file target `.c`**: code file gốc khớp code processed/split sau chuẩn hóa CRLF/LF và strip hai đầu. Metadata có một số khác biệt bố cục dòng được giữ hash riêng (`metadata_code_sha256`); không âm thầm thay code processed bằng metadata.
- `attach_manifest()` chỉ tạo bản copy trong bộ nhớ; từ chối sai thứ tự/code/nhãn/UID/manifest hash. Chưa tích hợp adapter này vào các runner lịch sử: bước 4 phải dùng manifest trong runner/cache mới trước run xác nhận.
- Sidecar là artifact sinh cục bộ trong vùng `data/` đang gitignored; script tái lập và report nằm trong source. Khi đóng gói runner mới phải kèm sidecar và hash, không chỉ upload code rồi bỏ quên identity manifest.

## Phân bố và overlap

| Dataset | Target thực | Metadata lịch sử | Exact train–target code overlap |
|---|---|---|---|
| Devign | 54 vulnerable / 46 safe | 50/50 | 0/100 |
| ReVeal | 50/50 | 50/50 | 2/100, cả hai khác nhãn train |

Hai target ReVeal `-16551315108292821` và `3728341105073176576` có code giống hệt train nhưng target=1/train=0. Sidecar gắn `QUARANTINED_CODE_OVERLAP`; **không tự sửa nhãn**, không tự chọn mẫu thay thế và không tính lại metric lịch sử như thể run đã dùng split mới. Muốn dùng cho đánh giá xác nhận phải xử lý lineage/nhãn hoặc đăng ký split mới trước khi chạy.

## Near-clone theo phép đo lexical đã công bố

Đã kiểm tra full train với 100 target mỗi dataset bằng Jaccard của tập token 5-gram, ngưỡng **0.8**, tối thiểu **20 token**. Inverted index chỉ tăng tốc tìm shared shingles; score theo đúng Jaccard, không dùng nhãn để chọn candidate.

| Dataset | Cặp candidate | Target có candidate | Cặp khác nhãn | Query ngoài scope vì ngắn |
|---|---:|---:|---:|---:|
| Devign | 8 | 6 | 4 | 1 |
| ReVeal | 89 | 31 | 46 | 2 |

Trong train có 434 Devign và 554 ReVeal dưới 20 token ngoài scope lexical này. Hai exact overlaps ReVeal đã nêu nằm trong 89 cặp, không cộng hai lần. `near_clone_audit.json` giữ function UID, row index, score và nhãn từng cặp.

Đây là **candidate cần đọc code**, không phải gold clone hoặc gold label. Không kết luận mọi near-clone đã được loại, đặc biệt renamed identifiers/control-flow/semantic clones. Tất cả target chưa overlap vẫn được đánh dấu development-only; không tự chuyển thành test sạch vì vượt qua một ngưỡng lexical.

## Kiểm tra và tái lập

1. `python scripts/build_dataset_contracts.py` — đối chiếu source metadata/code/file và tạo sidecar. Đọc toàn bộ source files nên lần chạy có thể mất vài phút.
2. `python scripts/audit_near_clones.py` — chạy offline full train, ghi candidate audit có hash manifests.
3. Tests mới: `tests/test_dataset_contract.py` (12 ca), `tests/test_near_clone_audit.py` (3 ca). Bao gồm ID collision, label không vào UID, sai code/order/nhãn/hash không được reuse, lexical candidates không bị tự relabel.

## Giới hạn còn mở

- Upstream dataset revision/gold labels chưa xác minh độc lập; input local snapshots được pin bằng SHA-256.
- Chưa adjudicate 97 cặp lexical candidates hoặc hai nhãn mâu thuẫn; giữ trạng thái unknown/quarantine phù hợp.
- Graph provenance/endpoints, token budget và checkpoint của runner cũ thuộc bước 4–5; identity manifest không tự sửa các vấn đề đó.
- Không tạo phiếu con người hoặc kết quả LLM mới trong việc 2.
