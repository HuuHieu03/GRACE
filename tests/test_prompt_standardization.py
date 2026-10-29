"""
Unit tests for GRACE prompt standardization and token budgeting.
Covers Figure 6 canonical ordering, token budget truncation, no silent empty demo,
prevention of target label leakage, and backward compatibility.
"""

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from prompt_engine import (
    build_grace_prompt_canonical,
    build_grace_prompt_canonical_with_metadata,
    build_grace_prompt,
    build_grace_prompt_legacy,
    build_prompt,
)
from prompt_contract import render_control, render_control_v2, CONDITIONS_V2
from token_budget import TokenBudgetManager, OfflineFallbackTokenizer


def sample_fixture(pair=False):
    demos = [{"function_uid": "d1", "func": 'void demo_a(){ puts("vulnerable"); }', "target": 1}]
    if pair:
        demos.append({"function_uid": "d2", "func": 'void demo_b(){ return; }', "target": 0})
    return {
        "query_code": "int target_func(int x) {\n    char buf[16];\n    strcpy(buf, x);\n    return 0;\n}",
        "nodes": [
            {"id": 1, "type": "METHOD", "code": "target_func"},
            {"id": 2, "type": "CALL", "code": "strcpy(buf, x)"},
            {"id": 3, "type": "RETURN", "code": "return 0"},
        ],
        "edges": [
            {"start": 1, "end": 2, "type": "CFG"},
            {"start": 2, "end": 3, "type": "CFG"},
        ],
        "demonstrations": demos,
        "security_difference": "demo_a has unchecked buffer copy; demo_b returns directly." if pair else "",
    }


def test_figure6_block_ordering():
    """
    Xác minh thứ tự chính xác theo Figure 6 của bài báo gốc:
    1. Target Code đứng trước Task Instruction
    2. Task Instruction đứng trước Node & Edge info
    3. Demonstration xuất hiện ở cuối cùng trước Answer indicator
    4. Answer indicator nằm ở dòng cuối cùng
    """
    spec = sample_fixture()
    result = render_control_v2(spec)
    prompt = result["prompt"]

    target_code_snippet = "int target_func"
    task_instruction_snippet = "In the above code snippet, check for potential security vulnerabilities"
    node_info_snippet = "The node information of the code snippet is as follows:"
    edge_info_snippet = "The edge information of the code snippet is as follows:"
    demo_snippet = "The following is an example, and it is Vulnerable."
    answer_snippet = "Answer (0 or 1):"

    assert target_code_snippet in prompt
    assert task_instruction_snippet in prompt
    assert node_info_snippet in prompt
    assert edge_info_snippet in prompt
    assert demo_snippet in prompt
    assert answer_snippet in prompt

    idx_target = prompt.index(target_code_snippet)
    idx_inst = prompt.index(task_instruction_snippet)
    idx_node = prompt.index(node_info_snippet)
    idx_edge = prompt.index(edge_info_snippet)
    idx_demo = prompt.index(demo_snippet)
    idx_ans = prompt.index(answer_snippet)

    # Khẳng định thứ tự Figure 6
    assert idx_target < idx_inst, "Target code must come before task instruction"
    assert idx_inst < idx_node, "Task instruction must come before node info"
    assert idx_node < idx_edge, "Node info must come before edge info"
    assert idx_edge < idx_demo, "CPG graph must come before demonstration"
    assert idx_demo < idx_ans, "Demonstration must come before answer indicator"

    # Cũng xác minh qua hàm build_grace_prompt_canonical
    engine_sample = {
        "func": spec["query_code"],
        "nodes": spec["nodes"],
        "edges": spec["edges"],
        "example": spec["demonstrations"][0],
    }
    canonical_prompt = build_grace_prompt_canonical(engine_sample, include_demonstration=True)
    c_idx_target = canonical_prompt.index(target_code_snippet)
    c_idx_inst = canonical_prompt.index(task_instruction_snippet)
    c_idx_node = canonical_prompt.index(node_info_snippet)
    c_idx_edge = canonical_prompt.index(edge_info_snippet)
    c_idx_demo = canonical_prompt.index(demo_snippet)
    c_idx_ans = canonical_prompt.index(answer_snippet)

    assert c_idx_target < c_idx_inst < c_idx_node < c_idx_edge < c_idx_demo < c_idx_ans


