"""Trích xuất dữ liệu CPG (stream streaming) từ data/processed/*.json sang data/raw/*.jsonl.
Các trường chuẩn: {id, func, target, nodes, edges, commit_id, project}.
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


def stream_json_array(file_path: Path | str, chunk_size: int = 1048576):
    """Bộ phân tích cú pháp streaming cho mảng JSON lớn để tiết kiệm RAM."""
    decoder = json.JSONDecoder()
    with open(file_path, "r", encoding="utf-8") as f:
        buffer = ""
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                return
            buffer += chunk
            idx = buffer.find("[")
            if idx != -1:
                buffer = buffer[idx + 1 :]
                break
        while True:
            buffer = buffer.lstrip(" \t\r\n,")
            if not buffer:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                buffer += chunk
                buffer = buffer.lstrip(" \t\r\n,")
            if buffer.startswith("]"):
                break
            try:
                obj, idx = decoder.raw_decode(buffer)
                yield obj
                buffer = buffer[idx:]
            except json.JSONDecodeError:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                buffer += chunk


def extract_clean_id(raw_id: str | int) -> str:
    s = str(raw_id).strip()
    # Nếu là dạng id_10000_label_False_qemu.c -> lấy '10000'
    m = re.match(r"^id_(\d+)_", s)
    if m:
        return m.group(1)
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


def load_metadata_map(meta_path: Path) -> dict[str, dict]:
    """Tạo map từ clean_id / legacy_id / filename sang thông tin commit_id, project."""
    if not meta_path.exists():
        return {}
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_list = json.load(f)
    mapping = {}
    for m in meta_list:
        clean_id = extract_clean_id(m.get("id", ""))
        mapping[clean_id] = m
        if "id" in m:
            mapping[str(m["id"])] = m
        if "c_file_path" in m:
            fn = Path(str(m["c_file_path"]).replace("\\", "/")).name
            mapping[fn] = m
            m_fn = re.match(r"^id_(\d+)_", fn)
            if m_fn:
                mapping[m_fn.group(1)] = m
    return mapping


def process_dataset_split(
    processed_path: Path,
    metadata_path: Path,
    out_path: Path,
    dataset: str,
    split: str,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta_map = load_metadata_map(metadata_path)
    count = 0
    t0 = time.time()
    with open(out_path, "w", encoding="utf-8") as out_f:
        for item in stream_json_array(processed_path):
            raw_id = item.get("id", "")
            clean_id = extract_clean_id(raw_id)
            meta = meta_map.get(clean_id) or meta_map.get(str(raw_id)) or {}

            func_code = item.get("func") or meta.get("func") or ""
            target_val = item.get("target")
            if target_val is None:
                target_val = meta.get("target", 0)
            target = 1 if bool(target_val) else 0

            commit_id = meta.get("commit_id") or item.get("commit_id")
            project = meta.get("project") or item.get("project")

            nodes, edges = clean_graph(item.get("nodes"), item.get("edges"))

            row = {
                "id": clean_id,
                "func": func_code,
                "target": target,
                "nodes": nodes,
                "edges": edges,
                "commit_id": commit_id,
                "project": project,
            }
            out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
            if count % 5000 == 0:
                print(f"[{dataset}/{split}] Đã trích xuất {count} mẫu...", flush=True)

    elapsed = time.time() - t0
    print(f"[{dataset}/{split}] Hoàn thành {count} mẫu -> {out_path} ({elapsed:.2f}s)", flush=True)
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
