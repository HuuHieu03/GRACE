"""
GRACE Demonstration Retrieval Engine (Stage 2)
Thay thế hoàn toàn `genexample.py` cũ.
Tích hợp CodeT5 embedding, tìm kiếm ứng viên bằng khoảng cách L2 (Euclidean Distance),
và cơ chế sắp xếp lại kép (Hybrid Reranking: 0.7*Jaccard + 0.3*GraphSim).
"""

import math
import logging
import difflib
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def jaccard_similarity(code1: str, code2: str) -> float:
    """Tính độ tương đồng từ vựng Jaccard giữa hai đoạn mã nguồn C/C++."""
    tokens1 = set(code1.split())
    tokens2 = set(code2.split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / float(len(union))


def graph_similarity(nodes1: List[Any], edges1: List[Any], nodes2: List[Any], edges2: List[Any]) -> float:
    """
    Tính độ tương đồng cấu trúc đồ thị (AST/CPG) giữa hai mẫu.
    Sử dụng difflib.SequenceMatcher.ratio() trên chuỗi tuần tự hóa đồ thị (tương đương Levenshtein Ratio)
    để đảm bảo tính kiên cố, không phụ thuộc vào gói thư viện bên thứ 3 dễ lỗi.
    """
    def serialize_graph(nodes, edges) -> str:
        n_str = "_".join([str(n.get("type", n.get("label", n.get("id", "")))) if isinstance(n, dict) else str(n) for n in nodes[:30]])
        e_str = f"|E:{len(edges)}|"
        return f"N:{len(nodes)}_{n_str}{e_str}"
        
    str1 = serialize_graph(nodes1, edges1)
    str2 = serialize_graph(nodes2, edges2)
    return difflib.SequenceMatcher(None, str1, str2).ratio()


def compute_hybrid_score(test_sample: Dict[str, Any], train_sample: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Tính điểm số tương đồng tổng hợp dựa theo công thức trong bài báo GRACE:
    Score = 0.7 * Jaccard_Code + 0.3 * Sim_Graph
    Returns: (hybrid_score, jaccard_score, graph_score)
    """
    j_score = jaccard_similarity(test_sample.get("func", ""), train_sample.get("func", ""))
    g_score = graph_similarity(
        test_sample.get("nodes", []), test_sample.get("edges", []),
        train_sample.get("nodes", []), train_sample.get("edges", [])
    )
    hybrid_score = (0.7 * j_score) + (0.3 * g_score)
    return hybrid_score, j_score, g_score


class CodeT5Embedder:
    """
    Trình nạp mô hình CodeT5 để trích xuất vector nhúng ngữ nghĩa cho đoạn code C/C++.
    Có cơ chế tự động chuyển đổi sang TF-IDF Fallback nếu máy offline hoặc khi test nhanh trên CPU.
    """
    def __init__(self, model_name: str = "Salesforce/codet5-base", use_fallback_default: bool = False):
        self.model_name = model_name
        self.device = config.device
        self.is_fallback = use_fallback_default
        self.tokenizer = None
        self.model = None
        self.tfidf_vectorizer = None

        if not use_fallback_default and config.is_kaggle:
            try:
                import torch
                from transformers import RobertaTokenizer, AutoTokenizer, AutoModel
                logger.info(f"Đang nạp mô hình {model_name} trên thiết bị {self.device}...")
                
                # Khắc phục triệt để lỗi `extra_special_tokens: null` trong tokenizer_config.json của Salesforce/codet5-base
                tokenizer_loaded = False
                
                # Chiến lược 1: Tải trực tiếp vocab.json và merges.txt (Bỏ qua hoàn toàn file tokenizer_config.json bị lỗi)
                try:
                    from huggingface_hub import hf_hub_download
                    v_file = hf_hub_download(repo_id=model_name, filename="vocab.json")
                    m_file = hf_hub_download(repo_id=model_name, filename="merges.txt")
                    self.tokenizer = RobertaTokenizer(vocab_file=v_file, merges_file=m_file)
                    tokenizer_loaded = True
                    logger.info("Khởi tạo RobertaTokenizer thành công từ direct vocab/merges.")
                except Exception as e_direct:
                    logger.debug(f"Direct vocab load failed: {e_direct}")

                # Chiến lược 2: Ghi đè extra_special_tokens=[] trong RobertaTokenizer.from_pretrained
                if not tokenizer_loaded:
                    try:
                        self.tokenizer = RobertaTokenizer.from_pretrained(model_name, extra_special_tokens=[], use_fast=False)
                        tokenizer_loaded = True
                        logger.info("Khởi tạo RobertaTokenizer thành công với extra_special_tokens=[].")
                    except Exception as e_rob:
                        logger.debug(f"RobertaTokenizer override failed: {e_rob}")

                # Chiến lược 3: AutoTokenizer với extra_special_tokens=[]
                if not tokenizer_loaded:
                    self.tokenizer = AutoTokenizer.from_pretrained(model_name, extra_special_tokens=[], use_fast=False)

                # Đảm bảo các token điều khiển cơ bản tồn tại
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = "<pad>"
                if self.tokenizer.bos_token is None:
                    self.tokenizer.bos_token = "<s>"
                if self.tokenizer.eos_token is None:
                    self.tokenizer.eos_token = "</s>"

                # Nạp Encoder để trích xuất embedding tối ưu bộ nhớ GPU
                try:
                    from transformers import T5EncoderModel
                    self.model = T5EncoderModel.from_pretrained(model_name).to(self.device)
                except Exception:
                    self.model = AutoModel.from_pretrained(model_name).to(self.device)

                self.model.eval()
                logger.info(f"✓ Nạp mô hình CodeT5 ({model_name}) thành công trên thiết bị {self.device}!")
            except Exception as e:
                logger.warning(f"Không thể nạp CodeT5 ({e}). Chuyển sang Offline TF-IDF Embedder...")
                self.is_fallback = True
        else:
            logger.info("Môi trường Local/Test: Kích hoạt chế độ TF-IDF Fast Embedder để tối ưu tốc độ kiểm thử.")
            self.is_fallback = True

        if self.is_fallback:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.tfidf_vectorizer = TfidfVectorizer(max_features=256, token_pattern=r"(?u)\b\w+\b")

    def fit(self, texts: List[str]):
        """Căn chỉnh vectorizer nếu ở chế độ fallback."""
        if self.is_fallback and self.tfidf_vectorizer:
            self.tfidf_vectorizer.fit(texts)

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Trích xuất ma trận vector đặc trưng cho danh sách chuỗi mã nguồn."""
        if not texts:
            return np.empty((0, 768 if not self.is_fallback else 256), dtype="float32")
            
        if self.is_fallback:
            return self.tfidf_vectorizer.transform(texts).toarray().astype("float32")
            
        import torch
        vecs = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                cleaned = [t if (t and t.strip()) else " " for t in batch_texts]
                inputs = self.tokenizer(cleaned, padding=True, max_length=512, truncation=True, return_tensors="pt").to(self.device)
                if hasattr(self.model, "encoder"):
                    outputs = self.model.encoder(**inputs)
                else:
                    outputs = self.model(**inputs)
                mask = inputs["attention_mask"].unsqueeze(-1)
                sum_embeds = torch.sum(outputs.last_hidden_state * mask, dim=1)
                sum_mask = torch.clamp(mask.sum(dim=1), min=1e-9)
                embeds = (sum_embeds / sum_mask).cpu().numpy().astype("float32")
                vecs.append(embeds)
        return np.vstack(vecs)


class DemonstrationRetriever:
    """
    Bộ tìm kiếm & re-rank ví dụ mẫu (Demonstration Retrieval Engine).
    Quản lý tập mẫu huấn luyện (Train database), tính khoảng cách L2 để lọc Top-K, 
    và re-rank theo Hybrid Score.
    """
    def __init__(self, embedder: Optional[CodeT5Embedder] = None):
        self.embedder = embedder if embedder else CodeT5Embedder()
        self.train_samples: List[Dict[str, Any]] = []
        self.train_vecs: Optional[np.ndarray] = None

    def fit(self, train_samples: List[Dict[str, Any]]):
        """Khởi tạo chỉ mục tìm kiếm (Index database) từ tập huấn luyện."""
        logger.info(f"Đang xây dựng Index cho {len(train_samples)} mẫu huấn luyện...")
        self.train_samples = train_samples
        texts = [s.get("func", "") for s in train_samples]
        self.embedder.fit(texts)
        self.train_vecs = self.embedder.encode(texts)
        logger.info(f"Xây dựng xong Index ma trận vector với kích thước: {self.train_vecs.shape}")

    def search_l2(self, query_vec: np.ndarray, top_k: int = 5) -> List[int]:
        """Tính khoảng cách L2 (Euclidean distance) giữa query và tất cả mẫu trong index."""
        if self.train_vecs is None or len(self.train_samples) == 0:
            return []
        # L2 Euclidean norm = sqrt(sum((train_vecs - query_vec)^2))
        dists = np.linalg.norm(self.train_vecs - query_vec, axis=1)
        # Lấy chỉ số các phần tử có khoảng cách L2 nhỏ nhất
        top_k = min(top_k, len(self.train_samples))
        nearest_indices = np.argsort(dists)[:top_k].tolist()
        return nearest_indices

    def retrieve(self, query_sample: Dict[str, Any], top_k: int = 5) -> Dict[str, Any]:
        """
        Thực hiện chu trình hoàn chỉnh:
        1. Tạo embedding cho query code.
        2. Lọc Top-K ứng viên gần nhất theo khoảng cách L2.
        3. Tính điểm Hybrid Score (0.7*Jaccard + 0.3*Graph) cho Top-K ứng viên.
        4. Trả về ví dụ mẫu có điểm Hybrid Score cao nhất cùng thông tin chi tiết.
        """
        query_text = query_sample.get("func", "")
        query_vec = self.embedder.encode([query_text])[0]
        
        # Lọc Top K bằng L2
        candidate_indices = self.search_l2(query_vec, top_k=top_k)
        
        candidates_info = []
        best_idx = -1
        max_score = -1.0
        
        for idx in candidate_indices:
            cand = self.train_samples[idx]
            h_score, j_score, g_score = compute_hybrid_score(query_sample, cand)
            candidates_info.append({
                "index": idx,
                "id": cand.get("id"),
                "target": cand.get("target"),
                "hybrid_score": h_score,
                "jaccard_score": j_score,
                "graph_score": g_score,
                "func_snippet": cand.get("func", "")[:100] + "..."
            })
            if h_score > max_score:
                max_score = h_score
                best_idx = idx
                
        best_example = self.train_samples[best_idx] if best_idx != -1 else {}
        return {
            "best_example": best_example,
            "best_hybrid_score": max_score,
            "top_k_candidates": sorted(candidates_info, key=lambda x: x["hybrid_score"], reverse=True)
        }

    def annotate_dataset(self, test_samples: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Gắn trực tiếp mẫu ví dụ tốt nhất vào trường 'example' cho từng mẫu kiểm tra."""
        annotated = []
        for sample in test_samples:
            res = self.retrieve(sample, top_k=top_k)
            sample_copy = dict(sample)
            sample_copy["example"] = res["best_example"]
            sample_copy["retrieval_score"] = res["best_hybrid_score"]
            annotated.append(sample_copy)
        return annotated
