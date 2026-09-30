"""Which predictors pay their way: repeated-CV scoring and forward selection.

The question is not "which model is best" but "which variables are worth
collecting". So every comparison here holds the model fixed -- a lightly
regularised logistic regression -- and varies only the predictor set.

Why logistic regression, and why each set gets its own regularisation:

  * it has almost nothing to tune, so it cannot favour one predictor set
    through hyperparameters that happened to be searched on another;
  * its one setting, the regularisation strength C, matters in opposite
    directions for small and large sets -- see C_GRID below. So every set is
    scored at the best C from a common grid rather than at one fixed value.

Scoring is repeated cross-validation on DEVELOPMENT rows only: several split
seeds, each a full PSU-grouped, stratum-preserving 5-fold partition. A step
is judged on the gain per seed, so a variable has to help consistently, not
just on average.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from . import cohorts, models as zoo, tuning

ROOT = Path(__file__).resolve().parents[2]
ENHANCED = ROOT / "outputs" / "enhanced"
HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"

MODEL = "Logistic regression"
# Every candidate set is scored at the best of these regularisation strengths.
# A single fixed C is biased either way: light regularisation lets a large set
# overfit (the 88 score 0.478 at C=1 but 0.508 at the tuned C), heavy
# regularisation handicaps a small one (the 21 score 0.464 at C=1, 0.458 at
# the tuned C). Letting each set take its own best C from a common grid
# removes that tilt. Choosing among four values on the same folds adds a small,
# roughly equal optimism to every set.
C_GRID = (0.003, 0.01, 0.1, 1.0)
PARAMS = {"C_grid": C_GRID}

THRESHOLD = 0.005        # AP a variable must add, on average
MIN_SEEDS_POSITIVE = 4   # ... and on at least this many of the seeds
N_SEEDS = 5

# Three constructs of the 21-predictor set that exist only in the notebook-1
# analysis frame; brought in so every one of the 21 competes on equal terms.
V1_ONLY = ["traditional_media_weekly_count", "household_size", "travel_time_min"]

# Measured at interview rather than during the pregnancy (Guide to DHS
# Statistics: "current status at time of survey"), and plausibly affected by
# the pregnancy or its aftermath. Selected anyway if they earn it, but tagged.
AT_INTERVIEW = {
    "v731": "worked in last 12 months -- pregnancy itself reduces work",
    "v716": "current occupation",
    "maternal_occupation_group": "current occupation",
    "v481": "current insurance -- enrolment can follow facility contact",
    "health_insurance": "current insurance -- enrolment can follow facility contact",
    "v171a": "current internet use",
    "internet_exposure": "current internet use",
    "v613": "ideal family size -- shaped by children already born",
    "children_over_ideal": "ideal family size -- shaped by children already born",
    "v467b": "access problems now, for any illness",
    "v467c": "access problems now, for any illness",
    "v467d": "access problems now, for any illness",
    "v467f": "access problems now, for any illness",
    "access_barrier_count": "access problems now, for any illness",
    "v170": "current bank account",
    "v169a": "current mobile phone",
}


@dataclass
class Pool:
    """The candidate predictors and how each one is typed."""
    numeric: list
    categorical: list
    original21: list          # as used in selection (age at birth for age)
    original21_published: list
    names: list = field(init=False)

    def __post_init__(self):
        self.names = self.numeric + self.categorical

    def split(self, cols):
        return ([c for c in cols if c in self.numeric],
                [c for c in cols if c in self.categorical])


def build_pool(df: pd.DataFrame) -> tuple[pd.DataFrame, Pool]:
    """The 88 candidates: 85 distinct variables plus the 21-set's 3 constructs
    (89 at the ANC-entry horizon, which adds `early_anc`).

    Current age is replaced by age at birth. Number of living children is
    already absent (it duplicates children ever born, and it also falls when
    the index child dies, which leaks what happened after the birth).
    """
    spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
    dropped = set(json.load(open(ENHANCED / "redundancy" / "redundancy_summary.json"))
                  ["dropped"])
    orig = json.load(open(HANDOFF / "predictor_architecture.json"))

    v1 = pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")
    v1["caseid"] = v1.caseid.astype(str)
    df = df.merge(v1[["caseid"] + V1_ONLY], on="caseid", how="left",
                  validate="one_to_one")

    numeric = [c for c in spec["numeric_predictors"] if c not in dropped]
    categorical = [c for c in spec["categorical_predictors"] if c not in dropped]
    assert "v218" not in numeric + categorical

    numeric = ["age_at_birth" if c == "v012" else c for c in numeric]
    numeric += [c for c in V1_ONLY if c in orig["numeric_predictors"]]
    categorical += [c for c in V1_ONLY if c not in orig["numeric_predictors"]]

    published = list(orig["full_cohort_predictors"])
    original21 = ["age_at_birth" if c == "v012" else c for c in published]
    missing = [c for c in original21 if c not in numeric + categorical]
    assert not missing, f"original predictors absent from the pool: {missing}"

    # At the ANC-entry horizon the timing of the first contact is known, and
    # competes like any other candidate.
    if "early_anc" in df.columns:
        categorical = categorical + ["early_anc"]

    for c in categorical:
        df[c] = df[c].astype(str)
    return df, Pool(numeric, categorical, original21, published)


def _digest(ids) -> str:
    """Stable fingerprint of a set of women (Python's str hash is salted per run)."""
    import hashlib
    return hashlib.md5("|".join(map(str, ids)).encode()).hexdigest()[:10]


class Scorer:
    """Repeated-CV AP for any predictor subset, on one cohort's development set.

    The fast path precomputes, for every fold of every seed, the preprocessed
    design matrix of ALL candidates, fitted on that fold's training rows. A
    subset is then scored by slicing columns and fitting only the logistic
    regression.

    That is exact, not an approximation: every step of the linear preprocessor
    -- median imputation, scaling, most-frequent imputation, one-hot encoding --
    is fitted column by column, so fitting it on 88 columns and keeping 5 gives
    the same matrix as fitting it on the 5. `check_exact` verifies it against
    the full pipeline. It turns a ~40-second candidate evaluation into well
    under a second, which is what makes bootstrap re-selection affordable.
    """

    def __init__(self, dev: pd.DataFrame, outcome: str, pool: Pool,
                 n_seeds: int = N_SEEDS, params: dict | None = None):
        assert (dev.partition == "development").all(), "held-out rows reached selection"
        self.dev = dev
        self.pool = pool
        self.outcome = outcome
        self.y = dev[outcome].astype(int).to_numpy()
        self.w = (dev.v005 / 1e6).to_numpy()
        self.prevalence = float(np.average(self.y, weights=self.w))
        self.params = dict(params or PARAMS)
        self.splits = [cohorts.folds(dev, seed=2026 + s) for s in range(n_seeds)]
        self.cache_key = (f"{outcome}_n{len(dev)}_s{n_seeds}_"
                          f"C{'-'.join(map(str, self.params.get('C_grid', [self.params.get('C')])))}_"
                          f"{_digest(dev.caseid)}")
        self._executor = None
        self._precompute()

    def _precompute(self):
        """Per fold: transformed fit/validation matrices and each predictor's columns."""
        num, cat = self.pool.numeric, self.pool.categorical
        X = self.dev[num + cat]
        self.folds = []
        for sp in self.splits:
            per_seed = []
            for fit_idx, val_idx in sp:
                pre = zoo.make_linear_preprocessor(num, cat)
                A = pre.fit_transform(X.iloc[fit_idx])
                B = pre.transform(X.iloc[val_idx])
                # Map each predictor to its output columns, in the same order
                # the pipeline would produce them for any subset.
                cols, start = {}, 0
                for c in num:
                    cols[c] = [start]
                    start += 1
                enc = pre.named_transformers_["categorical"].named_steps["onehot"]
                for c, levels in zip(cat, enc.categories_):
                    cols[c] = list(range(start, start + len(levels)))
                    start += len(levels)
                assert start == A.shape[1]
                wf = self.w[fit_idx] / self.w[fit_idx].mean()
                per_seed.append((np.ascontiguousarray(A), np.ascontiguousarray(B),
                                 fit_idx, val_idx, wf, cols))
            self.folds.append(per_seed)

    def seeds(self, cols) -> np.ndarray:
        """AP on each seed, at the best C in the grid for this set.

        An empty set scores the prevalence: a model with no information ranks
        at random, and random ranking's AP is the base rate.
        """
        from sklearn.linear_model import LogisticRegression

        cols = list(cols)
        if not cols:
            self.last_C = None
            return np.full(len(self.folds), self.prevalence)
        # Pipeline order: numerics first, then categoricals, each in pool order.
        ordered = ([c for c in self.pool.numeric if c in cols]
                   + [c for c in self.pool.categorical if c in cols])
        grid = self.params.get("C_grid", (self.params.get("C", 1.0),))
        best, best_C = None, None
        for C in grid:
            out = []
            for per_seed in self.folds:
                oof = np.zeros(len(self.y))
                for A, B, fit_idx, val_idx, wf, cmap in per_seed:
                    j = [k for c in ordered for k in cmap[c]]
                    m = LogisticRegression(C=C, max_iter=5000,
                                           random_state=zoo.RANDOM_STATE)
                    m.fit(A[:, j], self.y[fit_idx], sample_weight=wf)
                    oof[val_idx] = m.predict_proba(B[:, j])[:, 1]
                out.append(average_precision_score(self.y, oof, sample_weight=self.w))
            out = np.asarray(out)
            if best is None or out.mean() > best.mean():
                best, best_C = out, C
        self.last_C = best_C
        return best

    def seeds_pipeline(self, cols, C: float) -> np.ndarray:
        """The slow, reference path: the real pipeline refitted per subset."""
        num, cat = self.pool.split(list(cols))
        X = self.dev[num + cat]
        return np.asarray([
            average_precision_score(
                self.y,
                tuning.oof_predict(MODEL, {"C": C}, X, self.y, self.w, sp, num, cat),
                sample_weight=self.w)
            for sp in self.splits])

    def check_exact(self, subsets) -> float:
        """Largest AP difference between the fast path and the real pipeline,
        each at the C the fast path chose for that subset."""
        worst = 0.0
        for s in subsets:
            fast = self.seeds(s)
            worst = max(worst, float(np.abs(fast - self.seeds_pipeline(s, self.last_C)).max()))
        return worst


CACHE = ENHANCED / "selection_cache"
_WORKER = None   # the memory-mapped scorer inside each worker process


def _dump(scorer: Scorer, path: Path):
    """Write the precomputed fold matrices where workers can map them."""
    import pickle

    path.mkdir(parents=True, exist_ok=True)
    meta = {"y": scorer.y, "w": scorer.w, "prevalence": scorer.prevalence,
            "params": scorer.params, "pool": scorer.pool, "folds": []}
    for s, per_seed in enumerate(scorer.folds):
        row = []
        for f, (A, B, fit_idx, val_idx, wf, cols) in enumerate(per_seed):
            np.save(path / f"A_{s}_{f}.npy", A)
            np.save(path / f"B_{s}_{f}.npy", B)
            row.append((fit_idx, val_idx, wf, cols))
        meta["folds"].append(row)
    with open(path / "meta.pkl", "wb") as fh:
        pickle.dump(meta, fh)


def _init_worker(path: str):
    """Build a scorer over memory-mapped matrices, once per worker process."""
    import pickle
    from threadpoolctl import threadpool_limits

    global _WORKER
    threadpool_limits(limits=1)   # one core per worker; the pool supplies the rest
    path = Path(path)
    with open(path / "meta.pkl", "rb") as fh:
        meta = pickle.load(fh)
    sc = Scorer.__new__(Scorer)
    sc.y, sc.w, sc.prevalence = meta["y"], meta["w"], meta["prevalence"]
    sc.params, sc.pool = meta["params"], meta["pool"]
    sc.splits = meta["folds"]
    sc.folds = [[(np.load(path / f"A_{s}_{f}.npy", mmap_mode="r"),
                  np.load(path / f"B_{s}_{f}.npy", mmap_mode="r"), *rest)
                 for f, rest in enumerate(row)]
                for s, row in enumerate(meta["folds"])]
    _WORKER = sc


def _worker_seeds(cols):
    return _WORKER.seeds(cols)


def _score_many(scorer: Scorer, sets: list, n_jobs: int) -> list:
    """Score many subsets in parallel.

    Logistic fits take milliseconds, so the unit of parallel work is a whole
    candidate, not a fold. Threads do not help -- the fit holds the GIL -- so
    this uses processes. Each worker maps the fold matrices from disk rather
    than receiving a copy, so eight workers share one ~350 MB set of pages
    instead of holding eight.

    The pool is kept on the scorer and reused across calls, so a forward
    selection pays the worker start-up once rather than at every step.
    """
    if n_jobs == 1:
        return [scorer.seeds(s) for s in sets]
    if getattr(scorer, "_executor", None) is None:
        from concurrent.futures import ProcessPoolExecutor

        path = CACHE / scorer.cache_key
        if not (path / "meta.pkl").exists():
            _dump(scorer, path)
        scorer._executor = ProcessPoolExecutor(
            max_workers=n_jobs, initializer=_init_worker, initargs=(str(path),))
    return list(scorer._executor.map(_worker_seeds, sets, chunksize=1))


def shutdown(scorer: Scorer):
    ex = getattr(scorer, "_executor", None)
    if ex is not None:
        ex.shutdown()
        scorer._executor = None


def add_one(scorer: Scorer, base: list, candidates: list, n_jobs: int = 8) -> pd.DataFrame:
    """Gain from adding each candidate, alone, to a fixed base set."""
    base_ap = scorer.seeds(base)
    res = _score_many(scorer, [base + [c] for c in candidates], n_jobs)
    rows = []
    for c, ap in zip(candidates, res):
        gain = ap - base_ap
        rows.append({"predictor": c, "AP": ap.mean(), "gain": gain.mean(),
                     "gain_min": gain.min(), "gain_max": gain.max(),
                     "seeds_positive": int((gain > 0).sum())})
    return pd.DataFrame(rows).sort_values("gain", ascending=False).reset_index(drop=True)


def remove_one(scorer: Scorer, full: list, n_jobs: int = 8) -> pd.DataFrame:
    """Loss from removing each predictor from the full set."""
    full_ap = scorer.seeds(full)
    res = _score_many(scorer, [[x for x in full if x != c] for c in full], n_jobs)
    rows = []
    for c, ap in zip(full, res):
        loss = full_ap - ap
        rows.append({"predictor": c, "AP_without": ap.mean(), "loss": loss.mean(),
                     "seeds_positive": int((loss > 0).sum())})
    return pd.DataFrame(rows).sort_values("loss", ascending=False).reset_index(drop=True)


def cumulative(scorer: Scorer, base: list, ordered: list, n_jobs: int = 8) -> pd.DataFrame:
    """AP as the ordered candidates are added to the base one at a time."""
    sets = [base + ordered[:k] for k in range(len(ordered) + 1)]
    res = _score_many(scorer, sets, n_jobs)
    return pd.DataFrame({"n_added": range(len(sets)),
                         "added": [""] + ordered,
                         "AP": [r.mean() for r in res],
                         "AP_sd": [r.std(ddof=1) for r in res]})


def forward(scorer: Scorer, candidates: list, threshold: float = THRESHOLD,
            min_seeds: int = MIN_SEEDS_POSITIVE, n_jobs: int = 8,
            max_steps: int = 40, log=print) -> pd.DataFrame:
    """Greedy forward selection from an empty set, stopping at the first step
    whose best candidate fails the threshold.

    Each step records the winner, its gain per seed, and the runner-up -- a
    near-tie at the top means the order between two variables is not
    something the data can decide, and the write-up should say so.
    """
    chosen, remaining = [], list(candidates)
    current = scorer.seeds(chosen)
    steps = []
    for step in range(1, max_steps + 1):
        res = _score_many(scorer, [chosen + [c] for c in remaining], n_jobs)
        gains = [(r - current) for r in res]
        order = np.argsort([-g.mean() for g in gains])
        best, second = order[0], (order[1] if len(order) > 1 else None)
        g = gains[best]
        accepted = g.mean() >= threshold and int((g > 0).sum()) >= min_seeds
        steps.append({
            "step": step, "predictor": remaining[best],
            "AP": float(res[best].mean()), "gain": float(g.mean()),
            "gain_min": float(g.min()), "seeds_positive": int((g > 0).sum()),
            "runner_up": remaining[second] if second is not None else None,
            "runner_up_gain": float(gains[second].mean()) if second is not None else None,
            "accepted": bool(accepted),
        })
        log(f"    step {step:2d}  {remaining[best]:34s} AP {res[best].mean():.4f}  "
            f"gain {g.mean():+.4f} ({int((g > 0).sum())}/{len(g)})"
            f"{'' if accepted else '   <- below threshold, stop'}")
        if not accepted:
            break
        chosen.append(remaining.pop(best))
        current = res[best]
    return pd.DataFrame(steps)


def tiers(steps: pd.DataFrame, full_ap: float, prevalence: float,
          share: float = 0.90) -> pd.DataFrame:
    """Tier 1 = accepted steps until the set reaches `share` of the full
    model's lift over prevalence; Tier 2 = the remaining accepted steps.

    Relative to each outcome's own ceiling, because an absolute cut-off would
    leave ANC1+ -- whose AP starts near 0.78 and tops out near 0.92 -- with an
    empty first tier.
    """
    out = steps.copy()
    target = prevalence + share * (full_ap - prevalence)
    out["lift_share"] = (out.AP - prevalence) / (full_ap - prevalence)
    tier = []
    reached = False
    for r in out.itertuples():
        if not r.accepted:
            tier.append("not selected")
            continue
        tier.append("tier 2" if reached else "tier 1")
        if r.AP >= target:
            reached = True
    out["tier"] = tier
    return out
