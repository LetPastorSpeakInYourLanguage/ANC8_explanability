"""Render every figure the results support, from the artifacts on disk.

    python scripts/make_figures.py                 # everything available
    python scripts/make_figures.py --only cascade  # one family

Figures are built from committed CSV/JSON artifacts rather than from a live
model fit, so this is cheap, deterministic, and re-runnable after any stage
completes. A figure whose inputs do not exist yet is skipped with a note
instead of failing the run -- the ladder and policy panels appear once those
stages have produced their tables.

Output: outputs/figures/*.png (200 dpi) and *.svg, plus figures_manifest.csv
listing every figure, its inputs and a one-line caption.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUTPUTS = ROOT / "outputs"
ENHANCED = OUTPUTS / "enhanced"
LADDER_DIR = OUTPUTS / "ladder"
POLICY = OUTPUTS / "policy"
FIG = OUTPUTS / "figures"

# ---------------------------------------------------------------- house style
INK = "#17181a"
MUTED = "#6f7276"
LINE = "#d9dadd"
SET21C = "#b06a3b"   # the 21-predictor set
POOLC = "#2a6f6f"    # the full candidate pool / its models
POS = "#1f6f4a"
NEG = "#9d3b3b"
SEQ = ["#2a6f6f", "#4b8f88", "#7aaea2", "#b0cbc0", "#c9a227", "#8a6fa8", "#b06a3b"]
RUNG = {"anc1plus": "#7aaea2", "anc4plus": "#4b8f88", "anc8plus": "#1f5757"}

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": LINE,
    "axes.labelcolor": INK,
    "axes.titlesize": 11,
    "axes.titleweight": "semibold",
    "axes.titlelocation": "left",
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": "#eceef0",
    "grid.linewidth": 0.8,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "legend.frameon": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

MANIFEST: list[dict] = []


def strip(ax, left=True, bottom=True):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)


def save(fig, slug, title, caption, inputs):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{slug}.png")
    fig.savefig(FIG / f"{slug}.svg")
    plt.close(fig)
    rel = []
    for i in inputs:
        try:
            rel.append(str(Path(i).relative_to(ROOT)).replace("\\", "/"))
        except ValueError:
            rel.append(str(i))
    MANIFEST.append({"figure": slug, "title": title, "caption": caption,
                     "inputs": "; ".join(rel)})
    print(f"  [ok]   {slug}.png")


def skip(slug, why):
    print(f"  [skip] {slug}: {why}")


def have(*paths):
    return all(Path(p).exists() for p in paths)


def wmean(x, w):
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    return float(np.sum(x * w) / np.sum(w))


def load_frame():
    p = ENHANCED / "ANC8_analysis_frozen_v2.pkl"
    if not p.exists():
        return None
    df = pd.read_pickle(p)
    df["_w"] = df.v005 / 1e6
    return df


# ============================================================== 1. the cascade
def fig_cascade(df):
    if df is None or "anc_contacts" not in df:
        return skip("fig01_cascade", "analysis dataset not found")
    w = df._w.to_numpy()
    n = df.anc_contacts.fillna(0).to_numpy()
    reach = {k: wmean(n >= k, w) for k in (1, 4, 8)}

    started = n >= 1
    at4 = n >= 4
    c14 = wmean(n[started] >= 4, w[started])
    c48 = wmean(n[at4] >= 8, w[at4])

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.6, 3.8),
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    labels = ["Any contact\n(ANC1+)", "Four or more\n(ANC4+)", "Eight or more\n(ANC8+)"]
    vals = [reach[1], reach[4], reach[8]]
    bars = ax.bar(labels, [v * 100 for v in vals], width=0.58,
                  color=[RUNG["anc1plus"], RUNG["anc4plus"], RUNG["anc8plus"]])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 100 + 1.8, f"{v * 100:.1f}%",
                ha="center", fontweight="semibold")
    ax.set_ylim(0, 100)
    ax.set_ylabel("share of women (survey-weighted)")
    ax.set_title("Where women reach on the ANC ladder")
    strip(ax)

    trans = [("of those who start,\nreach 4+", c14), ("of those at 4+,\nreach 8+", c48)]
    y = np.arange(len(trans))[::-1]
    bx.barh(y, [t[1] * 100 for t in trans], height=0.45, color=POOLC)
    bx.barh(y, [100 - t[1] * 100 for t in trans], height=0.45,
            left=[t[1] * 100 for t in trans], color="#e6e8ea")
    for yi, (lab, v) in zip(y, trans):
        bx.text(v * 100 - 2, yi, f"{v * 100:.0f}% continue", ha="right",
                va="center", color="white", fontweight="semibold")
        bx.text(v * 100 + 2, yi, f"{100 - v * 100:.0f}% lost", ha="left",
                va="center", color=NEG, fontweight="semibold")
    bx.set_yticks(y)
    bx.set_yticklabels([t[0] for t in trans])
    bx.set_xlim(0, 100)
    bx.set_xlabel("percent")
    bx.set_title("The leak is between the 4th and 8th contact")
    bx.grid(False)
    strip(bx, left=False)
    fig.tight_layout()

    save(fig, "fig01_cascade", "The national ANC cascade",
         f"Weighted attainment {reach[1]*100:.1f}/{reach[4]*100:.1f}/{reach[8]*100:.1f}%; "
         f"continuation {c14*100:.0f}% then {c48*100:.0f}%.",
         [ENHANCED / "ANC8_analysis_frozen_v2.pkl"])


# ==================================================== 2. regional decomposition
def regional_cascade(df):
    w = df._w.to_numpy()
    n = df.anc_contacts.fillna(0).to_numpy()
    rows = []
    for region, g in df.groupby("region", observed=True):
        i = df.index.get_indexer(g.index)
        ni, wi = n[i], w[i]
        rows.append({
            "region": str(region), "n": len(i),
            "never": wmean(ni < 1, wi),
            "start_lt4": wmean((ni >= 1) & (ni < 4), wi),
            "four_lt8": wmean((ni >= 4) & (ni < 8), wi),
            "eight_plus": wmean(ni >= 8, wi),
        })
    return pd.DataFrame(rows).sort_values("eight_plus")


def fig_regional(df):
    if df is None or "region" not in df:
        return skip("fig02_regional_cascade", "analysis dataset not found")
    c = regional_cascade(df)
    fig, ax = plt.subplots(figsize=(8.8, 5.6))
    y = np.arange(len(c))
    segs = [("never", "#b8564f", "never start"),
            ("start_lt4", "#dc9a52", "start, stop before 4"),
            ("four_lt8", "#7aaea2", "reach 4, stop before 8"),
            ("eight_plus", "#1f5757", "reach 8+")]
    left = np.zeros(len(c))
    for key, col, lab in segs:
        v = c[key].to_numpy() * 100
        ax.barh(y, v, left=left, height=0.68, color=col, label=lab)
        for yi, (l, vi) in enumerate(zip(left, v)):
            if vi >= 9:
                ax.text(l + vi / 2, yi, f"{vi:.0f}", ha="center", va="center",
                        color="white", fontsize=8)
        left += v
    ax.set_yticks(y)
    ax.set_yticklabels(c.region)
    ax.set_xlim(0, 100)
    ax.set_xlabel("percent of women (survey-weighted)")
    ax.set_title("Where each region loses women")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.09), fontsize=8)
    ax.grid(False)
    strip(ax, left=False)
    FIG.mkdir(parents=True, exist_ok=True)
    c.to_csv(FIG / "fig02_regional_cascade.csv", index=False)
    save(fig, "fig02_regional_cascade", "Regional cascade decomposition",
         "Regions with similar ANC8+ coverage lose women at opposite points.",
         [ENHANCED / "ANC8_analysis_frozen_v2.pkl"])


# ================================================ 3. continuation equity (4->8)
def fig_continuation_equity(df):
    if df is None:
        return skip("fig03_continuation_equity", "analysis dataset not found")
    n = df.anc_contacts.fillna(0).to_numpy()
    at4 = n >= 4
    sub = df[at4]
    nn, ww = n[at4], df._w.to_numpy()[at4]

    panels = []
    for var in ("wealth_quintile", "residence", "maternal_education"):
        if var not in sub:
            continue
        rows = []
        for lev, g in sub.groupby(var, observed=True):
            i = sub.index.get_indexer(g.index)
            if len(i) < 25:
                continue
            rows.append((str(lev), wmean(nn[i] >= 8, ww[i]), len(i)))
        if rows:
            panels.append((var, rows))
    if not panels:
        return skip("fig03_continuation_equity", "no grouping variables present")

    fig, axes = plt.subplots(1, len(panels), figsize=(3.5 * len(panels), 3.6))
    axes = np.atleast_1d(axes)
    for ax, (var, rows) in zip(axes, panels):
        rows = sorted(rows, key=lambda r: r[1])
        y = np.arange(len(rows))
        ax.barh(y, [r[1] * 100 for r in rows], height=0.6, color=POOLC)
        for yi, r in zip(y, rows):
            ax.text(r[1] * 100 + 1, yi, f"{r[1]*100:.0f}%", va="center", fontsize=8)
        ax.set_yticks(y)
        ax.set_yticklabels([r[0] for r in rows], fontsize=8)
        ax.set_xlim(0, max(60, max(r[1] for r in rows) * 100 + 12))
        ax.set_title(var.replace("_", " "), fontsize=10)
        ax.set_xlabel("continue 4 -> 8 (%)")
        ax.grid(False)
        strip(ax, left=False)
    fig.suptitle("Among women who already reached four contacts, who finishes",
                 x=0.02, ha="left", fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save(fig, "fig03_continuation_equity", "Continuation from 4 to 8 by circumstance",
         "All women shown have already attended four times, so this isolates the "
         "cost of repeat attendance from initial demand.",
         [ENHANCED / "ANC8_analysis_frozen_v2.pkl"])


# ========================================================= 4. model leaderboard
def fig_leaderboard(outcome="anc8plus"):
    d = ENHANCED / outcome / "development_oof_performance.csv"
    h = ENHANCED / outcome / "heldout_performance.csv"
    slug = f"fig04_leaderboard_{outcome}"
    if not have(d, h):
        return skip(slug, "performance tables not found")
    dev = pd.read_csv(d).set_index("model")
    held = pd.read_csv(h)
    held = held[held.generation.astype(str).str.startswith("V2")].set_index("model")
    common = [m for m in dev.index if m in held.index]
    if not common:
        return skip(slug, "no models shared between tables")
    tab = pd.DataFrame({"dev": dev.loc[common, "AP"],
                        "held": held.loc[common, "AP"]}).sort_values("dev")

    fig, ax = plt.subplots(figsize=(8.4, 0.34 * len(tab) + 2.0))
    y = np.arange(len(tab))
    for yi, (dv, hv) in zip(y, tab.to_numpy()):
        ax.plot([hv, dv], [yi, yi], color=LINE, lw=2, zorder=1)
    ax.scatter(tab.dev, y, s=34, color=MUTED, zorder=2, label="development (out-of-fold)")
    ax.scatter(tab.held, y, s=46, color=POOLC, zorder=3, label="held-out (locked)")
    ax.set_yticks(y)
    ax.set_yticklabels(tab.index, fontsize=8.5)
    ax.set_xlabel("average precision")
    ax.set_title(f"Every model is optimistic in development ({outcome})")
    ax.legend(loc="lower right", fontsize=8)
    strip(ax, left=False)
    gap = float((tab.dev - tab.held).mean())
    save(fig, slug, "Development vs held-out AP",
         f"Mean development-to-held-out drop {gap:+.3f} AP -- the signature of "
         "selection over the same folds, not of a better model.", [d, h])


# ========================================================= 5. calibration curves
def fig_calibration(outcome="anc8plus"):
    p = ENHANCED / outcome / "heldout_locked_predictions_v2.csv"
    slug = "fig05_calibration"
    if not p.exists():
        return skip(slug, "locked held-out predictions not found")
    d = pd.read_csv(p)
    cols = set(d.columns)
    models = [m for m in ["Explainable Boosting", "XGBoost", "Logistic regression",
                          "V1 XGBoost", "V1 Logistic regression"]
              if f"prob::{m}" in cols]
    # Column names in the predictions file keep their generation prefix;
    # the legend names the predictor set instead.
    show = lambda m: (m.replace("V1 ", "") + " (21 predictors)") if m.startswith("V1")         else f"{m} (full pool)"
    if not models:
        return skip(slug, "requested models absent")

    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    ax.plot([0, 1], [0, 1], color=LINE, lw=1, ls="--", zorder=1)
    colors = [POOLC, "#4b8f88", "#7aaea2", SET21C, "#d9a06a"]
    y = d.y.to_numpy()
    w = d.w.to_numpy()
    for m, col in zip(models, colors):
        pr = d[f"prob::{m}"].to_numpy()
        q = np.quantile(pr, np.linspace(0, 1, 11))
        idx = np.clip(np.digitize(pr, q[1:-1]), 0, 9)
        xs, ys = [], []
        for b in range(10):
            sel = idx == b
            if sel.sum() < 15:
                continue
            xs.append(wmean(pr[sel], w[sel]))
            ys.append(wmean(y[sel], w[sel]))
        ax.plot(xs, ys, marker="o", ms=4, lw=1.6, color=col, label=show(m),
                ls="--" if m.startswith("V1") else "-")
    lim = 0.85
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("predicted probability (weighted decile mean)")
    ax.set_ylabel("observed attainment")
    ax.set_title("Calibration on the locked held-out set")
    ax.legend(fontsize=8, loc="upper left")
    strip(ax)
    save(fig, slug, "Held-out calibration",
         "Weighted decile means; the diagonal is perfect calibration.", [p])


# ==================================================== 6. stability across seeds
def fig_stability(outcome="anc8plus"):
    p = ENHANCED / outcome / "stability_repeated_splits.csv"
    s = ENHANCED / outcome / "stability_summary.json"
    if not have(p, s):
        return skip("fig06_stability", "stability artifacts not found")
    d = pd.read_csv(p)
    js = json.loads(Path(s).read_text())

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.4, 3.8))
    y = np.arange(len(d))
    ax.hlines(y, d.original_AP, d.enhanced_AP, color=LINE, lw=1.6)
    ax.scatter(d.original_AP, y, s=20, color=SET21C, label="21-predictor set")
    ax.scatter(d.enhanced_AP, y, s=24, color=POOLC, label="full candidate pool")
    ax.set_yticks([])
    ax.set_ylabel(f"{len(d)} repeated splits")
    ax.set_xlabel("average precision")
    ax.set_title("The full pool wins on every split")
    ax.legend(fontsize=8, loc="lower right")
    strip(ax, left=False)

    bx.hist(d.delta_AP, bins=12, color=POOLC, alpha=0.85)
    bx.axvline(0, color=NEG, lw=1.2)
    bx.axvline(d.delta_AP.mean(), color=INK, lw=1.4, ls="--")
    bx.text(d.delta_AP.mean(), bx.get_ylim()[1] * 0.92,
            f"  mean {d.delta_AP.mean():+.4f}", fontsize=8.5)
    bx.set_xlabel("AP gain, full pool over the 21-predictor set")
    bx.set_ylabel("splits")
    bx.set_title(f"{js['AP']['seeds_enhanced_better']}/{js['n_seeds']} splits favour it")
    strip(bx)
    fig.tight_layout()
    save(fig, "fig06_stability", "Repeated-split stability",
         f"Mean AP gain {js['AP']['delta_mean']:+.4f} "
         f"[{js['AP']['delta_lo']:+.4f}, {js['AP']['delta_hi']:+.4f}] over "
         f"{js['n_seeds']} independent splits.", [p, s])


# =============================================== 7. paired bootstrap, held-out
def fig_bootstrap(outcome="anc8plus"):
    p = ENHANCED / outcome / "paired_bootstrap_distribution.csv"
    c = ENHANCED / outcome / "paired_bootstrap_ci.json"
    if not have(p, c):
        return skip("fig07_bootstrap", "bootstrap artifacts not found")
    d = pd.read_csv(p)
    ci = json.loads(Path(c).read_text())

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.6))
    for ax, key, lab in ((axes[0], "d_AP", "AP"), (axes[1], "d_AUROC", "AUROC")):
        v = d[key].to_numpy()
        ax.hist(v, bins=45, color=POOLC, alpha=0.8)
        lo, hi = ci[key]["lo"], ci[key]["hi"]
        ax.axvspan(lo, hi, color=POOLC, alpha=0.12)
        ax.axvline(0, color=NEG, lw=1.3)
        ax.axvline(ci[key]["point"], color=INK, lw=1.4, ls="--")
        excl = ci.get(f"{key}_excludes_zero", False)
        ax.set_title(f"{lab}: {ci[key]['point']:+.3f} [{lo:+.3f}, {hi:+.3f}]"
                     + ("" if excl else "  — includes zero"), fontsize=10)
        ax.set_xlabel(f"held-out {lab} difference (full pool - 21-predictor set)")
        ax.set_ylabel("bootstrap replicates")
        strip(ax)
    fig.suptitle("One held-out set of 1,375 cannot resolve a difference this size",
                 x=0.02, ha="left", fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save(fig, "fig07_bootstrap", "Paired stratified-PSU bootstrap",
         f"{ci['champion']} (full pool) vs {ci['baseline'].replace('V1 ', '')} "
         "(21 predictors); the AP interval includes zero, "
         "which is why the repeated-split evidence carries the claim.", [p, c])


# ============================================================ 8. importance
def fig_importance(insights, top=22):
    if insights is None:
        return skip("fig08_global_importance", "insights.json not found")
    imp = pd.Series(insights["global_importance"]).sort_values(ascending=False).head(top)
    dirs = insights.get("direction", {})
    dom = insights.get("domains", {})
    doms = sorted({dom.get(k, "other") for k in imp.index})
    palette = {d: SEQ[i % len(SEQ)] for i, d in enumerate(doms)}

    fig, ax = plt.subplots(figsize=(8.6, 0.32 * len(imp) + 1.8))
    y = np.arange(len(imp))[::-1]
    ax.barh(y, imp.to_numpy(), height=0.68,
            color=[palette[dom.get(k, "other")] for k in imp.index])
    for yi, (k, v) in zip(y, imp.items()):
        dd = dirs.get(k)
        mark = {"increases": "↑", "decreases": "↓"}.get(dd, "")
        if mark:
            ax.text(v * 1.02, yi, f" {mark}", va="center", fontsize=9,
                    color=POS if dd == "increases" else NEG)
    ax.set_yticks(y)
    ax.set_yticklabels(imp.index, fontsize=8.5)
    ax.set_xlabel("mean absolute contribution to the log-odds (EBM, exact)")
    ax.set_title("What the model actually uses")
    ax.legend(handles=[Patch(color=palette[d], label=d) for d in doms],
              ncol=min(3, len(doms)), fontsize=8, loc="lower right")
    strip(ax, left=False)
    save(fig, "fig08_global_importance", "Global predictor importance",
         "Exact additive attribution from the Explainable Boosting model; "
         "arrows give the direction of the dominant effect.",
         [ROOT / "app/public/insights.json"])


def fig_shapes(insights, n=9):
    if insights is None:
        return skip("fig09_shape_functions", "insights.json not found")
    imp = pd.Series(insights["global_importance"]).sort_values(ascending=False)
    shapes = insights["shape_functions"]
    picks = [k for k in imp.index if k in shapes][:n]
    if not picks:
        return skip("fig09_shape_functions", "no shape functions present")

    rows = int(np.ceil(len(picks) / 3))
    fig, axes = plt.subplots(rows, 3, figsize=(10.4, 2.6 * rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, k in zip(axes, picks):
        s = shapes[k]
        cuts = s.get("cuts")
        if s["kind"] == "continuous" and cuts:
            cuts = np.asarray(cuts, float)
            sc = np.asarray(s["scores"], float)
            step = (cuts[1] - cuts[0]) if len(cuts) > 1 else 1.0
            edges = np.concatenate([[cuts[0] - step], cuts, [cuts[-1] + step]])
            m = min(len(sc), len(edges))
            ax.step(edges[:m], sc[:m], where="post", color=POOLC, lw=1.7)
            ax.axhline(0, color=LINE, lw=1)
        else:
            vals = s.get("values") or []
            sc = np.asarray(s["scores"], float)[:len(vals)]
            order = np.argsort(sc)
            ax.barh(np.arange(len(sc)), sc[order], height=0.66,
                    color=[POS if v > 0 else NEG for v in sc[order]])
            ax.set_yticks(np.arange(len(sc)))
            ax.set_yticklabels([str(vals[i])[:20] for i in order], fontsize=7)
            ax.axvline(0, color=LINE, lw=1)
        ax.set_xlabel(k, fontsize=8.5)
        ax.set_ylabel("log-odds", fontsize=8)
        ax.tick_params(labelsize=7.5)
        strip(ax)
    for ax in axes[len(picks):]:
        ax.set_visible(False)
    fig.suptitle("How each predictor enters the model", x=0.02, ha="left",
                 fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save(fig, "fig09_shape_functions", "Fitted shape functions",
         "The exact learned curve for each top predictor, on the log-odds scale. "
         "Flat regions are values the model does not distinguish.",
         [ROOT / "app/public/insights.json"])


# ========================================================= 10. decision curve
def fig_decision_curve(outcome="anc8plus"):
    p = ENHANCED / outcome / "decision_curve.csv"
    if not p.exists():
        return skip("fig10_decision_curve", "decision curve not found")
    d = pd.read_csv(p)
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ax.plot(d.threshold, d.treat_all, color=LINE, lw=1.4, label="treat all")
    ax.plot(d.threshold, d.treat_none, color="#bfc2c6", lw=1.2, ls=":", label="treat none")
    name = d.model_name.iloc[0] if "model_name" in d else "model"
    ax.plot(d.threshold, d.model, color=POOLC, lw=1.9, label=f"full pool ({name})")
    if "v1_xgboost" in d:
        ax.plot(d.threshold, d.v1_xgboost, color=SET21C, lw=1.6, ls="--", label="21-predictor XGBoost")
    ax.set_xlabel("threshold probability")
    ax.set_ylabel("net benefit")
    ax.set_title("Decision curve, held-out set")
    ax.legend(fontsize=8)
    strip(ax)
    save(fig, "fig10_decision_curve", "Decision-curve analysis",
         "Net benefit across plausible thresholds; the useful range is where "
         "the model sits above both default strategies.", [p])


# ==================================================== 11. subgroup performance
def fig_subgroups(outcome="anc8plus"):
    p = ENHANCED / outcome / "subgroup_performance.csv"
    if not p.exists():
        return skip("fig11_subgroups", "subgroup table not found")
    d = pd.read_csv(p)
    d = d[d.n >= 40].copy()
    d["key"] = d.variable + ": " + d.level.astype(str)
    d = d.sort_values("V2_AUROC")

    fig, ax = plt.subplots(figsize=(8.2, 0.28 * len(d) + 1.8))
    y = np.arange(len(d))
    ax.hlines(y, d.V1_AUROC, d.V2_AUROC, color=LINE, lw=1.6)
    ax.scatter(d.V1_AUROC, y, s=20, color=SET21C, label="21-predictor set")
    ax.scatter(d.V2_AUROC, y, s=24, color=POOLC, label="full candidate pool")
    ax.axvline(0.5, color=NEG, lw=1, ls=":")
    ax.set_yticks(y)
    ax.set_yticklabels(d.key, fontsize=7.5)
    ax.set_xlabel("AUROC within subgroup")
    ax.set_title("Where the model discriminates, and where it does not")
    ax.legend(fontsize=8, loc="lower right")
    strip(ax, left=False)
    save(fig, "fig11_subgroups", "Subgroup discrimination",
         "Several regional subgroups sit at or below chance; a national AUROC "
         "hides that. Subgroup n is small, so these are indicative.", [p])


# ======================================================== 14-15. screening
def fig_screening(top=25):
    p = ENHANCED / "candidate_screening.csv"
    if not p.exists():
        return skip("fig14_screening", "screening table not found")
    d = pd.read_csv(p)
    d = d[d.weighted_auc.notna()].copy()
    d["strength"] = (d.weighted_auc - 0.5).abs() + 0.5
    best = d.sort_values("strength", ascending=False).head(top)

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.0, 0.3 * top + 2.0),
                                 gridspec_kw={"width_ratios": [1.5, 1]})
    y = np.arange(len(best))[::-1]
    admitted = best.screen_status.astype(str).str.contains("candidate")
    ax.barh(y, best.strength, height=0.68,
            color=[POOLC if a else "#c9ccd0" for a in admitted])
    ax.set_yticks(y)
    ax.set_yticklabels(list(best.variable), fontsize=8)
    ax.set_xlim(0.5, float(best.strength.max()) * 1.02)
    ax.set_xlabel("survey-weighted univariate AUC (folded)")
    ax.set_title("Strongest candidates in the full IR file")
    ax.legend(handles=[Patch(color=POOLC, label="admitted"),
                       Patch(color="#c9ccd0", label="excluded (timing or leakage)")],
              fontsize=8, loc="lower right")
    strip(ax, left=False)

    counts = d.screen_status.astype(str).value_counts()
    yy = np.arange(len(counts))[::-1]
    bx.barh(yy, counts.to_numpy(), height=0.6, color=SEQ[1])
    bx.set_yticks(yy)
    bx.set_yticklabels([str(i)[:34] for i in counts.index], fontsize=8)
    for yi, v in zip(yy, counts.to_numpy()):
        bx.text(v, yi, f" {v}", va="center", fontsize=8)
    bx.set_xlabel("variables")
    bx.set_title("Screening outcome, all IR columns")
    bx.grid(False)
    strip(bx, left=False)
    fig.tight_layout()
    save(fig, "fig14_screening", "Systematic candidate screening",
         "Every column of the Individual Recode screened on the development "
         "fold only; admission required the variable to be measured before or early in the pregnancy.", [p])


def fig_redundancy(top=16):
    p = ENHANCED / "redundancy" / "grouped_importance.csv"
    if not p.exists():
        return skip("fig24_redundancy", "redundancy analysis not run yet")
    d = pd.read_csv(p).head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.6, 0.36 * len(d) + 1.8))
    y = np.arange(len(d))
    ax.barh(y, d.grouped_importance, height=0.66, color="#c9ccd0",
            label="all copies of the variable, added together")
    ax.barh(y, d.largest_single_member, height=0.66, color=POOLC,
            label="the single column the ranking actually saw")
    for yi, r in zip(y, d.itertuples()):
        if r.n_members > 1:
            ax.text(r.grouped_importance * 1.01, yi,
                    f"  rank {int(r.rank_grouped)} (was {int(r.rank_as_single_columns)})",
                    va="center", fontsize=7.5, color=MUTED)
    ax.set_yticks(y)
    ax.set_yticklabels(d.group, fontsize=8.5)
    ax.set_xlabel("mean absolute contribution to the log-odds")
    ax.set_title("A variable the survey ships twice is ranked at half its weight")
    ax.legend(fontsize=8, loc="lower right")
    strip(ax, left=False)
    save(fig, "fig24_redundancy", "Importance before and after grouping duplicates",
         "Travel time to hospital and residence are both present twice under "
         "different names, so per-column importance halves them.", [p])


def fig_set_comparison():
    base = ENHANCED / "set_comparison"
    files = [base / f"{r}_repeated.csv" for r in ("anc1plus", "anc4plus", "anc8plus")]
    files = [f for f in files if f.exists()]
    if not files:
        return skip("fig25_set_comparison", "set comparison not run yet")
    d = pd.concat([pd.read_csv(f) for f in files])
    rungs = [r for r in ("anc1plus", "anc4plus", "anc8plus") if r in set(d.outcome)]
    models = list(d.model.unique())
    sets = ["deduplicated 85", "enhanced 95"]
    colors = {"deduplicated 85": POOLC, "enhanced 95": "#7aaea2"}

    fig, axes = plt.subplots(len(models), len(rungs), figsize=(3.6 * len(rungs),
                             2.6 * len(models)), squeeze=False, sharey="row")
    for i, model in enumerate(models):
        for j, rung in enumerate(rungs):
            ax = axes[i][j]
            sub = d[(d.model == model) & (d.outcome == rung)]
            piv = sub.pivot_table(index="seed", columns="set", values="AP")
            for k, s in enumerate(sets):
                if s not in piv:
                    continue
                gain = (piv[s] - piv["original 21"]).to_numpy()
                x = np.full(len(gain), k) + np.linspace(-0.12, 0.12, len(gain))
                ax.scatter(x, gain, s=16, color=colors[s], alpha=0.85)
                ax.hlines(gain.mean(), k - 0.25, k + 0.25, color=INK, lw=1.6)
                ax.text(k + 0.28, gain.mean(), f"{gain.mean():+.3f}",
                        va="center", fontsize=7.5)
            ax.axhline(0, color=NEG, lw=1)
            ax.set_xticks(range(len(sets)))
            ax.set_xticklabels(["85", "95"])
            ax.set_xlim(-0.5, 1.8)
            if i == 0:
                ax.set_title(rung.replace("plus", "+").upper(), fontsize=10)
            if j == 0:
                ax.set_ylabel(f"{model}\nAP gain over the 21", fontsize=8)
            strip(ax)
    fig.suptitle("Gain over the 21-predictor set, every split shown",
                 x=0.02, ha="left", fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save(fig, "fig25_set_comparison", "21-predictor set vs the full pool (85 distinct, 95 columns)",
         "Paired repeated splits; each dot is one split, the bar its mean. "
         "Logistic regression has almost nothing to tune, so it cannot favour a "
         "set through its hyperparameters.", files)


def fig_preprocessing():
    p = ENHANCED / "preprocessing_ablation.csv"
    if not p.exists():
        return skip("fig15_preprocessing", "preprocessing ablation not found")
    d = pd.read_csv(p).sort_values("AP")
    fig, ax = plt.subplots(figsize=(7.8, 0.42 * len(d) + 1.8))
    y = np.arange(len(d))
    ax.barh(y, d.AP_vs_original, height=0.6,
            color=[POS if v > 0 else NEG for v in d.AP_vs_original])
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(d.variant, fontsize=8)
    ax.set_xlabel("AP change vs the baseline preprocessing")
    ax.set_title("Preprocessing choices barely move the result")
    strip(ax, left=False)
    save(fig, "fig15_preprocessing", "Preprocessing ablation",
         "The best variant buys +0.003 AP -- an order of magnitude less than the "
         "predictor set. Reported because a wins-only list would mislead.", [p])


# ================================================== 16-17. hyperparameter work
def fig_hyperparameters(outcome="anc8plus"):
    p = ENHANCED / outcome / "hyperparameter_ablation.csv"
    if not p.exists():
        return skip("fig16_hyperparameters", "ablation not run yet")
    d = pd.read_csv(p)
    real = d[~d.parameter.astype(str).str.startswith("(")]
    if not len(real):
        return skip("fig16_hyperparameters", "no perturbation rows")
    models = list(real.model.unique())
    fig, axes = plt.subplots(1, len(models), figsize=(4.4 * len(models), 4.6))
    axes = np.atleast_1d(axes)
    for ax, m in zip(axes, models):
        sub = (real[real.model == m].groupby("parameter").AP_vs_tuned.min()
               .sort_values().head(10))
        y = np.arange(len(sub))
        ax.barh(y, sub.to_numpy(), height=0.66, color=POOLC)
        ax.set_yticks(y)
        ax.set_yticklabels(sub.index, fontsize=8)
        ax.axvline(0, color=INK, lw=1)
        ax.set_xlabel("worst AP drop off the tuned value")
        ax.set_title(m, fontsize=10)
        strip(ax, left=False)
    fig.suptitle("Most tuned hyperparameters barely matter", x=0.02, ha="left",
                 fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save(fig, "fig16_hyperparameters", "Hyperparameter sensitivity",
         "Each bar moves one parameter away from the Optuna optimum with all "
         "others held; small bars mean the search bought little.", [p])


def fig_tuning_gain():
    rows, srcs = [], []
    for rung in ("anc1plus", "anc4plus", "anc8plus"):
        p = ENHANCED / rung / "hyperparameter_ablation.csv"
        if not p.exists():
            continue
        srcs.append(p)
        d = pd.read_csv(p)
        for m in d.model.unique():
            dflt = d[(d.model == m) & (d.parameter == "(library defaults)")]
            tund = d[(d.model == m) & (d.parameter == "(tuned optimum)")]
            if len(dflt) and len(tund):
                rows.append({"rung": rung, "model": m,
                             "defaults": float(dflt.AP.iloc[0]),
                             "tuned": float(tund.AP.iloc[0])})
    if not rows:
        return skip("fig17_tuning_gain", "no ablation tables yet")
    d = pd.DataFrame(rows)
    d["gain"] = d.tuned - d.defaults
    d = d.sort_values("gain")
    fig, ax = plt.subplots(figsize=(7.8, 0.36 * len(d) + 1.8))
    y = np.arange(len(d))
    ax.barh(y, d.gain, height=0.66, color=[RUNG.get(r, POOLC) for r in d.rung])
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.model}  ({r.rung})" for r in d.itertuples()], fontsize=8)
    ax.set_xlabel("AP bought by tuning, over library defaults")
    ax.set_title("What the whole Optuna budget actually bought")
    strip(ax, left=False)
    save(fig, "fig17_tuning_gain", "Tuning gain over library defaults",
         "Read against the ~0.08 development-to-held-out optimism gap: a tuning "
         "gain smaller than that is not evidence of better generalisation.", srcs)


# ================================================================ 18-20. ladder
def fig_ladder_performance():
    rows, srcs = [], []
    try:
        from anc8 import outcomes as oc
        prevalence = {k: v["weighted_prevalence"] for k, v in oc.OUTCOMES.items()}
    except Exception:
        prevalence = {"anc1plus": 0.7760, "anc4plus": 0.5243, "anc8plus": 0.1916}
    for rung in ("anc1plus", "anc4plus", "anc8plus"):
        p = ENHANCED / rung / "heldout_performance.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p)
        d = d[d.generation.astype(str).str.startswith("V2")]
        if not len(d):
            continue
        srcs.append(p)
        # The development champion, not the best held-out score: choosing on
        # the test set would make the comparison optimistic.
        dv = ENHANCED / rung / "development_oof_performance.csv"
        champ = None
        if dv.exists():
            dev = pd.read_csv(dv).dropna(subset=["AP"]).sort_values("AP", ascending=False)
            champ = next((m for m in dev.model if m in set(d.model)), None)
        if champ:
            best = d.set_index("model").loc[champ].copy()
            best["model"] = champ
        else:
            best = d.sort_values("AP", ascending=False).iloc[0]
        prev = prevalence.get(rung, np.nan)
        rows.append({"rung": rung, "model": best.model, "AP": float(best.AP),
                     "AUROC": float(best.AUROC), "prevalence": prev,
                     "AP_lift": float(best.AP) - prev})
    if len(rows) < 2:
        return skip("fig18_ladder_performance", "fewer than two rungs evaluated")
    d = pd.DataFrame(rows)
    order = {"anc1plus": 0, "anc4plus": 1, "anc8plus": 2}
    d = d.sort_values(by="rung", key=lambda s: s.map(order))

    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.6))
    x = np.arange(len(d))
    labs = [r.replace("plus", "+").upper() for r in d.rung]
    cols = [RUNG[r] for r in d.rung]

    axes[0].bar(x, d.prevalence * 100, color=cols, width=0.55)
    axes[0].set_title("Prevalence (a blind guess)")
    axes[0].set_ylabel("percent")
    axes[1].bar(x, d.AP, color=cols, width=0.55)
    axes[1].bar(x, d.prevalence, color="none", edgecolor=INK, lw=1.2,
                width=0.55, ls="--", label="prevalence floor")
    axes[1].set_title("Raw AP -- not comparable")
    axes[1].legend(fontsize=8)
    axes[2].bar(x, d.AUROC, color=cols, width=0.55)
    axes[2].axhline(0.5, color=NEG, lw=1, ls=":")
    axes[2].set_ylim(0.4, 1.0)
    axes[2].set_title("AUROC -- prevalence-free")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labs)
        strip(ax)
    for ax, vals, fmt in ((axes[0], d.prevalence * 100, "{:.1f}%"),
                          (axes[1], d.AP, "{:.3f}"), (axes[2], d.AUROC, "{:.3f}")):
        for xi, v in zip(x, vals):
            ax.text(xi, v, fmt.format(v), ha="center", va="bottom", fontsize=8.5)
    fig.suptitle("The easiest-looking rung is the one a blind guess already wins",
                 x=0.02, ha="left", fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    FIG.mkdir(parents=True, exist_ok=True)
    d.to_csv(FIG / "fig18_ladder_performance.csv", index=False)
    save(fig, "fig18_ladder_performance", "Performance across the ladder",
         "Development champion per rung, scored on held-out women. AP rises with "
         "prevalence and must never be compared across rungs; AUROC shows "
         "reaching care is easier to predict than completing it.", srcs)


def _ladder_shares():
    """Per-predictor importance share at each rung, averaged over the three
    methods (EBM, SHAP, drop-one) that run_ladder_analysis.py writes."""
    frames = []
    for method in ("EBM", "SHAP", "drop-one"):
        p = LADDER_DIR / f"importance_{method}.csv"
        if p.exists():
            d = pd.read_csv(p, index_col=0)
            cols = [c for c in ("anc1plus", "anc4plus", "anc8plus") if c in d.columns]
            frames.append(d[cols])
    if not frames:
        return None
    return sum(frames) / len(frames)


def fig_ladder_importance(top=18):
    piv = _ladder_shares()
    if piv is None:
        return skip("fig19_ladder_importance", "ladder analysis not run yet")
    order = [c for c in ("anc1plus", "anc4plus", "anc8plus") if c in piv.columns]
    if len(order) < 2:
        return skip("fig19_ladder_importance", "fewer than two rungs in shares")
    piv = piv[order].dropna()
    piv["span"] = piv[order[-1]] - piv[order[0]]
    piv = piv.reindex(piv[order].max(axis=1).sort_values(ascending=False).index).head(top)

    fig, ax = plt.subplots(figsize=(8.4, 0.36 * len(piv) + 1.8))
    y = np.arange(len(piv))[::-1]
    for yi, (_, r) in zip(y, piv.iterrows()):
        ax.plot([r[order[0]], r[order[-1]]], [yi, yi],
                color=POS if r["span"] > 0 else NEG, lw=1.8, alpha=0.5, zorder=2)
    for c in order:
        ax.scatter(piv[c], y, s=46, color=RUNG[c], zorder=3,
                   label=c.replace("plus", "+").upper())
    ax.set_yticks(y)
    ax.set_yticklabels([lab(p) for p in piv.index], fontsize=8.5)
    ax.set_xlabel("share of total importance within the rung (mean of EBM, SHAP, drop-one)")
    ax.set_title("What matters for reaching care is not what matters for finishing")
    ax.legend(fontsize=8, loc="lower right")
    strip(ax, left=False)
    save(fig, "fig19_ladder_importance", "Importance shift across the ladder",
         "Green links: predictors that matter more as the threshold rises "
         "(engagement-limited); red: less (access-limited). Shares averaged over "
         "three independent importance methods.",
         [LADDER_DIR / f"importance_{m}.csv" for m in ("EBM", "SHAP", "drop-one")])


def fig_domain_rollup():
    p = LADDER_DIR / "domain_rollup.csv"
    if not p.exists():
        return skip("fig20_domain_rollup", "domain roll-up not found")
    d = pd.read_csv(p)
    order = [c for c in ("anc1plus", "anc4plus", "anc8plus") if c in d.columns]
    if len(order) < 2:
        return skip("fig20_domain_rollup", "fewer than two rungs")
    piv = d.groupby("domain")[order].mean()
    piv = piv.loc[piv[order[-1]].sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    x = np.arange(len(order))
    for i, (dom, row) in enumerate(piv.iterrows()):
        ax.plot(x, row.to_numpy(), marker="o", ms=5, lw=1.8, color=SEQ[i % len(SEQ)])
        ax.annotate(str(dom), (x[-1], row.to_numpy()[-1]), textcoords="offset points",
                    xytext=(7, -3), fontsize=8, color=SEQ[i % len(SEQ)])
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("plus", "+").upper() for c in order])
    ax.set_ylabel("share of total importance (mean of three methods)")
    ax.set_title("How the balance of drivers moves up the ladder")
    ax.set_xlim(-0.2, len(order) - 0.2)
    strip(ax)
    save(fig, "fig20_domain_rollup", "Domain roll-up across the ladder",
         "Predictor importance aggregated into domains, normalised within rung, "
         "averaged over EBM, SHAP and drop-one.", [p])

# ================================================================ 21-23. policy
def fig_regional_gap():
    p = POLICY / "regional_performance.csv"
    if not p.exists():
        return skip("fig21_regional_gap", "policy analysis not run yet")
    d = pd.read_csv(p)
    d = d[d.rung == "anc8plus"].sort_values("gap")
    if not len(d):
        return skip("fig21_regional_gap", "no anc8plus rows")
    fig, ax = plt.subplots(figsize=(8.0, 0.34 * len(d) + 1.8))
    y = np.arange(len(d))
    ax.barh(y, d.gap * 100, height=0.66,
            color=[POS if v > 0 else NEG for v in d.gap])
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(d.region, fontsize=8.5)
    ax.set_xlabel("actual minus expected ANC8+ attainment (percentage points)")
    ax.set_title("Which regions beat their own circumstances")
    strip(ax, left=False)
    save(fig, "fig21_regional_gap", "Regional performance against circumstance",
         "Expected attainment predicted from wealth, education and household "
         "factors with region withheld; a positive gap means the region does "
         "better than its population profile implies.", [p])


def fig_modifiable():
    p = POLICY / "modifiable_vs_fixed.csv"
    if not p.exists():
        return skip("fig22_modifiable", "policy analysis not run yet")
    d = pd.read_csv(p)
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x = np.arange(len(d))
    wdt = 0.26
    ax.bar(x - wdt, d.all_predictors, wdt, color=POOLC, label="everything")
    ax.bar(x, d.modifiable_only, wdt, color=SEQ[2], label="service / modifiable only")
    ax.bar(x + wdt, d.fixed_only, wdt, color="#c9ccd0", label="fixed circumstance only")
    ax.axhline(0.5, color=NEG, lw=1, ls=":")
    ax.set_xticks(x)
    ax.set_xticklabels(d.rung)
    ax.set_ylim(0.4, 1.0)
    ax.set_ylabel("AUROC (development out-of-fold)")
    ax.set_title("How much rests on what a health system can change")
    ax.legend(fontsize=8)
    for xi, r in zip(x, d.itertuples()):
        for off, v in ((-wdt, r.all_predictors), (0, r.modifiable_only),
                       (wdt, r.fixed_only)):
            ax.text(xi + off, v, f"{v:.3f}", ha="center", va="bottom", fontsize=7.5)
    strip(ax)
    save(fig, "fig22_modifiable", "Modifiable versus fixed decomposition",
         "Same folds, same model, three predictor subsets.", [p])


def fig_risk_bands():
    p = POLICY / "risk_bands.csv"
    if not p.exists():
        return skip("fig23_risk_bands", "policy analysis not run yet")
    d = pd.read_csv(p)
    if "rung" in d.columns:
        d = d[d.rung.astype(str).str.contains("8")]
    if not len(d):
        return skip("fig23_risk_bands", "no rows for the ANC8+ rung")
    num = d.select_dtypes(include="number").columns
    share = next((c for c in num if "share" in c or "pct" in c or "population" in c), None)
    rate = next((c for c in num if "actual" in c or "observed" in c or "rate" in c), None)
    labcol = next((c for c in d.columns if d[c].dtype == object and c != "rung"),
                  d.columns[0])
    if share is None or rate is None:
        return skip("fig23_risk_bands", f"unexpected columns: {list(d.columns)}")
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    x = np.arange(len(d))
    ax.bar(x, d[rate] * 100, color=POOLC, width=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(d[labcol], fontsize=8, rotation=20, ha="right")
    ax.set_ylabel("observed ANC8+ attainment (%)")
    ax2 = ax.twinx()
    ax2.plot(x, d[share] * 100, color=SET21C, marker="o", ms=5, lw=1.6)
    ax2.set_ylabel("share of the population (%)", color=SET21C)
    ax2.grid(False)
    ax.set_title("Predicted-risk bands: where a targeted programme would land")
    strip(ax)
    save(fig, "fig23_risk_bands", "Near-threshold risk bands",
         "Women just below the operating threshold are the group a capacity-"
         "limited programme can realistically move.", [p])



# ============================================ 26-32. which predictors pay their way
FV = OUTPUTS / "feature_value"
WAR = OUTPUTS / "wartime"
COHORT_LABEL = {"full": "all births (6,893)", "recent": "last 24 months (sensitivity)",
                "entry": "ANC entry (5,001)"}
_LABELS = None


def lab(code):
    """Readable predictor names, taken from the web app's own label table."""
    global _LABELS
    if _LABELS is None:
        import re
        p = ROOT / "app" / "src" / "lib" / "labels.ts"
        _LABELS = {}
        if p.exists():
            _LABELS = dict(re.findall(r'^\s+([A-Za-z0-9_]+): "([^"]+)"',
                                      p.read_text(encoding="utf-8"), flags=re.M))
        _LABELS.update({"age_at_birth": "Mother's age at the birth",
                        "travel_time_min": "Travel time to hospital/health centre",
                        "household_size": "Household size",
                        "traditional_media_weekly_count": "Weekly media count (0-3)",
                        "early_anc": "First ANC contact by 3 months"})
    return _LABELS.get(code, code)


