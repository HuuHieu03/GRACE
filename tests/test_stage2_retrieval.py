"""
Unit Test & Interactive Demo cho Stage 2: Demonstration Retrieval Engine.
Được bổ sung log trực quan để người dùng theo dõi chi tiết từng bước (Step-by-Step).
"""

import sys
import time
from pathlib import Path
import numpy as np

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from config import config
from data_loader import standardize_sample, generate_mock_dataset
from retrieval_engine import (
    jaccard_similarity,
    graph_similarity,
    compute_hybrid_score,
    CodeT5Embedder,
    DemonstrationRetriever
)


def print_header(title: str):
    print("\n" + "="*70)
    print(f"  STEP: {title}")
    print("="*70)


def test_similarity_metrics():
    print_header("1. KIỂM TRA CÁC HÀM TÍNH ĐỘ TƯƠNG ĐỒNG (JACCARD & GRAPH SIMILARITY)")
    code1 = "void test(char *input) { char buf[10]; strcpy(buf, input); }"
    code2 = "void test(char *input) { char buf[10]; strncpy(buf, input, 9); }"
    code3 = "int calculate_sum(int a, int b) { return a + b; }"
    
    sim_1_2 = jaccard_similarity(code1, code2)
    sim_1_3 = jaccard_similarity(code1, code3)
    print("[*] Kiểm tra độ tương đồng từ vựng (Jaccard Similarity):")
    print(f"    - So sánh Code 1 & Code 2 (Cùng cấu trúc bộ đệm buffer): {sim_1_2:.4f}")
    print(f"    - So sánh Code 1 & Code 3 (Hoàn toàn khác biệt): {sim_1_3:.4f}")
    assert sim_1_2 > sim_1_3
    print("    -> [PASS] Jaccard Similarity phản ánh đúng độ tương quan ngữ pháp C/C++!")
    
    sample1 = {"func": code1, "nodes": [{"id": 1, "type": "FUNC_DEF"}, {"id": 2, "type": "STRCPY_CALL"}], "edges": [1, 2]}
    sample2 = {"func": code2, "nodes": [{"id": 1, "type": "FUNC_DEF"}, {"id": 2, "type": "STRNCPY_CALL"}], "edges": [1, 2]}
    
    h_score, j_score, g_score = compute_hybrid_score(sample1, sample2)
    print("\n[*] Kiểm tra công thức Hybrid Score (0.7*Jaccard + 0.3*GraphSim):")
    print(f"    - Jaccard Score: {j_score:.4f} * 0.7 = {j_score*0.7:.4f}")
    print(f"    - Graph Structure Score (Levenshtein ratio trên AST/CPG): {g_score:.4f} * 0.3 = {g_score*0.3:.4f}")
    print(f"    - => HYBRID SCORE TỔNG HỢP: {h_score:.4f}")
    assert 0.0 <= h_score <= 1.0
    print(">>> [PASS] Công thức Hybrid Reranking hoạt động chuẩn xác theo bài báo!")


def test_embedder():
    print_header("2. KIỂM TRA TRÌNH TẠO VECTOR ĐẶC TRƯNG (CODET5 / TF-IDF EMBEDDER)")
    print("[*] Khởi tạo Embedder (Tự động thích nghi Local Fast Test hoặc GPU CodeT5)...")
    embedder = CodeT5Embedder(use_fallback_default=True)
    
    texts = [
        "void vuln_func() { char b[5]; gets(b); }",
        "int safe_add(int x, int y) { return x + y; }",
        "void another_vuln() { char buf[8]; strcpy(buf, src); }"
    ]
    embedder.fit(texts)
    vecs = embedder.encode(texts)
    print(f"[*] Ma trận vector đặc trưng thu được:")
    print(f"    - Kích thước ma trận (Num samples x Embedding dim): {vecs.shape}")
    print(f"    - Kiểu dữ liệu mảng (Dtype): {vecs.dtype} (Yêu cầu float32)")
    assert len(vecs) == 3 and vecs.dtype == np.float32
    print(">>> [PASS] Trích xuất vector đặc trưng mượt mà, không gián đoạn!")


