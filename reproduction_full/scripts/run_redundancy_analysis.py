"""Which predictors are the same variable wearing two names?

    python scripts/run_redundancy_analysis.py

The enhanced set was assembled by screening every column of the Individual
Recode, and the DHS ships several variables more than once: `region` and
`v024` are the same fourteen regions, `wealth_quintile` and `v190` the same
five quintiles. Screening on univariate strength cannot see that, because a
duplicate scores exactly as well as its twin.

Two consequences, and only one of them is harmless:

  * **Prediction** barely notices. A tree or an additive model splits the
    signal between the copies and arrives at much the same answer.
  * **Interpretation** notices a great deal. Per-predictor importance is
    computed per column, so a variable present twice appears at roughly half
    its true weight and can be ranked below something that matters less. Any
    "top predictors" list built without checking for this is wrong.

This finds the groups -- exact one-to-one recodings first, then strong
near-duplicates -- and re-states importance at the group level. It also
refits without the redundant copies, so the claim that prediction does not
care is measured rather than asserted.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app" / "api" / "_lib"))

from anc8 import design, tuning  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"
OUT = ENHANCED / "redundancy"

# Strong enough that the pair carries the same information for any practical
# purpose, without sweeping up merely correlated predictors such as wealth and
# education.
NEAR_DUPLICATE = 0.95


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def codes(s: pd.Series) -> np.ndarray:
    """Integer codes for any column, so one routine handles both kinds."""
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
    return s.astype("category").cat.codes.replace(-1, np.nan).to_numpy(dtype=float)


def one_to_one(a: pd.Series, b: pd.Series) -> bool:
    """True when each level of a implies exactly one level of b, and back."""
    # Cast to str only after dropping missing, or NaN becomes the string "nan"
    # and two variables that are merely missing together look identical.
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 50:
        return False
    d = d.astype(str)
    return (d.groupby("a").b.nunique().max() == 1
            and d.groupby("b").a.nunique().max() == 1
            and d.a.nunique() > 1 and d.b.nunique() > 1)


def uncertainty(a: pd.Series, b: pd.Series):
    """How much each variable tells you about the other, both directions.

    Theil's U: the share of one variable's entropy that the other explains.
    Returns (U(a|b), U(b|a)).

    A symmetric measure is what redundancy needs, and Cramer's V is not one in
    the way it matters here. Against a two-level variable, V reaches 1.0 as
    soon as every level of one side falls entirely inside one level of the
    other -- so union status and partner education score a perfect 1.0, purely
    because partner education carries a "Not applicable" level that occurs for
    exactly the women who are not in a union. That is structural missingness
    encoded as a category, not two variables carrying the same information,
    and treating it as duplication would chain unrelated predictors together.
    """
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(d) < 50:
        return np.nan, np.nan
    t = pd.crosstab(d.a.astype(str), d.b.astype(str)).to_numpy(dtype=float)
    n = t.sum()
    if n == 0 or min(t.shape) < 2:
        return np.nan, np.nan
    p = t / n
    pa = p.sum(1)
    pb = p.sum(0)

    def H(q):
        q = q[q > 0]
        return float(-(q * np.log(q)).sum())

    ha, hb = H(pa), H(pb)
    nz = p > 0
    mutual = float((p[nz] * np.log(p[nz] / (pa[:, None] * pb[None, :])[nz])).sum())
    return (mutual / ha if ha > 0 else np.nan,
            mutual / hb if hb > 0 else np.nan)


def association(df, a, b, numeric):
    """How interchangeable two predictors are, in [0, 1], and which way.

    Returns (symmetric, directional, measure): `symmetric` is the weaker of the
    two directions -- high only when each variable determines the other, which
    is what "the same variable twice" means. `directional` is the stronger one:
    high when one variable is a coarsening of the other, which is a different
    kind of redundancy and is reported separately rather than grouped.
    """
    if a in numeric and b in numeric:
        x, y = codes(df[a]), codes(df[b])
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < 50 or np.std(x[ok]) == 0 or np.std(y[ok]) == 0:
            return np.nan, np.nan, "spearman"
        r = abs(float(pd.Series(x[ok]).corr(pd.Series(y[ok]), method="spearman")))
        return r, r, "spearman"
    # Categorical on at least one side: bin the numeric one, or the table gets
    # one row per distinct value and every pair looks informative.
    da, db = df[a], df[b]
    if a in numeric:
        da = pd.qcut(pd.to_numeric(da, errors="coerce"), 10, duplicates="drop")
    if b in numeric:
        db = pd.qcut(pd.to_numeric(db, errors="coerce"), 10, duplicates="drop")
    ua, ub = uncertainty(da, db)
    if not (np.isfinite(ua) and np.isfinite(ub)):
        return np.nan, np.nan, "theil_u"
    return min(ua, ub), max(ua, ub), "theil_u"


def group_of(pairs, names):
    """Connected components over the duplicate pairs."""
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    out = {}
    for n in names:
        out.setdefault(find(n), []).append(n)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_pickle(ENHANCED / "ANC8_analysis_frozen_v2.pkl")
    spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
    numeric = spec["numeric_predictors"]
    categorical = spec["categorical_predictors"]
    names = numeric + categorical

    train_psus, _ = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
    log(f"{len(names)} predictors, {len(dev)} development women")

    # ---- 1. find the pairs ------------------------------------------------
    log("scanning every pair")
    rows, nested = [], []
    for a, b in combinations(names, 2):
        sym, direct, how = association(dev, a, b, set(numeric))
        if not np.isfinite(sym):
            continue
        if sym >= NEAR_DUPLICATE:
            rows.append({"a": a, "b": b, "association": sym,
                         "strongest_direction": direct, "measure": how,
                         "exact_recoding": one_to_one(dev[a], dev[b])})
        elif direct >= NEAR_DUPLICATE:
            # One determines the other but not conversely: a coarsening, such
            # as a quintile of a continuous score. Redundant, but not the same
            # variable, so it is reported rather than folded into a group.
            nested.append({"finer": b, "coarser": a, "determination": direct,
                           "measure": how})
    pairs = (pd.DataFrame(rows).sort_values("association", ascending=False)
             if rows else pd.DataFrame(columns=["a", "b", "association",
                                                "strongest_direction", "measure",
                                                "exact_recoding"]))
    pairs.to_csv(OUT / "duplicate_pairs.csv", index=False)
    pd.DataFrame(nested).to_csv(OUT / "coarsening_pairs.csv", index=False)

    print()
    print("=" * 78)
    print("1. PREDICTORS THAT CARRY THE SAME INFORMATION")
    print("=" * 78)
    print("  Both directions must hold: each has to determine the other.")
    print()
    if not len(pairs):
        print("  none above the threshold")
    for r in pairs.itertuples():
        tag = "SAME VARIABLE" if r.exact_recoding else "near-duplicate"
        print(f"  {r.a:34s} {r.b:34s} {r.association:.3f}  {tag}")

    print()
    print(f"  {len(nested)} further pairs where one variable determines the other")
    print("  but not conversely -- a coarsening, kept separate from the groups:")
    for r in nested[:12]:
        print(f"    {r['coarser']:34s} is implied by {r['finer']:24s}"
              f" {r['determination']:.3f}")
    if len(nested) > 12:
        print(f"    ... and {len(nested) - 12} more, in coarsening_pairs.csv")

    # ---- 2. group them ----------------------------------------------------
    groups = group_of(list(zip(pairs.a, pairs.b)), names) if len(pairs) else {
        n: [n] for n in names}
    multi = {k: v for k, v in groups.items() if len(v) > 1}

    label = {}
    for root, members in groups.items():
        # Name the group after its shortest human-readable member.
        pick = sorted(members, key=lambda m: (m.startswith("v") or m.startswith("s"),
                                              len(m)))[0]
        for m in members:
            label[m] = pick

    pd.DataFrame([{"group": label[m], "predictor": m, "group_size": len(members)}
                  for members in groups.values() for m in members]
                 ).sort_values(["group_size", "group"], ascending=[False, True]
                               ).to_csv(OUT / "redundancy_groups.csv", index=False)

    print()
    print(f"  {len(multi)} groups with more than one member, covering "
          f"{sum(len(v) for v in multi.values())} of {len(names)} predictors")

    # ---- 3. re-state importance at the group level ------------------------
    ins_path = ROOT / "app" / "public" / "insights.json"
    grouped = None
    if ins_path.exists():
        ins = json.loads(ins_path.read_text(encoding="utf-8"))
        imp = pd.Series(ins["global_importance"])
        gimp = imp.groupby(imp.index.map(lambda n: label.get(n, n))).sum()
        members = {g: [m for m in imp.index if label.get(m, m) == g] for g in gimp.index}
        grouped = pd.DataFrame({
            "group": gimp.index,
            "grouped_importance": gimp.to_numpy(),
            "largest_single_member": [imp[members[g]].max() for g in gimp.index],
            "n_members": [len(members[g]) for g in gimp.index],
            "members": ["; ".join(members[g]) for g in gimp.index],
        }).sort_values("grouped_importance", ascending=False)
        grouped["rank_grouped"] = np.arange(1, len(grouped) + 1)
        single_rank = imp.rank(ascending=False)
        grouped["rank_as_single_columns"] = [
            float(single_rank[members[g]].min()) for g in grouped.group]
        grouped.to_csv(OUT / "grouped_importance.csv", index=False)

        print()
        print("=" * 78)
        print("2. IMPORTANCE ONCE DUPLICATES ARE ADDED BACK TOGETHER")
        print("=" * 78)
        print(f"  {'group':30s}{'grouped':>9s}{'best single':>13s}{'rank':>6s}"
              f"{'was':>6s}  members")
        for r in grouped.head(15).itertuples():
            moved = "" if r.rank_grouped == r.rank_as_single_columns else "  <-- moved"
            print(f"  {r.group:30s}{r.grouped_importance:>9.4f}"
                  f"{r.largest_single_member:>13.4f}{r.rank_grouped:>6.0f}"
                  f"{r.rank_as_single_columns:>6.0f}{moved}")
            if r.n_members > 1:
                print(f"      {r.members}")

    # ---- 4. does dropping the duplicates cost anything? -------------------
    log("\nrefitting without the redundant copies")
    keep = sorted({label[n] for n in names})
    drop = [n for n in names if n not in keep]
    log(f"  keeping {len(keep)} of {len(names)}; dropping {len(drop)}")

    best = json.load(open(ENHANCED / "anc8plus" / "best_hyperparameters.json"))
    model = "LightGBM" if "LightGBM" in best else list(best)[0]
    params = best[model]

    splits = design.folds_to_splits(design.make_psu_stratum_folds(dev))
    w = (dev.v005 / 1e6).to_numpy()
    y = dev.anc8plus.astype(int).to_numpy()
    from sklearn.metrics import average_precision_score, roc_auc_score

    def run(cols):
        num = [c for c in numeric if c in cols]
        cat = [c for c in categorical if c in cols]
        X = dev[num + cat].copy()
        for c in cat:
            X[c] = X[c].astype(str)
        p = tuning.oof_predict(model, params, X, y, w, splits, num, cat)
        return (float(average_precision_score(y, p, sample_weight=w)),
                float(roc_auc_score(y, p, sample_weight=w)))

    full_ap, full_auc = run(set(names))
    log(f"  all {len(names)}: AP={full_ap:.4f} AUROC={full_auc:.4f}")
    lean_ap, lean_auc = run(set(keep))
    log(f"  lean {len(keep)}: AP={lean_ap:.4f} AUROC={lean_auc:.4f}")

    # If removing an exact copy costs accuracy, the copy was not carrying
    # information -- it was carrying weight. Under column subsampling a
    # variable present twice gets two chances to be offered at each split, so
    # duplication acts as an implicit prior that this variable matters.
    #
    # That mechanism is testable. Switch off column subsampling, and re-run
    # with a model that has none at all: if the gap closes, the duplicates were
    # upweighting rather than informing.
    mech = {}
    nosub = dict(params)
    changed = [k for k in ("colsample_bytree", "colsample_bynode", "colsample_bylevel",
                           "feature_fraction", "max_features") if k in nosub]
    for k in changed:
        nosub[k] = 1.0
    if changed:
        log(f"  re-running with {', '.join(changed)} = 1.0")
        saved, params = params, nosub
        mech["nosubsample_full"], _ = run(set(names))
        mech["nosubsample_lean"], _ = run(set(keep))
        params = saved
        log(f"    full {mech['nosubsample_full']:.4f}  lean {mech['nosubsample_lean']:.4f}"
            f"  gap {mech['nosubsample_lean'] - mech['nosubsample_full']:+.4f}")

    lr_params = json.load(open(ENHANCED / "anc8plus" / "best_hyperparameters.json")
                          ).get("Logistic regression", {})
    saved_model, saved_params = model, params
    model, params = "Logistic regression", lr_params
    log("  re-running with logistic regression (no feature sampling at all)")
    mech["logistic_full"], _ = run(set(names))
    mech["logistic_lean"], _ = run(set(keep))
    model, params = saved_model, saved_params
    log(f"    full {mech['logistic_full']:.4f}  lean {mech['logistic_lean']:.4f}"
        f"  gap {mech['logistic_lean'] - mech['logistic_full']:+.4f}")

    summary = {
        "n_predictors": len(names),
        "n_after_deduplication": len(keep),
        "dropped": drop,
        "threshold": NEAR_DUPLICATE,
        "exact_recodings": int(pairs.exact_recoding.sum()) if len(pairs) else 0,
        "development_AP_full": full_ap,
        "development_AP_deduplicated": lean_ap,
        "development_AUROC_full": full_auc,
        "development_AUROC_deduplicated": lean_auc,
        "AP_cost_of_deduplication": lean_ap - full_ap,
        "mechanism_check": mech,
    }
    json.dump(summary, open(OUT / "redundancy_summary.json", "w"), indent=2)

    print()
    print("=" * 78)
    print("3. WHAT THE DUPLICATES WERE BUYING")
    print("=" * 78)
    print(f"  {model:<22s}  all {len(names):>3d}   AP {full_ap:.4f}   AUROC {full_auc:.4f}")
    print(f"  {'':<22s}  lean {len(keep):>3d}   AP {lean_ap:.4f}   AUROC {lean_auc:.4f}")
    print(f"  {'':<22s}  difference   AP {lean_ap - full_ap:+.4f}   "
          f"AUROC {lean_auc - full_auc:+.4f}")
    if "logistic_full" in mech:
        print()
        print(f"  {'Logistic regression':<22s}  all {len(names):>3d}   "
              f"AP {mech['logistic_full']:.4f}")
        print(f"  {'(no feature sampling)':<22s}  lean {len(keep):>3d}   "
              f"AP {mech['logistic_lean']:.4f}")
        print(f"  {'':<22s}  difference   AP "
              f"{mech['logistic_lean'] - mech['logistic_full']:+.4f}")
    print()
    gap = lean_ap - full_ap
    lin = mech.get("logistic_lean", np.nan) - mech.get("logistic_full", np.nan)
    if gap >= -0.002:
        print("  Reading: removing the duplicate columns does not cost accuracy")
        print(f"  ({gap:+.4f} AP), so they were carrying no information the")
        print("  remaining columns did not already have. They were pure")
        print("  bookkeeping -- the same variable admitted twice under two names.")
    elif np.isfinite(lin) and lin > gap + 0.004:
        print("  Reading: the booster loses accuracy on deduplication while the")
        print(f"  linear model does not ({gap:+.4f} against {lin:+.4f}). The")
        print("  duplicates were not adding information; they were raising the")
        print("  chance a column-subsampling booster offered those variables at a")
        print("  split -- an accidental feature prior rather than a finding.")
    else:
        print(f"  Reading: deduplication costs {gap:+.4f} AP and the linear model")
        print(f"  moves {lin:+.4f}. The copies are doing something beyond")
        print("  bookkeeping; do not drop them without checking this again.")
    print()
    print("  For interpretation the conclusion holds either way: rank any")
    print("  'most important predictors' list at the group level, or a variable")
    print("  the file happens to ship twice is reported at half its weight.")
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
