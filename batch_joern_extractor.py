"""
GRACE Joern Batch Graph Extractor
Trích xuất hàng loạt đồ thị cấu trúc mã (CPG - AST, CFG, PDG) từ các file .c
và chuyển đổi thành định dạng JSON chuẩn hóa tương thích cho GRACE.
"""

import os
import sys
import csv
import json
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
JOERN_PARSE_BIN = os.path.join(WORKSPACE_ROOT, "data", "preproceed", "joern", "joern", "joern", "joern-parse")


def parse_nodes_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Đọc file nodes.csv sinh ra từ Joern và lọc ra các thông tin quan trọng."""
    nodes = []
    if not os.path.exists(csv_path):
        return nodes
        
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            node_key = row.get("key") or row.get("id")
            node_type = row.get("type", "")
            node_code = row.get("code", "")
            node_ident = row.get("identifier", "")
            is_cfg = row.get("isCFGNode", "False") == "True"
            
            # Bỏ qua node file toàn cục
            if node_type == "File":
                continue
                
            nodes.append({
                "id": node_key,
                "type": node_type,
                "code": node_code.strip() if node_code else "",
                "identifier": node_ident.strip() if node_ident else "",
                "is_cfg": is_cfg
            })
    return nodes


def parse_edges_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Đọc file edges.csv sinh ra từ Joern."""
    edges = []
    if not os.path.exists(csv_path):
        return edges
        
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            start_node = row.get("start")
            end_node = row.get("end")
            edge_type = row.get("type", "")
            var_name = row.get("var", "")
            
            if start_node and end_node:
                edges.append({
                    "start": start_node,
                    "end": end_node,
                    "type": edge_type,
                    "var": var_name.strip() if var_name else ""
                })
    return edges


def run_joern_batch(
    c_files: List[str], 
    timeout_sec: int = 120
) -> Dict[str, Dict[str, Any]]:
    """
    Chạy Joern một lần cho một lô (batch) file .c để đạt tốc độ cao nhất.
    Trả về dictionary map từ c_filepath -> {'nodes': [...], 'edges': [...]}.
    """
    results = {}
    if not c_files:
        return results

    # Tạo thư mục tạm cho batch input và output
    with tempfile.TemporaryDirectory(prefix="joern_batch_in_") as temp_in_dir:
        temp_out_dir = tempfile.mkdtemp(prefix="joern_batch_out_")
        
        try:
            # Copy các file vào thư mục batch
            file_map = {} # filename -> original_path
            for file_path in c_files:
                filename = os.path.basename(file_path)
                dest = os.path.join(temp_in_dir, filename)
                shutil.copy2(file_path, dest)
                file_map[filename] = file_path

            # Gọi joern-parse
            # Lưu ý: joern-parse yêu cầu thư mục output chưa tồn tại
            if os.path.exists(temp_out_dir):
                shutil.rmtree(temp_out_dir)

            cmd = [JOERN_PARSE_BIN, temp_in_dir, temp_out_dir]
            proc = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                timeout=timeout_sec
            )

            # Thu thập kết quả từ thư mục output
            for filename, orig_path in file_map.items():
                # Joern tạo thư mục con chứa kết quả cho từng file
                # Cấu trúc: temp_out_dir/.../<temp_in_dir>/<filename>/nodes.csv
                found_nodes = []
                found_edges = []
                
                # Tìm đường dẫn chứa filename trong temp_out_dir
                for root, dirs, files in os.walk(temp_out_dir):
                    if os.path.basename(root) == filename:
                        nodes_csv = os.path.join(root, "nodes.csv")
                        edges_csv = os.path.join(root, "edges.csv")
                        if os.path.exists(nodes_csv):
                            found_nodes = parse_nodes_csv(nodes_csv)
                        if os.path.exists(edges_csv):
                            found_edges = parse_edges_csv(edges_csv)
                        break

                results[orig_path] = {
                    "nodes": found_nodes,
                    "edges": found_edges
                }
        except subprocess.TimeoutExpired:
            print(f"[Warning] Batch timeout after {timeout_sec}s for {len(c_files)} files. Falling back to empty graphs.")
            for file_path in c_files:
                results[file_path] = {"nodes": [], "edges": []}
        except Exception as e:
            print(f"[Error] Error during batch processing: {e}")
            for file_path in c_files:
                results[file_path] = {"nodes": [], "edges": []}
        finally:
            if os.path.exists(temp_out_dir):
                shutil.rmtree(temp_out_dir, ignore_errors=True)

    return results