def test_token_budget_limits():
    """
    Xác minh các đoạn code dài không bao giờ vượt quá ngân sách token quy định:
    target_code <= 3000, graph <= 1500, demonstration <= 1500, total <= 8192.
    """
    budget_mgr = TokenBudgetManager(force_offline=True)

    long_target = "int func() {\n" + ("    int a = 1;\n" * 2000) + "    return 0;\n}"
    long_demo = "void demo() {\n" + ("    char c = 'x';\n" * 1500) + "}"

    truncated_code, code_stats = budget_mgr.truncate_target_code(long_target)
    assert code_stats["was_truncated"] is True
    assert budget_mgr.count_tokens(truncated_code) <= budget_mgr.target_code_max_tokens + 50

    truncated_demo, demo_stats = budget_mgr.truncate_demonstration(long_demo)
    assert demo_stats["was_truncated"] is True
    assert budget_mgr.count_tokens(truncated_demo) <= budget_mgr.demonstration_max_tokens + 50

    audit = budget_mgr.audit_prompt_tokens(
        code_text=truncated_code,
        graph_text="Node 1... Edge...",
        demo_text=truncated_demo,
        instruction_text="Instruction...",
        format_text="Answer (0 or 1):",
    )
    assert audit["is_valid"] is True
    assert audit["tokens_total"] + audit["output_reserve"] <= audit["context_limit"]


def test_no_silent_empty_demo():
    """
    Đảm bảo nếu demo bị cắt quá mức (> 75%) hoặc rỗng thì:
    - TokenBudgetManager đánh dấu cờ truncated_demo = True
    - render_control_v2 từ chối demo rỗng hoàn toàn với ValueError
    """
    budget_mgr = TokenBudgetManager(force_offline=True)

    # 1. Demo rỗng
    _, stats_empty = budget_mgr.truncate_demonstration("   \n  ")
    assert stats_empty["truncated_demo"] is True
    assert stats_empty["empty_demo"] is True

    # 2. Demo bị cắt rất nặng (> 75% độ dài bị loại bỏ)
    huge_demo = "void a() {\n" + ("puts('very long statement line');\n" * 2000) + "}"
    _, stats_heavy = budget_mgr.truncate_demonstration(huge_demo, max_tokens=20)
    assert stats_heavy["was_truncated"] is True
    assert stats_heavy["truncated_ratio"] > 0.75
    assert stats_heavy["truncated_demo"] is True

    # 3. render_control_v2 chặn demo rỗng
    spec = sample_fixture()
    spec["demonstrations"][0]["func"] = "   "
    with pytest.raises(ValueError, match="Demo code/label contract failed"):
        render_control_v2(spec)


def test_no_target_label_leakage():
    """
    Đảm bảo nhãn của target (target, target_label, ground_truth) tuyệt đối không
    được phép lọt vào input của renderer.
    """
    for forbidden_key in ["target", "target_label", "ground_truth"]:
        spec = sample_fixture()
        spec[forbidden_key] = 1
        with pytest.raises(ValueError, match="Query labels cannot enter the renderer"):
            render_control_v2(spec)