def _fv(cohort, rung, name):
    p = FV / cohort / rung / name
    return pd.read_csv(p) if p.exists() else None


def _grid(slug, title, caption, draw, height=2.9):
    done = [(c, r) for c in ("full", "recent") for r in ("anc1plus", "anc4plus", "anc8plus")
            if (FV / c / r / "summary.json").exists()]
    if not done:
        return skip(slug, "feature-value analysis not run yet")
    fig, axes = plt.subplots(2, 3, figsize=(11.6, 2 * height), squeeze=False)
    srcs = []
    for i, c in enumerate(("full", "recent")):
        for j, r in enumerate(("anc1plus", "anc4plus", "anc8plus")):
            ax = axes[i][j]
            if draw(ax, c, r):
                srcs.append(FV / c / r)
            else:
                ax.text(0.5, 0.5, "not run yet", ha="center", va="center",
                        transform=ax.transAxes, color=MUTED)
                ax.set_xticks([])
                ax.set_yticks([])
            if i == 0:
                ax.set_title(r.replace("plus", "+").upper(), fontsize=10)
            if j == 0:
                ax.set_ylabel(COHORT_LABEL[c], fontsize=8)
            strip(ax)
    fig.suptitle(title, x=0.02, ha="left", fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save(fig, slug, title, caption, srcs)


def fig_add_one():
    def draw(ax, c, r):
        d = _fv(c, r, "add_one_to_21.csv")
        if d is None:
            return False
        d = d.sort_values("gain")
        ax.bar(np.arange(len(d)), d.gain, width=0.85,
               color=[POOLC if ok else "#c9ccd0" for ok in d.clears_threshold])
        ax.axhline(0.005, color=NEG, lw=1, ls="--")
        ax.axhline(0, color=INK, lw=0.6)
        ax.set_xticks([])
        ax.text(0.03, 0.95, f"{int(d.clears_threshold.sum())} of {len(d)} clear +0.005\n"
                f"median {d.gain.median():+.4f}", transform=ax.transAxes, va="top",
                fontsize=7.5)
        return True
    _grid("fig26_add_one", "Each other candidate added, alone, to the 21-predictor set",
          "Every bar is one of the 67 pool candidates outside the 21; "
          "teal bars clear +0.005 AP on at least 4 of 5 splits. Dashed line is "
          "the threshold.", draw)


def fig_diminishing():
    def draw(ax, c, r):
        d = _fv(c, r, "cumulative_from_21.csv")
        if d is None:
            return False
        ax.plot(d.n_added, d.AP, color=POOLC, lw=1.6)
        ax.fill_between(d.n_added, d.AP - d.AP_sd, d.AP + d.AP_sd, color=POOLC, alpha=0.12)
        ax.axhline(d.AP.iloc[0], color=SET21C, lw=1, ls="--")
        best = int(d.AP.idxmax())
        ax.scatter([d.n_added[best]], [d.AP[best]], color=INK, s=14, zorder=3)
        ax.text(d.n_added[best], d.AP[best], f"  peak at {int(d.n_added[best])}",
                fontsize=7, va="bottom")
        ax.set_xlabel("new variables added, best first", fontsize=7.5)
        return True
    _grid("fig27_diminishing_returns",
          "Stacking the additions onto the 21: a few carry the gain",
          "Development AP as the 67 candidates are added in order of their "
          "individual gain; dashed line is the 21-predictor set alone; band is one "
          "SD across split seeds.", draw)


def fig_tier_ladders():
    def draw(ax, c, r):
        d = _fv(c, r, "forward_steps.csv")
        s = FV / c / r / "summary.json"
        if d is None or not s.exists():
            return False
        a = json.loads(s.read_text())["anchors"]
        colors = {"tier 1": POOLC, "tier 2": "#7aaea2", "not selected": "#c9ccd0"}
        y = np.arange(len(d))[::-1]
        ax.barh(y, d.AP - a["prevalence"], color=[colors[t] for t in d.tier], height=0.7)
        ax.axvline(a["original21"] - a["prevalence"], color=SET21C, lw=1, ls="--")
        ax.axvline(a["all88"] - a["prevalence"], color=INK, lw=1, ls=":")
        ax.set_yticks(y)
        ax.set_yticklabels([lab(p)[:28] for p in d.predictor], fontsize=6.5)
        ax.set_xlabel("AP above prevalence", fontsize=7.5)
        return True
    _grid("fig28_tier_ladders", "Forward selection: the tiers, step by step",
          "Each row adds one variable. Dark teal = tier 1 (reaches 90% of the full "
          "model's lift), light = tier 2 (each adds >= 0.005), grey = the first "
          "step that failed. Dashed = the 21-predictor set; dotted = the full pool. A selected "
          "set's development score is optimistic -- fig30 has the held-out view.",
          draw, height=3.4)


def fig_selection_frequency():
    rows = [d.assign(cohort=c) for c in ("full", "recent")
            if (d := _fv(c, "anc8plus", "selection_frequency.csv")) is not None]
    if not rows:
        return skip("fig29_selection_frequency", "bootstrap re-selection not run yet")
    d = pd.concat(rows)
    piv = d.pivot_table(index="predictor", columns="cohort", values="selected_share",
                        aggfunc="first").fillna(0)
    piv = piv.loc[piv.max(axis=1).sort_values().index].tail(18)
    fig, ax = plt.subplots(figsize=(7.8, 0.34 * len(piv) + 1.6))
    y = np.arange(len(piv))
    for k, (c, col) in enumerate((("full", POOLC), ("recent", "#7aaea2"))):
        if c in piv:
            ax.barh(y + (k - 0.5) * 0.38, piv[c], height=0.38, color=col,
                    label=COHORT_LABEL[c])
    ax.axvline(0.7, color=NEG, lw=1, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels([lab(p) for p in piv.index], fontsize=8)
    ax.set_xlabel("share of bootstrap resamples in which the variable was selected")
    ax.set_title("How often each variable is chosen again (ANC8+)")
    ax.legend(fontsize=8, loc="lower right")
    strip(ax, left=False)
    save(fig, "fig29_selection_frequency", "Selection stability",
         "Forward selection repeated on PSU-bootstrap resamples of the development "
         "set; below the dashed 70% line a variable's place is not reliable.",
         [FV / c / "anc8plus" / "selection_frequency.csv" for c in ("full", "recent")])


def fig_heldout_sets():
    order = ["tier 1", "tier 1+2", "original 21", "all 88"]

    def draw(ax, c, r):
        d = _fv(c, r, "heldout.csv")
        if d is None:
            return False
        x = np.arange(len(order))
        for k, (m, col) in enumerate((("Logistic regression", POOLC), ("LightGBM", "#7aaea2"))):
            sub = d[d.model == m].set_index("set").reindex(order)
            ax.bar(x + (k - 0.5) * 0.38, sub.AP_lift, width=0.38, color=col,
                   label=m)
        ns = d.drop_duplicates("set").set_index("set").reindex(order).n_predictors
        ax.set_xticks(x)
        names = {"original 21": "the 21", "all 88": "full pool"}
        ax.set_xticklabels([f"{names.get(o, o)}\n({'-' if pd.isna(n) else int(n)})"
                            for o, n in zip(order, ns)], fontsize=6.5)
        if (c, r) == ("full", "anc1plus"):
            ax.legend(fontsize=7, loc="lower left", framealpha=0.9)
        return True
    _grid("fig30_heldout_sets",
          "On the held-out women: compact sets against the 21 and the full pool",
          "AP above prevalence; each set fitted on development and scored once on "
          "held-out; bracketed counts are predictors. Paired bootstrap intervals "
          "against the 21 are in heldout_bootstrap.json -- most overlap zero.", draw)


def fig_tigray_did():
    p = WAR / "tigray_difference_in_differences.csv"
    if not p.exists():
        return skip("fig31_tigray_did", "wartime analysis not run yet")
    d = pd.read_csv(p)
    d = d[(d.window_shift_months == 0) & (d.controls == "peaceful regions")]
    names = {"never": "never start ANC", "start_lt4": "start, stop before 4",
             "four_lt8": "reach 4, stop before 8", "eight_plus": "reach 8+",
             "anc1plus": "ANC1+", "anc4plus": "ANC4+", "anc8plus": "ANC8+"}
    order = [m for m in ["anc1plus", "anc4plus", "anc8plus", "never", "start_lt4",
                         "four_lt8"] if m in set(d.measure)]
    d = d.set_index("measure").reindex(order)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.6, 3.8),
                                 gridspec_kw={"width_ratios": [1.1, 1]})
    y = np.arange(len(d))[::-1]
    ax.hlines(y, d.tigray_during * 100, d.tigray_after * 100, color=LINE, lw=2)
    ax.scatter(d.tigray_during * 100, y, color=NEG, s=26, label="wartime pregnancy")
    ax.scatter(d.tigray_after * 100, y, color=POOLC, s=30, label="post-war pregnancy")
    ax.set_yticks(y)
    ax.set_yticklabels([names[m] for m in d.index])
    ax.set_xlabel("percent of Tigrayan women")
    ax.set_title("Tigray, before and after the ceasefire", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    strip(ax, left=False)

    # One colour: the sign means different things per row (fewer women
    # never starting is good; more is bad), so red/green would mislead.
    bx.barh(y, d["did"] * 100, height=0.6, color=POOLC)
    bx.errorbar(d["did"] * 100, y, xerr=[(d["did"] - d.lo) * 100, (d.hi - d["did"]) * 100],
                fmt="none", ecolor=INK, lw=1, capsize=2)
    bx.axvline(0, color=INK, lw=0.8)
    bx.set_yticks(y)
    bx.set_yticklabels([])
    bx.set_ylim(ax.get_ylim())
    bx.set_xlabel("change beyond the within-region change in peaceful regions (pts)")
    bx.set_title("Difference-in-differences, 95% interval", fontsize=10)
    strip(bx, left=False)
    fig.suptitle(f"Antenatal care for pregnancies during and after the Tigray war "
                 f"(n = {int(d.tigray_during_n.iloc[0])} wartime, "
                 f"{int(d.tigray_after_n.iloc[0])} post-war)",
                 x=0.02, ha="left", fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    save(fig, "fig31_tigray_did", "Tigray wartime difference-in-differences",
         "Peaceful regions absorb the national trend and the extra recall error "
         "of older births (their within-region change is near zero); the "
         "remainder is the change associated with the war. Stratified PSU "
         "bootstrap intervals; robust to +/-3-month shifts of the war window.", [p])


def fig_regional_gap_cohort():
    p = WAR / "regional_gap_by_cohort.csv"
    if not p.exists():
        return skip("fig32_regional_gap_cohort", "wartime analysis not run yet")
    d = pd.read_csv(p)
    d = d[(d.outcome == "anc8plus") & d.cohort.isin(["full", "recent"])]
    d = d.pivot(index="region", columns="cohort", values="gap").sort_values("recent")
    fig, ax = plt.subplots(figsize=(7.8, 0.36 * len(d) + 1.6))
    y = np.arange(len(d))
    ax.hlines(y, d["full"] * 100, d["recent"] * 100, color=LINE, lw=1.8)
    ax.scatter(d["full"] * 100, y, color=SET21C, s=24, label="all births")
    ax.scatter(d["recent"] * 100, y, color=POOLC, s=30, label="births < 24 months")
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(d.index, fontsize=8.5)
    ax.set_xlabel("ANC8+ actual minus expected from circumstances (percentage points)")
    ax.set_title("Regions against their circumstances, in both birth windows")
    ax.legend(fontsize=8, loc="lower right")
    strip(ax, left=False)
    save(fig, "fig32_regional_gap_cohort", "Regional gap, all births vs recent births",
         "Expected attainment predicted with region withheld. The ranking is "
         "stable across the two windows, so it is not a period artefact.", [p])



# ================================================ 33-35. the 21 on their own
PV = OUTPUTS / "predictor_value"
HOR = OUTPUTS / "horizons"
RUNGS3 = ("anc1plus", "anc4plus", "anc8plus")
RLAB = {"anc1plus": "ANC1+", "anc4plus": "ANC4+", "anc8plus": "ANC8+"}


def fig_drop_within_21():
    frames = {r: d for r in RUNGS3
              if (d := _fv("full", r, "drop_one_within_21.csv")) is not None}
    if not frames:
        return skip("fig33_drop_within_21", "stage 0 not run yet")
    last = frames[list(frames)[-1]].sort_values("loss")
    order = list(last.predictor)
    fig, axes = plt.subplots(1, len(frames), figsize=(3.7 * len(frames) + 1.6, 6.2),
                             sharey=True, squeeze=False)
    y = np.arange(len(order))
    for ax, (r, d) in zip(axes[0], frames.items()):
        v = d.set_index("predictor").loss.reindex(order)
        ax.barh(y, v, height=0.7, color=[POS if x > 0 else "#c9ccd0" for x in v])
        ax.axvline(0, color=INK, lw=0.8)
        n0 = int((v <= 0).sum())
        ax.set_title(f"{RLAB[r]}: {n0} of 21 add nothing", fontsize=10)
        ax.set_xlabel("AP lost when dropped from the 21", fontsize=8)
        strip(ax, left=False)
    axes[0][0].set_yticks(y)
    axes[0][0].set_yticklabels([lab(c) for c in order], fontsize=7.5)
    fig.suptitle("Which of the 21 carry weight, rung by rung", x=0.02, ha="left",
                 fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, "fig33_drop_within_21", "Drop-one within the 21-predictor set",
         "Development AP lost when each member is removed from the 21 (fixed logistic "
         "regression at its own best regularisation, 5 split seeds). Grey = removing it "
         "costs nothing or helps. Ordered by ANC8+.",
         [FV / "full" / r / "drop_one_within_21.csv" for r in frames])


def fig_why21():
    done = [r for r in RUNGS3 if (FV / "full" / r / "forward_within_21.csv").exists()]
    if not done:
        return skip("fig34_why21", "stage 0 not run yet")
    fig, axes = plt.subplots(1, len(done), figsize=(3.9 * len(done), 3.6), squeeze=False)
    for ax, r in zip(axes[0], done):
        js = json.loads((FV / "full" / r / "summary.json").read_text())
        a = js["anchors"]
        ceil = a["all88"] - a["prevalence"]
        share = lambda ap: (np.asarray(ap) - a["prevalence"]) / ceil * 100
        path = _fv("full", r, "forward_within_21.csv")
        ax.plot(path.step, share(path.AP), marker="o", ms=3, color=SET21C, lw=1.6,
                label="best k of the 21")
        steps = _fv("full", r, "forward_steps.csv")
        sel_ = steps[steps.tier.isin(["tier 1", "tier 2"])]
        ax.plot(np.arange(1, len(sel_) + 1), share(sel_.AP), marker="s", ms=3.5,
                color=POOLC, lw=1.6, label="selected from the full pool")
        ax.axhline(float(share(a["original21"])), color=SET21C, lw=1, ls="--")
        ax.axhline(100, color=INK, lw=1, ls=":")
        ax.text(21.5, float(share(a["original21"])) - 1.5, " all 21", ha="left", va="top",
                fontsize=7.5, color=SET21C)
        ax.text(21.5, 101.5, " full pool", ha="left", va="bottom", fontsize=7.5)
        ax.set_xlim(0, 25.5)
        ax.set_xlabel("number of predictors")
        ax.set_title(RLAB[r], fontsize=10)
        top = max(float(share(path.AP).max()), float(share(sel_.AP).max()) if len(sel_) else 0)
        ax.set_ylim(min(0, float(share(path.AP).min())) - 5, max(110, top + 8))
        strip(ax)
    axes[0][0].set_ylabel("share of the full pool's lift (%)")
    axes[0][0].legend(fontsize=7.5, loc="lower right")
    fig.suptitle("How many predictors are needed: value by set size", x=0.02, ha="left",
                 fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save(fig, "fig34_why21", "Value by set size, within the 21 and from the full pool",
         "Development AP above prevalence as a share of what the full pool reaches. The "
         "greedy path within the 21 peaks well before 21 and then falls; the sets chosen "
         "from the full pool reach further with fewer. Development folds, so the chosen "
         "sets are optimistic -- fig30 has the held-out view.",
         [FV / "full" / r for r in done])


def fig_predictor_matrix(top=22):
    p = PV / "full" / "matrix.csv"
    if not p.exists():
        return skip("fig35_predictor_rung_matrix", "predictor matrix not built yet")
    m = pd.read_csv(p)
    wide = m.pivot(index="predictor", columns="rung", values="marginal_share")
    rungs = [r for r in RUNGS3 if r in wide]
    wide = wide[rungs]
    keep = wide.max(axis=1).sort_values(ascending=False).head(top).index
    wide = wide.loc[keep]
    wide = wide.loc[(wide[rungs[-1]] - wide[rungs[0]]).sort_values().index]
    in21 = m.groupby("predictor").in_21.first()
    fig, ax = plt.subplots(figsize=(6.4, 0.3 * len(wide) + 1.8))
    vmax = float(np.nanmax(np.abs(wide.to_numpy()))) * 100
    im = ax.imshow(wide.to_numpy() * 100, aspect="auto", cmap="BrBG", vmin=-vmax, vmax=vmax)
    for i in range(len(wide)):
        for j in range(len(rungs)):
            v = wide.iloc[i, j] * 100
            if not np.isnan(v):
                ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=7,
                        color="white" if abs(v) > vmax * 0.6 else INK)
    ax.set_xticks(range(len(rungs)))
    ax.set_xticklabels([RLAB[r] for r in rungs])
    ax.set_yticks(range(len(wide)))
    ax.set_yticklabels([lab(c) + ("  [21]" if in21[c] else "") for c in wide.index],
                       fontsize=7.5)
    ax.grid(False)
    ax.set_title("Each predictor's value, reaching care to completing it")
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("% of the rung's ceiling", fontsize=8)
    save(fig, "fig35_predictor_rung_matrix", "Predictor value across the ANC ladder",
         "Marginal value relative to the 21-predictor set (loss when dropped for "
         "members, marked [21]; gain when added for the rest), as a share of each rung's "
         "ceiling (full-pool AP minus prevalence). Sorted from most ANC1+-weighted to most "
         "ANC8+-weighted.", [p])


# ==================================================== 36-37. the two horizons
def fig_horizons():
    p = HOR / "cross_horizon.csv"
    q = HOR / "heldout_entry.csv"
    if not have(p, q):
        return skip("fig36_horizons", "horizon analysis not run yet")
    cross = pd.read_csv(p)
    held = pd.read_csv(q)
    rungs = [r for r in ("anc4plus", "anc8plus") if r in set(held.outcome)]
    fig, axes = plt.subplots(1, len(rungs), figsize=(5.2 * len(rungs), 3.6), squeeze=False)
    for ax, r in zip(axes[0], rungs):
        h = held[held.outcome == r]
        labels, vals, cols = [], [], []
        for s in ("21", "tier set", "full pool"):
            for e in (False, True):
                row = h[(h.set == s) & (h.early_anc == e)]
                if len(row):
                    labels.append(f"{s}{' + early ANC' if e else ''}")
                    vals.append(float(row.AUROC.iloc[0]))
                    cols.append(POOLC if e else "#9fb9b3")
        c = cross[(cross.outcome == r) & (cross.trained_on == "full-cohort development")]
        for s in ("21", "full pool"):
            row = c[c.set == s]
            if len(row):
                labels.append(f"{s}, fitted before ANC")
                vals.append(float(row.AUROC.iloc[0]))
                cols.append(SET21C)
        y = np.arange(len(vals))[::-1]
        ax.barh(y, vals, color=cols, height=0.66)
        for yi, v in zip(y, vals):
            ax.text(v, yi, f" {v:.3f}", va="center", fontsize=7.5)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlim(0.5, max(vals) + 0.06)
        ax.set_xlabel("held-out AUROC, women who started ANC")
        ax.set_title(RLAB[r], fontsize=10)
        strip(ax, left=False)
    fig.suptitle("At ANC entry: what the timing of the first contact adds",
                 x=0.02, ha="left", fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    save(fig, "fig36_horizons", "The two prediction horizons on the same women",
         "Held-out AUROC on the 984 ANC-entry women. Light = without early ANC, dark = "
         "with it, brown = the same sets fitted on the full cohort (before ANC). Paired "
         "intervals are in outputs/horizons/heldout_bootstrap.json.", [p, q])


def fig_early_anc():
    p, b = HOR / "early_anc_development.csv", HOR / "heldout_bootstrap.json"
    if not have(p, b):
        return skip("fig37_early_anc", "horizon analysis not run yet")
    d = pd.read_csv(p)
    boot = json.loads(b.read_text())
    rows = []
    for x in d.itertuples():
        k = boot.get(f"{x.outcome} | {x.base} + early ANC vs {x.base}")
        if k:
            rows.append((f"{RLAB[x.outcome]} · added to {x.base}", k))
    fig, ax = plt.subplots(figsize=(7.2, 0.5 * len(rows) + 1.6))
    y = np.arange(len(rows))[::-1]
    for yi, (name, k) in zip(y, rows):
        ax.errorbar(k["d_AUROC"], yi, xerr=[[k["d_AUROC"] - k["d_AUROC_lo"]],
                                            [k["d_AUROC_hi"] - k["d_AUROC"]]],
                    fmt="o", color=POOLC, ecolor=INK, capsize=3, ms=5)
    ax.axvline(0, color=NEG, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([n for n, _ in rows], fontsize=8.5)
    ax.set_xlabel("held-out AUROC gain from adding early ANC, 95% interval")
    ax.set_title("Early ANC initiation as a predictor")
    strip(ax, left=False)
    save(fig, "fig37_early_anc", "Value of early ANC initiation",
         "Paired stratified-PSU bootstrap on the 984 held-out ANC-entry women.", [p, b])


# ============================================ 38. Tigray against every region
def fig_tigray_regions():
    p = WAR / "region_by_war_period.csv"
    if not p.exists():
        return skip("fig38_tigray_regions_by_period", "wartime analysis not run yet")
    d = pd.read_csv(p).pivot(index="region", columns="period")
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.8), sharey=True)
    order = (d[("anc4plus", "after")] - d[("anc4plus", "during")]).sort_values().index
    y = np.arange(len(order))
    for ax, m, title in zip(axes, ("never", "anc4plus", "anc8plus"),
                            ("No ANC at all", "ANC4+", "ANC8+")):
        a = d[(m, "during")].reindex(order) * 100
        b = d[(m, "after")].reindex(order) * 100
        ax.hlines(y, a, b, color=LINE, lw=2)
        ax.scatter(a, y, color=NEG, s=18, label="wartime period")
        ax.scatter(b, y, color=POOLC, s=22, label="post-war period")
        t = list(order).index("Tigray")
        ax.axhspan(t - 0.45, t + 0.45, color="#f3e7c9", zorder=0)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("percent of women")
        strip(ax, left=False)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(order, fontsize=8.5)
    axes[0].legend(fontsize=7.5, loc="lower right")
    fig.suptitle("Tigray against every region over the same calendar periods",
                 x=0.02, ha="left", fontsize=11, fontweight="semibold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save(fig, "fig38_tigray_regions_by_period", "Every region, wartime vs post-war period",
         "Pregnancies with at least 3 months inside the Tigray war window vs those "
         "conceived after the ceasefire, in every region. Sorted by the ANC4+ change.", [p])

# ================================================================ orchestration
FAMILIES = {
    "cascade": ["fig_cascade", "fig_regional", "fig_continuation_equity"],
    "models": ["fig_leaderboard", "fig_calibration", "fig_stability", "fig_bootstrap",
               "fig_decision_curve", "fig_subgroups"],
    "features": ["fig_importance", "fig_shapes",
                 "fig_screening", "fig_preprocessing", "fig_redundancy", "fig_set_comparison"],
    "tuning": ["fig_hyperparameters", "fig_tuning_gain"],
    "selection": ["fig_add_one", "fig_diminishing", "fig_tier_ladders",
                  "fig_selection_frequency", "fig_heldout_sets"],
    "wartime": ["fig_tigray_did", "fig_regional_gap_cohort", "fig_tigray_regions"],
    "value": ["fig_drop_within_21", "fig_why21", "fig_predictor_matrix"],
    "horizons": ["fig_horizons", "fig_early_anc"],
    "ladder": ["fig_ladder_performance", "fig_ladder_importance", "fig_domain_rollup"],
    "policy": ["fig_regional_gap", "fig_modifiable", "fig_risk_bands"],
}

NEEDS_DF = {"fig_cascade", "fig_regional", "fig_continuation_equity"}
NEEDS_INSIGHTS = {"fig_importance", "fig_shapes"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(FAMILIES), default=None)
    args = ap.parse_args()

    FIG.mkdir(parents=True, exist_ok=True)
    df = load_frame()
    ins_path = ROOT / "app" / "public" / "insights.json"
    insights = json.loads(ins_path.read_text(encoding="utf-8")) if ins_path.exists() else None

    wanted = FAMILIES[args.only] if args.only else [f for v in FAMILIES.values() for f in v]
    for name in wanted:
        fn = globals()[name]
        try:
            if name in NEEDS_DF:
                fn(df)
            elif name in NEEDS_INSIGHTS:
                fn(insights)
            else:
                fn()
        except Exception as exc:
            print(f"  [FAIL] {name}: {type(exc).__name__}: {exc}")

    if MANIFEST:
        man = pd.DataFrame(MANIFEST)
        path = FIG / "figures_manifest.csv"
        if path.exists():
            old = pd.read_csv(path)
            man = pd.concat([old[~old.figure.isin(man.figure)], man])
        man.sort_values("figure").to_csv(path, index=False)
        print(f"\n{len(MANIFEST)} figures written to {FIG}")
        print(f"manifest: {path}")


if __name__ == "__main__":
    main()
