"""
GRACE Prompt Engine (Stage 3)
Module chuyên trách lắp ráp Câu Lệnh Dẫn Hướng (Prompt) tuân thủ 100% nguyên bản
thiết kế tại Mục 3.3 và Hình 6 (Figure 6) trong bài báo khoa học GRACE.

Cấu trúc chuẩn theo bài báo:
1. Basic Prompt, Identity & Domain Information (Pi, Pd, Pb).
2. Demonstration Example (Chỉ bao gồm Mã nguồn ví dụ + Nhãn Ground Truth).
3. Target Function (Mã nguồn mục tiêu + Thông tin Nút Node & Cạnh Edge của Đồ thị CPG).
4. Output Formatting Constraint (Dự đoán nhị phân 1/0 hoặc Vulnerable/Non-vulnerable).
"""

from typing import Dict, Any, List, Union, Optional, Tuple


def format_node_information(nodes: List[Any], max_nodes: int = 30) -> str:
    """
    Định dạng danh sách nút (Nodes) của đồ thị CPG/AST cho hàm mục tiêu (Target Function)
    theo phong cách Figure 5 & Figure 6 trong bài báo GRACE.
    """
    if not nodes:
        return "[No Node Information Available]"
        
    lines = []
    for idx, n in enumerate(nodes[:max_nodes]):
        if isinstance(n, dict):
            n_id = n.get("id", idx)
            n_type = n.get("type", n.get("label", "Node"))
            n_code = n.get("code", "").strip()
            if n_code:
                # Cắt ngắn nếu code trong node quá dài
                snippet = n_code[:40] + "..." if len(n_code) > 40 else n_code
                lines.append(f"Node {n_id}: ({n_type}) '{snippet}'")
            else:
                lines.append(f"Node {n_id}: ({n_type})")
        else:
            lines.append(f"Node {idx}: {str(n)}")
            
    if len(nodes) > max_nodes:
        lines.append(f"... (and {len(nodes) - max_nodes} more nodes omitted for token budget)")
        
    return "\n".join(lines)


def format_edge_information(edges: List[Any], max_edges: int = 30) -> str:
    """
    Định dạng danh sách cạnh (Edges - AST, CFG, PDG) của đồ thị CPG cho hàm mục tiêu (Target Function)
    theo phong cách Figure 5 & Figure 6 trong bài báo GRACE.
    """
    if not edges:
        return "[No Edge Information Available]"
        
    lines = []
    for idx, e in enumerate(edges[:max_edges]):
        if isinstance(e, dict):
            src = e.get("start", e.get("source", "?"))
            dst = e.get("end", e.get("target", "?"))
            e_type = e.get("type", "CONNECTED_TO")
            lines.append(f"Edge: Node {src} -> {e_type} -> Node {dst}")
        else:
            lines.append(f"Edge {idx}: {str(e)}")
            
    if len(edges) > max_edges:
        lines.append(f"... (and {len(edges) - max_edges} more edges omitted for token budget)")
        
    return "\n".join(lines)


def format_graph_structure(nodes: List[Any], edges: List[Any], max_nodes: int = 25, max_edges: int = 25) -> str:
    """
    Hàm tiện ích gom nhóm toàn bộ cấu trúc đồ thị CPG (Node + Edge) thành văn bản trực quan.
    """
    node_str = format_node_information(nodes, max_nodes=max_nodes)
    edge_str = format_edge_information(edges, max_edges=max_edges)
    
    return (
        f"The node information of the function is as follows:\n{node_str}\n\n"
        f"The edge information of the function is as follows:\n{edge_str}"
    )