def test_backward_compatibility():
    """
    Đảm bảo layout figure6_legacy vẫn tạo ra đúng cấu trúc prompt cũ
    và bảo toàn tương thích ngược 100%.
    """
    spec = sample_fixture()

    # 1. render_control mặc định dùng figure6_legacy khi không khai báo
    legacy_res = render_control(spec)
    assert legacy_res["prompt"].startswith("### TASK INSTRUCTION")
    assert "### REFERENCE DEMONSTRATIONS" in legacy_res["prompt"]
    assert "### TARGET FUNCTION" in legacy_res["prompt"]
    assert "### OUTPUT FORMAT REQUIREMENT" in legacy_res["prompt"]

    # 2. render_control với layout="figure6_v2" sinh prompt chuẩn
    v2_res = render_control(spec, layout="figure6_v2")
    assert "Answer (0 or 1):" in v2_res["prompt"]
    assert v2_res["evidence"]["layout_version"] == "figure6_v2"

    # 3. build_grace_prompt với canonical=False giữ nguyên legacy
    sample_engine = {
        "func": spec["query_code"],
        "example": spec["demonstrations"][0],
        "nodes": spec["nodes"],
        "edges": spec["edges"],
    }
    legacy_prompt = build_grace_prompt(sample_engine, canonical=False)
    assert legacy_prompt == build_grace_prompt_legacy(sample_engine)
    assert "### TASK INSTRUCTION" in legacy_prompt

    # 4. build_prompt dispatcher hỗ trợ figure6_v2
    disp_v2 = build_prompt(sample_engine, mode="figure6_v2")
    assert "Answer (0 or 1):" in disp_v2


def test_offline_fallback_tokenizer():
    """
    Kiểm tra tokenizer ngoại tuyến:
    Lossless tokenization, đếm token chính xác và cắt tỉa ổn định.
    """
    tok = OfflineFallbackTokenizer()
    text = "int calculate(int x, int y) {\n    return x + y;\n}"
    tokens = tok.tokenize(text)
    assert "".join(tokens) == text, "Offline tokenizer must be lossless"
    assert tok.count_tokens(text) == len(tokens)
    assert tok.truncate(text, 5) == "".join(tokens[:5])


def test_probe_conditions_v2():
    """
    Kiểm tra đầy đủ các probe chẩn đoán trong CONDITIONS_V2:
    label_flip, order_swap, graph_omitted, graph_shuffled, demo_nolabel, demo_labelonly, no_difference.
    """
    spec = sample_fixture(pair=True)

    # original vs label_flip
    orig = render_control_v2(spec, condition="original")
    flipped = render_control_v2(spec, condition="label_flip")
    assert [d["displayed_label"] for d in orig["evidence"]["displayed_demonstrations"]] == [1, 0]
    assert [d["displayed_label"] for d in flipped["evidence"]["displayed_demonstrations"]] == [0, 1]

    # order_swap
    swapped = render_control_v2(spec, condition="order_swap")
    assert swapped["prompt"].index("demo_b") < swapped["prompt"].index("demo_a")

    # graph_omitted
    no_graph = render_control_v2(spec, condition="graph_omitted")
    assert "The node information of the code snippet is as follows:" not in no_graph["prompt"]
    assert no_graph["evidence"]["graph"]["included"] is False

    # graph_shuffled
    shuffled = render_control_v2(spec, condition="graph_shuffled")
    assert "The node information of the code snippet is as follows:" in shuffled["prompt"]

    # demo_nolabel
    nolabel = render_control_v2(spec, condition="demo_nolabel")
    assert "is Vulnerable" not in nolabel["prompt"]
    assert "The following is an example.\n" in nolabel["prompt"]

    # demo_labelonly
    labelonly = render_control_v2(spec, condition="demo_labelonly")
    assert "void demo_a" not in labelonly["prompt"]
    assert "The following is an example, and it is Vulnerable." in labelonly["prompt"]

    # no_difference
    nodiff = render_control_v2(spec, condition="no_difference")
    assert "--- SECURITY DIFFERENCE CLUES ---" not in nodiff["prompt"]


def test_metadata_audit_reporting():
    """
    Kiểm tra build_grace_prompt_canonical_with_metadata sinh đầy đủ thông tin kiểm toán:
    tokens_code, tokens_graph, tokens_demo, tokens_total.
    """
    spec = sample_fixture()
    sample_engine = {
        "func": spec["query_code"],
        "example": spec["demonstrations"][0],
        "nodes": spec["nodes"],
        "edges": spec["edges"],
    }
    mgr = TokenBudgetManager(force_offline=True)
    prompt, meta = build_grace_prompt_canonical_with_metadata(
        sample=sample_engine,
        include_demonstration=True,
        budget_manager=mgr,
    )
    assert meta["layout_version"] == "figure6_v2"
    assert "tokens_code" in meta and meta["tokens_code"] > 0
    assert "tokens_graph" in meta and meta["tokens_graph"] > 0
    assert "tokens_demo" in meta and meta["tokens_demo"] > 0
    assert "tokens_total" in meta and meta["tokens_total"] > 0
    assert meta["truncated_demo"] is False
    assert meta["empty_demo"] is False
    assert meta["audit"]["is_valid"] is True


