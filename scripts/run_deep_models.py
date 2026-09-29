"""Train and evaluate the neural networks (src/anc8/deep.py) against the tree models.

    python scripts/run_deep_models.py            # full run (about two hours on CPU)
    python scripts/run_deep_models.py --quick    # one seed, few epochs: a smoke test

Everything is on the study's own ground: the full cohort, the same 95 predictors,
the same development/held-out split and the same five PSU-grouped folds the tree
models were tuned and compared on. Survey weights in every loss and metric.

  1. Out-of-fold on development: each network on each fold, three seeds, so the
     table shows the run-to-run spread as well as the level.
  2. One final fit per network on all development women (seed 2026), scored once
     on the held-out women, with a paired stratified-PSU bootstrap against XGBoost,
     the explainable boosting model and each rung's development champion.
  3. What the networks attend to: per predictor, per concept, per region, and for
     the sequence network per contact step.
  4. The whole predicted distribution of contacts against the observed one.
  5. Weights for the browser.

Writes outputs/deep/.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import deep, design, metrics  # noqa: E402
from anc8.concepts import BY_KEY, concept_of  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"
OUT = ROOT / "outputs" / "deep"
RUNGS = [("anc1plus", "ANC1+"), ("anc4plus", "ANC4+"), ("anc8plus", "ANC8+")]
KINDS = {"ladder": "Ladder transformer", "sequence": "Contact-sequence encoder-decoder"}
SEEDS = [2026, 2027, 2028]
N_BOOT = 1000


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def load():
    df = pd.read_pickle(ENHANCED / "ANC8_analysis_frozen_v2.pkl")
    df["caseid"] = df.caseid.astype(str)
    spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
    numeric, categorical = spec["numeric_predictors"], spec["categorical_predictors"]
    train_psus, test_psus = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
    held = df[df.v021.isin(test_psus)].reset_index(drop=True)
    splits = design.folds_to_splits(design.make_psu_stratum_folds(dev))
    return df, dev, held, splits, numeric, categorical


fit = deep.fit


def weighted_metrics(y, p, w):
    return metrics.probability_metrics(y, p, w)


def oof(kind, dev, splits, numeric, categorical, seeds, cfg):
    rows = []
    for seed in seeds:
        P = np.zeros((len(dev), 3))
        for k, (fi, vi) in enumerate(splits):
            model, prep, info = fit(kind, dev.iloc[fi].reset_index(drop=True), numeric, categorical,
                                    seed + 100 * k, cfg)
            P[vi] = deep.predict(model, prep, dev.iloc[vi].reset_index(drop=True))
            log(f"  {kind} seed {seed} fold {k}: {info['epochs']} epochs, val loss {info['best_val_loss']:.4f}")
        w = (dev.v005 / 1e6).to_numpy()
        for j, (outcome, label) in enumerate(RUNGS):
            m = weighted_metrics(dev[outcome].to_numpy(), P[:, j], w)
            rows.append({"model": KINDS[kind], "kind": kind, "seed": seed, "rung": label, **m})
        viol = float(((P[:, 2] > P[:, 1] + 1e-9) | (P[:, 1] > P[:, 0] + 1e-9)).mean())
        rows[-1]["ladder_violations"] = viol
    return pd.DataFrame(rows)


def tree_oof_reference():
    """The tree models' development out-of-fold scores, from the same folds."""
    out = []
    for outcome, label in RUNGS:
        p = ENHANCED / outcome / "development_oof_performance.csv"
        if p.exists():
            d = pd.read_csv(p)
            d["rung"] = label
            out.append(d)
    return pd.concat(out) if out else pd.DataFrame()


def champions():
    p = ROOT / "outputs" / "ladder" / "ladder_performance.csv"
    if not p.exists():
        return {}
    d = pd.read_csv(p)
    return dict(zip(d.outcome, d.best_model))


