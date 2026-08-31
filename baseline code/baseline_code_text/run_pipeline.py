"""
GRACE End-to-End Orchestration CLI (Stage 4)
Đầu não điều phối toàn bộ quy trình tái thiết kế và chạy thực nghiệm phương pháp GRACE:
Phase 1: Nạp & chuẩn hóa dữ liệu từ Hugging Face / Mock (với Stratified Slicing).
Phase 2: Xây dựng Index L2 & Tìm kiếm ví dụ mẫu Reranking (Demonstration Retrieval Engine).
Phase 3: Đánh giá mô hình bằng LLM (Resilient Evaluator với JSONL Checkpointing).
Phase 4: Đo đạc chỉ số F1-Score/Confusion Matrix & Xuất báo cáo nghiệm thu ra thư mục output/.
"""

import sys
import os
import io

# Tối ưu hoá bộ nhớ PyTorch (Chống phân mảnh VRAM)
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"

import json
import time
import logging
import argparse
from pathlib import Path

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Đảm bảo import đúng trong PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from config import config
from data_loader import load_hf_dataset, generate_mock_dataset, standardize_sample
from retrieval_engine import DemonstrationRetriever
from evaluator import LLMEvaluator
from metrics import print_metrics_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("GRACE-Orchestrator")


def run_grace_pipeline(
    dataset_name: str = "DetectVul/devign",
    sample_ratio: float = 0.05,
    experiment_name: str = "grace_run",
    model_name: str = config.default_llm_model,
    use_mock: bool = False,
    top_k_demo: int = 5,
    seed: int = 42
):
    start_time = time.time()
    print("\n" + "#" * 75)
    print("###  GRACE VULNERABILITY DETECTION - END-TO-END ORCHESTRATION PIPELINE  ###")
    print("#" * 75)
    print(f"[*] Experiment Name  : {experiment_name}")
    print(f"[*] Target Dataset   : {dataset_name} (Sample Ratio: {sample_ratio * 100:.1f}%)")
    print(f"[*] Execution Mode   : {'Mock/Local Test (CPU/Fast)' if use_mock else f'Full Open-Weights LLM ({model_name} on GPU)'}")
    print(f"[*] Checkpoint Dir   : {config.checkpoint_dir}")
    print(f"[*] Output Dir       : {config.output_dir}")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # PHASE 1: DATA INGESTION & STRATIFIED SLICING
    # -------------------------------------------------------------------------
    print("\n>>> [PHASE 1] NẠP DỮ LIỆU & BÓC TÁCH MẨU KHẢO SÁT CÂN BẰNG NHÃN (STRATIFIED SLICING)...")
    if use_mock or dataset_name.lower() == "mock":
        logger.info("Chế độ Mock được kích hoạt: Khởi tạo dữ liệu giả lập chất lượng cao...")
        raw_train = generate_mock_dataset(num_samples=50)
        raw_test = generate_mock_dataset(num_samples=20)
        train_samples = [standardize_sample(s, idx=i) for i, s in enumerate(raw_train)]
        test_samples = [standardize_sample(s, idx=i) for i, s in enumerate(raw_test)]
    else:
        logger.info(f"Đang kết nối tải dataset '{dataset_name}' từ Hugging Face Hub...")
        train_samples = load_hf_dataset(dataset_name=dataset_name, split="train", sample_ratio=sample_ratio, seed=seed)
        test_samples = load_hf_dataset(dataset_name=dataset_name, split="test", sample_ratio=sample_ratio, seed=seed)
        
    logger.info(f"Hoàn tất chuẩn bị dữ liệu -> Train index: {len(train_samples)} mẫu | Test eval: {len(test_samples)} mẫu.")

    # -------------------------------------------------------------------------
    # PHASE 2: DEMONSTRATION INDEXING & HYBRID RERANKING
    # -------------------------------------------------------------------------
    print("\n>>> [PHASE 2] XÂY DỰNG INDEX L2 & GÁN MẪU VÍ DỤ DEMONSTRATION (HYBRID RERANKING)...")
    retriever = DemonstrationRetriever()
    retriever.fit(train_samples)
    
    logger.info(f"Đang tiến hành truy xuất và gán mẫu In-Context Demonstration cho {len(test_samples)} mẫu Test...")
    annotated_test = retriever.annotate_dataset(test_samples, top_k=top_k_demo)
    logger.info("Hoàn tất quy trình Retrieval Engine. Tự động gán trường 'example' cho 100% mẫu kiểm thử.")

    # -------------------------------------------------------------------------
    # PHASE 3: RESILIENT LLM EVALUATION (WITH JSONL CHECKPOINTING)
    # -------------------------------------------------------------------------
    print("\n>>> [PHASE 3] THỰC THI SUY LUẬN AI EVALUATOR & TỰ PHỤC HỒI CHECKPOINTING...")
    evaluator = LLMEvaluator(model_name=model_name, use_mock=use_mock)
    
    results, metrics = evaluator.evaluate_dataset(
        test_samples=annotated_test,
        experiment_name=experiment_name,
        include_demonstration=True
    )

    # -------------------------------------------------------------------------
    # PHASE 4: EVALUATION METRICS REPORT & ARTIFACT EXPORT
    # -------------------------------------------------------------------------
    print("\n>>> [PHASE 4] ĐO LƯỜNG CHỈ SỐ AN NINH MẠNG & XUẤT BÁO CÁO NGHIỆM THU...")
    print_metrics_summary(metrics, dataset_name=dataset_name if not use_mock else "Mock Dry-Run E2E")
    
    # Lưu báo cáo chi tiết JSON
    json_path = config.output_dir / f"results_{experiment_name}.json"
    report_payload = {
        "experiment_name": experiment_name,
        "dataset": dataset_name,
        "sample_ratio": sample_ratio,
        "model": model_name if not use_mock else "Intelligent-Mock-Evaluator",
        "execution_time_seconds": round(time.time() - start_time, 2),
        "metrics_summary": metrics,
        "detailed_predictions": results
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, ensure_ascii=False, indent=2)
    logger.info(f"[✓] Đã xuất báo cáo chi tiết định dạng JSON tại: {json_path}")

    # Lưu báo cáo tóm tắt CSV
    csv_path = config.output_dir / f"summary_{experiment_name}.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("id,target,prediction,parse_method\n")
        for r in results:
            f.write(f"{r['id']},{r['target']},{r['prediction']},\"{r['parse_method']}\"\n")
    logger.info(f"[✓] Đã xuất báo cáo đối chiếu nhãn CSV tại: {csv_path}")

    elapsed_min = (time.time() - start_time) / 60.0
    print("\n" + "=" * 75)
    print(f"🎉 HOÀN THÀNH QUY TRÌNH GRACE END-TO-END PIPELINE! (Thời gian tổng: {elapsed_min:.2f} phút)")
    print("=" * 75 + "\n")
    return report_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GRACE End-to-End Vulnerability Detection CLI")
    parser.add_argument("--dataset", type=str, default="DetectVul/devign", help="Tên dataset trên Hugging Face (hoặc 'mock')")
    parser.add_argument("--sample_ratio", type=float, default=0.05, help="Tỷ lệ trích xuất mẫu cân bằng nhãn (ví dụ 0.05 là 5%%)")
    parser.add_argument("--experiment_name", type=str, default="grace_exp", help="Tên mã định danh cho phiên test (Checkpointing)")
    parser.add_argument("--model_name", type=str, default=config.default_llm_model, help="Tên mô hình LLM chuyên code cho Kaggle")
    parser.add_argument("--use_mock", action="store_true", help="Kích hoạt chế độ Mock cho test siêu nhanh tại Local")
    parser.add_argument("--top_k", type=int, default=5, help="Số lượng ứng viên Top-K tìm kiếm qua khoảng cách L2")
    parser.add_argument("--seed", type=int, default=42, help="Hạt giống ngẫu nhiên cho Stratified Sampling")
    
    args = parser.parse_args()
    
    run_grace_pipeline(
        dataset_name=args.dataset,
        sample_ratio=args.sample_ratio,
        experiment_name=args.experiment_name,
        model_name=args.model_name,
        use_mock=args.use_mock,
        top_k_demo=args.top_k,
        seed=args.seed
    )
