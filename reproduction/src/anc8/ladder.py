"""Comparing predictor importance across the ANC contact ladder.

The question this module exists to answer: **does what predicts reaching
antenatal care at all differ from what predicts completing the full schedule?**

The hypothesis worth testing is that they do differ, and in a specific
direction -- that distance, transport and physical access govern whether a
woman reaches care even once, while wealth, education and her own decision-making
latitude govern whether she keeps coming back eight times. If that holds, it
says something operational: improving access buys ANC1, but improving ANC8
needs something else.

Three guards against fooling ourselves:

**Importance is computed three independent ways.** A shift that appears in only
one method is a property of that method, not of Ethiopian antenatal care. Only
shifts visible in at least two are reported as findings.

**Importance is normalised within each rung.** Base rates differ four-fold
across the ladder, and the raw scale of log-odds contributions moves with them.
Comparing shares of total importance removes that; comparing raw magnitudes
would mostly rediscover the prevalence difference.

**Rank shifts get bootstrap intervals.** With 95 predictors, several will
reorder between rungs by chance alone. A shift that a resampling interval
cannot separate from zero is not a finding.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import outcomes as _outcomes

# Grouping used for the domain roll-up. The ladder hypothesis is really about
# these blocks rather than individual predictors, and a block-level shift is
# far more robust than any single variable's.
DOMAINS = {
    "Access and distance": [
        "s1101", "s1101b", "s1102", "s1101a", "travel_hospital_log",
        "travel_healthpost_log", "travel_hospital_is_zero",
        "travel_healthpost_is_zero", "travel_hospital_topcoded",
        "travel_healthpost_topcoded", "healthpost_time_missing",
        "transport_mode_group", "v467b", "v467c", "v467d", "v467f",
        "access_barrier_count", "v115",
    ],
    "Socioeconomic": [
        "v191", "v191a", "v190", "v190a", "wealth_quintile", "asset_index",
        "v119", "v120", "v121", "v123", "v169a", "v170", "v113", "v116",
        "v127", "v481", "health_insurance", "v136", "v137", "v138",
    ],
    "Education and information": [
        "v133", "v106", "v149", "v155", "maternal_education", "v157", "v158",
        "v159", "v171a", "internet_exposure", "newspaper_weekly",
        "radio_weekly", "television_weekly",
    ],
    "Agency and household": [
        "v743b", "v743d", "v743f", "v744a", "v744b", "v744c", "v744d", "v744e",
        "v745a", "v745b", "decision_participation_count",
        "ipv_justification_count", "healthcare_decision_participation",
        "maternal_current_union_status", "v151", "v152",
        "spousal_education_gap", "spousal_age_gap", "v715", "v729", "v730",
        "partner_education", "partner_occupation_group",
    ],
    "Reproductive history": [
        "v201", "v212", "v218", "v511", "v613", "children_over_ideal",
        "pregnancy_order_group", "preceding_pregnancy_interval_group",
        "pregnancy_intention", "previous_pregnancy_history", "v012",
    ],
    "Geography and culture": [
        "v024", "region", "v025", "residence", "v130", "religion_group",
        "v045c",
    ],
    "Work": ["v716", "v731", "maternal_occupation_group"],
}

PREDICTOR_DOMAIN = {p: d for d, ps in DOMAINS.items() for p in ps}


def domain_of(predictor: str) -> str:
    return PREDICTOR_DOMAIN.get(predictor, "Other")


def normalise(importance: pd.Series) -> pd.Series:
    """Express importance as a share of the rung's total.

    Makes the three rungs comparable despite their different base rates, at the
    cost of hiding whether one rung is predictable overall -- which is what the
    AUROC comparison is for.
    """
    total = importance.abs().sum()
    return importance.abs() / total if total > 0 else importance * 0.0


def assemble(per_rung: dict, method: str) -> pd.DataFrame:
    """Stack one method's per-rung importances into a comparison table.

    `per_rung` maps outcome name -> Series indexed by predictor.
    """
    frame = pd.DataFrame({r: normalise(pd.Series(v)) for r, v in per_rung.items()})
    frame = frame.reindex(columns=[r for r in _outcomes.LADDER if r in frame])
    frame = frame.fillna(0.0)

    for r in frame.columns:
        frame[f"rank_{r}"] = frame[r].rank(ascending=False, method="min").astype(int)

    # Shifts only mean something with at least two rungs to shift between.
    # With one rung the "first" and "last" columns are the same, and every
    # predictor would be labelled flat -- a vacuous result that reads like a
    # real one.
    rungs = [c for c in frame.columns if c in _outcomes.LADDER]
    first, last = (rungs[0], rungs[-1]) if len(rungs) >= 2 else (None, None)
    if last is not None:
        frame["share_shift"] = frame[last] - frame[first]
        frame["rank_shift"] = frame[f"rank_{first}"] - frame[f"rank_{last}"]

        # A predictor whose share GROWS towards ANC8 matters more for sustained
        # engagement than for first contact, and vice versa. The threshold is
        # deliberately loose: it labels a tendency, and the bootstrap decides
        # whether it is real.
        def classify(row):
            if row["share_shift"] > 0.005:
                return "engagement-limited"
            if row["share_shift"] < -0.005:
                return "access-limited"
            return "flat"

        frame["pattern"] = frame.apply(classify, axis=1)

    frame["domain"] = [domain_of(p) for p in frame.index]
    frame["method"] = method
    return frame.sort_values(_outcomes.LADDER[-1], ascending=False)


def domain_rollup(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate shares to domain level.

    Individual predictors reorder noisily between rungs; domains are where a
    ladder effect, if there is one, should show up robustly.
    """
    rungs = [r for r in _outcomes.LADDER if r in frame.columns]
    roll = frame.groupby("domain")[rungs].sum()
    if len(rungs) > 1:
        roll["shift"] = roll[rungs[-1]] - roll[rungs[0]]
    return roll.sort_values(rungs[-1], ascending=False)


