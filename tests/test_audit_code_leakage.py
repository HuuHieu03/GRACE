"""
Unit Tests cho Script Kiểm Toán Rò Rỉ Dữ Liệu (Code Leakage Audit)
Kiểm tra toàn diện:
- Chuẩn hóa mã nguồn C/C++ (loại bỏ comment block /* */ và line //)
- Giữ nguyên chuỗi ký tự trong dấu nháy kép / nháy đơn
- Thu gọn khoảng trắng ngữ nghĩa (Semantic Normalization)
- Trích xuất token tối giản (Token Stream Normalization)
- Đối soát trùng lặp chính xác (Exact Duplicates)
- Đối soát trùng lặp chuẩn hóa (Normalized Duplicates)
- Phát hiện mâu thuẫn gán nhãn (Contradictory Labels: Train=0 vs Test=1 hoặc Train=1 vs Test=0)
- Xử lý các trường hợp biên: tập rỗng, không trùng lặp, trùng lặp 100%
"""

import sys
import pytest
from pathlib import Path

# Đảm bảo import được từ scripts và src
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from audit_code_leakage import (
    strip_c_comments,
    normalize_code_semantic,
    normalize_code_tokens,
    hash_string,
    audit_split_pair,
    parse_item,
    stream_json_records
)


def test_strip_c_comments_basic():
    """Kiểm tra xóa comment C đơn giản."""
    code = """
    // Line comment 1
    int add(int a, int b) {
        /* Block comment
           multiline */
        return a + b; // return sum
    }
    """
    cleaned = strip_c_comments(code)
    assert "// Line comment 1" not in cleaned
    assert "Block comment" not in cleaned
    assert "multiline" not in cleaned
    assert "return sum" not in cleaned
    assert "int add(int a, int b)" in cleaned
    assert "return a + b;" in cleaned


def test_strip_c_comments_inside_string_literals():
    """Đảm bảo chuỗi chứa ký tự comment không bị xóa nhầm."""
    code = r'const char *url = "http://example.com/*not_a_comment*/";'
    cleaned = strip_c_comments(code)
    assert r'"http://example.com/*not_a_comment*/"' in cleaned


def test_normalize_code_semantic():
    """Kiểm tra chuẩn hóa ngữ nghĩa: khoảng trắng, thụt đầu dòng, xuống dòng khác nhau."""
    code_v1 = "int foo(int x) {\n    return x + 1;\n}"
    code_v2 = "int   foo  (  int x  )  {\n\n\n\treturn x + 1;\n}"
    code_v3 = "int foo(int x) { /* add one */ return x + 1; // done \n}"

    norm1 = normalize_code_semantic(code_v1)
    norm2 = normalize_code_semantic(code_v2)
    norm3 = normalize_code_semantic(code_v3)

    assert norm1 == norm2
    assert norm1 == norm3
    assert norm1 == "int foo(int x) { return x + 1; }"

    # Kiểm tra biến thể hàm rỗng với khoảng trắng và xuống dòng khác nhau
    empty_v1 = "void bar() {}"
    empty_v2 = "void bar  (   )   {\n\n}"
    assert normalize_code_semantic(empty_v1) == normalize_code_semantic(empty_v2) == "void bar() {}"


def test_normalize_code_tokens():
    """Kiểm tra chuẩn hóa token stream loại bỏ mọi khoảng trắng."""
    code1 = "void test(void) { int a = 1; }"
    code2 = "void    test ( void ) {\n\nint a=1;\n}"
    # Sau khi xóa comment và khoảng trắng
    tok1 = normalize_code_tokens(code1)
    assert " " not in tok1
    assert "\n" not in tok1
    assert tok1 == "voidtest(void){inta=1;}"


def test_audit_split_pair_zero_overlap():
    """Trường hợp lý tưởng: 0% rò rỉ mã nguồn giữa train và test."""
    train_records = [
        {"id": "tr_1", "code": "void func_a() { int x = 0; }", "target": 0, "project": "projA"},
        {"id": "tr_2", "code": "void func_b() { char b[10]; }", "target": 1, "project": "projA"},
    ]
    test_records = [
        {"id": "te_1", "code": "void func_c() { float f = 1.0; }", "target": 0, "project": "projA"},
        {"id": "te_2", "code": "void func_d() { double d = 2.0; }", "target": 1, "project": "projA"},
    ]

    report = audit_split_pair("CleanDataset", train_records, test_records)
    assert report["id_overlap"]["count"] == 0
    assert report["exact_duplicates"]["duplicate_count"] == 0
    assert report["exact_duplicates"]["leakage_rate_pct"] == 0.0
    assert report["normalized_duplicates"]["duplicate_count"] == 0
    assert report["normalized_duplicates"]["leakage_rate_pct"] == 0.0


