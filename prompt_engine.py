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

from typing import Dict, Any, List, Union


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


def build_grace_prompt(sample: Dict[str, Any], include_demonstration: bool = True) -> str:
    """
    Xây dựng toàn bộ Prompt tuân thủ 100% thiết kế tại Mục 3.3 & Hình 6 (Figure 6) bài báo GRACE:
    
    1. Identity & Domain Setting:
       - 'You are now an excellent programmer.' (Pi)
       - 'You are conducting a function vulnerability detection task for C/C++ language.' (Pd)
       
    2. Demonstration Section (In-Context Learning - Nếu được kích hoạt):
       - 'Here is an example for you to learn from:'
       - [Demonstration Code Snippet] (Chỉ mã nguồn, KHÔNG đưa graph và reasoning tự chế)
       - [Demonstration Ground Truth Label] ('Vulnerable' (1) hoặc 'Non-vulnerable' (0))
       
    3. Target Query Function (Hàm cần kiểm tra):
       - [Target Code Snippet]
       - The node information of the function is as follows: [Node info]
       - The edge information of the function is as follows: [Edge info]
       
    4. Task Instruction & Output Constraint:
       - 'In the above target code snippet, check for potential security vulnerabilities and output either '1' if Vulnerable or '0' if Non-vulnerable.'
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
        
    if include_demonstration and demo_sample and isinstance(demo_sample, dict) and "func" in demo_sample:
        demo_label_num = demo_sample.get("target", 0)
        demo_label_str = "Vulnerable (1)" if demo_label_num == 1 else "Non-vulnerable (0)"
        
        demo_func = demo_sample.get("func", "").strip()
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
    
    # 4. OUTPUT FORMAT CONSTRAINT
    format_constraint = (
        "### OUTPUT FORMAT REQUIREMENT\n"
        "In the above target code snippet, check for potential security vulnerabilities.\n"
        "You must output ONLY a single character: '1' if Vulnerable, or '0' if Non-vulnerable. Do not output any explanation."
    )
    prompt_parts.append(format_constraint)
    
    return "\n\n".join(prompt_parts)


def build_contrastive_prompt(sample: Dict[str, Any]) -> str:
    """
    Xây dựng Câu Lệnh Tương Phản (Contrastive ICL Prompt - 2-shot) tuân thủ Figure 6:
    Cung cấp đồng thời 1 Cặp ví dụ mẫu (1 Vulnerable + 1 Safe) có cơ chế an ninh tương đồng nhất
    để giúp LLM tự thiết lập ranh giới quyết định (Decision Boundary).
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
    
    if pair_obj:
        v_func = pair_obj.vulnerable_example.get("func", "").strip()
        s_func = pair_obj.safe_example.get("func", "").strip()
    elif pair and isinstance(pair, dict):
        v_func = pair.get("vulnerable", {}).get("func_snippet", "")
        s_func = pair.get("safe", {}).get("func_snippet", "")
    else:
        # Fallback to standard demo if contrastive pair is missing
        return build_grace_prompt(sample, include_demonstration=True)
        
    if len(v_func) > 1200:
        v_func = v_func[:1200] + "\n/* [TRUNCATED TO PRESERVE CONTEXT] */"
    if len(s_func) > 1200:
        s_func = s_func[:1200] + "\n/* [TRUNCATED TO PRESERVE CONTEXT] */"
        
    contrastive_section = (
        "### CONTRASTIVE DEMONSTRATION EXAMPLES (In-Context Reference Pair)\n"
        "Here are two comparative examples (one Vulnerable and one Safe) demonstrating key security conditions:\n\n"
        "--- EXAMPLE 1 (VULNERABLE REFERENCE) ---\n"
        f"{v_func}\n"
        "Label: Vulnerable (1)\n\n"
        "--- EXAMPLE 2 (SAFE / NON-VULNERABLE REFERENCE) ---\n"
        f"{s_func}\n"
        "Label: Non-vulnerable (0)\n"
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
    Hàm Dispatcher tập trung sinh prompt theo 3 chế độ thực nghiệm khoa học:
    - 'zero_shot': Không có demonstration
    - 'standard_1shot': GRACE baseline 1-shot (Chuẩn Figure 6)
    - 'contrastive_2shot': Security-Aware Contrastive ICL 2-shot (Cải tiến Stage 5)
    """
    if mode == "zero_shot":
        return build_grace_prompt(sample, include_demonstration=False)
    elif mode == "standard_1shot":
        return build_grace_prompt(sample, include_demonstration=True)
    elif mode == "contrastive_2shot":
        return build_contrastive_prompt(sample)
    else:
        raise ValueError(f"Chế độ mode '{mode}' không hợp lệ. Chọn: 'zero_shot', 'standard_1shot', 'contrastive_2shot'.")

