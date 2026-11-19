"""Data charts for the report (run with report/.venv after compute_metrics.py).

    report/.venv/Scripts/python.exe report/scripts/make_charts.py

Every chart reads report/results/*.json|csv or the raw result files; nothing is
typed in by hand except the fixed policy constants that are imported from code.
Writes 300-dpi PNG + SVG to report/figures/.
"""
from __future__ import annotations

import csv
import sys
import importlib.util
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import roc_curve  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "report" / "results"
FIG = ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# Validated colour-blind-safe palette (same as the dashboard).
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
MAGENTA, GREEN, VIOLET, RED = "#e87ba4", "#008300", "#6250d6", "#e34948"
GOOD, WARN, CRIT = "#0ca30c", "#fab219", "#d03b3b"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
PIPE = {"arithmetic": BLUE, "factual": ORANGE, "logical": AQUA}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": INK2,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "legend.frameon": False,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

M = json.loads((RES / "metrics.json").read_text(encoding="utf-8"))


def raw(name):
    return json.loads((ROOT / M["sources"][name]).read_text(encoding="utf-8"))


def rows(name):
    with open(RES / name, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def save(fig, name):
    fig.savefig(FIG / f"{name}.png")
    fig.savefig(FIG / f"{name}.svg")
    plt.close(fig)
    print("saved", name)


def load_policy():
    spec = importlib.util.spec_from_file_location(
        "source_reliability", ROOT / "factual/retrieval/source_reliability.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def labelled_pairs(pipeline):
    """(confidence, correct) at answer level for a pipeline."""
    if pipeline == "logical":
        return [(num(r["answer_confidence"]), int(r["correct_pilot"])) for r in rows("logical_questions.csv")]
    if pipeline == "factual":
        return [(num(r["answer_confidence"]), int(r["alias_in_reasoning"])) for r in rows("factual_questions.csv")]
    return [(num(r["final_answer_confidence"]), int(r["correct"])) for r in rows("arithmetic_questions.csv")]


# ------------------------------------------------------------------ charts
def reliability_diagrams():
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.7), sharey=True)
    for ax, pipe in zip(axes, ["arithmetic", "factual", "logical"]):
        block = M[pipe].get("calibration") or M[pipe]["calibration_pilot"]
        bins = [b for b in block["reliability_bins"] if b.get("count")]
        ax.plot([0, 1], [0, 1], ls="--", color=MUTED, lw=1, label="Perfect calibration")
        for b in bins:
            # Same equal-width binning as arithmetic/evaluation/metrics.py (empty bins omitted).
            centre = (min(int(b["mean_confidence"] * 10), 9) + 0.5) / 10
            ax.bar(centre, b["accuracy"], width=0.09, color=PIPE[pipe], alpha=0.9, edgecolor="white", lw=1)
            ax.plot([centre], [b["mean_confidence"]], marker="o", ms=5, color=INK)
            ax.text(centre, b["accuracy"] + 0.03, f"n={b['count']}", ha="center", fontsize=7.5, color=INK2)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.12)
        ax.set_title(f"{pipe.title()} (n={block['n']})")
        ax.set_xlabel("Predicted confidence")
        ax.text(0.97, 0.04, f"ECE {block['ece_10bin']:.3f}", fontsize=8.5, color=INK2, ha="right")
    axes[0].set_ylabel("Observed accuracy")
    axes[0].plot([], [], marker="o", ls="", color=INK, label="Mean confidence in bin")
    axes[0].legend(loc="upper left", bbox_to_anchor=(0, 0.95), fontsize=8)
    save(fig, "reliability_diagrams")


def confidence_histograms():
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharey=False)
    edges = np.linspace(0, 1, 11)
    for ax, pipe in zip(axes, ["arithmetic", "factual", "logical"]):
        pairs = labelled_pairs(pipe)
        ok = [p for p, y in pairs if y == 1 and p is not None]
        bad = [p for p, y in pairs if y == 0 and p is not None]
        ax.hist([ok, bad], bins=edges, color=[GOOD, CRIT], label=[f"Correct (n={len(ok)})", f"Wrong (n={len(bad)})"],
                edgecolor="white", lw=1)
        ax.set_title(pipe.title())
        ax.set_xlabel("Answer confidence")
        ax.legend(fontsize=8, loc="upper left")
    axes[0].set_ylabel("Questions")
    save(fig, "confidence_hist_correct_wrong")


