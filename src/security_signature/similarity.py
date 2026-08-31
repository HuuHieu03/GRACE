"""
Security Signature Similarity Metric Module
Tính toán độ tương đồng cơ chế bảo mật (Security Signature Similarity) giữa hai hàm C/C++.
"""

from typing import Dict, Any, Tuple
from .schema import SecuritySignature


def compute_jaccard_set(set1: set, set2: set) -> float:
    """Tính chỉ số Jaccard giữa hai tập hợp."""
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    return len(set1.intersection(set2)) / float(len(set1.union(set2)))


def compute_security_signature_similarity(
    sig1: SecuritySignature, 
    sig2: SecuritySignature,
    weights: Dict[str, float] = None
) -> Tuple[float, Dict[str, float]]:
    """
    Tính toán độ tương đồng cơ chế an ninh toàn diện giữa hai SecuritySignature.
    
    Công thức tổng hợp:
    Score_sec = w_sink * Sim_Sink + w_san * Sim_Sanitizer + w_mem * Sim_Memory + w_clue * Sim_Clues
    
    Returns:
        (composite_score, sub_scores_dict)
    """
    if weights is None:
        weights = {
            "sink": 0.35,
            "sanitizer": 0.25,
            "memory": 0.20,
            "clues": 0.20
        }
        
    # 1. Sink Similarity (APIs & Danh mục Sink)
    apis1, apis2 = sig1.sink_apis, sig2.sink_apis
    cats1 = {s.sink_category for s in sig1.sinks}
    cats2 = {s.sink_category for s in sig2.sinks}
    api_sim = compute_jaccard_set(apis1, apis2)
    cat_sim = compute_jaccard_set(cats1, cats2)
    sink_sim = 0.6 * api_sim + 0.4 * cat_sim
    
    # 2. Sanitizer / Guard Similarity
    sans1, sans2 = sig1.sanitizer_types, sig2.sanitizer_types
    sanitizer_sim = compute_jaccard_set(sans1, sans2)
    
    # 3. Memory Operations Similarity
    m1, m2 = sig1.memory_ops, sig2.memory_ops
    mem_matches = sum([
        1 if m1.has_pointer_deref == m2.has_pointer_deref else 0,
        1 if m1.has_array_indexing == m2.has_array_indexing else 0,
        1 if m1.has_dynamic_alloc == m2.has_dynamic_alloc else 0,
        1 if m1.has_explicit_free == m2.has_explicit_free else 0,
        1 if m1.has_pointer_arithmetic == m2.has_pointer_arithmetic else 0
    ])
    mem_sim = mem_matches / 5.0
    
    # 4. Vulnerability Clues Similarity
    clues1, clues2 = sig1.vulnerability_clues, sig2.vulnerability_clues
    clues_sim = compute_jaccard_set(clues1, clues2)
    
    # Tính điểm tổng hợp
    composite_score = (
        weights["sink"] * sink_sim +
        weights["sanitizer"] * sanitizer_sim +
        weights["memory"] * mem_sim +
        weights["clues"] * clues_sim
    )
    
    sub_scores = {
        "sink_similarity": round(sink_sim, 4),
        "sanitizer_similarity": round(sanitizer_sim, 4),
        "memory_similarity": round(mem_sim, 4),
        "clues_similarity": round(clues_sim, 4),
        "composite_security_score": round(composite_score, 4)
    }
    
    return round(composite_score, 4), sub_scores
