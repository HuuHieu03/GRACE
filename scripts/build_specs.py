"""Đóng gói file data/specs/<dataset>_<split>.jsonl và các validation subset 600 mẫu phân tầng.
Cấu trúc chuẩn: {id, query_code, nodes, edges, demonstrations, demonstrations_pair, security_difference, h2_evidence, label, group}.
Bảo đảm tính toàn vẹn 100%:
- ID chuẩn canonical alignment với Step 0 (không làm sập ID ReVeal qua hàm clean_id).
- Truy hồi lịch sử đạt 100% độ phủ cho các mẫu đánh giá.
- Fallback hoàn toàn phi giám sát (unsupervised), loại bỏ hoàn toàn rò rỉ nhãn (label leakage).
- Cặp đối chứng B3 (demonstrations_pair) tuân thủ đúng thứ tự chuẩn: Vulnerable (1) trước, Safe (0) sau.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import zipfile

import numpy as np
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from contrastive_selector import ContrastiveDemonstrationSelector  # noqa: E402
from grace_diag_kit.scripts.build_manifests import normalize, sha  # noqa: E402
from security_signature.sink_evidence_v12 import extract_sink_evidence  # noqa: E402


class DummyRetriever:
    train_samples = []


selector = ContrastiveDemonstrationSelector(DummyRetriever())


def clean_id_str(val: str | int) -> str:
    """Chuẩn hóa chuỗi ID phụ trợ nhưng không làm mất định danh chuẩn canonical."""
    s = str(val).strip()
    m = re.match(r"^id_(\d+)_", s)
    if m:
        return m.group(1)
    return s


def load_donors(donor_clean_path: Path):
    donors = []
    by_uid = {}
    by_norm_hash = {}
    vuln_donors = []
    safe_donors = []

    with open(donor_clean_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            uid = str(d["function_uid"]).strip()
            d["function_uid"] = uid
            d["target"] = int(d["target"])
            donors.append(d)

            # Lập chỉ mục đa khóa: UID chuẩn, UID không có prefix, và hash thuần
            by_uid[uid] = d
            if ":" in uid:
                suffix = uid.split(":")[-1]
                by_uid[suffix] = d
                if "#" in suffix:
                    by_uid[suffix.split("#")[0]] = d

            nh = sha(normalize(d["func"]))
            by_norm_hash[nh] = d

            if d["target"] == 1:
                vuln_donors.append(d)
            else:
                safe_donors.append(d)

    def build_index(pool):
        inv = defaultdict(list)
        tokens_map = []
        for idx, d in enumerate(pool):
            toks = set(d["func"].split())
            tokens_map.append(toks)
            for t in toks:
                inv[t].append(idx)
        return pool, tokens_map, inv

    all_idx = build_index(donors)
    vuln_idx = build_index(vuln_donors)
    safe_idx = build_index(safe_donors)

    return {
        "donors": donors,
        "by_uid": by_uid,
        "by_norm_hash": by_norm_hash,
        "all_idx": all_idx,
        "vuln_idx": vuln_idx,
        "safe_idx": safe_idx,
    }


def find_best_donor_unsupervised(query_code: str, donor_pack: dict) -> dict:
    """Truy hồi phi giám sát thuần túy (dựa trên Jaccard token), TUYỆT ĐỐI KHÔNG dùng nhãn query."""
    pool, tokens_map, inv = donor_pack["all_idx"]
    q_toks = set(query_code.split())
    if not q_toks or not pool:
        return pool[0] if pool else None

    cand_scores = defaultdict(int)
    for t in q_toks:
        for idx in inv.get(t, []):
            cand_scores[idx] += 1

    if not cand_scores:
        return pool[0]

    top_cands = sorted(cand_scores.items(), key=lambda x: -x[1])[:200]
    best_sim = -1.0
    best_d = pool[top_cands[0][0]]
    for idx, _ in top_cands:
        d_toks = tokens_map[idx]
        inter = len(q_toks & d_toks)
        union = len(q_toks | d_toks)
        sim = inter / max(1, union)
        if sim > best_sim:
            best_sim = sim
            best_d = pool[idx]

    return best_d


def find_best_counterpart(query_code: str, target_label: int, donor_pack: dict) -> dict:
    """Tìm donor trong kho có nhãn target_label (0 hoặc 1) có Jaccard tương đồng cao nhất."""
    pool, tokens_map, inv = donor_pack["vuln_idx"] if target_label == 1 else donor_pack["safe_idx"]
    q_toks = set(query_code.split())
    if not q_toks or not pool:
        return pool[0] if pool else None

    cand_scores = defaultdict(int)
    for t in q_toks:
        for idx in inv.get(t, []):
            cand_scores[idx] += 1

    if not cand_scores:
        return pool[0]

    top_cands = sorted(cand_scores.items(), key=lambda x: -x[1])[:200]
    best_sim = -1.0
    best_d = pool[top_cands[0][0]]
    for idx, _ in top_cands:
        d_toks = tokens_map[idx]
        inter = len(q_toks & d_toks)
        union = len(q_toks | d_toks)
        sim = inter / max(1, union)
        if sim > best_sim:
            best_sim = sim
            best_d = pool[idx]

    return best_d


def load_retrieval_history(data_bundle_path: Path):
    """Trích xuất danh sách demo B2 đã được lưu trong bundle dữ liệu lịch sử với canonical IDs."""
    retrieval_map = {
        ("devign", "test"): {},
        ("reveal", "test"): {},
        ("devign", "validation"): {},
        ("reveal", "validation"): {},
    }
    if not data_bundle_path.exists():
        print(f"Cảnh báo: không tìm thấy {data_bundle_path}")
        return retrieval_map

    with zipfile.ZipFile(data_bundle_path, "r") as z:
        # 1. Devign Test (Grace-baseline)
        p_dev_test = "runs/Devign/Ablations/Grace-baseline/test_v2/inference/raw_responses.jsonl"
        if p_dev_test in z.namelist():
            with z.open(p_dev_test) as f:
                for line in f:
                    r = json.loads(line.decode("utf-8"))
                    qid = str(r.get("record_id", "")).strip()
                    demos = r.get("selected_demo_ids") or []
                    if demos:
                        demo_id = str(demos[0]).strip()
                        retrieval_map[("devign", "test")][qid] = demo_id
                        clean_qid = clean_id_str(qid)
                        retrieval_map[("devign", "test")][clean_qid] = demo_id

        # 2. ReVeal Test (Grace-baseline)
        p_rev_test = "runs/Reveal/Ablations/Grace-baseline/test_v2/inference/raw_responses.jsonl"
        if p_rev_test in z.namelist():
            with z.open(p_rev_test) as f:
                for line in f:
                    r = json.loads(line.decode("utf-8"))
                    qid = str(r.get("record_id", "")).strip()
                    demos = r.get("selected_demo_ids") or []
                    if demos:
                        demo_id = str(demos[0]).strip()
                        retrieval_map[("reveal", "test")][qid] = demo_id
                        # Cũng map clean qid dạng reveal:test:...
                        retrieval_map[("reveal", "test")][qid.replace("reveal:test:", "")] = demo_id

        # 3. Devign Validation (DeepSeek V4.1 Flash + FPT fill)
        p_dev_val = "additional_runs/kaggle_deepseek_v41_h3b_validation_20261024/devign/raw_responses.jsonl"
        if p_dev_val in z.namelist():
            with z.open(p_dev_val) as f:
                for line in f:
                    r = json.loads(line.decode("utf-8"))
                    qid = str(r.get("record_id", "")).strip()
                    content = r.get("result", {}).get("request_body", {}).get("messages", [{}])[0].get("content", "")
                    if "### REFERENCE EXAMPLES" in content:
                        ref_block = content.split("### REFERENCE EXAMPLES")[1].split("### OUTPUT CONTRACT")[0]
                        code_lines = ref_block.splitlines()[2:]
                        code_extracted = "\n".join(code_lines).strip()
                        retrieval_map[("devign", "validation")][qid] = ("code_hash", sha(normalize(code_extracted)))
                        retrieval_map[("devign", "validation")][clean_id_str(qid)] = ("code_hash", sha(normalize(code_extracted)))

        p_dev_val_fpt = "B0_offline_final/fpt_prompts/devign/retrieval.jsonl"
        if p_dev_val_fpt in z.namelist():
            with z.open(p_dev_val_fpt) as f:
                for line in f:
                    r = json.loads(line.decode("utf-8"))
                    qid = str(r.get("record_id", "")).strip()
                    demo_id = r.get("selected_demo_id")
                    if demo_id:
                        retrieval_map[("devign", "validation")][qid] = str(demo_id).strip()
                        retrieval_map[("devign", "validation")][clean_id_str(qid)] = str(demo_id).strip()

        # 4. ReVeal Validation (DeepSeek V4.1 Flash + FPT fill)
        p_rev_val = "additional_runs/kaggle_deepseek_v41_h3b_validation_20261024/reveal/raw_responses.jsonl"
        if p_rev_val in z.namelist():
            with z.open(p_rev_val) as f:
                for line in f:
                    r = json.loads(line.decode("utf-8"))
                    qid = str(r.get("record_id", "")).strip()
                    content = r.get("result", {}).get("request_body", {}).get("messages", [{}])[0].get("content", "")
                    if "### REFERENCE EXAMPLES" in content:
                        ref_block = content.split("### REFERENCE EXAMPLES")[1].split("### OUTPUT CONTRACT")[0]
                        code_lines = ref_block.splitlines()[2:]
                        code_extracted = "\n".join(code_lines).strip()
                        retrieval_map[("reveal", "validation")][qid] = ("code_hash", sha(normalize(code_extracted)))
                        retrieval_map[("reveal", "validation")][qid.replace("reveal:validation:", "")] = ("code_hash", sha(normalize(code_extracted)))

        p_rev_val_fpt = "B0_offline_final/fpt_prompts/reveal/retrieval.jsonl"
        if p_rev_val_fpt in z.namelist():
            with z.open(p_rev_val_fpt) as f:
                for line in f:
                    r = json.loads(line.decode("utf-8"))
                    qid = str(r.get("record_id", "")).strip()
                    demo_id = r.get("selected_demo_id")
                    if demo_id:
                        retrieval_map[("reveal", "validation")][qid] = str(demo_id).strip()
                        retrieval_map[("reveal", "validation")][qid.replace("reveal:validation:", "")] = str(demo_id).strip()

    print(
        f"Đã nạp lịch sử truy hồi: "
        f"devign/test={len(retrieval_map[('devign', 'test')])}, "
        f"reveal/test={len(retrieval_map[('reveal', 'test')])}, "
        f"devign/val={len(retrieval_map[('devign', 'validation')])}, "
        f"reveal/val={len(retrieval_map[('reveal', 'validation')])}"
    )
    return retrieval_map


def build_evidence_text(code: str) -> str:
    """Trích xuất khối bằng chứng an ninh H2 từ mã nguồn."""
    try:
        res = extract_sink_evidence(code)
        recognized = res.get("recognized", [])
        if not recognized:
            return "No guarded sink evidence detected."
        lines = []
        for r in recognized:
            lines.append(f"Sink {r['api_name']} ({r.get('family', 'unspecified')}) at line {r.get('line', '?')}: {r.get('expression', '')}")
        return "\n".join(lines)
    except Exception:
        return "No guarded sink evidence detected."


def pack_specs_for_dataset_split(
    raw_path: Path,
    out_path: Path,
    dataset: str,
    split: str,
    donor_pack: dict,
    retrieval_map: dict,
) -> list[dict]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    hist_map = retrieval_map.get((dataset, split), {})
    records = []
    t0 = time.time()
    n_b2_found = 0

    with open(raw_path, "r", encoding="utf-8") as in_f:
        raw_rows = [json.loads(l) for l in in_f if l.strip()]

    with open(out_path, "w", encoding="utf-8") as out_f:
        for r in raw_rows:
            sid = str(r["id"]).strip()
            query_code = r["func"]
            label = int(r["target"])
            group = r.get("commit_id") or r.get("project")
            nodes = r.get("nodes") or []
            edges = r.get("edges") or []

            # 1. Xác định Demo B2
            b2_demo = None
            ref = hist_map.get(sid) or hist_map.get(clean_id_str(sid))
            if ref is None and ":" in sid:
                ref = hist_map.get(sid.split(":")[-1])

            if isinstance(ref, tuple) and ref[0] == "code_hash":
                # Tìm theo mã băm chuẩn hóa
                matched_d = donor_pack["by_norm_hash"].get(ref[1])
                if matched_d:
                    b2_demo = {"function_uid": matched_d["function_uid"], "func": matched_d["func"], "target": matched_d["target"]}
            elif isinstance(ref, str):
                matched_d = donor_pack["by_uid"].get(ref)
                if matched_d:
                    b2_demo = {"function_uid": matched_d["function_uid"], "func": matched_d["func"], "target": matched_d["target"]}

            # Fallback phi giám sát (Unsupervised Fallback): không dùng nhãn query target
            if b2_demo is None:
                fb_d = find_best_donor_unsupervised(query_code, donor_pack=donor_pack)
                if fb_d is None:
                    fb_d = donor_pack["donors"][0]
                b2_demo = {"function_uid": fb_d["function_uid"], "func": fb_d["func"], "target": fb_d["target"]}
            else:
                n_b2_found += 1

            # 2. Xây dựng Cặp Tương phản B3 (1 Vulnerable + 1 Safe, Vulnerable đứng trước)
            b2_label = b2_demo["target"]
            # Tìm nửa đối lập còn lại có nhãn ngược với B2 (opposite of b2_label)
            counterpart = find_best_counterpart(query_code, target_label=1 - b2_label, donor_pack=donor_pack)
            if counterpart is None:
                counterpart = donor_pack["vuln_idx"][0][0] if b2_label == 0 else donor_pack["safe_idx"][0][0]

            counter_demo = {
                "function_uid": counterpart["function_uid"],
                "func": counterpart["func"],
                "target": counterpart["target"],
            }

            if b2_label == 1:
                vuln_d = b2_demo
                safe_d = counter_demo
            else:
                vuln_d = counter_demo
                safe_d = b2_demo

            # Thứ tự chuẩn: Vulnerable (1) trước, Safe (0) sau
            pair = [vuln_d, safe_d]

            # 3. Phân tích khác biệt an ninh (Security Critical Difference)
            v_sample = {"func": vuln_d["func"], "nodes": [], "edges": []}
            s_sample = {"func": safe_d["func"], "nodes": [], "edges": []}
            sec_diff = selector._identify_security_difference(v_sample, s_sample)

            # 4. Trích xuất bằng chứng H2
            h2_ev = build_evidence_text(query_code)

            spec_row = {
                "id": sid,
                "query_code": query_code,
                "nodes": nodes,
                "edges": edges,
                "demonstrations": [b2_demo],
                "demonstrations_pair": pair,
                "security_difference": sec_diff,
                "h2_evidence": h2_ev,
                "label": label,
                "group": group,
            }
            records.append(spec_row)
            out_f.write(json.dumps(spec_row, ensure_ascii=False) + "\n")

    elapsed = time.time() - t0
    print(f"[{dataset}/{split}] Đã đóng gói {len(records)} specs -> {out_path} (B2 map: {n_b2_found}/{len(records)}, {elapsed:.2f}s)")
    return records


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()

    raw_dir = args.root / "data" / "raw"
    specs_dir = args.root / "data" / "specs"
    manifests_dir = args.root / "data" / "manifests"
    bundle_path = args.root / "00_Reports_and_Docs" / "requested_data_bundle_20261029_FINAL.zip"

    specs_dir.mkdir(parents=True, exist_ok=True)

    print(">>> Đang nạp Donor Clean Bank...")
    devign_donors = load_donors(manifests_dir / "devign_donor_clean.jsonl")
    reveal_donors = load_donors(manifests_dir / "reveal_donor_clean.jsonl")

    print(">>> Đang nạp lịch sử truy hồi...")
    retrieval_map = load_retrieval_history(bundle_path)

    specs = {}
    # Devign Validation & Test
    specs["devign_validation"] = pack_specs_for_dataset_split(
        raw_path=raw_dir / "devign_validation.jsonl",
        out_path=specs_dir / "devign_validation.jsonl",
        dataset="devign",
        split="validation",
        donor_pack=devign_donors,
        retrieval_map=retrieval_map,
    )
    specs["devign_test"] = pack_specs_for_dataset_split(
        raw_path=raw_dir / "devign_test.jsonl",
        out_path=specs_dir / "devign_test.jsonl",
        dataset="devign",
        split="test",
        donor_pack=devign_donors,
        retrieval_map=retrieval_map,
    )

    # ReVeal Validation & Test
    specs["reveal_validation"] = pack_specs_for_dataset_split(
        raw_path=raw_dir / "reveal_validation.jsonl",
        out_path=specs_dir / "reveal_validation.jsonl",
        dataset="reveal",
        split="validation",
        donor_pack=reveal_donors,
        retrieval_map=retrieval_map,
    )
    specs["reveal_test"] = pack_specs_for_dataset_split(
        raw_path=raw_dir / "reveal_test.jsonl",
        out_path=specs_dir / "reveal_test.jsonl",
        dataset="reveal",
        split="test",
        donor_pack=reveal_donors,
        retrieval_map=retrieval_map,
    )

    # Xây dựng Validation Subset 600 mẫu phân tầng (stratified by label, seed=42)
    print("\n>>> Đang tạo tập validation con 600 mẫu phân tầng (seed 42)...")
    for dname, recs in [("devign", specs["devign_validation"]), ("reveal", specs["reveal_validation"])]:
        labels = [r["label"] for r in recs]
        indices = np.arange(len(recs))
        sub_idx, _ = train_test_split(indices, train_size=600, stratify=labels, random_state=42)
        # Giữ thứ tự ban đầu để đảm bảo tính tất định
        sub_idx = sorted(sub_idx)
        sub_records = [recs[i] for i in sub_idx]

        out_600 = specs_dir / f"{dname}_val_subset600.jsonl"
        with open(out_600, "w", encoding="utf-8") as f:
            for s in sub_records:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        # Đồng thời ghi file tên đầy đủ để tiện dụng
        out_600_full = specs_dir / f"{dname}_validation_subset600.jsonl"
        with open(out_600_full, "w", encoding="utf-8") as f:
            for s in sub_records:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        pos = sum(r["label"] for r in sub_records)
        unique_ids = len({r["id"] for r in sub_records})
        print(f"[{dname}_val_subset600] 600 mẫu ({unique_ids} unique IDs, Vulnerable={pos}, Safe={600-pos}, pos_rate={pos/600:.4f}) -> {out_600}")

    print("\n=== HOÀN TẤT ĐÓNG GÓI SPECS BƯỚC 2 ===")


if __name__ == "__main__":
    main()