def build_grace_prompt_legacy(sample: Dict[str, Any], include_demonstration: bool = True) -> str:
    """
    Xây dựng toàn bộ Prompt theo thiết kế cũ (Legacy):
    1. Basic Prompt, Identity & Domain Information (Pi, Pd, Pb).
    2. Demonstration Example (Chỉ bao gồm Mã nguồn ví dụ + Nhãn Ground Truth).
    3. Target Query Function (Mã nguồn mục tiêu + Thông tin Nút Node & Cạnh Edge của Đồ thị CPG).
    4. Output Formatting Constraint (Dự đoán nhị phân 1/0 hoặc Vulnerable/Non-vulnerable).
    """
    prompt_parts = []
    
    # 1. TASK, IDENTITY & DOMAIN INSTRUCTION (Theo chuẩn Pi + Pd + Pb)
    system_role = (
        "### TASK INSTRUCTION\n"
        "You are now an excellent programmer.\n"
        "You are conducting a function vulnerability detection task for C/C++ language.\n"
        "Your objective is to evaluate whether the given target function contains software vulnerabilities "
        "(e.g., buffer overflows, memory corruptions, race conditions, null pointer dereferences)."
    )
    prompt_parts.append(system_role)
    
    # 2. IN-CONTEXT DEMONSTRATION SECTION (100% Chuẩn Figure 6: Code mẫu + Nhãn)
    demo_sample = sample.get("example")
    if demo_sample is None and sample.get("contrastive_obj"):
        demo_sample = sample["contrastive_obj"].vulnerable_example
        
    if include_demonstration and demo_sample and isinstance(demo_sample, dict) and ("func" in demo_sample or "code" in demo_sample or "functionSource" in demo_sample):
        demo_label_num = demo_sample.get("target", 0)
        demo_label_str = "Vulnerable (1)" if demo_label_num == 1 else "Non-vulnerable (0)"
        
        demo_func = str(demo_sample.get("func") or demo_sample.get("code") or demo_sample.get("functionSource") or "").strip()
        # Truncate demo code if excessively long
        if len(demo_func) > 1500:
            demo_func = demo_func[:1500] + "\n/* [TRUNCATED TO PRESERVE CONTEXT] */"
            
        demo_section = (
            "### DEMONSTRATION EXAMPLE (In-Context Reference)\n"
            "Here is an example for you to learn from:\n\n"
            f"--- DEMONSTRATION CODE ---\n{demo_func}\n\n"
            f"--- DEMONSTRATION GROUND TRUTH LABEL ---\n"
            f"Label: {demo_label_str}\n"
            "--------------------------------------------------"
        )
        prompt_parts.append(demo_section)
        
    # 3. TARGET QUERY SECTION (Mã nguồn mục tiêu + Đồ thị CPG Node & Edge)
    query_code = str(sample.get("func") or sample.get("code") or sample.get("functionSource") or "").strip()
    if len(query_code) > 3000:
        query_code = query_code[:3000] + "\n/* [TRUNCATED TO PREVENT MEMORY OVERFLOW] */"
        
    nodes = sample.get("nodes", [])
    edges = sample.get("edges", [])
    target_graph_str = format_graph_structure(nodes, edges, max_nodes=25, max_edges=25)
    
    query_section = (
        "### TARGET QUERY FOR EVALUATION\n"
        f"--- TARGET CODE ---\n{query_code}\n\n"
        f"--- TARGET GRAPH STRUCTURE ---\n{target_graph_str}"
    )
    prompt_parts.append(query_section)
    
    # 4. OUTPUT FORMAT CONSTRAINT
    format_constraint = (
        "### OUTPUT FORMAT REQUIREMENT\n"
        "In the above target code snippet, check for potential security vulnerabilities.\n"
        "You must output ONLY a single character: '1' if Vulnerable, or '0' if Non-vulnerable. Do not output any explanation."
    )
    prompt_parts.append(format_constraint)
    
    return "\n\n".join(prompt_parts)