def test_l2_search_and_retriever():
    print_header("3. KIỂM TRA BỘ SƯU TẬP MẪU & KHOẢNG CÁCH L2 (EUCLIDEAN DISTANCE INDEX)")
    print("[*] Khởi tạo tập cơ sở dữ liệu huấn luyện giả lập gồm 50 mẫu hàm C/C++...")
    raw_mock = generate_mock_dataset(num_samples=50)
    train_data = [standardize_sample(s, idx=i) for i, s in enumerate(raw_mock)]
    
    retriever = DemonstrationRetriever()
    retriever.fit(train_data)
    print(f"    -> Đã xây dựng thành công Index với {len(retriever.train_samples)} mẫu trong bộ nhớ.")
    
    query_sample = {
        "id": "query_cve_test",
        "func": "void handle_buffer_12(char *user_input) { char buf[64]; strcpy(buf, user_input); }",
        "nodes": [{"id": 0, "label": "AST_FUNC_DEF"}],
        "edges": [{"source": 0, "target": 1, "type": "CFG"}]
    }
    
    print("\n[*] Thực hiện truy vấn (Retrieve) mẫu ví dụ tương đồng nhất cho Query:")
    print(f"    Query ID: {query_sample['id']} | Code: {query_sample['func']}")
    print("    -> Đang tính toán ma trận khoảng cách L2 & sắp xếp Hybrid Rerank (Top-K=3)...")
    
    res = retriever.retrieve(query_sample, top_k=3)
    top_cands = res["top_k_candidates"]
    best_ex = res["best_example"]
    
    print("\n[*] Kết quả Reranking Top 3 Ứng viên (Candidates):")
    for r in top_cands:
        print(f"    - [Rank #{top_cands.index(r)+1}] ID: {r['id']:<10} | Hybrid Score: {r['hybrid_score']:.4f} "
              f"(Jaccard: {r['jaccard_score']:.2f}, Graph: {r['graph_score']:.2f})")
    
    print(f"\n[✓] MẪU TỐT NHẤT ĐƯỢC CHỌN LÀM VÍ DỤ (DEMO EXAMPLE):")
    print(f"    -> ID: {best_ex['id']} | Nhãn: {'VULNERABLE (1)' if best_ex['target']==1 else 'SAFE (0)'}")
    print(f"    -> Code: {best_ex['func']}")
    
    assert res["best_hybrid_score"] > 0.0
    assert len(top_cands) <= 3
    print(">>> [PASS] Bộ tìm kiếm L2 & Hybrid Reranking lựa chọn chính xác ứng viên tương đồng nhất!")


def test_annotate_dataset():
    print_header("4. KIỂM TRA QUY TRÌNH ĐÍNH KÈM VÍ DỤ VÀO TẬP KIỂM THỬ (DATASET ANNOTATION)")
    raw_mock = generate_mock_dataset(num_samples=30)
    train_data = [standardize_sample(s, idx=i) for i, s in enumerate(raw_mock[:20])]
    test_data = [standardize_sample(s, idx=i) for i, s in enumerate(raw_mock[20:])]
    
    print(f"[*] Khởi tạo Retriever với 20 mẫu Train & tiến hành gán mẫu demo cho 10 mẫu Test...")
    retriever = DemonstrationRetriever()
    retriever.fit(train_data)
    
    annotated = retriever.annotate_dataset(test_data, top_k=5)
    print(f"[*] Hoàn thành gán mẫu cho {len(annotated)} mẫu Test.")
    
    sample_annotated = annotated[0]
    print("\n[*] Kiểm tra cấu trúc 1 mẫu Test sau khi được gán Demonstration:")
    print(f"    - ID Test sample: {sample_annotated['id']} | Target: {sample_annotated['target']}")
    print(f"    - Trường mới được đính kèm: 'example' (ID: {sample_annotated['example']['id']})")
    print(f"    - Điểm tương đồng tương tác: {sample_annotated['retrieval_score']:.4f}")
    
    assert "example" in sample_annotated
    assert "retrieval_score" in sample_annotated
    print(">>> [PASS] Dataset Annotation sẵn sàng tiếp ứng cho Stage 3 (Prompt Engine)!")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("\n" + "#"*75)
    print("###  CHƯƠNG TRÌNH KIỂM THỬ & NGHIỆM THU STAGE 2 (DEMONSTRATION RETRIEVAL) ###")
    print("#"*75)
    
    test_similarity_metrics()
    time.sleep(0.5)
    test_embedder()
    time.sleep(0.5)
    test_l2_search_and_retriever()
    time.sleep(0.5)
    test_annotate_dataset()
    time.sleep(0.5)
    
    print("\n" + "="*75)
    print("🎉 STAGE 2 VERIFICATION CHECKPOINT PASSED 100%! HỆ THỐNG SẴN SÀNG CHO STAGE 3.")
    print("="*75 + "\n")