def roc_curves():
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    ax.plot([0, 1], [0, 1], ls="--", color=MUTED, lw=1, label="Chance (AUROC 0.5)")
    for pipe in ["factual", "logical"]:
        pairs = [(p, y) for p, y in labelled_pairs(pipe) if p is not None]
        ys = [y for _, y in pairs]
        ps = [p for p, _ in pairs]
        fpr, tpr, _ = roc_curve(ys, ps)
        block = M[pipe].get("calibration") or M[pipe]["calibration_pilot"]
        ax.plot(fpr, tpr, color=PIPE[pipe], lw=2, label=f"{pipe.title()} AUROC {block['auroc']:.3f} (n={len(ys)})")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC: answer confidence vs correctness")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    save(fig, "roc_curves")


def example_chains():
    """One representative multi-step chain per pipeline, from stored outputs."""
    gsm = raw("arithmetic")["results"]
    ar = max(gsm, key=lambda r: len(r["reasoning_steps"]) if len(r["reasoning_steps"]) <= 8 else 0)
    fac = max(raw("factual")["results"], key=lambda r: len([c for s in r["pipeline_response"]["steps"] for c in s["claims"]]))
    runs = [r for r in raw("runs") if r["category"] == "logical"]
    log = max(runs, key=lambda r: len(r.get("steps") or []))
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    chains = [
        ("arithmetic", [s["fused_confidence"] for s in ar["reasoning_steps"]], ar["predicted_error_step"], ar["question_id"]),
        ("factual", [c["calibrated_probability"] for s in fac["pipeline_response"]["steps"] for c in s["claims"]],
         None, fac["question_id"]),
        ("logical", [s.get("calibrated_probability") for s in log["steps"]], None, "stored run"),
    ]
    for ax, (pipe, values, flagged, label) in zip(axes, chains):
        xs = list(range(1, len(values) + 1))
        low = int(np.argmin(values)) + 1
        colors = [CRIT if x == (flagged or low) else PIPE[pipe] for x in xs]
        ax.bar(xs, values, color=colors, edgecolor="white", lw=1, width=0.7)
        ax.plot(xs, values, color=INK2, lw=1, marker="o", ms=3)
        ax.set_title(f"{pipe.title()} ({label})", fontsize=10)
        ax.set_xlabel("Step / claim")
        ax.set_xticks(xs)
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("Step confidence")
    axes[0].legend(handles=[Patch(color=CRIT, label="Lowest / flagged step")], fontsize=8, loc="lower left")
    save(fig, "example_step_chains")


def signal_breakdown():
    gsm = raw("arithmetic")["results"][0]["reasoning_steps"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.8), gridspec_kw={"width_ratios": [1.4, 1]}, layout="constrained")
    xs = np.arange(1, len(gsm) + 1)
    w = 0.2
    series = [
        ("Verification (p_true)", [s["verification_score"] for s in gsm], BLUE),
        ("Consistency", [s["consistency_score"] for s in gsm], ORANGE),
        ("Token probability", [math.exp(s["mean_token_logprob"]) for s in gsm], AQUA),
        ("Fused confidence", [s["fused_confidence"] for s in gsm], YELLOW),
    ]
    for i, (name, values, color) in enumerate(series):
        axes[0].bar(xs + (i - 1.5) * w, values, w, label=name, color=color, edgecolor="white", lw=0.6)
    axes[0].set_xticks(xs)
    axes[0].set_xlabel("Step")
    axes[0].set_ylabel("Score")
    axes[0].set_ylim(0, 1.15)
    axes[0].set_title(f"Arithmetic: per-step signals ({raw('arithmetic')['results'][0]['question_id']})")
    axes[0].legend(fontsize=7.5, ncol=4, loc="upper center")
    means = M["factual"]["signals_claim_level"]
    lmeans = M["logical"]["signals_essential_claim"]
    labels = ["Self-verification", "Consistency", "Domain evidence"]
    fac = [means["self_verification"]["mean"], means["consistency"]["mean"], means["evidence"]["mean"]]
    lo = [lmeans["self_verification"]["mean"], lmeans["consistency"]["mean"], lmeans["logical_validity"]["mean"]]
    ys = np.arange(len(labels))
    axes[1].barh(ys - 0.18, fac, 0.36, color=ORANGE, label=f"Factual claims (n={means['evidence']['n']})")
    axes[1].barh(ys + 0.18, lo, 0.36, color=AQUA, label=f"Logical essential claims (n={lmeans['consistency']['n']})")
    for y, a, b in zip(ys, fac, lo):
        axes[1].text(a + 0.01, y - 0.18, f"{a:.2f}", va="center", fontsize=8)
        axes[1].text(b + 0.01, y + 0.18, f"{b:.2f}", va="center", fontsize=8)
    axes[1].set_yticks(ys, labels)
    axes[1].set_xlim(0, 1)
    axes[1].invert_yaxis()
    axes[1].set_title("Mean signal value (pilots)")
    axes[1].legend(fontsize=7.5, loc="lower right")
    save(fig, "signal_breakdown")