def test_audit_split_pair_exact_and_contradictory_leakage():
    """
    Kiểm tra rò rỉ mã nguồn và phân tích tính nhất quán nhãn:
    - te_1: Exact duplicate CÙNG nhãn Safe (0 == 0) -> Consistent
    - te_2: Normalized duplicate CÙNG nhãn Vuln (1 == 1) -> Consistent
    - te_3: Exact duplicate MÂU THUẪN nhãn (Train Safe=0 vs Test Vuln=1) -> Contradictory / Label Noise
    - te_4: Mẫu sạch, không trùng lặp
    """
    train_records = [
        {"id": "tr_1", "code": "void safe_func() { int a = 1; }", "target": 0, "project": "projX"},
        {"id": "tr_2", "code": "void vuln_func() { char buf[10]; strcpy(buf, input); }", "target": 1, "project": "projX"},
        {"id": "tr_3", "code": "void ambiguous_func() { return 0; }", "target": 0, "project": "projX"},
    ]
    test_records = [
        # te_1: trùng chính xác tr_1, cùng nhãn 0
        {"id": "te_1", "code": "void safe_func() { int a = 1; }", "target": 0, "project": "projX"},
        # te_2: trùng tr_2 sau khi xóa comment và khoảng trắng, cùng nhãn 1
        {"id": "te_2", "code": "void vuln_func() {\n  /* unsafe copy */\n  char buf[10];\n  strcpy(buf, input);\n}", "target": 1, "project": "projX"},
        # te_3: trùng tr_3 nhưng nhãn bị mâu thuẫn (Test gán 1 trong khi Train gán 0)
        {"id": "te_3", "code": "void ambiguous_func() { return 0; }", "target": 1, "project": "projX"},
        # te_4: không trùng
        {"id": "te_4", "code": "void unique_test() { int z = 99; }", "target": 0, "project": "projX"},
    ]

    report = audit_split_pair("LeakageTestDataset", train_records, test_records)
    
    # Exact Duplicates: te_1 và te_3 (2 mẫu)
    assert report["exact_duplicates"]["duplicate_count"] == 2
    assert report["exact_duplicates"]["leakage_rate_pct"] == 50.0  # 2 / 4 = 50%
    assert report["exact_duplicates"]["consistent_label_count"] == 1  # te_1 (0 == 0)
    assert report["exact_duplicates"]["contradictory_label_count"] == 1  # te_3 (Train 0 vs Test 1)
    assert report["exact_duplicates"]["label_conflict_details"]["train_safe_test_vuln"] == 1

    # Normalized Duplicates: te_1, te_2, te_3 (3 mẫu)
    assert report["normalized_duplicates"]["duplicate_count"] == 3
    assert report["normalized_duplicates"]["leakage_rate_pct"] == 75.0  # 3 / 4 = 75%
    assert report["normalized_duplicates"]["consistent_label_count"] == 2  # te_1, te_2
    assert report["normalized_duplicates"]["contradictory_label_count"] == 1  # te_3


def test_audit_split_pair_empty_inputs():
    """Kiểm tra xử lý danh sách rỗng an toàn."""
    report = audit_split_pair("EmptyDataset", [], [])
    assert report["sample_counts"]["train_samples"] == 0
    assert report["sample_counts"]["test_samples"] == 0
    assert report["exact_duplicates"]["duplicate_count"] == 0
    assert report["exact_duplicates"]["leakage_rate_pct"] == 0.0


def test_parse_item_type_coercions():
    """Kiểm tra ép kiểu mục dữ liệu từ nhiều định dạng nhãn và ID khác nhau."""
    # Boolean true/false
    item1 = parse_item({"id": 101, "func": "void foo() {}", "target": True, "project": "projA"}, 0)
    assert item1["target"] == 1
    assert item1["id"] == "101"

    item2 = parse_item({"id": 102, "func": "void bar() {}", "target": False, "project": "projA"}, 1)
    assert item2["target"] == 0

    # String representations
    item3 = parse_item({"idx": "sample_3", "code": "void baz() {}", "label": "True"}, 2)
    assert item3["target"] == 1
    assert item3["id"] == "sample_3"

    item4 = parse_item({"hash": "h_99", "functionSource": "int x = 1;", "target": "0"}, 3)
    assert item4["target"] == 0
    assert item4["id"] == "h_99"

    # Missing target defaults to 0
    item5 = parse_item({"function": "int y = 2;"}, 4)
    assert item5["target"] == 0
    assert item5["id"] == "sample_4"


def test_stream_json_records_arbitrary_indentation(tmp_path):
    """Kiểm tra stream_json_records hoạt động chính xác với file thụt đầu dòng 4 spaces."""
    import json
    sample_data = [
        {"id": 1, "func": "void func_1() {}", "target": 0, "project": "p1"},
        {"id": 2, "func": "void func_2() {}", "target": 1, "project": "p2"},
    ]
    json_file = tmp_path / "indented_4spaces.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=4)

    records = stream_json_records(json_file)
    assert len(records) == 2
    assert records[0]["id"] == "1"
    assert records[0]["target"] == 0
    assert records[1]["id"] == "2"
    assert records[1]["target"] == 1


def test_audit_split_pair_ambiguous_train_labels():
    """Kiểm tra trường hợp nhãn mơ hồ: Train chứa cùng 1 code với cả nhãn 0 và nhãn 1."""
    train_records = [
        {"id": "tr_1", "code": "void dup() { return; }", "target": 0, "project": "proj"},
        {"id": "tr_2", "code": "void dup() { return; }", "target": 1, "project": "proj"},
    ]
    test_records = [
        {"id": "te_1", "code": "void dup() { return; }", "target": 1, "project": "proj"},
    ]

    report = audit_split_pair("AmbiguousDataset", train_records, test_records)
    assert report["exact_duplicates"]["duplicate_count"] == 1
    sample = report["exact_duplicates"]["samples"][0]
    assert sample["is_ambiguous"] is True

