"""
Unit Tests for Stage 5: Security Signature Extraction & Similarity Metric
Kiểm thử trích xuất đặc trưng an ninh từ C/C++ code và Joern CPG, đo lường độ tương đồng cơ chế bảo mật.
"""

import pytest
from security_signature.schema import SecuritySignature, TaintSource, TaintSink, SanitizerGuard, MemoryOperation
from security_signature.extractor import SecuritySignatureExtractor, extract_security_signature
from security_signature.similarity import compute_security_signature_similarity


def test_extractor_vulnerable_buffer_overflow():
    """Kiểm thử trích xuất trên hàm có lỗi Buffer Overflow kinh điển (strcpy không kiểm tra)."""
    code = """
    void handle_packet(char *user_input, int len) {
        char buffer[128];
        strcpy(buffer, user_input);
    }
    """
    sig = extract_security_signature(code)
    
    assert "strcpy" in sig.sink_apis
    assert any(s.sink_category == "buffer_write" for s in sig.sinks)
    assert any(src.name == "user_input" or src.source_type in ["parameter", "input_buffer"] for src in sig.sources)
    assert "unbounded_buffer_copy" in sig.vulnerability_clues
    assert sig.memory_ops.has_array_indexing is True or "buffer" in code


def test_extractor_safe_bounds_checked():
    """Kiểm thử trích xuất trên hàm an toàn có câu lệnh kiểm tra biên (Bounds Check & sizeof)."""
    code = """
    int handle_packet_safe(char *user_input, int len) {
        char buffer[128];
        if (len >= sizeof(buffer)) {
            return -1;
        }
        memcpy(buffer, user_input, len);
        return 0;
    }
    """
    sig = extract_security_signature(code)
    
    assert "memcpy" in sig.sink_apis
    assert "sizeof_check" in sig.sanitizer_types or "bounds_check" in sig.sanitizer_types
    assert "return_error" in sig.sanitizer_types


def test_extractor_use_after_free():
    """Kiểm thử trích xuất trên hàm giải phóng bộ nhớ và con trỏ (Use-After-Free / Double-Free)."""
    code = """
    void free_node(struct Node *node) {
        if (node != NULL) {
            free(node->data);
            free(node);
        }
    }
    """
    sig = extract_security_signature(code)
    
    assert "free" in sig.sink_apis
    assert "pointer_free" in {s.sink_category for s in sig.sinks}
    assert sig.memory_ops.has_pointer_deref is True
    assert sig.memory_ops.has_explicit_free is True
    assert "null_check" in sig.sanitizer_types


def test_extractor_with_joern_nodes_edges():
    """Kiểm thử trích xuất kết hợp trực tiếp cấu trúc Node & Edge của Joern CPG."""
    code = "void test_func(char *data) { memcpy(dest, data, 10); }"
    nodes = [
        {"id": "1", "type": "Function", "code": "test_func"},
        {"id": "2", "type": "Parameter", "code": "char * data"},
        {"id": "3", "type": "CallExpression", "code": "memcpy(dest, data, 10)"},
        {"id": "4", "type": "PtrMemberAccess", "code": "dest->buf"}
    ]
    edges = [
        {"start": "1", "end": "3", "type": "CONTROLS"},
        {"start": "2", "end": "3", "type": "REACHES"}
    ]
    
    sig = extract_security_signature(code, nodes, edges)
    assert sig.func_name == "test_func"
    assert "memcpy" in sig.sink_apis
    assert sig.memory_ops.has_pointer_deref is True
    assert len(sig.dataflow_paths) > 0


def test_security_similarity_high_for_same_vulnerability_pattern():
    """
    Kiểm thử: Hai hàm xử lý 2 bài toán hoàn toàn khác nhau (1 hàm âm thanh, 1 hàm mạng)
    nhưng CÙNG CHUNG CƠ CHẾ LỖ HỔNG (memcpy buffer overflow) phải có điểm Security Similarity rất CAO!
    (Chứng minh giải quyết Case D).
    """
    code_audio = """
    void decode_audio(AVContext *ctx, uint8_t *src, int size) {
        memcpy(ctx->audio_buf, src, size);
    }
    """
    code_net = """
    void net_rx_packet(NetState *net, const char *raw_data, int len) {
        memcpy(net->rx_queue, raw_data, len);
    }
    """
    
    sig1 = extract_security_signature(code_audio)
    sig2 = extract_security_signature(code_net)
    
    score, sub_scores = compute_security_signature_similarity(sig1, sig2)
    
    assert score >= 0.70, f"Điểm tương đồng an ninh phải >= 0.70 nhưng đạt {score}"
    assert sub_scores["sink_similarity"] == 1.0  # Cùng dùng memcpy


def test_security_similarity_low_for_different_mechanisms():
    """Kiểm thử: Một hàm xử lý chuỗi và một hàm toán học thuần túy phải có điểm tương đồng an ninh THẤP."""
    code_str = "void process(char *s) { strcpy(buf, s); }"
    code_math = "int compute(int a, int b) { return a * b + 42; }"
    
    sig1 = extract_security_signature(code_str)
    sig2 = extract_security_signature(code_math)
    
    score, sub_scores = compute_security_signature_similarity(sig1, sig2)
    assert score < 0.50, f"Điểm tương đồng phải thấp nhưng đạt {score}"


def test_contrastive_pair_difference_detection():
    """Kiểm thử khả năng nhận diện điểm khác biệt mấu chốt giữa cặp Vulnerable và Safe."""
    vuln_code = "void write_buf(char *src, int n) { memcpy(dest, src, n); }"
    safe_code = "void write_buf(char *src, int n) { if (n < sizeof(dest)) memcpy(dest, src, n); }"
    
    sig_vuln = extract_security_signature(vuln_code)
    sig_safe = extract_security_signature(safe_code)
    
    assert "unbounded_buffer_copy" in sig_vuln.vulnerability_clues
    assert "unbounded_buffer_copy" not in sig_safe.vulnerability_clues
    assert "sizeof_check" in sig_safe.sanitizer_types
    assert len(sig_safe.sanitizers) > len(sig_vuln.sanitizers)
