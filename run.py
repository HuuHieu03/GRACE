"""
GRACE Entry Point Shortcut
Cho phép thực thi pipeline trực tiếp từ thư mục gốc hoặc qua python src/run_pipeline.py
"""
import sys
from pathlib import Path

src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from run_pipeline import run_grace_pipeline

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GRACE End-to-End Orchestration CLI")
    parser.add_argument("--dataset_name", type=str, default="DetectVul/devign")
    parser.add_argument("--sample_ratio", type=float, default=0.05)
    parser.add_argument("--experiment_name", type=str, default="grace_run")
    parser.add_argument("--retrieval_method", type=str, default="contrastive_icl")
    parser.add_argument("--use_mock", action="store_true", default=False)
    parser.add_argument("--top_k_demo", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    run_grace_pipeline(
        dataset_name=args.dataset_name,
        sample_ratio=args.sample_ratio,
        experiment_name=args.experiment_name,
        retrieval_method=args.retrieval_method,
        use_mock=args.use_mock,
        top_k_demo=args.top_k_demo,
        seed=args.seed
    )