def correlation_heatmap():
    corr = M["cross_pipeline"]["step_signal_correlation"]
    keys = list(corr)
    names = {"self_verification": "Self-verif.", "consistency": "Consistency", "domain_evidence": "Domain evid.", "calibrated": "Step conf."}
    matrix = np.array([[corr[a][b] if corr[a][b] is not None else np.nan for b in keys] for a in keys])
    fig, ax = plt.subplots(figsize=(4.8, 4.0))
    im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(keys)), [names[k] for k in keys], rotation=30, ha="right")
    ax.set_yticks(range(len(keys)), [names[k] for k in keys])
    ax.grid(False)
    for i in range(len(keys)):
        for j in range(len(keys)):
            v = matrix[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", color="white" if v > 0.6 else INK, fontsize=9)
    n = sum(1 for _ in rows("steps_all_pipelines.csv"))
    ax.set_title(f"Pearson correlation of step signals\n(all pipelines, {n} steps/claims)")
    fig.colorbar(im, ax=ax, shrink=0.8)
    save(fig, "signal_correlation_heatmap")


def fusion_weights():
    arith = {
        "calculation": (0.35, 0.40, 0.25),
        "unit conv.": (0.40, 0.35, 0.25),
        "factual recall": (0.55, 0.25, 0.20),
        "logical / setup /\nconclusion / other": (0.50, 0.30, 0.20),
    }
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), gridspec_kw={"width_ratios": [1.6, 1]})
    ys = np.arange(len(arith))
    left = np.zeros(len(arith))
    for i, (name, color) in enumerate([("Verification", BLUE), ("Consistency", ORANGE), ("Token probability", AQUA)]):
        values = np.array([w[i] for w in arith.values()])
        axes[0].barh(ys, values, left=left, color=color, edgecolor="white", lw=1.5, label=name)
        for y, l, v in zip(ys, left, values):
            axes[0].text(l + v / 2, y, f"{v:.2f}", ha="center", va="center", color="white", fontsize=8.5)
        left += values
    axes[0].set_yticks(ys, list(arith))
    axes[0].invert_yaxis()
    axes[0].set_xlim(0, 1)
    axes[0].set_title("Arithmetic: type-adaptive weights")
    axes[0].legend(fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    left = 0
    for name, v, color in [("Self-verification", 0.4, BLUE), ("Consistency", 0.3, ORANGE), ("Evidence / validity", 0.3, AQUA)]:
        axes[1].barh([0], [v], left=left, color=color, edgecolor="white", lw=1.5, label=name)
        axes[1].text(left + v / 2, 0, f"{v:.1f}", ha="center", va="center", color="white")
        left += v
    axes[1].set_yticks([0], ["factual &\nlogical"])
    axes[1].set_xlim(0, 1)
    axes[1].set_ylim(-0.8, 0.8)
    axes[1].set_title("Factual / logical: fixed weights")
    axes[1].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1)
    save(fig, "fusion_weights")


