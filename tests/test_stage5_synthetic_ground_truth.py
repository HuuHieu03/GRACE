"""
Unit Tests for Synthetic Ground-Truth Suite (Pillar 3: Auxiliary Ground-Truth Verification)
Kiểm thử bộ vi mô tổng hợp 100% ground-truth nhằm chứng minh năng lực phân biệt khách quan của Reranker.
"""

import sys
from pathlib import Path
import pytest

# Đảm bảo đường dẫn import
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
for p in [str(SRC_DIR), str(SCRIPTS_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from run_synthetic_ground_truth_eval import (
    build_synthetic_benchmark_suite,
    evaluate_test_case,
    run_evaluation_suite
)
from security_signature.extractor import extract_security_signature
from security_signature.similarity import compute_security_signature_similarity


def test_synthetic_suite_all_pass():
    """Kiểm thử: Toàn bộ 10 ca kiểm thử trong Synthetic Ground-Truth Suite phải đạt trạng thái PASSED."""
    res = run_evaluation_suite(verbose=False)
    assert res["all_passed"] is True, f"Có {res['failed_cases']} ca kiểm thử bị fail trong synthetic suite!"
    assert res["pass_rate_pct"] == 100.0
    assert res["average_margin"] > 0.05


def test_guard_variable_relevance():
    """
    SYNTH-01: Kiểm tra Guard đúng biến (len <= max) vs Guard biến rác (retry > 0)
    Điểm SecSim của ca đúng biến phải cao hơn rõ rệt so với ca kiểm tra biến không liên quan.
    """
    target = "void copy(char *dst, char *src, int len) { if (len <= dst_size) { memcpy(dst, src, len); } }"
    pos_cand = "void transfer(char *out, char *in, int count) { if (count <= max_cap) { memcpy(out, in, count); } }"
    dist_cand = "void transfer(char *out, char *in, int count) { if (retry > 0) { memcpy(out, in, count); } }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.10


def test_guard_ordering_before_vs_after_sink():
    """
    SYNTH-02: Kiểm tra Guard đặt trước Sink vs Guard đặt sau Sink
    Guard đặt sau sink không thể ngăn chặn lỗ hổng đã xảy ra, SecSim phải thấp hơn guard đặt trước sink.
    """
    target = "void send_buf(char *dest, char *msg, int size) { if (size <= MAX_BUF) { memcpy(dest, msg, size); } }"
    pos_cand = "void log_msg(char *dst, char *src, int len) { if (len <= LIMIT) { memcpy(dst, src, len); } }"
    dist_cand = "void log_msg(char *dst, char *src, int len) { memcpy(dst, src, len); if (len <= LIMIT) { return; } }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.10


def test_null_check_binding_correct_vs_wrong_pointer():
    """
    SYNTH-04: Kiểm tra Null Check đúng con trỏ (node != NULL) vs sai con trỏ (other != NULL)
    Kiểm tra một con trỏ không liên quan phải bị coi là null check vô hiệu.
    """
    target = "void process_node(struct Node *node) { if (node != NULL) { free(node->data); free(node); } }"
    pos_cand = "void release_item(struct Item *item) { if (item != NULL) { free(item->payload); free(item); } }"
    dist_cand = "void release_item(struct Item *item, struct Item *other) { if (other != NULL) { free(item->payload); free(item); } }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.10


def test_sink_semantic_matching():
    """SYNTH-03: Kiểm tra Sink cùng bản chất (buffer_write) vs Sink khác loại (exec)."""
    target = "void write_data(char *src, int n) { memcpy(buffer, src, n); }"
    pos_cand = "void packet_in(char *raw, int sz) { memmove(storage, raw, sz); }"
    dist_cand = "void audit_log(char *name) { system(name); }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.15


def test_memory_lifecycle_uaf():
    """SYNTH-05: Kiểm tra cơ chế giải phóng bộ nhớ động vs tính toán số học."""
    target = "void cleanup(Object *obj) { free(obj->buf); free(obj); }"
    pos_cand = "void teardown(Session *s) { free(s->token); free(s); }"
    dist_cand = "int calc_hash(int a, int b) { return (a * 31 + b) % 1000; }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.20


def test_integer_arithmetic_bounds():
    """SYNTH-06: Kiểm tra tràn số nguyên trước phép nhân vs nhân không kiểm soát."""
    target = "int alloc_mem(int count, int elem_sz) { if (count > 0 && count <= MAX_INT / elem_sz) { return count * elem_sz; } return -1; }"
    pos_cand = "int calc_size(int n, int sz) { if (n <= INT_MAX / sz) { return n * sz; } return 0; }"
    dist_cand = "int calc_size(int n, int sz) { return n * sz; }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.05


def test_array_access_bounds_guard():
    """SYNTH-07: Kiểm tra biên chỉ số mảng vs truy cập mảng tự do."""
    target = "int get_elem(int *arr, int idx) { if (idx >= 0 && idx < MAX_LEN) { return arr[idx]; } return -1; }"
    pos_cand = "int fetch_data(int *buf, int pos) { if (pos < BUF_SIZE) { return buf[pos]; } return 0; }"
    dist_cand = "int fetch_data(int *buf, int pos) { return buf[pos]; }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.05


def test_format_string_safety():
    """SYNTH-08: Format string cùng loại vs I/O không liên quan."""
    target = "void log_user(char *fmt, char *arg) { printf(fmt); }"
    pos_cand = "void debug_msg(char *user_input) { sprintf(log_buf, user_input); }"
    dist_cand = "void close_connection(FILE *fp) { fclose(fp); }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.15


def test_vulnerable_target_retrieval_preference():
    """
    SYNTH-09: Khi Target có lỗi (memcpy không kiểm tra), bộ đo an ninh phải ưu tiên
    ví dụ demo CŨNG CÓ LỖ HỔNG thay vì ví dụ an toàn đã vá, đảm bảo tính tương đồng cơ chế lỗi.
    """
    target = "void process_req(char *src, int len) { memcpy(dest, src, len); }"
    pos_cand = "void parse_chunk(char *payload, int n) { memcpy(temp_buf, payload, n); }"
    dist_cand = "void parse_chunk(char *payload, int n) { if (n <= sizeof(temp_buf)) { memcpy(temp_buf, payload, n); } }"

    sig_target = extract_security_signature(target)
    sig_pos = extract_security_signature(pos_cand)
    sig_dist = extract_security_signature(dist_cand)

    score_pos, _ = compute_security_signature_similarity(sig_target, sig_pos)
    score_dist, _ = compute_security_signature_similarity(sig_target, sig_dist)

    assert score_pos > score_dist
    assert (score_pos - score_dist) >= 0.10 - 1e-6


def test_end_to_end_reranker_selection():
    """SYNTH-10: SecurityAwareRetriever tái xếp hạng ưu tiên ví dụ có cùng bản chất an ninh."""
    suite = build_synthetic_benchmark_suite()
    tc10 = [tc for tc in suite if tc.id == "SYNTH-10"][0]
    res = evaluate_test_case(tc10)

    assert res["passed"] is True
    assert res["top_selected"] == "positive_cand"
    assert res["margin"] >= 0.05

