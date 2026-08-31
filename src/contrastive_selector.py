"""
Contrastive Demonstration Selector Module (Stage 5 - Phase 4)
Xây dựng cặp mẫu đối sánh tương phản (Contrastive Pair: 1 Vulnerable + 1 Safe)
để thiết lập ranh giới quyết định (Decision Boundary) rõ ràng cho LLM.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional

from retrieval_security_engine import SecurityAwareRetriever
from retrieval_engine import jaccard_similarity
from security_signature.extractor import extract_security_signature
from security_signature.similarity import compute_security_signature_similarity
from security_signature.schema import SecuritySignature

logger = logging.getLogger("ContrastiveSelector")


@dataclass
class ContrastivePair:
    """Đại diện cho 1 cặp ví dụ mẫu tương phản hoàn chỉnh (1 Lỗ hổng + 1 An toàn)."""
    vulnerable_example: Dict[str, Any]
    safe_example: Dict[str, Any]
    vuln_security_score: float
    safe_security_score: float
    pair_code_similarity: float
    security_critical_difference: str
    selection_strategy: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vulnerable": {
                "id": self.vulnerable_example.get("id"),
                "target": 1,
                "security_score": self.vuln_security_score,
                "func_snippet": self.vulnerable_example.get("func", "")[:120] + "..."
            },
            "safe": {
                "id": self.safe_example.get("id"),
                "target": 0,
                "security_score": self.safe_security_score,
                "func_snippet": self.safe_example.get("func", "")[:120] + "..."
            },
            "pair_code_similarity": round(self.pair_code_similarity, 4),
            "security_difference": self.security_critical_difference,
            "strategy": self.selection_strategy
        }


class ContrastiveDemonstrationSelector:
    """
    Bộ lựa chọn cặp mẫu đối sánh tương phản (Contrastive Demonstration Selector).
    Hỗ trợ 3 chiến lược:
    - Strategy C: Counterexample Pair (Tối ưu hóa Decision Boundary giữa cặp tương đồng bối cảnh nhất)
    - Strategy B: Minimal Security Difference (Cặp có sai khác tối thiểu về điều kiện an ninh)
    - Strategy A: Label Contrast (Top-1 Vulnerable + Top-1 Safe từ Security Ranker)
    """

    def __init__(self, retriever: SecurityAwareRetriever):
        self.retriever = retriever

    def select_pair(
        self, 
        query_sample: Dict[str, Any], 
        strategy: str = "counterexample_pair",
        top_candidates: int = 50
    ) -> Optional[ContrastivePair]:
        """
        Lựa chọn cặp mẫu (1 Lỗ hổng + 1 An toàn) tối ưu nhất cho hàm mục tiêu query_sample.
        """
        # 1. Lấy danh sách ứng viên Top-N từ Security-Aware Retriever
        retrieval_res = self.retriever.retrieve(
            query_sample, 
            top_candidates=top_candidates, 
            final_top_k=top_candidates
        )
        candidates = retrieval_res.get("top_candidates", [])
        if not candidates:
            return None
            
        # 2. Phân loại ứng viên thành 2 nhóm: Vulnerable (target=1) và Safe (target=0)
        vuln_cands = [c for c in candidates if c.get("target") == 1]
        safe_cands = [c for c in candidates if c.get("target") == 0]
        
        # Nếu thiếu 1 trong 2 nhóm trong Top-N, tìm tiếp trong toàn bộ tập train
        if not vuln_cands:
            for idx, s in enumerate(self.retriever.train_samples):
                if s.get("target") == 1:
                    vuln_cands.append({
                        "index": idx,
                        "id": s.get("id"),
                        "target": 1,
                        "security_score": 0.5,
                        "grace_score": 0.5
                    })
                    if len(vuln_cands) >= 5:
                        break
                        
        if not safe_cands:
            for idx, s in enumerate(self.retriever.train_samples):
                if s.get("target") == 0:
                    safe_cands.append({
                        "index": idx,
                        "id": s.get("id"),
                        "target": 0,
                        "security_score": 0.5,
                        "grace_score": 0.5
                    })
                    if len(safe_cands) >= 5:
                        break
                        
        if not vuln_cands or not safe_cands:
            return None
            
        # 3. Thực thi chiến lược chọn cặp
        if strategy == "counterexample_pair":
            return self._select_counterexample_pair(query_sample, vuln_cands, safe_cands)
        elif strategy == "minimal_security_diff":
            return self._select_minimal_diff_pair(query_sample, vuln_cands, safe_cands)
        else: # "label_contrast"
            return self._select_label_contrast_pair(query_sample, vuln_cands, safe_cands)

    def _select_counterexample_pair(
        self, 
        query_sample: Dict[str, Any], 
        vuln_cands: List[Dict[str, Any]], 
        safe_cands: List[Dict[str, Any]]
    ) -> ContrastivePair:
        """
        Strategy C (Khuyến nghị hàng đầu):
        Tối ưu hàm mục tiêu:
        Score_pair = SecSim(Target, Vuln) + SecSim(Target, Safe) + 0.5 * CodeSim(Vuln, Safe)
        -> Cặp mẫu vừa bám sát bài toán của Target, vừa có ngữ cảnh tương đồng cao với nhau
           để làm nổi bật sự khác biệt về kiểm tra an toàn.
        """
        best_pair = None
        best_score = -1.0
        
        # Duyệt qua các tổ hợp ứng viên tốt nhất (Top 10 mỗi bên để tối ưu thời gian)
        for v in vuln_cands[:10]:
            v_sample = self.retriever.train_samples[v["index"]]
            v_code = v_sample.get("func", "")
            v_sec = v.get("security_score", 0.5)
            
            for s in safe_cands[:10]:
                s_sample = self.retriever.train_samples[s["index"]]
                s_code = s_sample.get("func", "")
                s_sec = s.get("security_score", 0.5)
                
                # Tính độ tương đồng ngữ cảnh giữa 2 demo
                pair_code_sim = jaccard_similarity(v_code, s_code)
                
                # Điểm số kết hợp
                pair_score = v_sec + s_sec + (0.5 * pair_code_sim)
                
                if pair_score > best_score:
                    best_score = pair_score
                    diff_desc = self._identify_security_difference(v_sample, s_sample)
                    best_pair = ContrastivePair(
                        vulnerable_example=v_sample,
                        safe_example=s_sample,
                        vuln_security_score=round(v_sec, 4),
                        safe_security_score=round(s_sec, 4),
                        pair_code_similarity=round(pair_code_sim, 4),
                        security_critical_difference=diff_desc,
                        selection_strategy="counterexample_pair"
                    )
                    
        return best_pair

    def _select_minimal_diff_pair(
        self, 
        query_sample: Dict[str, Any], 
        vuln_cands: List[Dict[str, Any]], 
        safe_cands: List[Dict[str, Any]]
    ) -> ContrastivePair:
        """
        Strategy B: Chọn cặp có độ tương đồng cú pháp giữa chúng cao nhất (Minimal textual/AST diff).
        """
        best_pair = None
        max_sim = -1.0
        
        for v in vuln_cands[:10]:
            v_sample = self.retriever.train_samples[v["index"]]
            for s in safe_cands[:10]:
                s_sample = self.retriever.train_samples[s["index"]]
                sim = jaccard_similarity(v_sample.get("func", ""), s_sample.get("func", ""))
                if sim > max_sim:
                    max_sim = sim
                    diff_desc = self._identify_security_difference(v_sample, s_sample)
                    best_pair = ContrastivePair(
                        vulnerable_example=v_sample,
                        safe_example=s_sample,
                        vuln_security_score=round(v.get("security_score", 0.5), 4),
                        safe_security_score=round(s.get("security_score", 0.5), 4),
                        pair_code_similarity=round(sim, 4),
                        security_critical_difference=diff_desc,
                        selection_strategy="minimal_security_diff"
                    )
        return best_pair

    def _select_label_contrast_pair(
        self, 
        query_sample: Dict[str, Any], 
        vuln_cands: List[Dict[str, Any]], 
        safe_cands: List[Dict[str, Any]]
    ) -> ContrastivePair:
        """
        Strategy A: Lấy Top-1 Vulnerable và Top-1 Safe độc lập từ bảng xếp hạng an ninh.
        """
        top_v = vuln_cands[0]
        top_s = safe_cands[0]
        v_sample = self.retriever.train_samples[top_v["index"]]
        s_sample = self.retriever.train_samples[top_s["index"]]
        pair_sim = jaccard_similarity(v_sample.get("func", ""), s_sample.get("func", ""))
        diff_desc = self._identify_security_difference(v_sample, s_sample)
        
        return ContrastivePair(
            vulnerable_example=v_sample,
            safe_example=s_sample,
            vuln_security_score=round(top_v.get("security_score", 0.5), 4),
            safe_security_score=round(top_s.get("security_score", 0.5), 4),
            pair_code_similarity=round(pair_sim, 4),
            security_critical_difference=diff_desc,
            selection_strategy="label_contrast"
        )

    def _identify_security_difference(self, v_sample: Dict[str, Any], s_sample: Dict[str, Any]) -> str:
        """Tự động phân tích điểm khác biệt mấu chốt giữa mẫu Vulnerable và Safe."""
        v_sig = extract_security_signature(v_sample.get("func", ""), v_sample.get("nodes", []), v_sample.get("edges", []))
        s_sig = extract_security_signature(s_sample.get("func", ""), s_sample.get("nodes", []), s_sample.get("edges", []))
        
        diffs = []
        extra_sanitizers = s_sig.sanitizer_types - v_sig.sanitizer_types
        if extra_sanitizers:
            san_names = ", ".join(extra_sanitizers)
            diffs.append(f"Safe demo contains sanitization guards ({san_names}) absent in Vulnerable demo")
            
        if "unbounded_buffer_copy" in v_sig.vulnerability_clues and "unbounded_buffer_copy" not in s_sig.vulnerability_clues:
            diffs.append("Vulnerable demo performs unbounded memory copy without bounds check")
            
        if "unchecked_pointer_dereference" in v_sig.vulnerability_clues and "null_check" in s_sig.sanitizer_types:
            diffs.append("Safe demo validates pointers against NULL before dereferencing")
            
        if not diffs:
            diffs.append("Differences in bounds validation conditions and control flow constraints")
            
        return "; ".join(diffs)

    def annotate_dataset_contrastive(
        self, 
        test_samples: List[Dict[str, Any]], 
        strategy: str = "counterexample_pair",
        top_candidates: int = 50
    ) -> List[Dict[str, Any]]:
        """Gắn cặp mẫu tương phản hoàn chỉnh vào trường 'contrastive_pair' cho từng mẫu kiểm tra."""
        annotated = []
        for sample in test_samples:
            pair = self.select_pair(sample, strategy=strategy, top_candidates=top_candidates)
            sample_copy = dict(sample)
            if pair:
                sample_copy["contrastive_pair"] = pair.to_dict()
                sample_copy["contrastive_obj"] = pair
            annotated.append(sample_copy)
        return annotated