def test_offline_fallback_tokenizer_unicode_lossless():
    """
    Kiểm tra tính toàn vẹn (Lossless) của tokenizer ngoại tuyến khi xử lý chuỗi Unicode,
    tiếng Việt có dấu, ký tự C/C++ đa ngôn ngữ và comment.
    Đảm bảo tuyệt đối không làm rơi rụng ký tự nào!
    """
    tok = OfflineFallbackTokenizer()
    text = (
        '// Kiểm tra hàm phát hiện lỗ hổng an ninh mạng\n'
        'int kiem_tra(char* du_lieu, int do_dai) {\n'
        '    /* Cảnh báo: bộ đệm có thể bị tràn nếu dữ liệu vượt ngưỡng */\n'
        '    char buffer[128] = "Đã nhận";\n'
        '    return 0;\n'
        '}'
    )
    tokens = tok.tokenize(text)
    assert "".join(tokens) == text, "Offline tokenizer must be 100% lossless with Unicode text"
    assert "lỗ" in "".join(tokens)
    assert "Đã nhận" in "".join(tokens)
    assert tok.count_tokens(text) == len(tokens)


def test_demonstration_truncation_ratio_accuracy():
    """
    Kiểm tra tỷ lệ cắt tỉa demonstration không bị méo mó bởi suffix comment.
    Khi 90% code demo bị loại bỏ, cờ truncated_demo bắt buộc phải bật True.
    """
    mgr = TokenBudgetManager(force_offline=True)
    demo_code = "int a = 1; int b = 2; int c = 3; int d = 4;"
    orig_tokens = mgr.count_tokens(demo_code)
    # Cắt với ngân sách rất nhỏ (3 tokens)
    truncated, stats = mgr.truncate_demonstration(demo_code, max_tokens=3)
    assert stats["was_truncated"] is True
    # Tỷ lệ cắt thực tế trên code phải > 75%
    assert stats["truncated_ratio"] > 0.75
    assert stats["truncated_demo"] is True
    # Invariant: code giữ lại + code bị loại bỏ phải bằng đúng demo_code
    cut_idx = stats["cut_char_index"]
    assert demo_code[:cut_idx] == stats["truncated_core"]
    assert demo_code[:cut_idx] + demo_code[cut_idx:] == demo_code


def test_omitted_code_exact_accounting():
    """
    Đảm bảo target_omitted_code và demo_omitted_code không bị nhảy cóc hay mất ký tự
    do độ dài của suffix thông báo cắt tỉa.
    Bảo toàn định luật toàn vẹn dữ liệu: retained_code + omitted_code == full_code.
    """
    long_target = "int target_func() {\n" + ("    int x = 12345;\n" * 600) + "    return 0;\n}"
    long_demo = "void demo_func() {\n" + ("    char c = 'a';\n" * 600) + "}"
    spec = sample_fixture()
    spec["query_code"] = long_target
    spec["demonstrations"][0]["func"] = long_demo

    res = render_control_v2(spec)
    ev = res["evidence"]

    # Target audit invariant
    target_omitted = ev["target_omitted_code"]
    assert len(target_omitted) > 0
    assert long_target.endswith(target_omitted)
    retained_target = long_target[:len(long_target) - len(target_omitted)]
    assert retained_target + target_omitted == long_target

    # Demo audit invariant
    demo_omitted = ev["demo_omitted_code"][0]["omitted_code"]
    assert len(demo_omitted) > 0
    assert long_demo.endswith(demo_omitted)
    retained_demo = long_demo[:len(long_demo) - len(demo_omitted)]
    assert retained_demo + demo_omitted == long_demo


