"""
GRACE Train Assets Preparation & Pre-Extraction Script
Chuẩn hóa kho dữ liệu huấn luyện 21,854 mẫu theo nguyên bản B2 bài báo GRACE:
1. Trích xuất cấu trúc đồ thị Joern CPG rút gọn (Compact CPG: max 25 nodes, max 25 edges)
   từ file processed 3.23 GB (devign_train_processed.json) thành file nén devign_train_compact_cpg.json.gz (~20 MB).
2. Tiền trích xuất ma trận vector ngữ nghĩa Salesforce/codet5-base 768 chiều 
   thành devign_train_codet5_embeddings.npy (~67 MB) để nạp tức thì vào Kaggle GPU.
"""

import os
import sys
import io
import json
import gzip
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr.encoding != "utf-8":
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

repo_root = Path(__file__).parent.parent.resolve()
src_dir = repo_root / "src"
for p in [str(repo_root), str(src_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import config
from retrieval_engine import CodeT5Embedder

log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[log_handler])
logger = logging.getLogger(__name__)


def stream_extract_compact_cpg(
    input_file: Path,
    output_file: Path,
    max_nodes: int = 25,
    max_edges: int = 25
) -> int:
    """
    Đọc luồng file JSON lớn và xuất ra file compact CPG.
    Mỗi mẫu giữ lại: id, func, target, project, nodes[:25], edges[:25], num_nodes, num_edges.
    """
    logger.info(f"[*] Bắt đầu trích xuất Compact CPG từ {input_file}...")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    count = 0
    compact_samples = []

    # Kiểm tra phương thức đọc phù hợp kích thước
    file_size_mb = input_file.stat().st_size / (1024 * 1024)
    logger.info(f"[*] Kích thước file đầu vào: {file_size_mb:.2f} MB")

    if file_size_mb > 500:
        # Đọc theo generator luồng để tối ưu RAM
        from data_loader import iter_json_array
        raw_iterator = iter_json_array(input_file)
    else:
        with open(input_file, "r", encoding="utf-8") as f:
            raw_iterator = json.load(f)

    logger.info(f"[*] Đang bóc tách và rút gọn đồ thị...")
    for idx, item in enumerate(raw_iterator):
        raw_nodes = item.get("node", item.get("nodes", []))
        raw_edges = item.get("edge", item.get("edges", []))

        # Rút gọn nodes
        compact_nodes = []
        for n in raw_nodes[:max_nodes]:
            if isinstance(n, dict):
                n_code = n.get("code", "").strip()
                compact_nodes.append({
                    "id": n.get("id", len(compact_nodes)),
                    "type": n.get("type", n.get("label", "Node")),
                    "code": n_code[:40] if len(n_code) > 40 else n_code
                })
            else:
                compact_nodes.append({"id": len(compact_nodes), "type": str(n), "code": ""})

        # Rút gọn edges
        compact_edges = []
        for e in raw_edges[:max_edges]:
            if isinstance(e, dict):
                compact_edges.append({
                    "start": e.get("start", e.get("source", 0)),
                    "end": e.get("end", e.get("target", 0)),
                    "type": e.get("type", "CONNECTED_TO")
                })
            else:
                compact_edges.append({"start": 0, "end": 0, "type": str(e)})

        code = item.get("func") or item.get("functionSource") or item.get("code") or ""
        t = item.get("target", item.get("label", 0))
        target_int = 1 if (t is True or t == 1 or str(t).lower() in ("1", "true")) else 0

        # Nếu hoàn toàn thiếu graph, fallback sang parser AST/CFG chuẩn
        if (not compact_nodes or not compact_edges) and code:
            try:
                from scripts.pull_kaggle_graphs import extract_c_graph_ast_cfg
                g = extract_c_graph_ast_cfg(code)
                if not compact_nodes:
                    compact_nodes = g.get("nodes", [])[:max_nodes]
                if not compact_edges:
                    compact_edges = g.get("edges", [])[:max_edges]
            except Exception:
                pass

        ds_prefix = "reveal" if "reveal" in input_file.name.lower() else "devign"
        sample_id = item.get("id") or item.get("hash") or item.get("raw_id") or f"{ds_prefix}_train_{idx}"
        compact_samples.append({
            "id": str(sample_id),
            "func": code,
            "target": target_int,
            "project": str(item.get("project", "unknown")),
            "nodes": compact_nodes,
            "edges": compact_edges,
            "num_nodes": len(raw_nodes) if raw_nodes else len(compact_nodes),
            "num_edges": len(raw_edges) if raw_edges else len(compact_edges),
        })
        count += 1

    # Lưu bản JSON thông thường
    if output_file.name.endswith(".gz"):
        json_path = output_file.parent / output_file.name[:-3]
    else:
        json_path = output_file
    logger.info(f"[*] Đang lưu {count} mẫu compact vào {json_path}...")
    with open(json_path, "w", encoding="utf-8") as f_out:
        json.dump(compact_samples, f_out, ensure_ascii=False)

    # Lưu thêm bản nén .json.gz để tải lên Kaggle siêu nhẹ (~15-20 MB)
    gz_path = output_file if output_file.name.endswith(".gz") else output_file.with_suffix(output_file.suffix + ".gz")
    logger.info(f"[*] Đang nén gzip vào {gz_path}...")
    with gzip.open(gz_path, "wt", encoding="utf-8") as f_gz:
        json.dump(compact_samples, f_gz, ensure_ascii=False)

    gz_size_mb = gz_path.stat().st_size / (1024 * 1024)
    logger.info(f"[OK] Hoan tat trich xuat Compact CPG! File nen: {gz_path} ({gz_size_mb:.2f} MB)")
    return count


def precompute_codet5_embeddings(
    train_file: Path,
    output_npy: Path,
    batch_size: int = 64,
    use_fallback: bool = False
) -> int:
    """
    Tiền trích xuất toàn bộ vector CodeT5 768 chiều cho tập train và lưu dưới dạng .npy.
    """
    import numpy as np

    logger.info(f"[*] Đang nạp dữ liệu train từ: {train_file}...")
    file_p = Path(train_file)
    if str(train_file).endswith(".gz"):
        with gzip.open(train_file, "rt", encoding="utf-8") as f:
            samples = json.load(f)
    elif file_p.stat().st_size > 500 * 1024 * 1024:
        from data_loader import iter_json_array
        samples = list(iter_json_array(file_p))
    else:
        with open(train_file, "r", encoding="utf-8") as f:
            samples = json.load(f)

    logger.info(f"[*] Số lượng mẫu cần mã hóa: {len(samples)}")
    texts = [s.get("func") or s.get("code") or "" for s in samples]

    embedder = CodeT5Embedder(model_name="Salesforce/codet5-base", use_fallback_default=use_fallback)
    embedder.fit(texts)

    logger.info(f"[*] Đang mã hóa {len(texts)} đoạn code với batch_size={batch_size}...")
    vecs = embedder.encode(texts, batch_size=batch_size)

    output_npy.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(output_npy), vecs)
    
    file_size_mb = output_npy.stat().st_size / (1024 * 1024)
    logger.info(f"[OK] Da luu thanh cong ma tran embeddings tai: {output_npy} ({file_size_mb:.2f} MB, shape={vecs.shape})")
    return len(samples)


