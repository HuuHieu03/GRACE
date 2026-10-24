"""
Driver Script for H2 GuardedEvidence v3 Evaluation on Vertex AI MaaS (DeepSeek-V4.1-Flash)
Conforms to: evaluation_contract.yaml
Backbone LLM: deepseek-ai/deepseek-v4.1-flash-maas (location: global)
Datasets: Devign (2,732 prompts), ReVeal (2,274 prompts)
"""

import os
import sys
import io
import json
import time
import shutil
import zipfile
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Force UTF-8 on stdout/stderr for Windows console
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("H2_Vertex_Evaluator")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_DIR = Path(
    r"D:\tai lieu hoc tap\Đề tài nghiên cứu khoa học\papers source code"
    r"\SHARE_H2_VERTEX_DEEPSEEK_V41_CONTEXT8192_20261022\SHARE_H2_VERTEX_DEEPSEEK_V41_CONTEXT8192_20261022"
)
DEFAULT_GCP_KEY = REPO_ROOT / ".gcp_key.json"
DEFAULT_PROJECT_ID = "grace-research-2903"
DEFAULT_ENDPOINT = "deepseek-ai/deepseek-v4.1-flash-maas"
DEFAULT_LOCATION = "global"

# Baselines from project_docs/reports/v1.0.0_2026-10-21_stage3_b3_vs_b2_comparison_report.md
BASELINES = {
    "B2_baseline_1shot": {
        "f1": 0.3614,
        "recall": 0.2778,
        "precision": 0.5172,
        "accuracy": 0.4700,
        "mcc": -0.0292,
        "balanced_accuracy": 0.4867,
    },
    "B3_contrastive_2shot": {
        "f1": 0.5500,
        "recall": 0.6111,
        "precision": 0.5000,
        "accuracy": 0.4600,
        "mcc": -0.1118,
        "balanced_accuracy": 0.4469,
    }
}


def configure_environment(gcp_key_path: Path, project_id: str):
    """Sets up Google Application Credentials and Vertex AI environment variables."""
    if not gcp_key_path.exists():
        raise FileNotFoundError(f"GCP service account key not found at: {gcp_key_path}")

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(gcp_key_path.resolve())
    os.environ["CLOUD_ML_PROJECT_ID"] = project_id
    os.environ["GCP_PROJECT"] = project_id
    os.environ["VERTEX_LOCATION"] = DEFAULT_LOCATION
    logger.info(f"Configured GOOGLE_APPLICATION_CREDENTIALS -> {gcp_key_path.resolve()}")
    logger.info(f"Project ID: {project_id}, Vertex Location: {DEFAULT_LOCATION}")


def load_runner_module(bundle_dir: Path):
    """Dynamically adds bundle directory to sys.path and imports runner."""
    bundle_resolved = bundle_dir.resolve()
    if not bundle_resolved.exists():
        raise FileNotFoundError(
            f"Bundle directory does not exist or cannot be accessed: {bundle_resolved}.\n"
            f"Please verify the bundle path."
        )

    if str(bundle_resolved) not in sys.path:
        sys.path.insert(0, str(bundle_resolved))
        logger.info(f"Added bundle to sys.path: {bundle_resolved}")

    try:
        import runner
        logger.info("Successfully imported 'runner' module from bundle.")
        return runner
    except ImportError as e:
        logger.error(f"Failed to import 'runner' from {bundle_resolved}: {e}")
        raise


def run_smoke_test(runner_module, bundle_dir: Path, project_id: str) -> bool:
    """
    Step 1: Smoke Test
    Executes limit=1 for both Devign and ReVeal with allow_api=True.
    Validates status == 'valid' and parsed label in {0, 1}.
    """
    logger.info("==================================================")
    logger.info("STEP 1: Starting Smoke Test (limit=1, allow_api=True)")
    logger.info("==================================================")

    all_passed = True
    datasets = ["devign", "reveal"]

    for ds in datasets:
        logger.info(f"\n--- Smoke Testing Dataset: {ds} ---")
        try:
            replay = runner_module.Replay(bundle_dir, ds, project_id)
            logger.info(f"Initialized Replay for {ds}: total prompts = {len(replay.prompts)}")

            start_t = time.perf_counter()
            status = replay.run(limit=1, allow_api=True)
            elapsed_ms = (time.perf_counter() - start_t) * 1000

            logger.info(f"Smoke run finished for {ds} in {elapsed_ms:.1f}ms: {status}")

            first_p = replay.prompts[0]
            first_res = replay.result(first_p)

            if not first_res:
                logger.error(f"Smoke test for {ds} produced no result file.")
                all_passed = False
                continue

            res_status = first_res.get("status")
            parsed_label = first_res.get("prediction")
            raw_response = first_res.get("raw_response", "")

            logger.info(f"Record ID: {first_p.get('record_id', 'N/A')}")
            logger.info(f"Status: {res_status}")
            logger.info(f"Parsed prediction: {parsed_label}")
            logger.info(f"Raw response preview: {repr(raw_response[:120])}...")

            if res_status != "valid" or parsed_label not in [0, 1]:
                logger.error(
                    f"Smoke test validation FAILED for {ds}: status='{res_status}', "
                    f"prediction={parsed_label} (expected status=='valid', prediction in [0, 1])"
                )
                all_passed = False
            else:
                logger.info(f"Smoke test PASSED for {ds}!")

        except Exception as e:
            logger.exception(f"Exception during smoke test for {ds}: {e}")
            all_passed = False

    return all_passed


