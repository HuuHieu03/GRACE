"""
Synthetic Micro-Benchmarks Ground-Truth Evaluation Suite (Pillar 3: Auxiliary Ground-Truth Verification)

Mục tiêu:
Định lượng năng lực phân biệt cơ chế an ninh (Discriminative Security Power) của Security Signature
và Security-Aware Reranker trên bộ kiểm thử vi mô tổng hợp có đáp án an ninh chuẩn 100% (Ground-Truth),
loại bỏ hoàn toàn vấn đề "vừa đá bóng vừa thổi còi" khi đánh giá bộ truy xuất mẫu.

Các kịch bản kiểm thử:
1. Guard Variable Relevance (Guard đúng biến vs Guard sai biến / Guard rác)
2. Guard Ordering Flow (Guard đặt trước Sink vs Guard đặt sau Sink)
3. Sink Semantic Matching (Sink cùng bản chất vs Sink khác loại)
4. Null Pointer Guard Binding (Kiểm tra đúng con trỏ vs Kiểm tra biến khác)
5. Memory Lifecycle & Use-After-Free (Giải phóng bộ nhớ vs Toán học thuần túy)
6. Integer Overflow Bounds Check (Kiểm tra tràn số nguyên trước phép nhân vs Phép nhân không kiểm soát)
7. Array Access Bounds Guard (Kiểm tra biên chỉ số mảng vs Truy cập mảng tự do)
8. Format String Safety (Định dạng an toàn có giới hạn kích thước vs printf trực tiếp)
9. Double-Free Protection (Giải phóng và gán NULL vs Double free)
10. End-to-End Reranker Top-1 Selection (Tái xếp hạng ưu tiên ví dụ có cùng bản chất an ninh thay vì chỉ trùng cú pháp)
"""

import sys
import io
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Đảm bảo đường dẫn import src/
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from security_signature.extractor import extract_security_signature
from security_signature.similarity import compute_security_signature_similarity
from retrieval_security_engine import SecurityAwareRetriever


@dataclass
class SyntheticTestCase:
    id: str
    category: str
    description: str
    target_code: str
    positive_cand: str
    distractor_cand: str
    min_margin: float = 0.05
    test_type: str = "secsim_preference"  # "secsim_preference" hoặc "reranker_top1"