def heldout_compare(kind_preds: dict, held: pd.DataFrame):
    """Held-out AP/AUROC for every network and reference model, and paired bootstrap
    differences network - reference."""
    champ = champions()
    perf, diffs = [], []
    for j, (outcome, label) in enumerate(RUNGS):
        ref = pd.read_csv(ENHANCED / outcome / "heldout_locked_predictions_v2.csv")
        ref["caseid"] = ref.caseid.astype(str)
        frame = held[["caseid", "v021", "v022", "v005", outcome]].merge(ref, on="caseid", how="inner")
        assert len(frame) == len(held), "held-out women do not line up with the stored predictions"
        y = frame[outcome].to_numpy()
        w = (frame.v005 / 1e6).to_numpy()
        refs = {"XGBoost": "prob::XGBoost", "Explainable Boosting": "prob::Explainable Boosting",
                "Logistic regression": "prob::Logistic regression"}
        if champ.get(outcome) and f"prob::{champ[outcome]}" in frame:
            refs[f"Development champion ({champ[outcome]})"] = f"prob::{champ[outcome]}"
        preds = {name: frame[col].to_numpy() for name, col in refs.items()}
        order = held.set_index("caseid").index
        for kind, P in kind_preds.items():
            s = pd.Series(P[:, j], index=order).reindex(frame.caseid).to_numpy()
            preds[KINDS[kind]] = s
        for name, p in preds.items():
            perf.append({"rung": label, "model": name, **weighted_metrics(y, p, w)})
        # paired bootstrap, network minus each reference
        from sklearn.metrics import average_precision_score, roc_auc_score
        boots = {(k, r): [] for k in kind_preds for r in refs}
        for idx in design.stratified_psu_bootstrap(frame.v022.to_numpy(), frame.v021.to_numpy(),
                                                   n_resamples=N_BOOT, seed=2026):
            yy, ww = y[idx], w[idx]
            if yy.min() == yy.max():
                continue
            cache = {}
            for name, p in preds.items():
                cache[name] = (average_precision_score(yy, p[idx], sample_weight=ww),
                               roc_auc_score(yy, p[idx], sample_weight=ww))
            for k in kind_preds:
                for r in refs:
                    a, b = cache[KINDS[k]], cache[r]
                    boots[(k, r)].append((a[0] - b[0], a[1] - b[1]))
        for (k, r), b in boots.items():
            b = np.array(b)
            full_a = weighted_metrics(y, preds[KINDS[k]], w)
            full_b = weighted_metrics(y, preds[r], w)
            diffs.append({"rung": label, "network": KINDS[k], "reference": r,
                          "d_AP": full_a["AP"] - full_b["AP"],
                          "d_AP_lo": float(np.percentile(b[:, 0], 2.5)), "d_AP_hi": float(np.percentile(b[:, 0], 97.5)),
                          "d_AUROC": full_a["AUROC"] - full_b["AUROC"],
                          "d_AUROC_lo": float(np.percentile(b[:, 1], 2.5)), "d_AUROC_hi": float(np.percentile(b[:, 1], 97.5))})
    return pd.DataFrame(perf), pd.DataFrame(diffs)


def tree_ladder_violations(held):
    """How often three separately fitted XGBoost models contradict the ladder."""
    P = []
    for outcome, _ in RUNGS:
        ref = pd.read_csv(ENHANCED / outcome / "heldout_locked_predictions_v2.csv")
        ref["caseid"] = ref.caseid.astype(str)
        P.append(ref.set_index("caseid")["prob::XGBoost"].reindex(held.caseid).to_numpy())
    P = np.stack(P, 1)
    return float(((P[:, 2] > P[:, 1] + 1e-9) | (P[:, 1] > P[:, 0] + 1e-9)).mean())