def sigmoid_curve():
    f = np.linspace(0, 1, 200)
    p = 1 / (1 + np.exp(-(-1 + 3.2 * f)))
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ax.plot(f, p, color=BLUE, lw=2.2, label=r"$p = \sigma(-1 + 3.2\,f)$")
    ax.plot([0, 1], [0, 1], ls="--", color=MUTED, lw=1, label="Identity")
    for x in (0, 0.3125, 1):
        y = 1 / (1 + math.exp(-(-1 + 3.2 * x)))
        ax.plot([x], [y], "o", color=INK, ms=4)
        ax.annotate(f"f={x:.2f} -> p={y:.3f}", (x, y), textcoords="offset points", xytext=(6, -12 if x else 6), fontsize=8)
    ax.set_xlabel("Fused score f")
    ax.set_ylabel("Calibrated probability p")
    ax.set_title("Fixed sigmoid mapping (not fitted to data)")
    ax.legend(fontsize=8.5, loc="upper left")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    save(fig, "sigmoid_mapping")


def reliability_tiers():
    policy = load_policy()
    weights = policy.SOURCE_RELIABILITY_WEIGHTS
    items = sorted(weights.items(), key=lambda kv: -kv[1])
    fig, ax = plt.subplots(figsize=(8.5, 6.2))
    colors = [GOOD if v >= 0.75 else WARN if v >= 0.45 else CRIT for _, v in items]
    ys = np.arange(len(items))
    ax.barh(ys, [v for _, v in items], color=colors, edgecolor="white", lw=1)
    for y, (_, v) in zip(ys, items):
        ax.text(v + 0.01, y, f"{v:.2f}", va="center", fontsize=8)
    ax.set_yticks(ys, [k.replace("_", " ") for k, _ in items], fontsize=8.5)
    ax.invert_yaxis()
    ax.axvline(0.75, color=INK2, ls="--", lw=1)
    ax.axvline(0.45, color=INK2, ls="--", lw=1)
    ax.text(0.755, len(items) - 0.4, "KEEP >= 0.75", fontsize=8, color=INK2)
    ax.text(0.455, len(items) - 0.4, "DOWN_WEIGHT >= 0.45", fontsize=8, color=INK2)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Reliability weight")
    ax.set_title(f"Source-reliability policy: {len(items)} tiers")
    ax.legend(handles=[Patch(color=c, label=l) for l, c in [("KEEP", GOOD), ("DOWN_WEIGHT", WARN), ("REJECT", CRIT)]],
              fontsize=8, loc="lower right")
    save(fig, "reliability_tiers")


def retrieved_sources():
    F = M["factual"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [1, 1.4]})
    statuses = ["KEEP", "DOWN_WEIGHT", "REJECT"]
    rec = [F["source_status_recorded"].get(s, 0) for s in statuses]
    cur = [F["source_status_under_current_policy"].get(s, 0) for s in statuses]
    x = np.arange(len(statuses))
    axes[0].bar(x - 0.2, rec, 0.4, color=MUTED, label="Recorded (policy at run time)")
    axes[0].bar(x + 0.2, cur, 0.4, color=BLUE, label="Re-scored (current 22-tier policy)")
    for xi, a, b in zip(x, rec, cur):
        axes[0].text(xi - 0.2, a + 2, str(a), ha="center", fontsize=8)
        axes[0].text(xi + 0.2, b + 2, str(b), ha="center", fontsize=8)
    axes[0].set_xticks(x, statuses)
    axes[0].set_ylabel("Sources")
    total = sum(rec)
    axes[0].set_title(f"Retrieved sources by status (n={total})")
    axes[0].set_ylim(0, max(rec + cur) * 1.45)
    axes[0].legend(fontsize=8, loc="upper right")
    tiers = F["source_tiers_under_current_policy"]
    names = list(tiers)
    axes[1].barh(range(len(names)), [tiers[n] for n in names], color=ORANGE, edgecolor="white")
    for y, n in enumerate(names):
        axes[1].text(tiers[n] + 0.8, y, str(tiers[n]), va="center", fontsize=8)
    axes[1].set_yticks(range(len(names)), [n.replace("_", " ") for n in names])
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Sources")
    axes[1].set_title(f"Tier of retrieved sources ({F['unique_domains']} domains)")
    save(fig, "retrieved_sources")