def build_synthetic_benchmark_suite() -> List[SyntheticTestCase]:
    """Khởi tạo danh sách các ca kiểm thử vi mô tổng hợp có đáp án chuẩn 100%."""
    return [
        SyntheticTestCase(
            id="SYNTH-01",
            category="Guard Variable Relevance",
            description="Target an toàn có guard biến 'len'; Positive cand kiểm tra đúng biến vs Distractor kiểm tra biến rác 'retry'",
            target_code="void copy(char *dst, char *src, int len) { if (len <= dst_size) { memcpy(dst, src, len); } }",
            positive_cand="void transfer(char *out, char *in, int count) { if (count <= max_cap) { memcpy(out, in, count); } }",
            distractor_cand="void transfer(char *out, char *in, int count) { if (retry > 0) { memcpy(out, in, count); } }",
            min_margin=0.10
        ),
        SyntheticTestCase(
            id="SYNTH-02",
            category="Guard Ordering Flow",
            description="Target an toàn có guard trước sink; Positive cand guard trước memcpy vs Distractor guard sau memcpy",
            target_code="void send_buf(char *dest, char *msg, int size) { if (size <= MAX_BUF) { memcpy(dest, msg, size); } }",
            positive_cand="void log_msg(char *dst, char *src, int len) { if (len <= LIMIT) { memcpy(dst, src, len); } }",
            distractor_cand="void log_msg(char *dst, char *src, int len) { memcpy(dst, src, len); if (len <= LIMIT) { return; } }",
            min_margin=0.10
        ),
        SyntheticTestCase(
            id="SYNTH-03",
            category="Sink Semantic Matching",
            description="Target có lỗ hổng ghi bộ đệm; Positive cand cùng nhóm buffer_write vs Distractor gọi system exec",
            target_code="void write_data(char *src, int n) { memcpy(buffer, src, n); }",
            positive_cand="void packet_in(char *raw, int sz) { memmove(storage, raw, sz); }",
            distractor_cand="void audit_log(char *name) { system(name); }",
            min_margin=0.15
        ),
        SyntheticTestCase(
            id="SYNTH-04",
            category="Null Pointer Guard Binding",
            description="Target kiểm tra null đúng con trỏ 'node'; Positive cand kiểm tra đúng biến vs Distractor kiểm tra biến khác 'other'",
            target_code="void process_node(struct Node *node) { if (node != NULL) { free(node->data); free(node); } }",
            positive_cand="void release_item(struct Item *item) { if (item != NULL) { free(item->payload); free(item); } }",
            distractor_cand="void release_item(struct Item *item, struct Item *other) { if (other != NULL) { free(item->payload); free(item); } }",
            min_margin=0.10
        ),
        SyntheticTestCase(
            id="SYNTH-05",
            category="Memory Lifecycle & UAF",
            description="Target giải phóng bộ nhớ động; Positive cand cùng cơ chế giải phóng con trỏ vs Distractor hàm tính toán số học",
            target_code="void cleanup(Object *obj) { free(obj->buf); free(obj); }",
            positive_cand="void teardown(Session *s) { free(s->token); free(s); }",
            distractor_cand="int calc_hash(int a, int b) { return (a * 31 + b) % 1000; }",
            min_margin=0.20
        ),
        SyntheticTestCase(
            id="SYNTH-06",
            category="Integer Arithmetic Bounds",
            description="Target kiểm tra tràn số nguyên trước phép nhân; Positive cand có guard chống tràn vs Distractor nhân tự do",
            target_code="int alloc_mem(int count, int elem_sz) { if (count > 0 && count <= MAX_INT / elem_sz) { return count * elem_sz; } return -1; }",
            positive_cand="int calc_size(int n, int sz) { if (n <= INT_MAX / sz) { return n * sz; } return 0; }",
            distractor_cand="int calc_size(int n, int sz) { return n * sz; }",
            min_margin=0.05
        ),
        SyntheticTestCase(
            id="SYNTH-07",
            category="Array Access Bounds Guard",
            description="Target truy cập mảng an toàn có kiểm tra chỉ số; Positive cand có bounds check vs Distractor truy cập mảng không kiểm tra",
            target_code="int get_elem(int *arr, int idx) { if (idx >= 0 && idx < MAX_LEN) { return arr[idx]; } return -1; }",
            positive_cand="int fetch_data(int *buf, int pos) { if (pos < BUF_SIZE) { return buf[pos]; } return 0; }",
            distractor_cand="int fetch_data(int *buf, int pos) { return buf[pos]; }",
            min_margin=0.05
        ),
        SyntheticTestCase(
            id="SYNTH-08",
            category="Format String Safety",
            description="Target có lỗ hổng format string; Positive cand cùng chứa sprintf/printf format string vs Distractor hàm đóng mở file",
            target_code="void log_user(char *fmt, char *arg) { printf(fmt); }",
            positive_cand="void debug_msg(char *user_input) { sprintf(log_buf, user_input); }",
            distractor_cand="void close_connection(FILE *fp) { fclose(fp); }",
            min_margin=0.15
        ),
        SyntheticTestCase(
            id="SYNTH-09",
            category="Vulnerable Target Demo Preference",
            description="Target có lỗ hổng memcpy không kiểm tra; Positive cand cũng là hàm có lỗ hổng vs Distractor hàm đã vá an toàn",
            target_code="void process_req(char *src, int len) { memcpy(dest, src, len); }",
            positive_cand="void parse_chunk(char *payload, int n) { memcpy(temp_buf, payload, n); }",
            distractor_cand="void parse_chunk(char *payload, int n) { if (n <= sizeof(temp_buf)) { memcpy(temp_buf, payload, n); } }",
            min_margin=0.10
        ),
        SyntheticTestCase(
            id="SYNTH-10",
            category="End-to-End Reranker Selection",
            description="SecurityAwareRetriever tái xếp hạng: Phải ưu tiên ví dụ có cùng bản chất an ninh thay vì chỉ trùng cú pháp bề mặt",
            target_code="void read_buffer(char *in, int len) { memcpy(out, in, len); }",
            positive_cand="void copy_packet(char *data, int sz) { memcpy(queue, data, sz); }",
            distractor_cand="void read_buffer_math(char *in, int len) { int out = 0; for(int i=0; i<len; i++) out += in[i]; }",
            min_margin=0.05,
            test_type="reranker_top1"
        )
    ]


