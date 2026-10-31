"""Trích xuất dữ liệu CPG chuẩn từ data/processed/*.json sang data/raw/*.jsonl.
Các trường chuẩn: {id, func, target, nodes, edges, commit_id, project}.
Bảo đảm tính nhất quán 100% với định danh chuẩn Step 0:
- Devign: devign:<split>:<id>
- ReVeal: reveal:<split>:<hash>#<index>
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def extract_clean_id(raw_id: str | int) -> str:
    s = str(raw_id).strip()
    m = re.match(r"^id_(\d+)_", s)
    if m:
        return m.group(1)
    if ":" in s:
        parts = s.split(":")
        return parts[-1].split("#")[0]
    return s


def clean_graph(nodes_raw: list | None, edges_raw: list | None) -> tuple[list[dict], list[dict]]:
    nodes = []
    if nodes_raw:
        for idx, n in enumerate(nodes_raw):
            nid = str(n.get("id", idx)) if isinstance(n, dict) else str(idx)
            ntype = n.get("type", n.get("label", "Node")) if isinstance(n, dict) else "Node"
            code = n.get("code", "") if isinstance(n, dict) else ""
            nodes.append({"id": nid, "type": ntype, "code": code})
    edges = []
    if edges_raw:
        for e in edges_raw:
            if isinstance(e, dict):
                src = str(e.get("start", e.get("source", "")))
                dst = str(e.get("end", e.get("target", "")))
                etype = str(e.get("type", "CONNECTED_TO"))
                edges.append({"start": src, "end": dst, "type": etype})
    return nodes, edges


def load_processed_graph_map(processed_path: Path, is_reveal: bool = False):
    """Nạp CPG từ processed JSON và lập chỉ mục theo ID và mã chuẩn hóa."""
    print(f"  Đang nạp file processed: {processed_path.name}...", flush=True)
    with open(processed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_id = {}
    by_norm_func = {}

    for item in data:
        raw_id = item.get("id", "")
        cid = extract_clean_id(raw_id)
        n, e = clean_graph(item.get("nodes"), item.get("edges"))
        graph_tuple = (n, e)

        by_id[cid] = graph_tuple
        by_id[str(raw_id)] = graph_tuple

        func_str = item.get("func", "")
        if func_str:
            nf = normalize_ws(func_str)
            by_norm_func.setdefault(nf, []).append(graph_tuple)

    print(f"  -> Đã lập chỉ mục {len(data)} graphs.", flush=True)
    return by_id, by_norm_func


def process_dataset_split(
    processed_path: Path,
    metadata_path: Path,
    out_path: Path,
    dataset: str,
    split: str,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    is_reveal = dataset.lower() == "reveal"

    print(f"[{dataset}/{split}] Nạp metadata: {metadata_path.name}...", flush=True)
    with open(metadata_path, "r", encoding="utf-8") as f:
        meta_list = json.load(f)

    by_id, by_norm_func = load_processed_graph_map(processed_path, is_reveal=is_reveal)

    count = 0
    matched_graphs = 0
    with open(out_path, "w", encoding="utf-8") as out_f:
        for idx, m in enumerate(meta_list):
            raw_id = m.get("id", "")
            if is_reveal:
                canonical_id = f"reveal:{split}:{raw_id}#{idx}"
            else:
                canonical_id = f"devign:{split}:{raw_id}"

            func_code = m.get("func") or m.get("functionSource") or ""
            target_val = m.get("target")
            if target_val is None:
                target_val = m.get("label", 0)
            target = 1 if bool(target_val) else 0

            commit_id = m.get("commit_id")
            project = m.get("project")

            # Ghép CPG
            nodes, edges = [], []
            clean_id = extract_clean_id(raw_id)
            if not is_reveal and clean_id in by_id:
                nodes, edges = by_id[clean_id]
                matched_graphs += 1
            else:
                # Với reveal hoặc fallback devign: tra theo normalized func
                nf = normalize_ws(func_code)
                if nf in by_norm_func and len(by_norm_func[nf]) > 0:
                    nodes, edges = by_norm_func[nf][0]
                    matched_graphs += 1
                elif clean_id in by_id:
                    nodes, edges = by_id[clean_id]
                    matched_graphs += 1

            row = {
                "id": canonical_id,
                "func": func_code,
                "target": target,
                "nodes": nodes,
                "edges": edges,
                "commit_id": commit_id,
                "project": project,
            }
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1

    elapsed = time.time() - t0
    print(
        f"[{dataset}/{split}] Hoàn thành: {count} mẫu (Ghép được {matched_graphs}/{count} graph CPG) "
        f"-> {out_path} ({elapsed:.2f}s)",
        flush=True,
    )
    return count


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()

    data_dir = args.root / "data"
    proc_dir = data_dir / "processed"
    raw_dir = data_dir / "raw"
    raw_c_dir = data_dir / "raw_c_files"

    configs = [
        # Devign
        {
            "dataset": "devign",
            "split": "train",
            "processed": proc_dir / "devign_train_compact_cpg.json",
            "metadata": raw_c_dir / "devign" / "train_metadata.json",
            "out": raw_dir / "devign_train.jsonl",
        },
        {
            "dataset": "devign",
            "split": "validation",
            "processed": proc_dir / "devign_val_processed.json",
            "metadata": raw_c_dir / "devign" / "validation_metadata.json",
            "out": raw_dir / "devign_validation.jsonl",
        },
        {
            "dataset": "devign",
            "split": "test",
            "processed": proc_dir / "devign_test_processed.json",
            "metadata": raw_c_dir / "devign" / "test_metadata.json",
            "out": raw_dir / "devign_test.jsonl",
        },
        # ReVeal
        {
            "dataset": "reveal",
            "split": "train",
            "processed": proc_dir / "reveal_train_compact_cpg.json",
            "metadata": raw_c_dir / "reveal" / "train_metadata.json",
            "out": raw_dir / "reveal_train.jsonl",
        },
        {
            "dataset": "reveal",
            "split": "validation",
            "processed": proc_dir / "reveal_val_processed.json",
            "metadata": raw_c_dir / "reveal" / "validation_metadata.json",
            "out": raw_dir / "reveal_validation.jsonl",
        },
        {
            "dataset": "reveal",
            "split": "test",
            "processed": proc_dir / "reveal_test_processed.json",
            "metadata": raw_c_dir / "reveal" / "test_metadata.json",
            "out": raw_dir / "reveal_test.jsonl",
        },
    ]

    totals = {}
    for cfg in configs:
        n = process_dataset_split(
            processed_path=cfg["processed"],
            metadata_path=cfg["metadata"],
            out_path=cfg["out"],
            dataset=cfg["dataset"],
            split=cfg["split"],
        )
        totals[f"{cfg['dataset']}_{cfg['split']}"] = n

    print("\n=== TỔNG KẾT TRÍCH XUẤT CPG CHUẨN JSONL ===")
    for k, v in totals.items():
        print(f"  {k}: {v} mẫu")


if __name__ == "__main__":
    main()