def main():
    parser = argparse.ArgumentParser(description="GRACE Train Assets Preparation")
    parser.add_argument("--dataset", type=str, default="devign", help="Tên bộ dữ liệu (devign/reveal)")
    parser.add_argument("--extract_cpg", action="store_true", help="Trích xuất Compact CPG")
    parser.add_argument("--precompute_embeddings", action="store_true", help="Tiền tính toán ma trận vector CodeT5 768-d")
    parser.add_argument("--input_processed", type=str, default=None, help="Đường dẫn file train processed gốc")
    parser.add_argument("--output_compact", type=str, default=None, help="Đường dẫn file compact CPG đầu ra")
    parser.add_argument("--output_embeddings", type=str, default=None, help="Đường dẫn file .npy embeddings đầu ra")
    parser.add_argument("--batch_size", type=int, default=64, help="Batch size khi mã hóa CodeT5")
    parser.add_argument("--use_fallback", action="store_true", help="Dùng TF-IDF fallback khi test nhanh trên CPU")
    args = parser.parse_args()

    ds = args.dataset.lower() if args.dataset else "devign"
    input_str = args.input_processed or f"data/processed/{ds}_train_processed.json"
    compact_str = args.output_compact or f"data/processed/{ds}_train_compact_cpg.json.gz"
    emb_str = args.output_embeddings or f"data/processed/{ds}_train_codet5_embeddings.npy"

    input_p = Path(input_str)
    compact_p = Path(compact_str)
    emb_p = Path(emb_str)

    if args.extract_cpg or (not args.extract_cpg and not args.precompute_embeddings):
        # Mặc định thực hiện extract nếu input tồn tại
        if input_p.exists():
            stream_extract_compact_cpg(input_p, compact_p)
        else:
            # Fallback sang raw_c_files nếu không có processed
            raw_cand = Path(f"data/raw_c_files/{ds}/train_metadata.json")
            if raw_cand.exists():
                logger.info(f"[!] Không thấy {input_p}, sử dụng fallback {raw_cand} để sinh compact CPG...")
                stream_extract_compact_cpg(raw_cand, compact_p)
            else:
                logger.error(f"[X] Không tìm thấy cả {input_p} lẫn {raw_cand}!")

    if args.precompute_embeddings:
        target_train_file = compact_p if compact_p.exists() else input_p
        precompute_codet5_embeddings(target_train_file, emb_p, batch_size=args.batch_size, use_fallback=args.use_fallback)


if __name__ == "__main__":
    main()
