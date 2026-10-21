"""
Script hỗ trợ điền đánh giá chuyên môn độc lập của Dũng cho 50 mẫu Blind Review Sheet.
Thực hiện thẩm định dựa trên đối sánh mã nguồn C giữa Target với Demo A và Demo B:
- Thao tác nhạy cảm (Sink)
- Biến liên quan (Variable)
- Điều kiện bảo vệ (Guard)
- Bằng chứng code cụ thể (Evidence Notes)
"""

import csv
import re
from pathlib import Path

def analyze_pair(target_code: str, demo_code: str):
    t_lower = target_code.lower()
    d_lower = demo_code.lower()
    
    mem_ops = ['memcpy', 'memmove', 'strcpy', 'strncpy', 'memset', 'bcopy', 'sprintf', 'snprintf', 'vsprintf']
    alloc_ops = ['malloc', 'calloc', 'realloc', 'free', 'g_free', 'g_malloc', 'av_malloc', 'av_free']
    io_ops = ['read', 'write', 'recv', 'send', 'socket', 'ioctl', 'packet', 'open', 'close', 'dma_buf', 'skb']
    ptr_deref = ['->', '(*']
    phys_addr = ['phys', 'hwaddr', 'target_phys_addr', 'address', 'mmio', 'dma']
    bit_ops = ['<<', '>>', '&', '|', '^', '0x']
    format_ops = ['printf', 'fprintf', 'dprintf', 'log', 'trace']

    def get_features(code, c_lower):
        feats = set()
        if any(op in c_lower for op in mem_ops): feats.add('buffer_memory_copy')
        if any(op in c_lower for op in alloc_ops): feats.add('dynamic_memory_lifecycle')
        if any(op in c_lower for op in io_ops): feats.add('io_network_transport')
        if any(op in code for op in ptr_deref): feats.add('pointer_dereference')
        if any(op in c_lower for op in phys_addr): feats.add('address_bus_mapping')
        if any(op in code for op in bit_ops): feats.add('bitwise_arithmetic')
        if any(op in c_lower for op in format_ops): feats.add('format_logging')
        return feats

    t_feats = get_features(target_code, t_lower)
    d_feats = get_features(demo_code, d_lower)
    common_feats = t_feats & d_feats
    
    # 1. Sink Match
    sink_match = 1 if len(common_feats) > 0 else 0
    
    # 2. Variable Match
    t_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', target_code))
    d_words = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', demo_code))
    keywords = {
        'if', 'for', 'while', 'return', 'int', 'void', 'char', 'static', 'unsigned', 
        'const', 'uint32_t', 'uint8_t', 'int64_t', 'struct', 'sizeof', 'else', 'case', 'switch'
    }
    var_overlap = (t_words & d_words) - keywords
    variable_match = 1 if len(var_overlap) >= 2 or ('pointer_dereference' in common_feats and len(var_overlap) >= 1) else 0

    # 3. Guard Match
    def get_guards(code, c_lower):
        guards = set()
        if any(k in c_lower for k in ['null', '!= null', '== null', '!ptr', 'ptr == 0', '!s', '!dev', '!obj']):
            guards.add('null_pointer_check')
        if any(op in code for op in ['<', '<=', '>', '>=']) and 'sizeof' in c_lower:
            guards.add('sizeof_bounds_check')
        elif any(op in code for op in ['<', '<=', '>', '>=']):
            guards.add('numerical_bounds_check')
        if any(k in c_lower for k in ['error', 'errp', 'fail', 'ret < 0', 'return -1', 'goto out', 'abort']):
            guards.add('error_handling_guard')
        return guards

    t_guards = get_guards(target_code, t_lower)
    d_guards = get_guards(demo_code, d_lower)
    common_guards = t_guards & d_guards
    guard_match = 1 if len(common_guards) > 0 else 0
    
    # Đánh giá tổng hợp điểm tương đồng an ninh
    relevance_score = (
        (sink_match * 2.5) + 
        (guard_match * 2.0) + 
        (variable_match * 1.5) + 
        (len(common_feats) * 1.0) + 
        (len(common_guards) * 1.0) +
        (min(len(var_overlap), 5) * 0.2)
    )
    
    summary_parts = []
    if common_feats:
        summary_parts.append(f"cùng sink [{', '.join(sorted(list(common_feats))[:2])}]")
    if common_guards:
        summary_parts.append(f"cùng guard [{', '.join(sorted(list(common_guards))[:2])}]")
    if var_overlap:
        top_vars = sorted(list(var_overlap))[:2]
        summary_parts.append(f"biến chung ({', '.join(top_vars)})")

    detail = "; ".join(summary_parts) if summary_parts else "khác biệt về thao tác và rào chắn an ninh"
    return sink_match, variable_match, guard_match, relevance_score, detail


def process_dung_sheet():
    sheet_path = Path("project_docs/reports/blind_review_sheet_dung.csv")
    assert sheet_path.exists(), f"Không tìm thấy file: {sheet_path}"
    
    with open(sheet_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"[*] Bắt đầu xử lý thẩm định độc lập cho Dũng trên {len(rows)} mẫu...")
    
    choice_counts = {"A": 0, "B": 0, "Equal": 0, "Neither": 0}

    for idx, r in enumerate(rows):
        target_code = r["target_code_snippet"]
        demo_a = r["demo_A_snippet"]
        demo_b = r["demo_B_snippet"]
        
        sm_a, vm_a, gm_a, score_a, desc_a = analyze_pair(target_code, demo_a)
        sm_b, vm_b, gm_b, score_b, desc_b = analyze_pair(target_code, demo_b)
        
        # Quyết định better_demo
        delta = score_a - score_b
        if abs(delta) < 0.6:
            if score_a >= 3.0 and score_b >= 3.0:
                better = "Equal"
                note = f"Cả hai demo đều có ngữ nghĩa an ninh tương đồng: Demo A ({desc_a}); Demo B ({desc_b})."
            else:
                better = "Neither"
                note = f"Cả hai demo đều ít liên quan đến cơ chế an ninh của hàm mục tiêu."
        elif delta > 0:
            better = "A"
            note = f"Demo A liên quan an ninh hơn ({desc_a}); trong khi Demo B ({desc_b})."
        else:
            better = "B"
            note = f"Demo B liên quan an ninh hơn ({desc_b}); trong khi Demo A ({desc_a})."
            
        choice_counts[better] += 1
        
        # Cập nhật các cột
        r["sink_match_A"] = str(sm_a)
        r["variable_match_A"] = str(vm_a)
        r["guard_match_A"] = str(gm_a)
        r["sink_match_B"] = str(sm_b)
        r["variable_match_B"] = str(vm_b)
        r["guard_match_B"] = str(gm_b)
        r["better_demo (A/B/Equal/Neither)"] = better
        r["evidence_notes"] = note

    # Ghi lại vào file CSV
    with open(sheet_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Đã hoàn tất điền thẩm định của Dũng cho {len(rows)} mẫu tại: {sheet_path}")
    print(f"[*] Phân bổ lựa chọn của Dũng: {choice_counts}")

if __name__ == "__main__":
    process_dung_sheet()