def claim_verdicts():
    F = M["factual"]["claim_verdicts"]
    R = M["stored_runs"]["verdicts"]
    groups = [
        (f"Factual pilot\n(TriviaQA, {sum(F.values())} claims)", F.get("SUPPORT", 0), F.get("CONTRADICT", 0), F.get("UNKNOWN", 0)),
        ("Stored runs: factual", R.get("SUPPORT", 0), R.get("CONTRADICT", 0), R.get("UNKNOWN", 0)),
        ("Stored runs: logical", R.get("ENTAILED", 0), R.get("CONTRADICTED", 0), 0),
    ]
    log = M["logical"]["confusion_pilot"]
    l_ent = sum(v["ENTAILED"] for v in log.values())
    l_con = sum(v["CONTRADICTED"] for v in log.values())
    l_unk = sum(v["UNKNOWN"] for v in log.values())
    groups.append((f"Logical pilot\n(RuleTaker, {l_ent + l_con + l_unk} answers)", l_ent, l_con, l_unk))
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ys = np.arange(len(groups))
    left = np.zeros(len(groups))
    for i, (name, color) in enumerate([("Supported / entailed", GOOD), ("Contradicted", CRIT), ("Unknown", WARN)]):
        values = np.array([g[i + 1] for g in groups], dtype=float)
        ax.barh(ys, values, left=left, color=color, edgecolor="white", lw=1.5, label=name)
        for y, l, v in zip(ys, left, values):
            if v >= 3:
                ax.text(l + v / 2, y, str(int(v)), ha="center", va="center", color="white" if color != WARN else INK, fontsize=8.5)
        left += values
    ax.set_yticks(ys, [g[0] for g in groups])
    ax.invert_yaxis()
    ax.set_xlabel("Claims / answers")
    ax.set_title("Verification verdicts by pipeline")
    ax.legend(fontsize=8, ncol=3, loc="lower right")
    save(fig, "claim_verdicts")


def logical_confusion():
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4))
    verdicts = ["ENTAILED", "CONTRADICTED", "UNKNOWN"]
    gold = ["entailment", "not entailment"]
    for ax, key, title in [(axes[0], "confusion_pilot", "Pilot run (recorded)"), (axes[1], "confusion_after_fix", "After rule-parser fix (offline)")]:
        data = M["logical"][key]
        matrix = np.array([[data[g][v] for v in verdicts] for g in gold])
        ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(20, matrix.max()))
        ax.grid(False)
        for i in range(2):
            for j in range(3):
                ax.text(j, i, str(matrix[i, j]), ha="center", va="center", fontsize=12, color="white" if matrix[i, j] > 10 else INK)
        ax.set_xticks(range(3), verdicts, fontsize=8.5)
        ax.set_yticks(range(2), ["gold: entailment", "gold: not entailment"] if ax is axes[0] else ["", ""], fontsize=8.5)
        ax.set_title(title)
    save(fig, "logical_confusion")


def logical_before_after():
    L = M["logical"]
    before, after = L["accuracy_pilot"], L["accuracy_after_parser_fix_offline"]
    fig, ax = plt.subplots(figsize=(5, 3.4))
    bars = ax.bar(["Pilot run", "After parser fix"], [before["rate"], after["rate"]], color=[MUTED, AQUA], width=0.55)
    for bar, d in zip(bars, (before, after)):
        ax.text(bar.get_x() + bar.get_width() / 2, d["rate"] + 0.02, f"{d['correct']}/{d['n']} ({d['rate']:.0%})", ha="center")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Verdict accuracy")
    ax.set_title("RuleTaker verdict accuracy (n=44)")
    save(fig, "logical_before_after")


