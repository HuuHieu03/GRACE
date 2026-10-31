"""Bộ dựng prompt theo thứ tự Hình 6 của bài GRACE và các probe thay-một-thành-phần.

Một hàm duy nhất `render_arm(spec, arm, seed, counter, donors)` sinh prompt cho mọi arm
B0 … B3-flip. Mỗi arm chỉ khác arm gốc của nó đúng một khối, nên `diff_blocks` trong
tests có thể kiểm tra điều đó tự động.

spec (không bao giờ chứa nhãn của target):
    id                 : mã target
    query_code         : mã nguồn target
    nodes, edges       : CPG từ Joern (list dict; node có id/type/code, edge có start/end/type)
    demonstrations     : [ {function_uid, func, target} ] — 1 demo (họ B2) hoặc 2 demo (họ B3,
                         demo vulnerable đứng trước)
    security_difference: khối "Key difference" do contrastive_selector sinh (họ B3)
    h2_evidence        : văn bản cụm evidence của H2 (arm B1-H2), đã ở dạng hiển thị

donors (DonorPool): cung cấp demo ngẫu nhiên và CPG của hàm khác cùng cỡ cho B2-rand, B1-shuf.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .token_budget import TokenCounter, FitResult

ROLE = ("You are now an excellent programmer. "
        "You are conducting a function vulnerability detection task for C/C++ language.")
QUESTION = ("In the above code snippet, check for potential security vulnerabilities and answer "
            "with a single digit: 1 if Vulnerable, 0 if Non-vulnerable.")
NODE_HEAD = "The node information of the code snippet is as follows:"
EDGE_HEAD = "The edge information of the code snippet is as follows:"
ANSWER = "Answer (0 or 1):"
LABEL_WORD = {1: "Vulnerable", 0: "Non-vulnerable"}

DEFAULT_BUDGET = {"total": 8192, "target_code": 3000, "demo": 1500, "graph": 1500, "reserve": 64}
DEFAULT_GRAPH_PREFIX = {"nodes": 25, "edges": 25}

# Định nghĩa arm mặc định (configs/arms.yaml có thể ghi đè)
ARMS: Dict[str, Dict[str, Any]] = {
    "B0":           {"graph": "none",    "demo": "none"},
    "B1":           {"graph": "prefix",  "demo": "none"},
    "B1-full":      {"graph": "fill",    "demo": "none"},
    "B1-H2":        {"graph": "h2",      "demo": "none"},
    "B1-shuf":      {"graph": "shuffle", "demo": "none"},
    "B2":           {"graph": "prefix",  "demo": "retrieved", "label": "true"},
    "B2-rand":      {"graph": "prefix",  "demo": "random",    "label": "true"},
    "B2-nolabel":   {"graph": "prefix",  "demo": "retrieved", "label": "none"},
    "B2-labelonly": {"graph": "prefix",  "demo": "labelonly", "label": "true"},
    "B2-flip":      {"graph": "prefix",  "demo": "retrieved", "label": "flip"},
    "B2-rep":       {"graph": "prefix",  "demo": "retrieved", "label": "true", "repeat": True},
    "B3":           {"graph": "prefix",  "demo": "contrastive", "label": "true", "diff": True},
    "B3-nodiff":    {"graph": "prefix",  "demo": "contrastive", "label": "true", "diff": False},
    "B3-swap":      {"graph": "prefix",  "demo": "contrastive", "label": "true", "diff": True, "order": "swap"},
    "B3-flip":      {"graph": "prefix",  "demo": "contrastive", "label": "flip", "diff": True},
}


def stable_seed(target_id: str, seed: int) -> int:
    h = int(hashlib.sha256(str(target_id).encode("utf-8")).hexdigest()[:8], 16)
    return (h + int(seed)) % (2 ** 32)


# ---------------------------------------------------------------------------
# Kho donor cho probe
# ---------------------------------------------------------------------------
class DonorPool:
    """Danh sách hàm train (đã khử trùng với validation/test) dùng làm demo ngẫu nhiên
    và graph xáo trộn. Mỗi phần tử: {function_uid, func, target, nodes?, edges?, n_nodes?}."""

    def __init__(self, rows: Sequence[Dict[str, Any]]):
        self.rows = list(rows)
        self.n_nodes = np.asarray([
            (r.get("n_nodes") if r.get("n_nodes") is not None else len(r.get("nodes") or []))
            for r in self.rows
        ], dtype=int)

    def random_demo(self, target_id: str, seed: int, exclude_uid: Optional[str] = None) -> Dict[str, Any]:
        rng = np.random.default_rng(stable_seed(target_id, seed))
        for _ in range(50):
            row = self.rows[int(rng.integers(0, len(self.rows)))]
            if row["function_uid"] != exclude_uid:
                func_lower = row.get("func", "").lower()
                if "label:" not in func_lower and "ground truth" not in func_lower and "target label" not in func_lower:
                    return row
        return row

    def shuffle_graph(self, target_id: str, seed: int, n_target_nodes: int, tol: float = 0.10,
                      exclude_uid: Optional[str] = None) -> Tuple[List[dict], List[dict], Dict[str, Any]]:
        """CPG của một hàm khác có số nút trong [ (1−tol)n ; (1+tol)n ]; nới dần nếu không có."""
        rng = np.random.default_rng(stable_seed(target_id, seed) ^ 0x5F3759DF)
        width = tol
        while True:
            lo, hi = int(np.floor(n_target_nodes * (1 - width))), int(np.ceil(n_target_nodes * (1 + width)))
            cand = np.flatnonzero((self.n_nodes >= max(lo, 1)) & (self.n_nodes <= max(hi, 1)))
            cand = [i for i in cand if self.rows[i].get("nodes") and self.rows[i]["function_uid"] != exclude_uid]
            if cand or width > 2.0:
                break
            width *= 2
        if not cand:
            raise ValueError("Không có donor graph nào cho target " + str(target_id))
        row = self.rows[int(rng.choice(cand))]
        return row["nodes"], row["edges"], {"donor_uid": row["function_uid"], "donor_nodes": int(len(row["nodes"])),
                                            "tolerance_used": width}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
def closed_prefix(nodes: List[dict], edges: List[dict], max_nodes: int, max_edges: int) -> Tuple[List[dict], List[dict]]:
    kept = nodes[:max_nodes]
    ids = {str(n.get("id", i)) for i, n in enumerate(kept)}
    closed = [e for e in edges
              if str(e.get("start", e.get("source"))) in ids and str(e.get("end", e.get("target"))) in ids]
    return kept, closed[:max_edges]


def format_nodes(nodes: List[dict]) -> str:
    lines = []
    for i, n in enumerate(nodes):
        code = str(n.get("code", "")).strip().replace("\n", " ")
        if len(code) > 40:
            code = code[:40] + "..."
        ntype = n.get("type", n.get("label", "Node"))
        lines.append(f"Node {n.get('id', i)}: ({ntype}) '{code}'" if code else f"Node {n.get('id', i)}: ({ntype})")
    return "\n".join(lines) if lines else "[No Node Information Available]"


def format_edges(edges: List[dict]) -> str:
    lines = [f"Edge: Node {e.get('start', e.get('source'))} -> {e.get('type', 'CONNECTED_TO')} -> Node {e.get('end', e.get('target'))}"
             for e in edges]
    return "\n".join(lines) if lines else "[No Edge Information Available]"


def render_graph(policy: str, spec: Dict[str, Any], counter: TokenCounter, budget: int,
                 prefix: Dict[str, int], seed: int, donors: Optional[DonorPool]) -> Tuple[str, Dict[str, Any]]:
    nodes, edges = spec.get("nodes") or [], spec.get("edges") or []
    info: Dict[str, Any] = {"policy": policy, "available_nodes": len(nodes), "available_edges": len(edges)}
    if policy == "none":
        return "", {**info, "rendered_nodes": 0, "rendered_edges": 0, "tokens": 0}
    if policy == "h2":
        text = spec.get("h2_evidence") or ""
        if not text.strip():
            return "", {**info, "rendered_nodes": 0, "rendered_edges": 0, "tokens": 0, "missing": True}
        fit = counter.fit(text, budget)
        return (NODE_HEAD.replace("node information", "guarded evidence") + "\n" + fit.text), {
            **info, "tokens": fit.tokens, "truncated": fit.truncated}
    if policy == "shuffle":
        if donors is None:
            raise ValueError("B1-shuf cần DonorPool")
        nodes, edges, donor = donors.shuffle_graph(spec["id"], seed, len(nodes), exclude_uid=spec.get("function_uid"))
        info.update(donor)
        policy = "prefix" if spec.get("shuffle_render", "prefix") == "prefix" else "fill"
    if not nodes:
        return "", {**info, "rendered_nodes": 0, "rendered_edges": 0, "tokens": 0, "missing": True}
    if policy == "prefix":
        kn, ke = closed_prefix(nodes, edges, prefix["nodes"], prefix["edges"])
        text = f"{NODE_HEAD}\n{format_nodes(kn)}\n{EDGE_HEAD}\n{format_edges(ke)}"
        fit = counter.fit(text, budget)
        return fit.text, {**info, "rendered_nodes": len(kn), "rendered_edges": len(ke), "tokens": fit.tokens, "truncated": fit.truncated}
    if policy == "fill":
        # thêm nút theo thứ tự cho đến khi hết ngân sách token; cạnh đóng trong tập nút đã chọn
        lo, hi = 1, len(nodes)
        best = None
        while lo <= hi:
            mid = (lo + hi) // 2
            kn, ke = closed_prefix(nodes, edges, mid, 10 ** 6)
            text = f"{NODE_HEAD}\n{format_nodes(kn)}\n{EDGE_HEAD}\n{format_edges(ke)}"
            if counter.count(text) <= budget:
                best, lo = (text, kn, ke), mid + 1
            else:
                hi = mid - 1
        if best is None:
            kn, ke = closed_prefix(nodes, edges, 1, 10 ** 6)
            text = f"{NODE_HEAD}\n{format_nodes(kn)}\n{EDGE_HEAD}\n{format_edges(ke)}"
            fit = counter.fit(text, budget)
            return fit.text, {**info, "rendered_nodes": len(kn), "rendered_edges": len(ke), "tokens": fit.tokens, "truncated": True}
        text, kn, ke = best
        return text, {**info, "rendered_nodes": len(kn), "rendered_edges": len(ke), "tokens": counter.count(text),
                      "truncated": len(kn) < len(nodes)}
    raise ValueError("graph policy không hợp lệ: " + policy)


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------
def _flip_words(text: str) -> str:
    """Đảo mọi từ chỉ nhãn trong văn bản tự do (dùng cho khối Key difference khi đảo nhãn)."""
    tmp = re.sub(r"\bNon-vulnerable\b", "\x00NV\x00", text, flags=re.I)
    tmp = re.sub(r"\bVulnerable\b", "Non-vulnerable", tmp, flags=re.I)
    tmp = tmp.replace("\x00NV\x00", "Vulnerable")
    tmp2 = re.sub(r"\bsafe\b", "\x00S\x00", tmp, flags=re.I)
    tmp2 = re.sub(r"\bunsafe\b", "safe", tmp2, flags=re.I)
    return tmp2.replace("\x00S\x00", "unsafe")


def render_demos(arm_cfg: Dict[str, Any], spec: Dict[str, Any], counter: TokenCounter, budget_each: int,
                 seed: int, donors: Optional[DonorPool]) -> Tuple[str, Dict[str, Any]]:
    policy = arm_cfg.get("demo", "none")
    label_policy = arm_cfg.get("label", "true")
    info: Dict[str, Any] = {"policy": policy, "label_policy": label_policy, "demos": []}
    if policy == "none":
        return "", {**info, "tokens": 0}
    if policy == "contrastive":
        demos = list(spec.get("demonstrations_pair") or spec.get("demonstrations") or [])
    else:
        demos = list(spec.get("demonstrations") or [])
    if policy == "random":
        if donors is None:
            raise ValueError("B2-rand cần DonorPool")
        base_uid = demos[0]["function_uid"] if demos else None
        demos = [donors.random_demo(spec["id"], seed, exclude_uid=base_uid)]
        info["donor_uid"] = demos[0]["function_uid"]
    if policy in ("retrieved", "random", "labelonly") and len(demos) < 1:
        raise ValueError("Arm cần một demonstration")
    if policy == "contrastive" and len(demos) != 2:
        raise ValueError("Họ B3 cần đúng hai demonstration (vulnerable trước, safe sau)")

    def shown_label(t: int) -> int:
        return 1 - int(t) if label_policy == "flip" else int(t)

    blocks: List[str] = []
    total = 0
    if policy == "labelonly":
        d = demos[0]
        lab = LABEL_WORD[shown_label(d["target"])]
        text = f"A function similar to the one above was labelled {lab}."
        info["demos"].append({"function_uid": d["function_uid"], "true_label": int(d["target"]), "displayed_label": shown_label(d["target"]), "code_shown": False})
        return text, {**info, "tokens": counter.count(text)}
    if policy in ("retrieved", "random"):
        d = demos[0]
        fit = counter.fit(d["func"].strip(), budget_each)
        if label_policy == "none":
            head = "The following is a related example."
            disp = None
        else:
            disp = shown_label(d["target"])
            head = f"The following is an example, and it is {LABEL_WORD[disp]}."
        blocks.append(f"{head}\n{fit.text}")
        total += fit.tokens
        info["demos"].append({"function_uid": d["function_uid"], "true_label": int(d["target"]), "displayed_label": disp,
                              "code_shown": True, "tokens": fit.tokens, "truncated": fit.truncated, "original_tokens": fit.original_tokens})
        return "\n\n".join(blocks), {**info, "tokens": total}
    # contrastive (B3 family)
    ordered = demos[::-1] if arm_cfg.get("order") == "swap" else demos
    for d in ordered:
        fit = counter.fit(d["func"].strip(), budget_each)
        disp = shown_label(d["target"])
        blocks.append(f"The following example is {LABEL_WORD[disp]}.\n{fit.text}")
        total += fit.tokens
        info["demos"].append({"function_uid": d["function_uid"], "true_label": int(d["target"]), "displayed_label": disp,
                              "code_shown": True, "tokens": fit.tokens, "truncated": fit.truncated, "original_tokens": fit.original_tokens})
    diff = (spec.get("security_difference") or "").strip()
    if arm_cfg.get("diff", False) and diff:
        if label_policy == "flip":
            diff = _flip_words(diff)
        fit = counter.fit("Key difference: " + diff, budget_each // 3)
        blocks.append(fit.text)
        total += fit.tokens
        info["diff_block"] = {"tokens": fit.tokens, "truncated": fit.truncated}
    else:
        info["diff_block"] = None
    return "\n\n".join(blocks), {**info, "tokens": total}


# ---------------------------------------------------------------------------
# Lắp prompt theo Hình 6
# ---------------------------------------------------------------------------
@dataclass
class Rendered:
    prompt: str
    evidence: Dict[str, Any]


def render_arm(spec: Dict[str, Any], arm: str, seed: int = 42, counter: Optional[TokenCounter] = None,
               donors: Optional[DonorPool] = None, budget: Optional[Dict[str, int]] = None,
               graph_prefix: Optional[Dict[str, int]] = None, arms: Optional[Dict[str, Dict[str, Any]]] = None) -> Rendered:
    for forbidden in ("target", "target_label", "label", "ground_truth"):
        if forbidden in spec:
            raise ValueError("Nhãn của target không được đi vào bộ dựng prompt: " + forbidden)
    arms = arms or ARMS
    if arm not in arms:
        raise ValueError("Arm không hợp lệ: " + arm)
    cfg = arms[arm]
    counter = counter or TokenCounter(None)
    budget = {**DEFAULT_BUDGET, **(budget or {})}
    prefix = {**DEFAULT_GRAPH_PREFIX, **(graph_prefix or {})}

    code_fit = counter.fit(spec["query_code"].strip(), budget["target_code"], marker="\n/* [TRUNCATED TARGET] */")
    graph_text, graph_info = render_graph(cfg.get("graph", "none"), spec, counter, budget["graph"], prefix, seed, donors)
    demo_text, demo_info = render_demos(cfg, spec, counter, budget["demo"], seed, donors)

    parts = [ROLE, code_fit.text, QUESTION]
    if graph_text:
        parts.append(graph_text)
    if demo_text:
        parts.append(demo_text)
    parts.append(ANSWER)
    prompt = "\n\n".join(parts)
    total = counter.count(prompt)
    evidence = {
        "arm": arm, "seed": int(seed), "id": spec["id"], "repeat": bool(cfg.get("repeat", False)),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "tokens": {"code": code_fit.tokens, "graph": graph_info.get("tokens", 0), "demo": demo_info.get("tokens", 0),
                   "total": total, "approx": counter.approx},
        "truncated": {"code": code_fit.truncated, "graph": bool(graph_info.get("truncated", False)),
                      "demo": any(d.get("truncated", False) for d in demo_info.get("demos", []))},
        "graph": graph_info, "demo": demo_info,
        "order": ["role", "code", "question", "graph", "demonstration", "answer"],
    }
    if total + budget["reserve"] > budget["total"]:
        raise ValueError(f"Vượt ngân sách context: {total} + {budget['reserve']} > {budget['total']} (arm {arm}, id {spec['id']})")
    return Rendered(prompt, evidence)


# ---------------------------------------------------------------------------
# Tiện ích kiểm thử
# ---------------------------------------------------------------------------
BLOCK_NAMES = ("role", "code", "question", "graph", "demo", "answer")


def split_blocks(prompt: str) -> Dict[str, str]:
    """Tách prompt thành các khối theo mốc văn bản cố định để diff giữa hai arm."""
    blocks = {k: "" for k in BLOCK_NAMES}
    body = prompt
    assert body.startswith(ROLE)
    body = body[len(ROLE):].strip("\n")
    blocks["role"] = ROLE
    code, _, rest = body.partition("\n\n" + QUESTION)
    blocks["code"] = code.strip("\n")
    blocks["question"] = QUESTION
    rest = rest.strip("\n")
    assert rest.endswith(ANSWER)
    rest = rest[: -len(ANSWER)].strip("\n")
    if rest.startswith(NODE_HEAD) or rest.startswith(NODE_HEAD.replace("node information", "guarded evidence")):
        # graph kết thúc trước khối demo (nếu có): demo bắt đầu bằng "The following" hoặc "A function similar"
        m = re.search(r"\n\n(?=The following|A function similar)", rest)
        if m:
            blocks["graph"], blocks["demo"] = rest[: m.start()], rest[m.end():]
        else:
            blocks["graph"] = rest
    else:
        blocks["demo"] = rest
    blocks["answer"] = ANSWER
    return blocks


def diff_blocks(prompt_a: str, prompt_b: str) -> List[str]:
    a, b = split_blocks(prompt_a), split_blocks(prompt_b)
    return [k for k in BLOCK_NAMES if a[k] != b[k]]


def assert_no_label_leak(prompt: str, label_words: Sequence[str] = ("Label:", "Ground truth", "TARGET LABEL")) -> None:
    for w in label_words:
        if w.lower() in prompt.lower():
            raise AssertionError("Prompt chứa dấu hiệu nhãn của target: " + w)


def load_arms(path) -> Dict[str, Dict[str, Any]]:
    import yaml
    data = yaml.safe_load(open(path, encoding="utf-8"))
    return {a["name"]: {k: v for k, v in a.items() if k != "name"} for a in data["arms"]}