def agreement(frames: dict) -> pd.DataFrame:
    """Spearman correlation between methods, within each rung.

    Reported rather than assumed: if two methods disagree about what matters,
    any ladder shift read off either one is on shaky ground, and the reader
    should know that before believing the headline.
    """
    from scipy.stats import spearmanr

    methods = list(frames)
    rows = []
    for rung in _outcomes.LADDER:
        for i, a in enumerate(methods):
            for b in methods[i + 1:]:
                fa, fb = frames[a], frames[b]
                if rung not in fa.columns or rung not in fb.columns:
                    continue
                common = fa.index.intersection(fb.index)
                if len(common) < 5:
                    continue
                rho = spearmanr(fa.loc[common, rung], fb.loc[common, rung]).statistic

                # Domain level too, because predictor level understates
                # agreement when predictors are correlated. Wealth is the
                # clearest case: SHAP on a booster concentrates it on the
                # single continuous score, while an additive model spreads it
                # across all four wealth variables. The methods are then saying
                # the same thing about WEALTH and different things about
                # v191 -- and the domain roll-up is what shows that.
                da = fa.loc[common].groupby(fa.loc[common, "domain"])[rung].sum()
                db = fb.loc[common].groupby(fb.loc[common, "domain"])[rung].sum()
                shared = da.index.intersection(db.index)
                rho_domain = (float(spearmanr(da[shared], db[shared]).statistic)
                              if len(shared) >= 3 else np.nan)

                rows.append({"rung": rung, "method_a": a, "method_b": b,
                             "spearman_predictor": float(rho),
                             "spearman_domain": rho_domain,
                             "n_predictors": len(common)})
    return pd.DataFrame(rows)


def corroborated(frames: dict, min_methods: int = 2) -> pd.DataFrame:
    """Predictors whose ladder pattern is seen by at least `min_methods`.

    This is the filter that separates a finding from an artefact. A pattern one
    method reports on its own does not appear in the writeup as a result.
    """
    votes = {}
    for method, f in frames.items():
        if "pattern" not in f.columns:
            continue
        for predictor, pattern in f["pattern"].items():
            votes.setdefault(predictor, []).append((method, pattern))

    rows = []
    for predictor, vs in votes.items():
        patterns = [p for _, p in vs]
        for label in ("engagement-limited", "access-limited"):
            n = patterns.count(label)
            if n >= min_methods:
                shifts = [frames[m].loc[predictor, "share_shift"]
                          for m, p in vs if p == label
                          and "share_shift" in frames[m].columns]
                rows.append({
                    "predictor": predictor,
                    "domain": domain_of(predictor),
                    "pattern": label,
                    "methods_agreeing": n,
                    "methods_total": len(vs),
                    "mean_share_shift": float(np.mean(shifts)) if shifts else np.nan,
                })
    if not rows:
        return pd.DataFrame(columns=["predictor", "domain", "pattern",
                                     "methods_agreeing", "methods_total",
                                     "mean_share_shift"])
    return (pd.DataFrame(rows)
            .sort_values("mean_share_shift", key=abs, ascending=False)
            .reset_index(drop=True))