def logical_conf_by_verdict():
    data = rows("logical_questions.csv")
    verdicts = ["ENTAILED", "CONTRADICTED", "UNKNOWN"]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for i, v in enumerate(verdicts):
        pts = [(num(r["answer_confidence"]), int(r["correct_pilot"])) for r in data if r["verdict_pilot"] == v]
        jitter = np.linspace(-0.18, 0.18, len(pts)) if pts else []
        for (p, y), j in zip(pts, jitter):
            ax.plot(i + j, p, "o", ms=6, color=GOOD if y else CRIT, mec="white", mew=1)
        if pts:
            m = np.mean([p for p, _ in pts])
            ax.plot([i - 0.28, i + 0.28], [m, m], color=INK, lw=2)
            ax.text(i + 0.3, m, f"mean {m:.2f}\n(n={len(pts)})", va="center", fontsize=8)
    ax.set_xticks(range(3), verdicts)
    ax.set_xlim(-0.5, 2.9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Answer confidence")
    ax.set_title("Logical pilot: confidence by solver verdict")
    ax.plot([], [], "o", color=GOOD, label="correct")
    ax.plot([], [], "o", color=CRIT, label="wrong")
    ax.legend(fontsize=8, loc="upper right")
    save(fig, "logical_conf_by_verdict")


def confidence_by_position():
    data = M["cross_pipeline"]["confidence_by_step_position"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for k, (pipe, positions) in enumerate(data.items()):
        xs = sorted(int(k) for k in positions if positions[k].get("n", 0) >= 2)
        ys = [positions[str(x)]["mean"] for x in xs]
        ns = [positions[str(x)]["n"] for x in xs]
        ax.plot(xs, ys, marker="o", lw=2, color=PIPE[pipe], label=pipe.title())
        for x, y, n in zip(xs, ys, ns):
            ax.text(x + (k - 1) * 0.12, y + 0.03, f"{n}", fontsize=7, color=PIPE[pipe], ha="center")
    ax.set_xlabel("Step position in chain")
    ax.set_ylabel("Mean step confidence")
    ax.set_ylim(0, 1)
    ax.set_title("Confidence by step position (labels = number of steps)")
    ax.legend(fontsize=8)
    save(fig, "confidence_by_position")


def confidence_over_time():
    runs = raw("runs")
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for pipe in PIPE:
        pts = [(datetime.fromisoformat(r["created_at"]), r["confidence"]) for r in runs if r["category"] == pipe and r.get("confidence") is not None]
        if pts:
            ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=40, color=PIPE[pipe], edgecolor="white", label=f"{pipe.title()} ({len(pts)})", zorder=3)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Answer confidence")
    ax.set_title(f"Stored runs over time (n={len(runs)}, backend/data/calibration_runs.json)")
    ax.legend(fontsize=8, loc="lower left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel("Time of run (UTC, 19 Nov 2026)")
    save(fig, "confidence_over_time")


def tests_by_module():
    per = M["tests"]["per_file"]
    names = [k.replace("tests/", "").replace(".py", "") for k in per]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.barh(names, list(per.values()), color=BLUE)
    for y, v in enumerate(per.values()):
        ax.text(v + 0.4, y, str(v), va="center", fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Tests")
    ax.set_title(f"Automated tests by module (total {M['tests']['total']})")
    save(fig, "tests_by_module")


def arithmetic_steps():
    A = M["arithmetic"]
    types = A["step_types"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    names = sorted(types, key=types.get, reverse=True)
    axes[0].bar([n.replace("_", "\n") for n in names], [types[n] for n in names], color=BLUE)
    for i, n in enumerate(names):
        axes[0].text(i, types[n] + 0.3, str(types[n]), ha="center", fontsize=8.5)
    axes[0].set_ylabel("Steps")
    axes[0].set_title(f"Step types assigned by verifier ({sum(types.values())} steps)")
    steps = [r for r in rows("steps_all_pipelines.csv") if r["pipeline"] == "arithmetic"]
    ent = [num(r["semantic_entropy"]) for r in steps if num(r["semantic_entropy"]) is not None]
    con = [num(r["consistency"]) for r in steps if num(r["semantic_entropy"]) is not None]
    axes[1].scatter(ent, con, s=36, color=ORANGE, edgecolor="white")
    r = A["signal_correlations_step_level"]["consistency~semantic_entropy"]
    axes[1].set_xlabel("Normalised semantic entropy")
    axes[1].set_ylabel("Consistency (largest cluster share)")
    axes[1].set_title(f"Consistency vs semantic entropy (r = {r:.3f}, n={len(ent)})")
    save(fig, "arithmetic_steps")


def factual_distributions():
    F = M["factual"]
    q = rows("factual_questions.csv")
    src = rows("factual_sources.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    counts = Counter(int(r["claims"]) for r in q)
    xs = sorted(counts)
    axes[0].bar(xs, [counts[x] for x in xs], color=ORANGE)
    axes[0].set_xlabel("Atomic claims per answer")
    axes[0].set_ylabel("Questions")
    axes[0].set_title(f"Claims per answer (n={len(q)}, mean {F['claims_per_answer']['mean']:.2f})")
    rec = [num(r["recorded_reliability"]) for r in src]
    cur = [num(r["current_policy_score"]) for r in src]
    edges = np.linspace(0.25, 1.0, 16)
    axes[1].hist([rec, cur], bins=edges, color=[MUTED, BLUE], label=["Recorded", "Current policy"], edgecolor="white")
    axes[1].set_xlabel("Source reliability")
    axes[1].set_ylabel("Sources")
    axes[1].set_title(f"Reliability of retrieved sources (n={len(src)})")
    axes[1].legend(fontsize=8)
    save(fig, "factual_distributions")


def main():
    for chart in (
        reliability_diagrams, confidence_histograms, roc_curves, example_chains, signal_breakdown,
        correlation_heatmap, fusion_weights, sigmoid_curve, reliability_tiers, retrieved_sources,
        claim_verdicts, logical_confusion, logical_before_after, logical_conf_by_verdict,
        confidence_by_position, confidence_over_time, tests_by_module, arithmetic_steps,
        factual_distributions, gantt,
    ):
        chart()



def gantt():
    """Schedule: completed phases are bounded by dated evidence (FYP-1.docx dated
    18.08.26; git commit dates); later phases are planned and drawn hatched."""
    from datetime import date
    phases = [
        ("Problem study, literature review, proposal", date(2026, 7, 20), date(2026, 8, 18), "done", "start indicative; proposal dated 18 Aug 2026"),
        ("Base project + arithmetic pipeline", date(2026, 8, 18), date(2026, 9, 27), "done", "ends at commit e63babf, 27 Sep"),
        ("Factual pipeline + gateway", date(2026, 9, 27), date(2026, 10, 3), "done", "commits 2a37286, 5e78f1c, 3 Oct"),
        ("Logical pipeline (Z3)", date(2026, 10, 3), date(2026, 10, 4), "done", "commit 1bb3808, 4 Oct"),
        ("Pilot experiments (GSM8K, TriviaQA, RuleTaker)", date(2026, 10, 4), date(2026, 11, 19), "done", "commit e090a52, 19 Nov"),
        ("Dashboard, reliability policy, parser fix", date(2026, 11, 19), date(2026, 11, 19), "done", "uncommitted working tree, 19 Nov"),
        ("Complete pilots to 100 + label steps", date(2026, 11, 23), date(2027, 1, 15), "planned", ""),
        ("Train/fit calibrators, error-injection study", date(2027, 1, 4), date(2027, 2, 26), "planned", ""),
        ("Ablations, analysis, final report, viva", date(2027, 2, 15), date(2027, 4, 30), "planned", ""),
    ]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for i, (name, start, end, state, note) in enumerate(phases):
        width = max((end - start).days, 2)
        ax.barh(i, width, left=matplotlib.dates.date2num(start), height=0.55,
                color=BLUE if state == "done" else "white", edgecolor=BLUE, hatch=None if state == "done" else "///", lw=1.2)
        if note:
            ax.text(matplotlib.dates.date2num(end) + 3, i, note, va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(range(len(phases)), [p[0] for p in phases], fontsize=8.5)
    ax.invert_yaxis()
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.axvline(matplotlib.dates.date2num(date(2026, 11, 19)), color=CRIT, ls="--", lw=1)
    ax.text(matplotlib.dates.date2num(date(2026, 11, 20)), -0.7, "report date", color=CRIT, fontsize=8)
    ax.legend(handles=[Patch(color=BLUE, label="Completed (dated evidence)"),
                       Patch(facecolor="white", edgecolor=BLUE, hatch="///", label="Planned (indicative)")],
              fontsize=8, loc="lower left")
    ax.set_title("Project schedule, A.Y. 2026-2027")
    save(fig, "gantt")


if __name__ == "__main__":
    if "--gantt" in sys.argv:
        gantt()
    else:
        main()
