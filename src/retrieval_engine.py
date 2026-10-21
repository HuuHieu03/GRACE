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
    Nếu một trong hai mẫu hoàn toàn thiếu đồ thị (0 nodes và 0 edges), trả về 0.0 để tránh thổi phồng điểm ảo.
    """
    if (not nodes1 and not edges1) or (not nodes2 and not edges2):
        return 0.0

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
    test_code = test_sample.get("func") or test_sample.get("code") or ""
    train_code = train_sample.get("func") or train_sample.get("code") or ""
    j_score = jaccard_similarity(test_code, train_code)
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
    def __init__(self, model_name: str = "Salesforce/codet5-base", use_fallback_default: Optional[bool] = None):
        self.model_name = model_name
        self.device = config.device
        self.tokenizer = None
        self.model = None
        self.tfidf_vectorizer = None

        if use_fallback_default is None:
            # Tự động nhận diện: Ưu tiên CodeT5 trên Kaggle GPU hoặc khi có CUDA;
            # Mặc định dùng TF-IDF fallback trên CPU local để kiểm thử siêu tốc không phụ thuộc mạng.
            try:
                import torch
                has_cuda = torch.cuda.is_available()
            except ImportError:
                has_cuda = False
            use_fallback_default = not (config.is_kaggle or has_cuda)

        self.is_fallback = use_fallback_default

        if not use_fallback_default:
            try:
                import torch
                from transformers import RobertaTokenizer, AutoTokenizer, AutoModel
                self.device = "cuda" if torch.cuda.is_available() else ("cpu" if config.device == "cpu" else config.device)
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
                self.is_fallback = False
                logger.info(f"✓ Nạp mô hình CodeT5 ({model_name}) thành công trên thiết bị {self.device} (768 chiều)!")
            except Exception as e:
                logger.warning(f"Không thể nạp CodeT5 ({e}). Chuyển sang Offline TF-IDF Embedder...")
                self.is_fallback = True
        else:
            logger.info("Kích hoạt chế độ TF-IDF Fallback Embedder (256 chiều).")
            self.is_fallback = True

        if self.is_fallback:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.tfidf_vectorizer = TfidfVectorizer(max_features=256, token_pattern=r"(?u)\b\w+\b")

    def fit(self, texts: List[str]):
        """Căn chỉnh vectorizer nếu ở chế độ fallback."""
        if self.is_fallback and self.tfidf_vectorizer:
            valid_texts = [t for t in texts if t and t.strip()]
            if not valid_texts:
                valid_texts = ["void fallback_dummy_function() { int x = 0; }"]
            self.tfidf_vectorizer.fit(valid_texts)

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
                if hasattr(self.model, "encoder") and hasattr(self.model, "decoder"):
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
    và re-rank theo Hybrid Score (0.7*Jaccard + 0.3*GraphSim).
    """
    def __init__(
        self, 
        embedder: Optional[CodeT5Embedder] = None,
        precomputed_embeddings_path: Optional[Any] = None
    ):
        if embedder is not None:
            self.embedder = embedder
        else:
            # Nếu không truyền embedder, tự động chọn fallback phù hợp với môi trường (CPU local test dùng fallback)
            fallback = not config.is_kaggle and config.device == "cpu"
            self.embedder = CodeT5Embedder(use_fallback_default=fallback)
        self.train_samples: List[Dict[str, Any]] = []
        self.train_vecs: Optional[np.ndarray] = None
        self.precomputed_embeddings_path = precomputed_embeddings_path

    def fit(
        self, 
        train_samples: List[Dict[str, Any]], 
        precomputed_embeddings: Optional[np.ndarray] = None
    ):
        """Khởi tạo chỉ mục tìm kiếm (Index database) từ tập huấn luyện."""
        from pathlib import Path
        logger.info(f"Đang xây dựng Index cho {len(train_samples)} mẫu huấn luyện...")
        self.train_samples = train_samples
        expected_dim = 256 if self.embedder.is_fallback else 768

        # 1. Kiểm tra precomputed_embeddings được truyền trực tiếp
        if precomputed_embeddings is not None:
            if len(precomputed_embeddings) == len(train_samples) and (precomputed_embeddings.shape[1] == expected_dim or not self.embedder.is_fallback):
                self.train_vecs = precomputed_embeddings.astype("float32")
                logger.info(f"✓ Đã nạp thành công ma trận embeddings truyền vào: {self.train_vecs.shape}")
                return
            else:
                logger.warning(
                    f"Kích thước/chiều precomputed_embeddings ({precomputed_embeddings.shape}) không khớp "
                    f"train_samples ({len(train_samples)}) hoặc embedder ({expected_dim}). Đang kiểm tra nguồn khác..."
                )

        # 2. Kiểm tra file precomputed_embeddings_path hoặc các vị trí mặc định
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
                        logger.info(f"✓ Đã nạp thành công ma trận vector từ {p}: {self.train_vecs.shape}")
                        return
                    elif len(emb) == len(train_samples) and emb.ndim == 2:
                        logger.warning(f"File {p} có chiều {emb.shape[1]} != expected {expected_dim} của embedder (fallback={self.embedder.is_fallback}).")
                    else:
                        logger.warning(f"File {p} có {len(emb)} vector != {len(train_samples)} mẫu train.")
                except Exception as e_load:
                    logger.warning(f"Không thể nạp file vector {p}: {e_load}")

        # 3. Trích xuất trực tiếp bằng embedder
        texts = [s.get("func") or s.get("code") or s.get("functionSource") or "" for s in train_samples]
        self.embedder.fit(texts)
        self.train_vecs = self.embedder.encode(texts)
        logger.info(f"Xây dựng xong Index ma trận vector với kích thước: {self.train_vecs.shape}")

        # Tự động lưu cache embeddings ra đĩa nếu tập train đủ lớn để tái sử dụng tức thì
        if len(self.train_samples) > 100:
            try:
                cache_file = Path("data/processed/devign_train_codet5_embeddings.npy")
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                np.save(str(cache_file), self.train_vecs)
                logger.info(f"✓ Đã lưu cache ma trận vector ({self.train_vecs.shape}) tại: {cache_file}")
            except Exception as e_cache:
                logger.debug(f"Không thể lưu cache embeddings: {e_cache}")

    def search_l2(self, query_vec: np.ndarray, top_k: int = 50) -> List[int]:
        """Tính khoảng cách L2 (Euclidean distance) giữa query và tất cả mẫu trong index."""
        if self.train_vecs is None or len(self.train_samples) == 0:
            return []
        
        # Đồng bộ chiều vector query nếu có sự lệch kích thước
        if query_vec.ndim == 1:
            q_dim = query_vec.shape[0]
            t_dim = self.train_vecs.shape[1]
            if q_dim != t_dim:
                if q_dim < t_dim:
                    padded = np.zeros(t_dim, dtype="float32")
                    padded[:q_dim] = query_vec
                    query_vec = padded
                else:
                    query_vec = query_vec[:t_dim]

        # L2 Euclidean norm = sqrt(sum((train_vecs - query_vec)^2))
        dists = np.linalg.norm(self.train_vecs - query_vec, axis=1)
        # Lấy chỉ số các phần tử có khoảng cách L2 nhỏ nhất
        top_k = min(top_k, len(self.train_samples))
        nearest_indices = np.argsort(dists)[:top_k].tolist()
        return nearest_indices

    def retrieve(self, query_sample: Dict[str, Any], top_k: int = 50) -> Dict[str, Any]:
        """
        Thực hiện chu trình hoàn chỉnh:
        1. Tạo embedding cho query code.
        2. Lọc Top-K ứng viên gần nhất theo khoảng cách L2.
        3. Tính điểm Hybrid Score (0.7*Jaccard + 0.3*Graph) cho Top-K ứng viên.
        4. Trả về ví dụ mẫu có điểm Hybrid Score cao nhất cùng thông tin chi tiết.
        """
        query_text = query_sample.get("func") or query_sample.get("code") or ""
        query_vec = self.embedder.encode([query_text])[0]
        
        # Lọc Top K bằng L2
        candidate_indices = self.search_l2(query_vec, top_k=top_k)
        
        candidates_info = []
        best_idx = -1
        max_score = -1.0
        
        for idx in candidate_indices:
            cand = self.train_samples[idx]
            h_score, j_score, g_score = compute_hybrid_score(query_sample, cand)
            cand_code = cand.get("func") or cand.get("code") or ""
            candidates_info.append({
                "index": idx,
                "id": cand.get("id"),
                "target": cand.get("target"),
                "hybrid_score": h_score,
                "jaccard_score": j_score,
                "graph_score": g_score,
                "func_snippet": cand_code[:100] + "..."
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
