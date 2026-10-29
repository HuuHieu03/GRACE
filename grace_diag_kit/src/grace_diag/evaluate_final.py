"""Sinh toàn bộ bảng kết quả từ thư mục runs/final/ và giao thức đã khóa.

Cấu trúc đầu vào: runs/final/<dataset>/<split>/<arm>/<seed>/records.jsonl, mỗi dòng theo schema B.2:
  id, dataset, split ("validation"|"test"), arm, seed, s, pred_argmax, valid, label[, group]
Các mốc có giám sát (SUP-*) đọc từ anchor_scores.csv (supervised_anchor.py) với cột label lấy
từ manifest.

Đầu ra (CSV + LaTeX):
  table_A_metrics.csv       mọi arm × dataset × seed: AUROC, AUPRC, MCC/BA/F1 tại s≥0,5 và tại τ*, tỷ lệ đoán 1, invalid
  table_B_contrasts.csv     các cặp đăng ký trước: Δ, CI 95%, McNemar, p Holm, kết luận theo biên δ
  table_C_sensitivity.csv   độ nhạy nhãn demo (B2/B2-flip/B2-rep; B3/B3-flip)
  fig_roc_<dataset>.png, fig_operating_points_<dataset>.png
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import stats as S

METRIC_FUNS = {"mcc": S.mcc, "auroc": S.auroc, "auprc": S.auprc, "ba": S.balanced_accuracy, "f1": S.f1}


def load_runs(root: Path) -> Dict[Tuple[str, str, int, str], Dict[str, Dict]]:
    """-> {(dataset, arm, seed, split): {id: record}}"""
    data: Dict[Tuple[str, str, int, str], Dict[str, Dict]] = defaultdict(dict)
    for path in sorted(root.glob("*/*/*/*/records.jsonl")):
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            data[(r["dataset"], r["arm"], int(r["seed"]), r["split"])][str(r["id"])] = r
    return data


def load_anchor(csv_path: Optional[Path], labels: Dict[Tuple[str, str], Dict[str, int]], data) -> None:
    if not csv_path or not csv_path.exists():
        return
    for r in csv.DictReader(open(csv_path, encoding="utf-8")):
        ds = r.get("dataset", "")
        key = (ds, r["arm"], int(r["seed"]), r["split"])
        lab = labels.get((ds, r["split"]), {}).get(r["id"])
        if lab is None:
            continue
        data[key][r["id"]] = {"id": r["id"], "dataset": ds, "split": r["split"], "arm": r["arm"], "seed": int(r["seed"]),
                              "s": float(r["score"]), "pred_argmax": int(float(r["score"]) >= 0.5), "valid": True, "label": lab}


def arrays(records: Dict[str, Dict], ids: List[str]):
    y = np.array([records[i]["label"] for i in ids], dtype=int)
    s = np.array([records[i]["s"] if records[i]["valid"] and records[i]["s"] == records[i]["s"] else np.nan for i in ids], dtype=float)
    valid = np.array([bool(records[i]["valid"]) for i in ids])
    pred = np.array([records[i]["pred_argmax"] if records[i]["valid"] else -1 for i in ids], dtype=int)
    grp = np.array([records[i].get("group") for i in ids]) if all("group" in records[i] for i in ids) else None
    return y, s, valid, pred, grp


def table_a(data, out_dir: Path, grid=None) -> Dict[Tuple[str, str, int], float]:
    rows, taus = [], {}
    keys = sorted({(d, a, sd) for (d, a, sd, sp) in data})
    for d, a, sd in keys:
        val, test = data.get((d, a, sd, "validation")), data.get((d, a, sd, "test"))
        if not test:
            continue
        ids = sorted(test)
        y, s, valid, pred, _ = arrays(test, ids)
        tau = 0.5
        if val:
            vids = sorted(val)
            yv, sv, vv, _, _ = arrays(val, vids)
            tau, _ = S.pick_threshold(yv[vv], sv[vv], grid)
        taus[(d, a, sd)] = tau
        ok = valid
        m05 = S.thresholded_metrics(y[ok], pred[ok])
        mt = S.thresholded_metrics(y[ok], (s[ok] >= tau).astype(int))
        rows.append({"dataset": d, "arm": a, "seed": sd, "n": len(ids), "invalid_rate": float((~valid).mean()),
                     "auroc": S.auroc(y[ok], s[ok]), "auprc": S.auprc(y[ok], s[ok]),
                     "mcc@0.5": m05["mcc"], "ba@0.5": m05["balanced_accuracy"], "f1@0.5": m05["f1"], "ppr@0.5": m05["positive_rate"],
                     "tau*": tau, "mcc@tau": mt["mcc"], "ba@tau": mt["balanced_accuracy"], "f1@tau": mt["f1"], "ppr@tau": mt["positive_rate"],
                     "TP": m05["TP"], "FP": m05["FP"], "TN": m05["TN"], "FN": m05["FN"]})
    for d in sorted({k[0] for k in keys}):
        any_test = next((data[k] for k in data if k[0] == d and k[3] == "test"), None)
        if any_test:
            y = np.array([r["label"] for r in any_test.values()])
            for name, m in S.constant_baselines(y).items():
                rows.append({"dataset": d, "arm": name, "seed": 0, "n": len(y), **{f"{k}@0.5": v for k, v in m.items() if k in ("mcc", "f1")},
                             "ba@0.5": m["balanced_accuracy"]})
    write_csv(out_dir / "table_A_metrics.csv", rows)
    write_latex(out_dir / "table_A_metrics.tex", rows, ["dataset", "arm", "seed", "auroc", "auprc", "mcc@0.5", "mcc@tau", "ba@tau", "f1@tau", "ppr@0.5", "invalid_rate"])
    return taus


def table_b(data, taus, contrasts: List[Dict], out_dir: Path, n_boot: int, seed: int) -> List[Dict]:
    rows, pvals = [], {}
    for c in contrasts:
        for d in (c.get("datasets") or sorted({k[0] for k in data})):
            A, B = data.get((d, c["a"], c.get("seed", 42), "test")), data.get((d, c["b"], c.get("seed", 42), "test"))
            if not A or not B:
                rows.append({"contrast": c["name"], "dataset": d, "status": "missing arm"})
                continue
            ids = sorted(set(A) & set(B))
            ya, sa, va, pa, ga = arrays(A, ids)
            yb, sb, vb, pb, gb = arrays(B, ids)
            ok = va & vb
            y = ya[ok]
            for metric in c.get("metrics", ["mcc", "auroc"]):
                if metric in ("auroc", "auprc"):
                    xa, xb = sa[ok], sb[ok]
                else:
                    ta, tb = taus.get((d, c["a"], c.get("seed", 42)), 0.5), taus.get((d, c["b"], c.get("seed", 42)), 0.5)
                    xa, xb = (sa[ok] >= ta).astype(int), (sb[ok] >= tb).astype(int)
                ci = S.paired_bootstrap(y, xa, xb, METRIC_FUNS[metric], n_boot=n_boot, seed=seed, groups=ga[ok] if ga is not None else None)
                margin = c.get("margins", {}).get(metric, 0.0)
                row = {"contrast": c["name"], "hypothesis": c.get("hypothesis", ""), "dataset": d, "metric": metric,
                       "n_paired_valid": int(ok.sum()), "delta": ci.delta, "ci_lo": ci.lo, "ci_hi": ci.hi,
                       "n_degenerate_boot": ci.n_degenerate, "margin": margin, "verdict": S.verdict(ci, margin),
                       "verdict_text": S.VERDICTS[S.verdict(ci, margin)]}
                if metric == "mcc":
                    mc = S.mcnemar_test(y, xa, xb)
                    row.update({"mcnemar_b": mc["b"], "mcnemar_c": mc["c"], "mcnemar_p": mc["p_value"]})
                    pvals[f"{c['name']}|{d}"] = mc["p_value"]
                rows.append(row)
    adj = S.holm(pvals) if pvals else {}
    for r in rows:
        key = f"{r.get('contrast')}|{r.get('dataset')}"
        if r.get("metric") == "mcc" and key in adj:
            r["mcnemar_p_holm"] = adj[key]
    write_csv(out_dir / "table_B_contrasts.csv", rows)
    write_latex(out_dir / "table_B_contrasts.tex", rows, ["contrast", "dataset", "metric", "delta", "ci_lo", "ci_hi", "margin", "verdict"])
    return rows


def table_c(data, out_dir: Path, seed: int = 42) -> List[Dict]:
    rows = []
    for d in sorted({k[0] for k in data}):
        for base, flip in (("B2", "B2-flip"), ("B3", "B3-flip")):
            Bk, Fk, Rk = data.get((d, base, seed, "test")), data.get((d, flip, seed, "test")), data.get((d, "B2-rep", seed, "test"))
            if not (Bk and Fk and Rk):
                continue
            ids = sorted(set(Bk) & set(Fk) & set(Rk))
            y, _, vb, pb, _ = arrays(Bk, ids)
            _, _, vf, pf, _ = arrays(Fk, ids)
            _, _, vr, pr, _ = arrays(Rk, ids)
            rows.append({"dataset": d, "base_arm": base, "flip_arm": flip, **S.label_sensitivity(y, pb, pf, pr, vb, vf, vr)})
    write_csv(out_dir / "table_C_sensitivity.csv", rows)
    return rows


def figures(data, taus, out_dir: Path, arms=("B0", "B2", "B3", "SUP-LR"), seed: int = 42) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import roc_curve
    except Exception:
        return
    for d in sorted({k[0] for k in data}):
        fig, ax = plt.subplots(figsize=(4.2, 4))
        for a in arms:
            rec = data.get((d, a, seed, "test"))
            if not rec:
                continue
            ids = sorted(rec)
            y, s, v, _, _ = arrays(rec, ids)
            fpr, tpr, _ = roc_curve(y[v], s[v])
            ax.plot(fpr, tpr, label=f"{a} (AUROC {S.auroc(y[v], s[v]):.2f})")
        ax.plot([0, 1], [0, 1], "k--", lw=0.8)
        ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate"); ax.set_title(d); ax.legend(fontsize=7)
        fig.tight_layout(); fig.savefig(out_dir / f"fig_roc_{d}.png", dpi=200); plt.close(fig)
        fig, ax = plt.subplots(figsize=(4.8, 3.2))
        pts = []
        for (dd, a, sd, sp), rec in data.items():
            if dd != d or sp != "test" or sd != seed or not a.startswith("B"):
                continue
            ids = sorted(rec); y, s, v, p, _ = arrays(rec, ids)
            m = S.thresholded_metrics(y[v], p[v])
            pts.append((a, m["positive_rate"], float("nan") if m["mcc"] is None else m["mcc"]))
        for a, x, yv in pts:
            ax.scatter(x, yv, s=18); ax.annotate(a, (x, yv), fontsize=6, xytext=(2, 2), textcoords="offset points")
        ax.axhline(0, color="k", lw=0.6); ax.set_xlabel("Tỷ lệ đoán 1 (s ≥ 0,5)"); ax.set_ylabel("MCC"); ax.set_title(d)
        fig.tight_layout(); fig.savefig(out_dir / f"fig_operating_points_{d}.png", dpi=200); plt.close(fig)


def write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def write_latex(path: Path, rows: List[Dict], cols: List[str]) -> None:
    def fmt(v):
        if v is None:
            return "N/A"
        if isinstance(v, float):
            return "N/A" if v != v else f"{v:.3f}"
        return str(v)
    lines = ["\\begin{tabular}{" + "l" * len(cols) + "}", "\\toprule", " & ".join(cols).replace("_", "\\_") + " \\\\", "\\midrule"]
    for r in rows:
        lines.append(" & ".join(fmt(r.get(c)) for c in cols).replace("_", "\\_") + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    path.write_text("\n".join(lines), encoding="utf-8")


def _main():
    import argparse, yaml
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", required=True, type=Path)
    ap.add_argument("--protocol", required=True, type=Path)
    ap.add_argument("--anchor-csv", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    proto = yaml.safe_load(a.protocol.read_text(encoding="utf-8"))
    data = load_runs(a.runs)
    labels = {}
    for (d, arm, sd, sp), rec in data.items():
        labels.setdefault((d, sp), {}).update({i: r["label"] for i, r in rec.items()})
    load_anchor(a.anchor_csv, labels, data)
    a.out.mkdir(parents=True, exist_ok=True)
    taus = table_a(data, a.out, proto.get("thresholds", {}).get("grid"))
    table_b(data, taus, proto["primary_contrasts"], a.out, proto["stats"]["n_boot"], proto["stats"]["bootstrap_seed"])
    table_c(data, a.out)
    figures(data, taus, a.out)
    json.dump({f"{k[0]}|{k[1]}|{k[2]}": v for k, v in taus.items()}, open(a.out / "thresholds.json", "w"), indent=2)
    print("wrote", a.out)


if __name__ == "__main__":
    _main()