def attention_tables(df, names, att_ladder, att_seq, S):
    """Aggregate attention to predictors, concepts, regions and contact steps."""
    w = (df.v005 / 1e6).to_numpy()
    concept = np.array([concept_of(n) for n in names])
    keys = sorted(set(concept))

    def by_concept(mat):  # (n, predictors) -> (n, concepts)
        return np.stack([mat[:, concept == k].sum(1) for k in keys], 1)

    rows = []
    lad_c = by_concept(att_ladder)
    for scope, m in [("Ethiopia", np.ones(len(df), bool))] + [
            (str(r), (df.region == r).to_numpy()) for r in sorted(df.region.unique())]:
        v = np.average(lad_c[m], axis=0, weights=w[m])
        for k, x in zip(keys, v):
            rows.append({"model": "ladder", "region": scope, "step": None, "concept": k, "attention": float(x)})
    # sequence network: per contact step
    for step in range(att_seq.shape[1]):
        c = by_concept(att_seq[:, step, :])
        for scope, m in [("Ethiopia", np.ones(len(df), bool))] + [
                (str(r), (df.region == r).to_numpy()) for r in sorted(df.region.unique())]:
            v = np.average(c[m], axis=0, weights=w[m])
            for k, x in zip(keys, v):
                rows.append({"model": "sequence", "region": scope, "step": step, "concept": k, "attention": float(x)})
    att = pd.DataFrame(rows)
    att["label"] = att.concept.map(lambda k: BY_KEY.get(k, {}).get("label", k))
    att["modifiable"] = att.concept.map(lambda k: BY_KEY.get(k, {}).get("modifiable", False))

    per_pred = pd.DataFrame({"predictor": names, "concept": concept,
                             "ladder_attention": np.average(att_ladder, axis=0, weights=w),
                             "sequence_attention": np.average(att_seq.mean(1), axis=0, weights=w)})
    # drop-off curves: predicted S_k against observed, per region
    counts = df.anc_contacts.fillna(0).clip(upper=deep.MAX_CONTACT).to_numpy()
    curves = []
    for scope, m in [("Ethiopia", np.ones(len(df), bool))] + [
            (str(r), (df.region == r).to_numpy()) for r in sorted(df.region.unique())]:
        pred = np.average(S[m], axis=0, weights=w[m])
        for k in range(S.shape[1]):
            obs = float(np.average(counts[m] >= k, weights=w[m]))
            curves.append({"region": scope, "contact": k, "predicted": float(pred[k]), "observed": obs})
    return att, per_pred, pd.DataFrame(curves)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    df, dev, held, splits, numeric, categorical = load()
    names = numeric + categorical
    cfg = deep.TrainConfig(epochs=8 if args.quick else 80, patience=3 if args.quick else 10)
    seeds = SEEDS[:1] if args.quick else SEEDS
    log(f"development {len(dev)}, held-out {len(held)}, predictors {len(names)}, seeds {seeds}")

    frames = []
    for kind in KINDS:
        log(f"out-of-fold: {KINDS[kind]}")
        frames.append(oof(kind, dev, splits, numeric, categorical, seeds, cfg))
    oof_df = pd.concat(frames)
    oof_df.to_csv(OUT / "oof_by_seed.csv", index=False)
    summary = (oof_df.groupby(["model", "rung"])
               .agg(AP=("AP", "mean"), AP_sd=("AP", "std"), AUROC=("AUROC", "mean"), AUROC_sd=("AUROC", "std"),
                    Brier=("Brier", "mean"), Calibration_slope=("Calibration_slope", "mean"), ICI=("ICI", "mean"))
               .reset_index())
    summary.to_csv(OUT / "oof_summary.csv", index=False)
    ref = tree_oof_reference()
    if len(ref):
        ref.to_csv(OUT / "tree_oof_reference.csv", index=False)

    log("final fits on all development women")
    finals, preds, extra = {}, {}, {}
    for kind in KINDS:
        model, prep, info = fit(kind, dev, numeric, categorical, 2026, cfg)
        finals[kind] = (model, prep)
        preds[kind] = deep.predict(model, prep, held)
        log(f"  {kind}: {info['epochs']} epochs")
    perf, diffs = heldout_compare(preds, held)
    perf.to_csv(OUT / "heldout_performance.csv", index=False)
    diffs.to_csv(OUT / "heldout_paired_bootstrap.csv", index=False)

    log("attention and drop-off curves on all women")
    p_l, a_l = deep.predict(*finals["ladder"], df, attention=True)
    p_s, a_s, S = deep.predict(*finals["sequence"], df, attention=True)
    att, per_pred, curves = attention_tables(df, names, a_l, a_s, S)
    att.to_csv(OUT / "attention_concepts.csv", index=False)
    per_pred.to_csv(OUT / "attention_predictors.csv", index=False)
    curves.to_csv(OUT / "dropoff_curves.csv", index=False)

    # predicted vs observed distribution of contacts (held-out), from the sequence net
    _, _, S_h = deep.predict(*finals["sequence"], held, attention=True)
    w_h = (held.v005 / 1e6).to_numpy()
    pmf = np.concatenate([S_h[:, :-1] - S_h[:, 1:], S_h[:, -1:]], axis=1)
    obs = held.anc_contacts.fillna(0).clip(upper=deep.MAX_CONTACT).astype(int).to_numpy()
    dist = pd.DataFrame({"contacts": np.arange(deep.MAX_CONTACT + 1),
                         "predicted": np.average(pmf, axis=0, weights=w_h),
                         "observed": [float(np.average(obs == k, weights=w_h)) for k in range(deep.MAX_CONTACT + 1)]})
    dist.to_csv(OUT / "contact_distribution_heldout.csv", index=False)

    ladder_viol = {"XGBoost, three separate models": tree_ladder_violations(held),
                   KINDS["ladder"]: float(((preds["ladder"][:, 2] > preds["ladder"][:, 1] + 1e-9) |
                                           (preds["ladder"][:, 1] > preds["ladder"][:, 0] + 1e-9)).mean()),
                   KINDS["sequence"]: float(((preds["sequence"][:, 2] > preds["sequence"][:, 1] + 1e-9) |
                                             (preds["sequence"][:, 1] > preds["sequence"][:, 0] + 1e-9)).mean())}

    weights = {kind: {"prep": finals[kind][1].to_dict(), "state": deep.export_weights(finals[kind][0]),
                      "arch": {"d": 32, "heads": 4, "ffn": 64,
                               "layers": 2 if kind == "ladder" else 1,
                               "steps": deep.MAX_CONTACT}} for kind in KINDS}
    (OUT / "weights.json").write_text(json.dumps(weights), encoding="utf-8")
    # held-out predictions for the browser parity check (aggregate-free: probabilities only, by row order)
    np.save(OUT / "parity_heldout.npy", np.stack([preds["ladder"], preds["sequence"]], 0))

    (OUT / "summary.json").write_text(json.dumps({
        "quick": args.quick, "seeds": seeds, "n_development": len(dev), "n_heldout": len(held),
        "predictors": len(names), "bootstrap_resamples": N_BOOT,
        "ladder_violations_heldout": ladder_viol,
        "minutes": round((time.time() - t0) / 60, 1)}, indent=1), encoding="utf-8")
    log(f"done in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
