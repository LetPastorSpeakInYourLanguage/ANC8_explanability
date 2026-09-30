"""Which predictors pay their way -- stages 0-3 of the predictor-value study.

    python scripts/run_feature_value.py --cohort full --outcome anc8plus
    python scripts/run_feature_value.py --cohort entry --outcome anc4plus
    python scripts/run_feature_value.py --cohort full --outcome anc1plus --stages 0

Stage 0 -- the 21 on their own.
    drop-one:   each of the 21 removed from the 21
    forward:    the full greedy path within the 21 (1, 2, ... 21 predictors)
    group drop: the 21 without every member whose removal costs nothing

Stage 1 -- what the additions add.
    add-one:    each non-original candidate added, alone, to the original 21
    cumulative: the additions stacked onto the 21 in order of their add-one gain
    remove-one: each candidate removed from the full pool of 88

Stage 2 -- the tiers.
    forward selection from nothing over the 88; a step is accepted only if it
    adds >= 0.005 AP on average AND helps on at least 4 of 5 split seeds.
    Tier 1 = accepted steps until 90% of the full model's lift over prevalence;
    Tier 2 = the remaining accepted steps. Optional PSU-bootstrap re-selection
    measures how often each variable would be chosen again, and a LightGBM
    re-scoring checks the tiers are not an artefact of the linear model.

Stage 3 -- one look at the held-out women.
    Tier 1, Tier 1+2, the original 21 and the full 88, each fitted on the
    development set and scored once on the held-out set, with a paired
    stratified-PSU bootstrap against the 21.

Everything in stages 1 and 2 sees development rows only; the Scorer asserts
it. The held-out set is touched in stage 3 and nowhere else.

The original 21 enter with maternal age AT BIRTH rather than current age --
the one change made to them, because current age is up to three years
removed from the pregnancy for the older births. Output lands in
outputs/feature_value/<cohort>/<outcome>/.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import cohorts, design, metrics, outcomes, selection as sel, tuning  # noqa: E402
from anc8 import models as zoo  # noqa: E402

OUT_ROOT = ROOT / "outputs" / "feature_value"
ENHANCED = ROOT / "outputs" / "enhanced"


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def stage0(scorer, pool, out, anchors):
    log("stage 0a: remove each of the 21 from the 21")
    drop = sel.remove_one(scorer, pool.original21)
    drop["contributes"] = drop.loss > 0
    drop.to_csv(out / "drop_one_within_21.csv", index=False)
    for r in drop.itertuples():
        log(f"    {r.predictor:36s} loss {r.loss:+.4f}  ({r.seeds_positive}/5)")

    log("stage 0b: the greedy path within the 21, all the way to 21")
    # No stopping rule: the whole path is the answer to "how many of the 21
    # are needed". The +0.005 bar is recorded alongside, not enforced.
    path = sel.forward(scorer, pool.original21, threshold=-np.inf, min_seeds=0,
                       max_steps=len(pool.original21), log=log)
    path["clears_threshold"] = (path.gain >= sel.THRESHOLD) &         (path.seeds_positive >= sel.MIN_SEEDS_POSITIVE)
    path["lift_share_of_88"] = (path.AP - scorer.prevalence) /         (anchors["all88"] - scorer.prevalence)
    path.to_csv(out / "forward_within_21.csv", index=False)
    best_k = int(path.AP.idxmax()) + 1

    log("stage 0c: the 21 without its non-contributors")
    idle = list(drop[~drop.contributes].predictor)
    kept = [c for c in pool.original21 if c not in idle]
    kept_ap = float(scorer.seeds(kept).mean())
    kept_C = scorer.last_C
    grp = pd.DataFrame([{"set": "21", "n": len(pool.original21),
                         "AP": anchors["original21"], "C": anchors["original21_C"],
                         "removed": ""},
                        {"set": "21 minus non-contributors", "n": len(kept),
                         "AP": kept_ap, "C": kept_C, "removed": "|".join(idle)}])
    grp.to_csv(out / "drop_group_21.csv", index=False)
    log(f"    {len(idle)} non-contributors {idle}: AP {anchors['original21']:.4f}"
        f" -> {kept_ap:.4f}; best path length {best_k} (AP {path.AP.max():.4f})")
    return {"n_non_contributors": len(idle), "non_contributors": idle,
            "AP_21_minus_non_contributors": kept_ap,
            "best_k_within_21": best_k, "best_AP_within_21": float(path.AP.max())}


def stage1(scorer, pool, out, anchors):
    log("stage 1a: add each new candidate, alone, to the original 21")
    new = [c for c in pool.names if c not in pool.original21]
    add = sel.add_one(scorer, pool.original21, new)
    add["at_interview"] = add.predictor.map(lambda c: sel.AT_INTERVIEW.get(c, ""))
    add["clears_threshold"] = (add.gain >= sel.THRESHOLD) & \
        (add.seeds_positive >= sel.MIN_SEEDS_POSITIVE)
    add.to_csv(out / "add_one_to_21.csv", index=False)
    n_pass = int(add.clears_threshold.sum())
    log(f"  {n_pass} of {len(new)} additions clear +{sel.THRESHOLD} AP; "
        f"median gain {add.gain.median():+.4f}")
    for r in add.head(8).itertuples():
        log(f"    {r.predictor:34s} {r.gain:+.4f}  ({r.seeds_positive}/5)")

    log("stage 1b: stack the additions onto the 21 in order of their gain")
    cum = sel.cumulative(scorer, pool.original21, list(add.predictor))
    cum["gain_over_21"] = cum.AP - anchors["original21"]
    cum.to_csv(out / "cumulative_from_21.csv", index=False)
    total = cum.AP.iloc[-1] - cum.AP.iloc[0]
    for k in (1, 3, 5, 10):
        if k < len(cum):
            share = (cum.AP.iloc[k] - cum.AP.iloc[0]) / total if total > 0 else np.nan
            log(f"    first {k:2d} additions carry {share:6.1%} of the total gain")

    log("stage 1c: remove each candidate from the full pool")
    rem = sel.remove_one(scorer, pool.names)
    rem.to_csv(out / "remove_one_from_all.csv", index=False)
    log(f"  {int((rem.loss >= sel.THRESHOLD).sum())} candidates cost >= "
        f"{sel.THRESHOLD} AP when removed from the full set")
    return {"n_new": len(new), "n_clear": n_pass,
            "median_gain": float(add.gain.median()),
            "total_gain_all_additions": float(total)}


def stage2(scorer, pool, out, anchors, n_boot, outcome, cohort_df):
    log("stage 2: forward selection from nothing")
    steps = sel.forward(scorer, pool.names, log=log)
    t = sel.tiers(steps, anchors["all88"], scorer.prevalence)
    t["in_original_21"] = t.predictor.isin(pool.original21)
    t["at_interview"] = t.predictor.map(lambda c: sel.AT_INTERVIEW.get(c, ""))
    t.to_csv(out / "forward_steps.csv", index=False)

    tier1 = list(t[t.tier == "tier 1"].predictor)
    tier2 = list(t[t.tier == "tier 2"].predictor)
    log(f"  tier 1 ({len(tier1)}): {tier1}")
    log(f"  tier 2 ({len(tier2)}): {tier2}")

    # How many of the original 21 earned a place, and in which tier.
    placement = pd.DataFrame({
        "predictor": pool.original21,
        "placement": ["tier 1" if c in tier1 else "tier 2" if c in tier2 else "not selected"
                      for c in pool.original21],
    })
    placement.to_csv(out / "original21_placement.csv", index=False)

    freq = None
    if n_boot:
        log(f"stage 2b: re-run the selection on {n_boot} PSU-bootstrap resamples")
        # Only one worker pool may exist at a time: each worker maps ~350 MB of
        # fold matrices, and a second pool of eight alongside the first
        # exhausted Windows' commit limit on a 16 GB machine.
        sel.shutdown(scorer)
        dev = scorer.dev
        picks = []
        for b, idx in enumerate(design.stratified_psu_bootstrap(
                dev.v022.to_numpy(), dev.v021.to_numpy(), n_resamples=n_boot,
                seed=7000)):
            dev_b = dev.iloc[idx].reset_index(drop=True)
            sb = sel.Scorer(dev_b, outcome, pool)
            st = sel.forward(sb, pool.names, log=lambda m: None)
            chosen = list(st[st.accepted].predictor)
            picks.append(chosen)
            sel.shutdown(sb)
            shutil.rmtree(sel.CACHE / sb.cache_key, ignore_errors=True)
            log(f"    resample {b + 1:2d}: {len(chosen)} selected -- {chosen[:6]}"
                f"{' ...' if len(chosen) > 6 else ''}")
        counts = pd.Series([c for p in picks for c in p]).value_counts()
        freq = pd.DataFrame({"predictor": counts.index,
                             "selected_share": (counts / n_boot).to_numpy()})
        freq["tier"] = freq.predictor.map(
            lambda c: "tier 1" if c in tier1 else "tier 2" if c in tier2 else "")
        freq.to_csv(out / "selection_frequency.csv", index=False)
        weak = [c for c in tier1 + tier2
                if float(freq.set_index("predictor").selected_share.get(c, 0)) < 0.70]
        log(f"  tier members selected in under 70% of resamples: {weak or 'none'}")

    # The same sets re-scored with a booster: tiers chosen by a linear model
    # should not collapse when a model that can find interactions scores them.
    log("stage 2c: re-score the tier sets with LightGBM")
    best = json.load(open(ENHANCED / outcome / "best_hyperparameters.json"))["LightGBM"]
    params = dict(best, n_estimators=min(best.get("n_estimators", 400), 400))
    dev = scorer.dev
    rows = []
    for name, cols in (("tier 1", tier1), ("tier 1+2", tier1 + tier2),
                       ("original 21", pool.original21), ("all 88", pool.names)):
        if not cols:
            continue
        num, cat = pool.split(cols)
        aps = []
        for sp in scorer.splits[:3]:
            p = tuning.oof_predict("LightGBM", params, dev[num + cat], scorer.y,
                                   scorer.w, sp, num, cat, n_jobs=5)
            aps.append(metrics.probability_metrics(scorer.y, p, scorer.w)["AP"])
        rows.append({"set": name, "n": len(cols), "LightGBM_AP": float(np.mean(aps)),
                     "logistic_AP": float(scorer.seeds(cols).mean())})
        log(f"    {name:12s} n={len(cols):2d}  logistic {rows[-1]['logistic_AP']:.4f}"
            f"  LightGBM {rows[-1]['LightGBM_AP']:.4f}")
    pd.DataFrame(rows).to_csv(out / "lightgbm_check.csv", index=False)
    return tier1, tier2, freq


def stage3(df, pool, tier1, tier2, outcome, out, n_trials, scorer):
    log("stage 3: fit on development, score once on the held-out women")
    dev, held = cohorts.development(df), cohorts.heldout(df)
    y_d = dev[outcome].astype(int).to_numpy()
    w_d = (dev.v005 / 1e6).to_numpy()
    y_h = held[outcome].astype(int).to_numpy()
    w_h = (held.v005 / 1e6).to_numpy()
    prevalence = float(np.average(y_h, weights=w_h))

    sets = {"tier 1": tier1, "tier 1+2": tier1 + tier2,
            "original 21": pool.original21, "all 88": pool.names}
    # At ANC entry: the 21 plus the timing of the first contact -- the
    # extended specification of that horizon.
    if "early_anc" in pool.names:
        sets["21 + early ANC"] = pool.original21 + ["early_anc"]
    sets = {k: v for k, v in sets.items() if v}
    preds, rows = {}, []
    for model in ("Logistic regression", "LightGBM"):
        for name, cols in sets.items():
            num, cat = pool.split(cols)
            if model == "Logistic regression":
                # The C this set earned on development folds -- never the
                # held-out set -- so each set is fitted at its own best setting.
                scorer.seeds(cols)
                params = {"C": scorer.last_C}
            else:
                # A small search per set, on development folds only, so no set
                # is scored with hyperparameters that were tuned for another.
                params, _ = tuning.tune("LightGBM", dev[num + cat], y_d, w_d,
                                        cohorts.folds(dev), num, cat,
                                        n_trials=n_trials, n_jobs=5)
            pipe = zoo.build(model, params, num, cat)
            tuning._fit(pipe, dev[num + cat], y_d, w_d / w_d.mean())
            p = pipe.predict_proba(held[num + cat])[:, 1]
            preds[(model, name)] = p
            m = metrics.probability_metrics(y_h, p, w_h)
            rows.append({"model": model, "set": name, "n_predictors": len(cols),
                         **m, "AP_lift": m["AP"] - prevalence})
            log(f"    {model[:8]:8s} {name:12s} n={len(cols):2d}  AP {m['AP']:.4f}  "
                f"AUROC {m['AUROC']:.4f}  slope {m['Calibration_slope']:.2f}")
    res = pd.DataFrame(rows)
    res["prevalence"] = prevalence
    res.to_csv(out / "heldout.csv", index=False)

    # Paired bootstrap against the 21: same resampled women for both sets.
    from sklearn.metrics import average_precision_score, roc_auc_score
    boot = {}
    for model in ("Logistic regression", "LightGBM"):
        base = preds[(model, "original 21")]
        for name in sets:
            if name == "original 21":
                continue
            p = preds[(model, name)]
            d_ap, d_auc = [], []
            for idx in design.stratified_psu_bootstrap(held.v022.to_numpy(),
                                                       held.v021.to_numpy(),
                                                       n_resamples=1000, seed=2026):
                yy, ww = y_h[idx], w_h[idx]
                if yy.min() == yy.max():
                    continue
                d_ap.append(average_precision_score(yy, p[idx], sample_weight=ww)
                            - average_precision_score(yy, base[idx], sample_weight=ww))
                d_auc.append(roc_auc_score(yy, p[idx], sample_weight=ww)
                             - roc_auc_score(yy, base[idx], sample_weight=ww))
            d_ap, d_auc = np.asarray(d_ap), np.asarray(d_auc)
            boot[f"{model} | {name} vs original 21"] = {
                "d_AP": float(np.mean(d_ap)),
                "d_AP_lo": float(np.quantile(d_ap, 0.025)),
                "d_AP_hi": float(np.quantile(d_ap, 0.975)),
                "d_AUROC": float(np.mean(d_auc)),
                "d_AUROC_lo": float(np.quantile(d_auc, 0.025)),
                "d_AUROC_hi": float(np.quantile(d_auc, 0.975)),
            }
    json.dump(boot, open(out / "heldout_bootstrap.json", "w"), indent=2)
    for k, v in boot.items():
        log(f"    {k:48s} dAP {v['d_AP']:+.4f} [{v['d_AP_lo']:+.4f}, {v['d_AP_hi']:+.4f}]")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", choices=cohorts.COHORTS, default="full")
    ap.add_argument("--outcome", choices=outcomes.LADDER, default="anc8plus")
    ap.add_argument("--stages", default="0123")
    ap.add_argument("--bootstrap", type=int, default=None,
                    help="bootstrap re-selections (default: 10 for anc8plus, else 0)")
    ap.add_argument("--trials", type=int, default=20)
    args = ap.parse_args()
    if args.outcome not in cohorts.COHORT_OUTCOMES[args.cohort]:
        ap.error(f"{args.outcome} is not defined in the {args.cohort} cohort")
    n_boot = args.bootstrap if args.bootstrap is not None else \
        (10 if args.outcome == "anc8plus" else 0)

    out = OUT_ROOT / args.cohort / args.outcome
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log(f"{args.cohort} cohort, {outcomes.OUTCOMES[args.outcome]['label']}")

    df, pool = sel.build_pool(cohorts.load(args.cohort))
    dev = cohorts.development(df)
    log(f"  {len(df)} women ({len(dev)} development), {len(pool.names)} candidates")

    scorer = sel.Scorer(dev, args.outcome, pool)
    anchors = {"prevalence": scorer.prevalence}
    anchors["original21"] = float(scorer.seeds(pool.original21).mean())
    anchors["original21_C"] = scorer.last_C
    anchors["all88"] = float(scorer.seeds(pool.names).mean())
    anchors["all88_C"] = scorer.last_C
    log(f"  prevalence {anchors['prevalence']:.4f}   21: {anchors['original21']:.4f} "
        f"(C={anchors['original21_C']})   88: {anchors['all88']:.4f} "
        f"(C={anchors['all88_C']})")

    # Stage 0 alone updates an earlier run's summary instead of replacing it.
    prev = out / "summary.json"
    summary = json.load(open(prev)) if prev.exists() and args.stages == "0" else {}
    summary.update({"cohort": args.cohort, "outcome": args.outcome, "anchors": anchors,
                    "threshold": sel.THRESHOLD, "min_seeds_positive": sel.MIN_SEEDS_POSITIVE,
                    "n_development": len(dev), "n_total": len(df),
                    "n_candidates": len(pool.names)})
    try:
        if "0" in args.stages:
            summary["stage0"] = stage0(scorer, pool, out, anchors)
        if "1" in args.stages:
            summary["stage1"] = stage1(scorer, pool, out, anchors)
        tier1 = tier2 = []
        if "2" in args.stages or "3" in args.stages:
            tier1, tier2, _ = stage2(scorer, pool, out, anchors,
                                     n_boot if "2" in args.stages else 0,
                                     args.outcome, df)
            summary["tier1"], summary["tier2"] = tier1, tier2
        if "3" in args.stages:
            stage3(df, pool, tier1, tier2, args.outcome, out, args.trials, scorer)
    finally:
        sel.shutdown(scorer)
        shutil.rmtree(sel.CACHE / scorer.cache_key, ignore_errors=True)

    summary.pop("minutes", None)
    json.dump(summary, open(out / "summary.json", "w"), indent=2)
    log(f"done in {(time.time() - t0) / 60:.1f} min -> {out}")


if __name__ == "__main__":
    main()