def test_token_budget_manager_fast_offline_init():
    """
    Đảm bảo khởi tạo TokenBudgetManager() trên máy trạm offline
    không bị treo hay timeout mạng kéo dài (tránh blocking network requests).
    """
    import os
    import time
    from token_budget import _is_network_available, _is_model_locally_cached

    # Kiểm tra helper với input rỗng/None an toàn
    assert _is_model_locally_cached("") is False

    # Kiểm tra helper với biến môi trường HF_HUB_OFFLINE
    old_offline = os.environ.get("HF_HUB_OFFLINE")
    try:
        os.environ["HF_HUB_OFFLINE"] = "1"
        assert _is_network_available(force_refresh=True) is False
    finally:
        if old_offline is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = old_offline

    # Khởi tạo chỉ định force_offline=True phải hoàn tất tức thì (< 0.2s)
    t_off = time.time()
    mgr_off = TokenBudgetManager(force_offline=True)
    elapsed_off = time.time() - t_off
    assert elapsed_off < 0.2, f"TokenBudgetManager force_offline took too long: {elapsed_off:.4f}s"
    assert mgr_off.tokenizer_type == "offline_fallback"

    # Khởi tạo mặc định (tự động phát hiện môi trường offline/local cache):
    # - Không bị treo timeout mạng kéo dài (thường 30-120s khi treo HuggingFace)
    # - Ngưỡng 20.0s thực tế trên Windows để phòng ngừa cold import transformers khi online
    t0 = time.time()
    mgr = TokenBudgetManager()
    elapsed = time.time() - t0
    assert elapsed < 20.0, f"TokenBudgetManager initial import/init took too long: {elapsed:.2f}s"
    assert mgr.tokenizer_type in ("offline_fallback", "transformers_local", "transformers")

    # Khởi tạo lần 2 (warm init, đã có cache hoặc sys.modules) phải hoàn tất tức thì (< 0.2s)
    t1 = time.time()
    mgr2 = TokenBudgetManager()
    elapsed2 = time.time() - t1
    assert elapsed2 < 0.2, f"Repeated TokenBudgetManager init took too long: {elapsed2:.4f}s"

    # Đếm token hoạt động bình thường
    assert mgr.count_tokens("int x = 1;") > 0


def test_demo_random_control_validation():
    """
    Đảm bảo probe điều kiện demo_random kiểm tra chặt chẽ random_demonstrations trong spec.
    """
    spec = sample_fixture()

    # Thiếu random_demonstrations -> ném lỗi
    with pytest.raises(ValueError, match="demo_random control requires nonempty random_demonstrations"):
        render_control_v2(spec, condition="demo_random")

    # Có random_demonstrations hợp lệ -> hoạt động đúng
    spec["random_demonstrations"] = [
        {"function_uid": "rand1", "func": "void random_code() { return; }", "target": 0}
    ]
    res = render_control_v2(spec, condition="demo_random")
    assert "random_code" in res["prompt"]
    assert res["evidence"]["displayed_demonstrations"][0]["function_uid"] == "rand1"


def test_layout_flag_interoperability():
    """
    Đảm bảo spec['layout_version'] == 'figure6_v2' hoặc spec['layout'] == 'figure6_v2'
    tự động kích hoạt canonical renderer ở cả render_control và build_grace_prompt.
    """
    spec = sample_fixture()
    spec["layout"] = "figure6_v2"
    res1 = render_control(spec)
    assert res1["evidence"]["layout_version"] == "figure6_v2"

    del spec["layout"]
    spec["layout_version"] = "figure6_v2"
    res2 = render_control(spec)
    assert res2["evidence"]["layout_version"] == "figure6_v2"

    # build_grace_prompt với sample chứa layout_version="figure6_v2"
    sample_engine = {
        "func": spec["query_code"],
        "example": spec["demonstrations"][0],
        "nodes": spec["nodes"],
        "edges": spec["edges"],
        "layout_version": "figure6_v2",
    }
    prompt = build_grace_prompt(sample_engine)
    assert "Answer (0 or 1):" in prompt
    assert prompt.startswith("int target_func")

