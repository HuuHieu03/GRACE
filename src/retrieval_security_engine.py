"""
Vulnerability-Aware Demonstration Retrieval Engine (Stage 5)
Nâng cấp toàn diện cơ chế truy xuất mẫu của GRACE:
1. Candidate Discovery: Dùng CodeT5 Embedder + L2 Distance để lọc nhanh Top-N ứng viên tiềm năng (N = 50~100).
2. Security Signature Analysis: Trích xuất Taint Source, Sink, Sanitizers và Memory Ops cho Query và Candidates.
3. Vulnerability-Aware Reranking: Kết hợp $Score_{final} = \\lambda \\cdot Score_{GRACE} + (1 - \\lambda) \\cdot Score_{security}$.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from config import config
from retrieval_engine import (
    CodeT5Embedder, 
    compute_hybrid_score, 
    jaccard_similarity, 
    graph_similarity
)
from security_signature.extractor import extract_security_signature
from security_signature.similarity import compute_security_signature_similarity
from security_signature.schema import SecuritySignature

logger = logging.getLogger("SecurityRetrievalEngine")


class SecurityAwareRetriever:
    """
    Bộ tìm kiếm và tái xếp hạng mẫu dựa trên cơ chế bảo mật (Security-Aware Retriever).
    Đảm bảo tính chính xác cao về mặt an ninh (Security Relevance) thay vì chỉ nhìn vào bề mặt mã nguồn.
    """
    def __init__(
        self, 
        embedder: Optional[CodeT5Embedder] = None, 
        lambda_weight: float = 0.3,
        precomputed_embeddings_path: Optional[Any] = None
    ):
        """
        Args:
            embedder: Trình trích xuất vector CodeT5 (hoặc TF-IDF fallback).
            lambda_weight: Trọng số cân bằng giữa Code/Graph Similarity (Score_GRACE) 
                           và Security Similarity (Score_security). Mặc định 0.3 (70% ưu tiên an ninh).
            precomputed_embeddings_path: Đường dẫn tới file .npy chứa vector đặc trưng tiền tính toán.
        """
        self.embedder = embedder if embedder else CodeT5Embedder()
        self.lambda_weight = lambda_weight
        self.precomputed_embeddings_path = precomputed_embeddings_path
        self.train_samples: List[Dict[str, Any]] = []
        self.train_vecs: Optional[np.ndarray] = None
        self.train_signatures: List[SecuritySignature] = []
        self._signature_cache: Dict[int, SecuritySignature] = {}

    def fit(
        self, 
        train_samples: List[Dict[str, Any]], 
        precomputed_embeddings: Optional[np.ndarray] = None,
        precompute_signatures: bool = False
    ):
        """
        Khởi tạo chỉ mục cơ sở dữ liệu huấn luyện:
        1. Xây dựng hoặc nạp ma trận vector nhúng CodeT5.
        2. Tùy chọn tiền trích xuất Security Signature (mặc định trích xuất theo nhu cầu cho Top-K ứng viên để tiết kiệm tài nguyên).
        """
        from pathlib import Path
        logger.info(f"Đang xây dựng Security Index cho {len(train_samples)} mẫu huấn luyện...")
        self.train_samples = train_samples
        self._signature_cache.clear()
        expected_dim = 256 if self.embedder.is_fallback else 768

        # 1. Kiểm tra precomputed_embeddings truyền trực tiếp
        if precomputed_embeddings is not None:
            if len(precomputed_embeddings) == len(train_samples) and (precomputed_embeddings.shape[1] == expected_dim or not self.embedder.is_fallback):
                self.train_vecs = precomputed_embeddings.astype("float32")
                logger.info(f"✓ Nạp ma trận embeddings truyền vào: {self.train_vecs.shape}")

        # 2. Kiểm tra file precomputed_embeddings_path hoặc các đường dẫn chuẩn
        if self.train_vecs is None:
            candidates_to_try = []
            if self.precomputed_embeddings_path:
                candidates_to_try.append(Path(str(self.precomputed_embeddings_path)))
            candidates_to_try.extend([
                Path("data/processed/devign_train_codet5_embeddings.npy"),
                Path("/kaggle/input/grace-devign-train-cpg/devign_train_codet5_embeddings.npy"),
                Path("/kaggle/input/devign-train-codet5-embeddings/devign_train_codet5_embeddings.npy"),
            ])
            for p in candidates_to_try:
                if p.exists() and p.stat().st_size > 1000:
                    try:
                        emb = np.load(str(p))
                        if len(emb) == len(train_samples) and emb.ndim == 2 and (emb.shape[1] == expected_dim or not self.embedder.is_fallback):
                            self.train_vecs = emb.astype("float32")
                            logger.info(f"✓ Nạp thành công vector nhúng từ file: {p} ({self.train_vecs.shape})")
                            break
                    except Exception as e:
                        logger.debug(f"Không thể nạp file vector {p}: {e}")

        # 3. Nếu chưa có vector, tính toán trực tiếp qua embedder
        if self.train_vecs is None:
            texts = [s.get("func", "") for s in train_samples]
            self.embedder.fit(texts)
            self.train_vecs = self.embedder.encode(texts)
        
        if precompute_signatures:
            logger.info("Đang tiền trích xuất Security Signatures cho tập huấn luyện...")
            self.train_signatures = []
            for s in train_samples:
                sig = extract_security_signature(
                    code=s.get("func", ""),
                    nodes=s.get("nodes", s.get("node", [])),
                    edges=s.get("edges", s.get("edge", []))
                )
                self.train_signatures.append(sig)
        else:
            self.train_signatures = []
            
        logger.info(f"✓ Hoàn tất xây dựng Security Index: Vector Shape={self.train_vecs.shape}, Signatures={len(self.train_signatures)}")

    def search_candidates_l2(self, query_vec: np.ndarray, top_n: int = 50) -> List[int]:
        """Lọc nhanh Top-N ứng viên gần nhất trong không gian vector nhúng bằng khoảng cách L2."""
        if self.train_vecs is None or len(self.train_samples) == 0:
            return []
        dists = np.linalg.norm(self.train_vecs - query_vec, axis=1)
        top_n = min(top_n, len(self.train_samples))
        nearest_indices = np.argsort(dists)[:top_n].tolist()
        return nearest_indices

    def retrieve(
        self, 
        query_sample: Dict[str, Any], 
        top_candidates: int = 50, 
        final_top_k: int = 5,
        lambda_weight: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Thực hiện chu trình truy xuất và tái xếp hạng mẫu an ninh hoàn chỉnh:
        1. Trích xuất vector cho Query Code.
        2. Lấy Top-N ứng viên bằng CodeT5 L2 search (Candidate Pool).
        3. Trích xuất Security Signature của Query.
        4. Tính toán đồng thời Score_GRACE và Score_security cho từng ứng viên.
        5. Tái xếp hạng theo Score_final = lambda * Score_GRACE + (1 - lambda) * Score_security.
        6. Trả về kết quả tối ưu nhất.
        """
        lam = self.lambda_weight if lambda_weight is None else lambda_weight
        query_text = query_sample.get("func", "")
        query_vec = self.embedder.encode([query_text])[0]
        
        # 1. Trích xuất Security Signature cho Query
        query_sig = extract_security_signature(
            code=query_text,
            nodes=query_sample.get("nodes", query_sample.get("node", [])),
            edges=query_sample.get("edges", query_sample.get("edge", []))
        )
        
        # 2. Lọc Top-N Candidates
        candidate_indices = self.search_candidates_l2(query_vec, top_n=top_candidates)
        
        ranked_candidates = []
        for idx in candidate_indices:
            cand = self.train_samples[idx]
            
            # Tính GRACE hybrid score (0.7 Jaccard + 0.3 GraphSim)
            grace_score, j_score, g_score = compute_hybrid_score(query_sample, cand)
            
            # Lấy hoặc trích xuất Security Signature của ứng viên
            if idx in self._signature_cache:
                cand_sig = self._signature_cache[idx]
            elif idx < len(self.train_signatures) and self.train_signatures:
                cand_sig = self.train_signatures[idx]
            else:
                cand_sig = extract_security_signature(
                    code=cand.get("func", ""),
                    nodes=cand.get("nodes", cand.get("node", [])),
                    edges=cand.get("edges", cand.get("edge", []))
                )
                self._signature_cache[idx] = cand_sig
                
            # Tính Security Similarity
            sec_score, sub_scores = compute_security_signature_similarity(query_sig, cand_sig)
            
            # Tính Score_final
            final_score = (lam * grace_score) + ((1.0 - lam) * sec_score)
            
            ranked_candidates.append({
                "index": idx,
                "id": cand.get("id"),
                "target": cand.get("target"),
                "final_score": round(final_score, 4),
                "security_score": round(sec_score, 4),
                "grace_score": round(grace_score, 4),
                "jaccard_score": round(j_score, 4),
                "graph_score": round(g_score, 4),
                "sub_scores": sub_scores,
                "candidate_signature": cand_sig.to_dict(),
                "func_snippet": cand.get("func", "")[:120] + "..."
            })
            
        # Sắp xếp giảm dần theo final_score
        ranked_candidates.sort(key=lambda x: x["final_score"], reverse=True)
        
        top_k_results = ranked_candidates[:final_top_k]
        best_candidate_info = top_k_results[0] if top_k_results else None
        best_example = self.train_samples[best_candidate_info["index"]] if best_candidate_info else {}
        
        return {
            "query_signature": query_sig.to_dict(),
            "best_example": best_example,
            "best_final_score": best_candidate_info["final_score"] if best_candidate_info else 0.0,
            "best_security_score": best_candidate_info["security_score"] if best_candidate_info else 0.0,
            "best_grace_score": best_candidate_info["grace_score"] if best_candidate_info else 0.0,
            "top_candidates": top_k_results,
            "total_candidates_evaluated": len(ranked_candidates)
        }

    def annotate_dataset(
        self, 
        test_samples: List[Dict[str, Any]], 
        top_candidates: int = 50, 
        final_top_k: int = 5,
        lambda_weight: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Gắn mẫu ví dụ bảo mật tốt nhất và các siêu dữ liệu an ninh vào từng mẫu kiểm tra."""
        annotated = []
        for sample in test_samples:
            res = self.retrieve(
                sample, 
                top_candidates=top_candidates, 
                final_top_k=final_top_k, 
                lambda_weight=lambda_weight
            )
            sample_copy = dict(sample)
            sample_copy["example"] = res["best_example"]
            sample_copy["security_signature"] = res["query_signature"]
            sample_copy["retrieval_final_score"] = res["best_final_score"]
            sample_copy["retrieval_security_score"] = res["best_security_score"]
            sample_copy["retrieval_grace_score"] = res["best_grace_score"]
            sample_copy["top_ranked_candidates"] = res["top_candidates"]
            annotated.append(sample_copy)
        return annotated