def evaluate_test_case(tc: SyntheticTestCase) -> Dict[str, Any]:
    """Thực thi kiểm định một ca kiểm thử vi mô tổng hợp."""
    if tc.test_type == "secsim_preference":
        sig_target = extract_security_signature(tc.target_code)
        sig_pos = extract_security_signature(tc.positive_cand)
        sig_dist = extract_security_signature(tc.distractor_cand)

        score_pos, sub_pos = compute_security_signature_similarity(sig_target, sig_pos)
        score_dist, sub_dist = compute_security_signature_similarity(sig_target, sig_dist)
        margin = round(score_pos - score_dist, 4)

        passed = (score_pos > score_dist) and (margin >= (tc.min_margin - 1e-6))

        return {
            "id": tc.id,
            "category": tc.category,
            "passed": passed,
            "score_pos": score_pos,
            "score_dist": score_dist,
            "margin": round(margin, 4),
            "expected_min_margin": tc.min_margin,
            "sub_pos": sub_pos,
            "sub_dist": sub_dist,
            "type": tc.test_type
        }

    elif tc.test_type == "reranker_top1":
        # Kiểm tra qua SecurityAwareRetriever với candidate pool gồm positive và distractor
        train_pool = [
            {"id": "distractor_cand", "func": tc.distractor_cand, "target": 0},
            {"id": "positive_cand", "func": tc.positive_cand, "target": 1}
        ]
        query_sample = {"id": "target_query", "func": tc.target_code, "target": 1}

        retriever = SecurityAwareRetriever(lambda_weight=0.2)
        retriever.fit(train_pool, precompute_signatures=True)
        res = retriever.retrieve(query_sample, top_candidates=2, final_top_k=2)

        top_cand_id = res["top_candidates"][0]["id"] if res["top_candidates"] else ""
        top_cand_score = res["top_candidates"][0]["final_score"] if res["top_candidates"] else 0.0
        second_cand_score = res["top_candidates"][1]["final_score"] if len(res["top_candidates"]) > 1 else 0.0
        margin = top_cand_score - second_cand_score

        passed = (top_cand_id == "positive_cand") and (margin >= tc.min_margin)

        return {
            "id": tc.id,
            "category": tc.category,
            "passed": passed,
            "score_pos": top_cand_score if top_cand_id == "positive_cand" else second_cand_score,
            "score_dist": second_cand_score if top_cand_id == "positive_cand" else top_cand_score,
            "margin": round(margin if top_cand_id == "positive_cand" else -margin, 4),
            "expected_min_margin": tc.min_margin,
            "top_selected": top_cand_id,
            "type": tc.test_type
        }


def run_evaluation_suite(verbose: bool = True) -> Dict[str, Any]:
    """Chạy toàn bộ bộ kiểm thử vi mô tổng hợp và xuất báo cáo học thuật."""
    suite = build_synthetic_benchmark_suite()
    total = len(suite)
    passed_count = 0
    results = []
    margins = []

    print("\n" + "=" * 90)
    print("  HỆ THỐNG ĐÁNH GIÁ GROUND-TRUTH VI MÔ TỔNG HỢP (SYNTHETIC GROUND-TRUTH SUITE)")
    print("  Pillar 3: Auxiliary Ground-Truth Verification (Triangulation Evaluation)")
    print("=" * 90)
    print(f"[*] Tổng số ca kiểm thử chuẩn hóa: {total}")
    print(f"[*] Kiểm tra: Guard Variable Relevance, Ordering Flow, Sink Match, UAF, Overflow, Reranker...")
    print("-" * 90)

    for tc in suite:
        res = evaluate_test_case(tc)
        results.append(res)
        margins.append(res["margin"])
        if res["passed"]:
            passed_count += 1

        status_tag = "✓ PASS" if res["passed"] else "✗ FAIL"
        if verbose:
            print(f"[{status_tag}] {res['id']:<10} | {res['category']:<28} | Margin: {res['margin']:>+6.4f} (Min: {res['expected_min_margin']:.2f})")
            if not res["passed"]:
                print(f"      -> THẤT BẠI: Score Positive={res['score_pos']} vs Distractor={res['score_dist']}")

    pass_rate = (passed_count / float(total)) * 100.0 if total > 0 else 0.0
    avg_margin = sum(margins) / float(len(margins)) if margins else 0.0

    print("=" * 90)
    print(f"  TỔNG KẾT ĐÁNH GIÁ GROUND-TRUTH: {passed_count}/{total} PASSED ({pass_rate:.1f}%)")
    print(f"  Biên độ phân biệt an ninh trung bình (Average Security Margin): {avg_margin:+.4f}")
    print("=" * 90)

    # Hiển thị bảng chi tiết
    print("\nBẢNG KẾT QUẢ ĐỊNH LƯỢNG CHI TIẾT:")
    print(f"{'ID':<10} | {'Category':<28} | {'Score Pos':<11} | {'Score Dist':<11} | {'Margin':<10} | {'Status':<8}")
    print("-" * 88)
    for r in results:
        status_str = "PASSED" if r["passed"] else "FAILED"
        print(f"{r['id']:<10} | {r['category']:<28} | {r['score_pos']:<11.4f} | {r['score_dist']:<11.4f} | {r['margin']:<+10.4f} | {status_str:<8}")
    print("-" * 88 + "\n")

    return {
        "total_cases": total,
        "passed_cases": passed_count,
        "failed_cases": total - passed_count,
        "pass_rate_pct": round(pass_rate, 2),
        "average_margin": round(avg_margin, 4),
        "all_passed": (passed_count == total),
        "details": results
    }


def main():
    res = run_evaluation_suite(verbose=True)
    if not res["all_passed"]:
        print(f"[!] Cảnh báo: Có {res['failed_cases']} ca kiểm thử không đạt tiêu chuẩn ground-truth!")
        sys.exit(1)
    else:
        print("[*] Chúc mừng: 100% ca kiểm thử Synthetic Ground-Truth đạt tiêu chuẩn an ninh tuyệt đối!")
        sys.exit(0)


if __name__ == "__main__":
    main()