def build_grace_prompt_canonical_with_metadata(
    sample: Dict[str, Any],
    include_demonstration: bool = True,
    budget_manager: Optional[Any] = None,
    include_graph: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """
    Xây dựng toàn bộ Prompt tuân thủ 100% Hình 6 (Figure 6) của bài báo gốc GRACE:
    1. Target Code ([CODE SNIPPET])
    2. Task Instruction (In the above code snippet, check for potential security vulnerabilities and answer with a single digit: 1 if Vulnerable, 0 if Non-vulnerable. You are now an excellent programmer. You are conducting a function vulnerability detection task for C/C++ language.)
    3. Node Info (The node information of the code snippet is as follows: ...)
    4. Edge Info (The edge information of the code snippet is as follows: ...)
    5. Demonstration (ở cuối cùng): The following is an example, and it is [Vulnerable | Non-vulnerable].\n[DEMO CODE]
    6. Answer Indicator (Answer (0 or 1):)
    """
    if budget_manager is None:
        try:
            from token_budget import TokenBudgetManager
            budget_manager = TokenBudgetManager(force_offline=True)
        except Exception:
            budget_manager = None

    # 1. Target Code
    raw_query_code = str(sample.get("func") or sample.get("code") or sample.get("functionSource") or sample.get("query_code") or "").strip()
    if budget_manager is not None:
        target_code, code_stats = budget_manager.truncate_target_code(raw_query_code)
    else:
        target_code = raw_query_code[:3000] if len(raw_query_code) > 3000 else raw_query_code
        code_stats = {"was_truncated": len(raw_query_code) > 3000}

    # 2. Task Instruction (Exact Figure 6 text)
    task_instruction = (
        "In the above code snippet, check for potential security vulnerabilities and answer with a single digit: 1 if Vulnerable, 0 if Non-vulnerable. "
        "You are now an excellent programmer. You are conducting a function vulnerability detection task for C/C++ language."
    )

    # 3 & 4. Node & Edge Info
    graph_text = ""
    graph_stats = {"was_truncated": False}
    render_graph = include_graph and sample.get("include_graph", True)
    if render_graph:
        nodes = sample.get("nodes", [])
        edges = sample.get("edges", [])
        node_str = format_node_information(nodes, max_nodes=25)
        edge_str = format_edge_information(edges, max_edges=25)

        node_section = f"The node information of the code snippet is as follows:\n{node_str}"
        edge_section = f"The edge information of the code snippet is as follows:\n{edge_str}"
        graph_full = f"{node_section}\n\n{edge_section}"

        if budget_manager is not None:
            graph_text, graph_stats = budget_manager.truncate_graph(graph_full)
        else:
            graph_text = graph_full

    # 5. Demonstration (ở cuối cùng)
    demo_section = ""
    demo_stats: Dict[str, Any] = {"was_truncated": False, "truncated_demo": False, "empty_demo": False}

    if include_demonstration:
        demo_sample = sample.get("example")
        if demo_sample is None and sample.get("contrastive_obj"):
            demo_sample = sample["contrastive_obj"].vulnerable_example
        if demo_sample is None and sample.get("demonstrations") and isinstance(sample["demonstrations"], list) and len(sample["demonstrations"]) > 0:
            demo_sample = sample["demonstrations"][0]

        if demo_sample:
            if isinstance(demo_sample, dict):
                demo_label_val = demo_sample.get("target", sample.get("example_target", 0))
                demo_raw_code = str(demo_sample.get("func") or demo_sample.get("code") or demo_sample.get("functionSource") or "").strip()
            else:
                demo_label_val = sample.get("example_target", 0)
                demo_raw_code = str(demo_sample).strip()

            demo_label_str = "Vulnerable" if (demo_label_val == 1 or str(demo_label_val).lower() in ("1", "vulnerable")) else "Non-vulnerable"

            if budget_manager is not None:
                truncated_demo_code, demo_stats = budget_manager.truncate_demonstration(demo_raw_code)
            else:
                truncated_demo_code = demo_raw_code[:1500] if len(demo_raw_code) > 1500 else demo_raw_code
                demo_stats = {
                    "was_truncated": len(demo_raw_code) > 1500,
                    "truncated_demo": len(demo_raw_code) > 1500 and len(truncated_demo_code) < len(demo_raw_code) * 0.25,
                    "empty_demo": not truncated_demo_code.strip()
                }

            demo_section = f"The following is an example, and it is {demo_label_str}.\n{truncated_demo_code}"

    # 6. Answer Indicator
    answer_indicator = "Answer (0 or 1):"

    # Assemble in exact Figure 6 order
    parts = [target_code, task_instruction]
    if graph_text:
        parts.append(graph_text)
    if demo_section:
        parts.append(demo_section)
    parts.append(answer_indicator)

    prompt = "\n\n".join(parts)

    audit_stats = {}
    if budget_manager is not None:
        audit_stats = budget_manager.audit_prompt_tokens(
            code_text=target_code,
            graph_text=graph_text,
            demo_text=demo_section,
            instruction_text=task_instruction,
            format_text=answer_indicator,
        )

    metadata = {
        "layout_version": "figure6_v2",
        "tokens_code": audit_stats.get("tokens_code", 0),
        "tokens_graph": audit_stats.get("tokens_graph", 0),
        "tokens_demo": audit_stats.get("tokens_demo", 0),
        "tokens_total": audit_stats.get("tokens_total", 0),
        "output_reserve": audit_stats.get("output_reserve", 64),
        "context_limit": audit_stats.get("context_limit", 8192),
        "truncated_demo": demo_stats.get("truncated_demo", False),
        "empty_demo": demo_stats.get("empty_demo", False),
        "code_stats": code_stats,
        "graph_stats": graph_stats,
        "demo_stats": demo_stats,
        "audit": audit_stats,
    }
    return prompt, metadata


def build_grace_prompt_canonical(
    sample: Dict[str, Any],
    include_demonstration: bool = True,
    budget_manager: Optional[Any] = None,
    include_graph: bool = True,
) -> str:
    """Wrapper trả về prompt string Figure 6 canonical."""
    prompt_str, _ = build_grace_prompt_canonical_with_metadata(
        sample=sample,
        include_demonstration=include_demonstration,
        budget_manager=budget_manager,
        include_graph=include_graph,
    )
    return prompt_str


def build_grace_prompt(
    sample: Dict[str, Any],
    include_demonstration: bool = True,
    canonical: bool = False,
    budget_manager: Optional[Any] = None,
    include_graph: bool = True,
) -> str:
    """
    Xây dựng prompt GRACE với hỗ trợ tương thích ngược (Zero Regression).
    - canonical=False (mặc định): giữ nguyên định dạng legacy trừ khi sample yêu cầu layout_version="figure6_v2"
    - canonical=True: sử dụng layout Figure 6 chuẩn bài báo
    """
    use_canonical = canonical or sample.get("layout_version") == "figure6_v2" or sample.get("layout") == "figure6_v2"
    if use_canonical:
        return build_grace_prompt_canonical(
            sample=sample,
            include_demonstration=include_demonstration,
            budget_manager=budget_manager,
            include_graph=include_graph,
        )
    return build_grace_prompt_legacy(sample=sample, include_demonstration=include_demonstration)


def build_contrastive_prompt(
    sample: Dict[str, Any],
    invert_order: bool = False,
    include_security_diff: bool = True
) -> str:
    """
    Xây dựng Câu Lệnh Tương Phản (Contrastive ICL Prompt - 2-shot) tuân thủ Figure 6:
    Cung cấp đồng thời 1 Cặp ví dụ mẫu (1 Vulnerable + 1 Safe) có cơ chế an ninh tương đồng nhất
    để giúp LLM tự thiết lập ranh giới quyết định (Decision Boundary).
    Bao gồm phân tích điểm khác biệt an ninh cốt lõi (Security Difference) giữa 2 mẫu.
    Khi include_security_diff=False (chế độ Ablation Study), khối '--- CORE SECURITY DIFFERENCE ---'
    sẽ được cắt bỏ để bóc tách tác động độc lập của Cặp mẫu cân bằng nhãn 1:1 so với khối giải thích an ninh.
    """
    prompt_parts = []
    
    # 1. TASK INSTRUCTION
    system_role = (
        "### TASK INSTRUCTION\n"
        "You are now an excellent programmer.\n"
        "You are conducting a function vulnerability detection task for C/C++ language.\n"
        "Your objective is to evaluate whether the given target function contains software vulnerabilities "
        "(e.g., buffer overflows, memory corruptions, race conditions, null pointer dereferences)."
    )
    prompt_parts.append(system_role)
    
    # 2. CONTRASTIVE DEMONSTRATION SECTION (1 Vulnerable + 1 Safe)
    pair = sample.get("contrastive_pair")
    pair_obj = sample.get("contrastive_obj")
    
    sec_diff = ""
    if pair_obj:
        v_func = str(pair_obj.vulnerable_example.get("func") or pair_obj.vulnerable_example.get("code") or "").strip()
        s_func = str(pair_obj.safe_example.get("func") or pair_obj.safe_example.get("code") or "").strip()
        sec_diff = getattr(pair_obj, "security_critical_difference", "")
    elif pair and isinstance(pair, dict):
        v_dict = pair.get("vulnerable", {})
        s_dict = pair.get("safe", {})
        v_func = str(v_dict.get("func") or v_dict.get("code") or v_dict.get("func_snippet") or "").strip()
        s_func = str(s_dict.get("func") or s_dict.get("code") or s_dict.get("func_snippet") or "").strip()
        sec_diff = pair.get("security_difference", "")
    else:
        # Fallback to standard demo if contrastive pair is missing
        return build_grace_prompt(sample, include_demonstration=True)
        
    if len(v_func) > 1200:
        v_func = v_func[:1200] + "\n/* [TRUNCATED TO PRESERVE CONTEXT] */"
    if len(s_func) > 1200:
        s_func = s_func[:1200] + "\n/* [TRUNCATED TO PRESERVE CONTEXT] */"

    diff_section = f"\n\n--- CORE SECURITY DIFFERENCE ---\n{sec_diff}" if (sec_diff and include_security_diff) else ""

    if not invert_order:
        contrastive_section = (
            "### CONTRASTIVE DEMONSTRATION EXAMPLES (In-Context Reference Pair)\n"
            "Here are two comparative examples (one Vulnerable and one Safe) demonstrating key security conditions:\n\n"
            "--- EXAMPLE 1 (VULNERABLE REFERENCE) ---\n"
            f"{v_func}\n"
            "Label: Vulnerable (1)\n\n"
            "--- EXAMPLE 2 (SAFE / NON-VULNERABLE REFERENCE) ---\n"
            f"{s_func}\n"
            f"Label: Non-vulnerable (0){diff_section}\n"
            "--------------------------------------------------"
        )
    else:
        contrastive_section = (
            "### CONTRASTIVE DEMONSTRATION EXAMPLES (In-Context Reference Pair)\n"
            "Here are two comparative examples (one Safe and one Vulnerable) demonstrating key security conditions:\n\n"
            "--- EXAMPLE 1 (SAFE / NON-VULNERABLE REFERENCE) ---\n"
            f"{s_func}\n"
            "Label: Non-vulnerable (0)\n\n"
            "--- EXAMPLE 2 (VULNERABLE REFERENCE) ---\n"
            f"{v_func}\n"
            f"Label: Vulnerable (1){diff_section}\n"
            "--------------------------------------------------"
        )
    prompt_parts.append(contrastive_section)
    
    # 3. TARGET QUERY SECTION
    query_code = sample.get("func", "").strip()
    if len(query_code) > 3000:
        query_code = query_code[:3000] + "\n/* [TRUNCATED TO PREVENT MEMORY OVERFLOW] */"
        
    nodes = sample.get("nodes", [])
    edges = sample.get("edges", [])
    target_graph_str = format_graph_structure(nodes, edges, max_nodes=25, max_edges=25)
    
    query_section = (
        "### TARGET QUERY FOR EVALUATION\n"
        f"--- TARGET CODE ---\n{query_code}\n\n"
        f"--- TARGET GRAPH STRUCTURE ---\n{target_graph_str}"
    )
    prompt_parts.append(query_section)
    
    # 4. OUTPUT FORMAT REQUIREMENT
    format_constraint = (
        "### OUTPUT FORMAT REQUIREMENT\n"
        "In the above target code snippet, check for potential security vulnerabilities by comparing against the contrastive examples.\n"
        "You must output ONLY a single character: '1' if Vulnerable, or '0' if Non-vulnerable. Do not output any explanation."
    )
    prompt_parts.append(format_constraint)
    
    return "\n\n".join(prompt_parts)


def build_prompt(sample: Dict[str, Any], mode: str = "contrastive_2shot") -> str:
    """
    Hàm Dispatcher tập trung sinh prompt theo 4 chế độ thực nghiệm khoa học:
    - 'zero_shot': Không có demonstration
    - 'standard_1shot': GRACE baseline 1-shot (Chuẩn Figure 6)
    - 'contrastive_2shot': Security-Aware Contrastive ICL 2-shot (Cải tiến Stage 5)
    - 'contrastive_2shot_nodiff': Ablation Study B3-NoDiff (Cắt bỏ Core Security Difference)
    """
    if mode == "zero_shot":
        return build_grace_prompt(sample, include_demonstration=False)
    elif mode == "standard_1shot":
        return build_grace_prompt(sample, include_demonstration=True)
    elif mode in ("standard_1shot_canonical", "canonical_1shot", "figure6_v2"):
        return build_grace_prompt_canonical(sample, include_demonstration=True)
    elif mode in ("zero_shot_canonical", "figure6_v2_zero_shot"):
        return build_grace_prompt_canonical(sample, include_demonstration=False)
    elif mode == "contrastive_2shot":
        return build_contrastive_prompt(sample, include_security_diff=True)
    elif mode == "contrastive_2shot_nodiff":
        return build_contrastive_prompt(sample, include_security_diff=False)
    else:
        raise ValueError(f"Chế độ mode '{mode}' không hợp lệ. Chọn: 'zero_shot', 'standard_1shot', 'figure6_v2', 'contrastive_2shot', 'contrastive_2shot_nodiff'.")