def process_dataset_split(
    dataset_name: str,
    split_name: str,
    batch_size: int = 50,
    max_samples: Optional[int] = None,
    output_dir: str = "data/processed"
) -> str:
    """
    Xử lý toàn bộ một split dữ liệu và xuất ra file JSON chuẩn cho GRACE.
    """
    raw_split_dir = os.path.join(WORKSPACE_ROOT, "data", "raw_c_files", dataset_name, split_name)
    meta_path = os.path.join(WORKSPACE_ROOT, "data", "raw_c_files", dataset_name, f"{split_name}_metadata.json")
    
    if not os.path.exists(raw_split_dir):
        raise FileNotFoundError(f"Thư mục không tồn tại: {raw_split_dir}")

    # Đọc metadata nếu có
    metadata_map = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                c_path = item.get("c_file_path")
                if c_path:
                    # chuẩn hóa path
                    fname = os.path.basename(c_path)
                    metadata_map[fname] = item

    all_c_files = [
        os.path.join(raw_split_dir, f) 
        for f in sorted(os.listdir(raw_split_dir)) 
        if f.endswith(".c")
    ]

    if max_samples and max_samples > 0:
        all_c_files = all_c_files[:max_samples]

    print(f"=== Bắt đầu xử lý {dataset_name} [{split_name}]: {len(all_c_files)} files (Batch size: {batch_size}) ===")
    
    processed_samples = []
    
    # Chia batch
    num_batches = (len(all_c_files) + batch_size - 1) // batch_size
    
    for b_idx in range(num_batches):
        batch_files = all_c_files[b_idx * batch_size : (b_idx + 1) * batch_size]
        start_t = time.time()
        batch_graphs = run_joern_batch(batch_files)
        elapsed = time.time() - start_t
        
        for file_path in batch_files:
            fname = os.path.basename(file_path)
            meta = metadata_map.get(fname, {})
            
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                func_code = f.read()
                
            target = meta.get("target")
            if target is None:
                # Trích xuất target từ filename (ví dụ: id_0_label_False_...)
                if "label_1" in fname or "label_True" in fname:
                    target = 1
                else:
                    target = 0
            else:
                try:
                    target = int(target)
                except Exception:
                    target = 1 if str(target).lower() in ["true", "1", "vuln"] else 0

            graph_data = batch_graphs.get(file_path, {"nodes": [], "edges": []})
            
            sample = {
                "id": str(meta.get("id", meta.get("hash", fname))),
                "func": func_code.strip(),
                "target": target,
                "project": meta.get("project", dataset_name),
                "nodes": graph_data["nodes"],
                "edges": graph_data["edges"]
            }
            processed_samples.append(sample)
            
        print(f"  Batch {b_idx + 1}/{num_batches} ({len(batch_files)} files) hoàn tất trong {elapsed:.2f}s | Tổng mẫu đã parse: {len(processed_samples)}")

    os.makedirs(os.path.join(WORKSPACE_ROOT, output_dir), exist_ok=True)
    out_file = os.path.join(WORKSPACE_ROOT, output_dir, f"{dataset_name}_{split_name}_processed.json")
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(processed_samples, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Đã lưu {len(processed_samples)} mẫu vào: {out_file}\n")
    return out_file


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GRACE Joern Batch Graph Extractor")
    parser.add_argument("--dataset", type=str, choices=["devign", "reveal", "all"], default="devign")
    parser.add_argument("--split", type=str, choices=["test", "validation", "train", "all"], default="test")
    parser.add_argument("--batch_size", type=int, default=20)
    parser.add_argument("--max_samples", type=int, default=None, help="Số lượng mẫu tối đa để thử nghiệm")
    parser.add_argument("--output_dir", type=str, default="data/processed")
    args = parser.parse_args()

    datasets = ["devign", "reveal"] if args.dataset == "all" else [args.dataset]
    for d in datasets:
        splits = ["test", "validation", "train"] if args.split == "all" else [args.split]
        for s in splits:
            try:
                process_dataset_split(
                    dataset_name=d,
                    split_name=s,
                    batch_size=args.batch_size,
                    max_samples=args.max_samples,
                    output_dir=args.output_dir
                )
            except Exception as e:
                print(f"[Error] Thất bại khi xử lý {d} - {s}: {e}")