def run_full_evaluation(runner_module, bundle_dir: Path, project_id: str, output_dir: Path, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Step 2: Full Evaluation
    Runs all prompts for Devign (2,732 prompts) and ReVeal (2,274 prompts).
    Tracks throughput, status codes, and atomic checkpoints.
    """
    logger.info("==================================================")
    limit_str = f"limit={limit}" if limit else "Full"
    logger.info(f"STEP 2: Starting Evaluation ({limit_str}) (Devign: 2,732, ReVeal: 2,274)")
    logger.info("==================================================")

    dataset_configs = [
        {"name": "devign", "expected_prompts": 2732},
        {"name": "reveal", "expected_prompts": 2274}
    ]

    eval_summary = {}

    for cfg in dataset_configs:
        ds = cfg["name"]
        expected = cfg["expected_prompts"]

        logger.info(f"\n==========================================")
        logger.info(f"Processing Dataset: {ds} (Expected: {expected} prompts, Limit: {limit})")
        logger.info(f"==========================================")

        replay = runner_module.Replay(bundle_dir, ds, project_id)
        current_status = replay.status()
        logger.info(f"Pre-run status for {ds}: {current_status}")

        start_time = time.perf_counter()
        final_status = replay.run(limit=limit, allow_api=True)
        total_time = time.perf_counter() - start_time

        logger.info(f"Dataset {ds} run finished in {total_time:.2f}s: {final_status}")

        # Call export to generate standard artifact files
        logger.info(f"Exporting results for {ds}...")
        report = replay.export()
        logger.info(f"Export report status: {report.get('status')}")

        # Copy exported files to output_dir
        ds_dest = output_dir / ds
        ds_dest.mkdir(parents=True, exist_ok=True)
        for fname in ["predictions.jsonl", "raw_responses.jsonl", "evaluation.json", "run_manifest.json"]:
            src_f = replay.out / fname
            if src_f.exists():
                shutil.copy2(src_f, ds_dest / fname)
                logger.info(f"Copied {fname} -> {ds_dest / fname}")

        eval_summary[ds] = {
            "total_prompts": len(replay.prompts),
            "expected_prompts": expected,
            "total_time_seconds": round(total_time, 2),
            "status": final_status,
            "report": report,
            "output_folder": str(ds_dest)
        }

    return eval_summary


def compute_metrics_and_compare(output_dir: Path, eval_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 3: Metrics Computation and Comparison against B2 and B3 baselines.
    """
    logger.info("==================================================")
    logger.info("STEP 3: Metrics Computation & Baseline Comparison")
    logger.info("==================================================")

    comparison_report = {
        "baselines": BASELINES,
        "h2_vertex_eval": {}
    }

    for ds in ["devign", "reveal"]:
        eval_file = output_dir / ds / "evaluation.json"
        if not eval_file.exists():
            logger.warning(f"evaluation.json not found for {ds} at {eval_file}")
            continue

        with open(eval_file, "r", encoding="utf-8") as f:
            h2_metrics_doc = json.load(f)

        metrics = h2_metrics_doc.get("metrics", {})
        logger.info(f"\n--- H2 Metrics on {ds.upper()} ---")
        logger.info(f"Accuracy:  {metrics.get('accuracy', 'N/A')}")
        logger.info(f"Precision: {metrics.get('precision', 'N/A')}")
        logger.info(f"Recall:    {metrics.get('recall', 'N/A')}")
        logger.info(f"F1-Score:  {metrics.get('f1_score', metrics.get('f1', 'N/A'))}")
        logger.info(f"MCC:       {metrics.get('mcc', 'N/A')}")

        comparison_report["h2_vertex_eval"][ds] = h2_metrics_doc

    # Print comparative table
    logger.info("\n" + "=" * 85)
    logger.info("COMPARATIVE TABLE: Baseline B2 vs B3 vs H2 GuardedEvidence v3 (Vertex AI DeepSeek)")
    logger.info("=" * 85)
    logger.info(f"{'Metric':<18} | {'B2 (1-shot)':<12} | {'B3 (Contrastive)':<16} | {'H2 Devign':<14} | {'H2 ReVeal':<14}")
    logger.info("-" * 85)

    d_m = comparison_report["h2_vertex_eval"].get("devign", {}).get("metrics", {})
    r_m = comparison_report["h2_vertex_eval"].get("reveal", {}).get("metrics", {})

    for m_key, m_name in [("f1_score", "F1-Score"), ("recall", "Recall"), ("precision", "Precision"), ("accuracy", "Accuracy"), ("mcc", "MCC")]:
        b2_val = BASELINES["B2_baseline_1shot"].get("f1" if m_key == "f1_score" else m_key, 0.0)
        b3_val = BASELINES["B3_contrastive_2shot"].get("f1" if m_key == "f1_score" else m_key, 0.0)
        h2_dev = d_m.get(m_key, d_m.get("f1", 0.0) if m_key == "f1_score" else 0.0)
        h2_rev = r_m.get(m_key, r_m.get("f1", 0.0) if m_key == "f1_score" else 0.0)
        logger.info(f"{m_name:<18} | {b2_val:<12.4f} | {b3_val:<16.4f} | {h2_dev:<14.4f} | {h2_rev:<14.4f}")
    logger.info("=" * 85)

    # Save comparison report
    report_path = output_dir / "baseline_comparison_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(comparison_report, f, indent=2, ensure_ascii=False)
    logger.info(f"Comparison report saved to: {report_path}")

    return comparison_report


def package_results_zip(output_dir: Path, zip_dest: Path):
    """
    Step 4: Package into H2_vertex_results.zip
    Packages predictions.jsonl, raw_responses.jsonl, evaluation.json and reports.
    """
    logger.info(f"Packaging evaluation results into zip: {zip_dest}")
    zip_dest.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                file_path = Path(root) / file
                if file_path == zip_dest:
                    continue
                rel_path = file_path.relative_to(output_dir)
                zipf.write(file_path, arcname=str(rel_path))
                logger.info(f"  Added to zip: {rel_path}")

    logger.info(f"ZIP package created successfully ({zip_dest.stat().st_size} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Evaluate H2 GuardedEvidence v3 on Vertex AI")
    parser.add_argument("--bundle-dir", type=Path, default=DEFAULT_BUNDLE_DIR,
                        help="Path to shared bundle containing runner.py")
    parser.add_argument("--gcp-key", type=Path, default=DEFAULT_GCP_KEY,
                        help="Path to GCP service account key JSON")
    parser.add_argument("--project-id", type=str, default=DEFAULT_PROJECT_ID,
                        help="GCP Project ID")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "output" / "h2_vertex_deepseek_v41",
                        help="Output directory for evaluations and artifacts")
    parser.add_argument("--mode", choices=["smoke", "full", "all"], default="all",
                        help="Execution mode: smoke (limit=1), full (all prompts), or all")
    parser.add_argument("--limit", type=int, default=None,
                        help="Optional limit on new requests per dataset (default: None for all)")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Environment & Credential Setup
    configure_environment(args.gcp_key, args.project_id)

    # 2. Runner Import
    runner_module = load_runner_module(args.bundle_dir)

    # 3. Execution
    smoke_passed = True
    if args.mode in ["smoke", "all"]:
        smoke_passed = run_smoke_test(runner_module, args.bundle_dir, args.project_id)
        if not smoke_passed and args.mode == "all":
            logger.error("Smoke test failed. Aborting full evaluation to avoid wasted API quota.")
            sys.exit(1)

    if args.mode in ["full", "all"]:
        eval_summary = run_full_evaluation(runner_module, args.bundle_dir, args.project_id, args.output_dir, limit=args.limit)
        compute_metrics_and_compare(args.output_dir, eval_summary)
        zip_dest = args.output_dir / "H2_vertex_results.zip"
        package_results_zip(args.output_dir, zip_dest)

    logger.info("\nExecution completed successfully.")


if __name__ == "__main__":
    main()
