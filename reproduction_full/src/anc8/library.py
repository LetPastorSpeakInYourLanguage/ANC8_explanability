"""The model library, and the study's own models within it.

The studio and the reproduction notebooks use one part of it: logistic regression,
random forest and XGBoost (and explainable boosting, in the four-model build) on the
21 predictors, at each rung of the ladder, each tuned over the grid notebook 2
prespecified (GRIDS). The rest -- other predictor sets, more model families,
recalibrated versions, ensembles, networks -- is kept as a record of what else was
tried; `ALL_SETS` and `FAMILIES` enumerate it.

A job is one cell of the grid (predictor set x rung x model), or one network
run that fills several rungs at once. Each job writes one file per cell,

    <root>/results/<set>/<rung>/<model>.npz

holding the development out-of-fold probabilities, the held-out probabilities
and a JSON block of what was done. A job whose files exist is done, so a run
that stops -- a Colab disconnect, a closed laptop -- carries on where it left
off. Files are written to a temporary name and renamed, so a half-written file
never counts as done.

Predictor sets, all free of duplicates:

  pool   the 86 distinct candidates: the 95 of feature_spec_v2.json less the
         ten duplicates the redundancy analysis found, current age replaced by
         age at birth, the 21-set's three constructs added, and less the two
         pool columns those constructs recode exactly (v136, travel_hospital_log)
  s21    the 21-predictor set
  short  Tier 1 + Tier 2 of the predictor-value study, per rung
  pars   the parsimonious forward-selection list, per rung, with each dropped
         duplicate replaced by the twin that was kept

Every job tunes, calibrates and ensembles on the development women only, over
the same PSU-grouped folds the rest of the study used; the held-out women are
scored once, after the model is fixed.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

from . import cohorts, design, metrics, outcomes, selection as sel, tuning
from . import models as zoo

ROOT = Path(__file__).resolve().parents[2]
ENHANCED = ROOT / "outputs" / "enhanced"
FEATURE_VALUE = ROOT / "outputs" / "feature_value" / "full"
HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"

RUNGS = ("anc1plus", "anc4plus", "anc8plus")
# The predictor sets the studio and the notebooks use: the 21 alone.
SETS = ("s21",)
# Every set the library holds (the record).
ALL_SETS = ("pool", "s21", "short", "pars")
SET_LABEL = {"pool": "Full pool", "s21": "21-predictor set", "short": "Short set",
             "pars": "Parsimonious set", "pool95": "95 predictors (reproduction check only)"}
FAMILIES = list(zoo.ZOO) + ["CatBoost"]
GPU_FAMILIES = {"CatBoost"}
CALIBRATIONS = ("isotonic", "platt")
NETS = {"ladder": "Ladder transformer", "sequence": "Contact-sequence encoder-decoder"}
NET_SEEDS = (2026, 2027, 2028)
STACK_TOP = 5

# The model lineups the studio is built on: three core models, and the same with
# explainable boosting as a fourth. Each lineup has its own two ensembles; the tuned
# and calibrated cells are shared.
LINEUPS = {
    "four": ["Logistic regression", "Random Forest", "XGBoost", "Explainable Boosting"],
    "three": ["Logistic regression", "Random Forest", "XGBoost"],
}

# The 21 predictors, as the models take them: current age is replaced by age at the
# birth, the one change made to the set. Numbers first, then categories.
S21_NUMERIC = ["age_at_birth", "household_size", "traditional_media_weekly_count", "travel_time_min"]
S21_CATEGORICAL = [
    "maternal_education", "maternal_current_union_status", "maternal_occupation_group", "partner_education",
    "partner_occupation_group", "healthcare_decision_participation", "wealth_quintile", "residence", "region",
    "religion_group", "internet_exposure", "health_insurance", "pregnancy_order_group",
    "preceding_pregnancy_interval_group", "pregnancy_intention", "previous_pregnancy_history",
    "transport_mode_group",
]

# Notebook 2's prespecified tuning grids (section 2.12), searched over the same
# folds, weights and objective as everything else.
GRIDS = {
    "Logistic regression": {"C": [0.01, 0.1, 1.0, 10.0]},
    "Random Forest": {"n_estimators": [300, 600], "max_depth": [None, 6, 12], "min_samples_split": [2, 10],
                      "min_samples_leaf": [1, 5], "max_features": ["sqrt", 0.5]},
    "XGBoost": {"n_estimators": [200, 400], "learning_rate": [0.03, 0.1], "max_depth": [3, 6],
                "min_child_weight": [1, 5], "subsample": [0.8, 1.0], "colsample_bytree": [0.8, 1.0]},
}


def grid_settings(model: str) -> list[dict]:
    """Every setting of a model's grid, in a fixed order."""
    from itertools import product
    g = GRIDS[model]
    return [dict(zip(g, v)) for v in product(*g.values())]


# Pool columns that the 21-set's constructs recode one-to-one (checked on every
# woman: each value of one maps to exactly one value of the other).
CONSTRUCT_TWINS = {"v136": "household_size", "travel_hospital_log": "travel_time_min"}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ------------------------------------------------------------------ predictor sets
@lru_cache(maxsize=1)
def _frame():
    df, pool = sel.build_pool(cohorts.load("full"))
    return df, pool


def raw_frame(cohort: str = "full") -> pd.DataFrame:
    """The cohort with every column in its survey type (codes stay numbers), plus the
    21-set's three constructs. For editing women's records (the planner's levers):
    the models' own preparation (design_matrix) turns categories into text afterwards,
    exactly as it did in training."""
    df = cohorts.load(cohort)
    v1 = pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")
    v1["caseid"] = v1.caseid.astype(str)
    return df.merge(v1[["caseid"] + sel.V1_ONLY], on="caseid", how="left", validate="one_to_one")


@lru_cache(maxsize=1)
def _frame21() -> pd.DataFrame:
    """The analysis frame for the 21 predictors, without the candidate pool: the
    cohort with the 21-set's constructs, categories as text (as the models read them)."""
    df = raw_frame("full")
    for c in S21_CATEGORICAL:
        df[c] = df[c].astype(str)
    return df


@lru_cache(maxsize=1)
def duplicate_of() -> dict:
    """Every dropped column -> the column kept in its place."""
    red = ENHANCED / "redundancy"
    dropped = set(json.load(open(red / "redundancy_summary.json"))["dropped"])
    out = {}
    for r in pd.read_csv(red / "duplicate_pairs.csv").itertuples():
        if r.a in dropped:
            out[r.a] = r.b
        elif r.b in dropped:
            out[r.b] = r.a
    assert set(out) == dropped, f"no kept twin for {dropped - set(out)}"
    out["v012"] = "age_at_birth"
    out.update(CONSTRUCT_TWINS)
    return out


@lru_cache(maxsize=1)
def clean_pool() -> tuple[list, list]:
    _, pool = _frame()
    num = [c for c in pool.numeric if c not in CONSTRUCT_TWINS]
    cat = [c for c in pool.categorical if c not in CONSTRUCT_TWINS]
    assert len(num) + len(cat) == 86, len(num) + len(cat)
    return num, cat


def _split(cols) -> tuple[list, list]:
    num, cat = clean_pool()
    cols = [duplicate_of().get(c, c) for c in cols]
    cols = list(dict.fromkeys(cols))  # a twin already on the list is not added twice
    missing = [c for c in cols if c not in num and c not in cat]
    assert not missing, f"not in the clean pool: {missing}"
    return [c for c in cols if c in num], [c for c in cols if c in cat]


@lru_cache(maxsize=None)
def predictors(set_: str, rung: str) -> tuple[tuple, tuple]:
    """(numeric, categorical) for one predictor set at one rung."""
    if set_ == "s21":
        num, cat = S21_NUMERIC, S21_CATEGORICAL
    elif set_ == "pool":
        num, cat = clean_pool()
    elif set_ == "short":
        s = json.load(open(FEATURE_VALUE / rung / "summary.json"))
        num, cat = _split(s["tier1"] + s["tier2"])
    elif set_ == "pars":
        num, cat = _split(json.load(open(ENHANCED / rung / "parsimonious_spec.json"))["predictors"])
    elif set_ == "pool95":
        spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
        num, cat = spec["numeric_predictors"], spec["categorical_predictors"]
    else:
        raise ValueError(set_)
    return tuple(num), tuple(cat)


def rung_free(set_: str) -> bool:
    """True when the set is the same at every rung, so one network run fills all three."""
    return set_ in ("pool", "s21", "pool95")


# ------------------------------------------------------------------ data
def _digest(ids) -> str:
    import hashlib
    return hashlib.md5("|".join(map(str, ids)).encode()).hexdigest()[:12]


# The study's partition, as digests of the women's case ids (in order) and of the
# fold assignment: any run, on any machine, must reproduce these exactly.
DEV_DIGEST, HELD_DIGEST, FOLD_DIGEST = "abe41580c1bb", "39b5ecd77018", "78fee5ef2269"


@lru_cache(maxsize=2)
def partitions(base: bool = False):
    """Development and held-out women, checked against the study's locked design.

    base=True takes them from the analysis frame alone, before the duplicate
    analysis the candidate pool depends on (for the 95-predictor pool)."""
    df = cohorts.load("full") if base else _frame21()
    dev, held = cohorts.development(df), cohorts.heldout(df)
    folds = design.make_psu_stratum_folds(dev).to_numpy()
    assert _digest(held.caseid) == HELD_DIGEST, "held-out women differ from the study's"
    assert _digest(dev.caseid) == DEV_DIGEST, "development women (or their order) differ from the study's"
    assert _digest(folds) == FOLD_DIGEST, "development folds differ from the study's"
    return dev, held


def design_matrix(frame, num, cat):
    X = frame[list(num) + list(cat)].copy()
    for c in cat:
        X[c] = X[c].astype(str)
    return X


@dataclass
class Data:
    X_dev: pd.DataFrame
    X_held: pd.DataFrame
    y_dev: np.ndarray
    y_held: np.ndarray
    w_dev: np.ndarray
    w_held: np.ndarray
    splits: list
    numeric: list
    categorical: list


def data(set_: str, rung: str) -> Data:
    if set_ not in ("s21", "pool95"):
        return _data_pool(set_, rung)
    dev, held = partitions(base=set_ == "pool95")
    num, cat = (list(x) for x in predictors(set_, rung))
    return Data(design_matrix(dev, num, cat), design_matrix(held, num, cat),
                dev[rung].astype(int).to_numpy(), held[rung].astype(int).to_numpy(),
                (dev.v005 / 1e6).to_numpy(), (held.v005 / 1e6).to_numpy(),
                cohorts.folds(dev), num, cat)


def _data_pool(set_: str, rung: str) -> Data:
    """A pool-derived set (the record): its categories as the candidate pool typed them."""
    df = _frame()[0]
    dev, held = cohorts.development(df), cohorts.heldout(df)
    num, cat = (list(x) for x in predictors(set_, rung))
    return Data(design_matrix(dev, num, cat), design_matrix(held, num, cat),
                dev[rung].astype(int).to_numpy(), held[rung].astype(int).to_numpy(),
                (dev.v005 / 1e6).to_numpy(), (held.v005 / 1e6).to_numpy(),
                cohorts.folds(dev), num, cat)


# ------------------------------------------------------------------ jobs
@dataclass(frozen=True)
class Job:
    kind: str            # grid | tune | calib | stack | cumlink | net
    set: str
    rung: str            # "all" for a network run that fills every rung
    model: str           # the cell's model name (for a net: the network's name)
    base: str = ""       # tune/calib: the family; net: ladder | sequence
    lineup: str = ""     # stack/cumlink over a lineup's models (empty: every family)

    @property
    def members(self) -> list[str]:
        """The tuned models an ensemble is built from."""
        return LINEUPS[self.lineup] if self.lineup else FAMILIES

    @property
    def id(self) -> str:
        return f"{self.set}/{self.rung}/{self.model}"

    @property
    def device(self) -> str:
        if self.kind == "net" or (self.kind in ("tune", "calib") and self.base in GPU_FAMILIES):
            return "gpu"
        return "cpu"

    @property
    def cells(self) -> list[tuple[str, str]]:
        """(rung, model) of every file this job writes."""
        rungs = RUNGS if self.rung == "all" else (self.rung,)
        return [(r, self.model) for r in rungs]

    @property
    def deps(self) -> list[tuple[str, str]]:
        if self.kind == "calib":
            return [(self.rung, self.base)]
        if self.kind in ("stack", "cumlink"):
            return [(self.rung, f) for f in self.members]
        return []


def calibrated_name(family: str, method: str) -> str:
    return f"{family} ({method} calibrated)"


def grid_jobs(models=None) -> list[Job]:
    """The study's models: each model of the lineup on the 21, at every rung, tuned over its grid."""
    return [Job("grid", "s21", r, m, m) for r in RUNGS for m in (models or LINEUPS["three"])]


def jobs(sets=ALL_SETS) -> list[Job]:
    out = []
    for s in sets:
        for r in RUNGS:
            for f in FAMILIES:
                out.append(Job("tune", s, r, f, f))
        for r in RUNGS:
            for f in FAMILIES:
                for m in CALIBRATIONS:
                    out.append(Job("calib", s, r, calibrated_name(f, m), f))
            out.append(Job("stack", s, r, "Stacked ensemble"))
            out.append(Job("cumlink", s, r, "Cumulative-link ensemble"))
        for kind, name in NETS.items():
            if rung_free(s):
                out.append(Job("net", s, "all", name, kind))
            else:
                out.extend(Job("net", s, r, name, kind) for r in RUNGS)
    return out


def ensemble_name(kind: str, lineup: str) -> str:
    """A lineup ensemble's cell name, e.g. "four/Stacked ensemble" (stored in a subfolder)."""
    return f"{lineup}/{'Stacked ensemble' if kind == 'stack' else 'Cumulative-link ensemble'}"


def lineup_jobs(lineup: str, sets=ALL_SETS) -> list[Job]:
    """The two ensembles of one lineup, for every set and rung."""
    return [Job(kind, s, r, ensemble_name(kind, lineup), lineup=lineup)
            for s in sets for r in RUNGS for kind in ("stack", "cumlink")]


def find(job_id: str) -> Job:
    """A job by id. The reproduction set (pool95) is not part of the library,
    but its cells can be run on request."""
    for j in jobs(ALL_SETS + ("pool95",)) + [j for ln in LINEUPS for j in lineup_jobs(ln)] + grid_jobs():
        if j.id == job_id:
            return j
    raise KeyError(job_id)


# ------------------------------------------------------------------ results on disk
def cell_path(root: Path, set_: str, rung: str, model: str) -> Path:
    return Path(root) / "results" / set_ / rung / f"{model}.npz"


def failed_path(root: Path, job: Job) -> Path:
    return Path(root) / "results" / job.set / job.rung / f"{job.model}.failed.txt"


def is_done(root, job: Job) -> bool:
    return all(cell_path(root, job.set, r, m).exists() for r, m in job.cells)


def deps_done(root, job: Job) -> bool:
    return all(cell_path(root, job.set, r, m).exists() for r, m in job.deps)


def load_cell(root, set_, rung, model) -> dict:
    with np.load(cell_path(root, set_, rung, model), allow_pickle=False) as z:
        return {"dev_oof": z["dev_oof"], "held": z["held"], "meta": json.loads(str(z["meta"]))}


def versions() -> dict:
    out = {"python": platform.python_version()}
    for mod in ("numpy", "pandas", "sklearn", "xgboost", "lightgbm", "catboost",
                "interpret", "optuna", "torch"):
        m = sys.modules.get(mod)
        if m is not None:
            out[mod] = getattr(m, "__version__", "?")
    return out


def save_cell(root, job: Job, rung: str, model: str, dev_oof, held, meta: dict, y_dev, w_dev, y_held, w_held):
    dev_oof, held = np.asarray(dev_oof, float), np.asarray(held, float)
    dev, held_df = partitions()
    meta = {
        "set": job.set, "set_label": SET_LABEL[job.set], "rung": rung, "model": model,
        "kind": job.kind, "base": job.base, "device": zoo.DEVICE,
        "predictors": {"numeric": list(predictors(job.set, rung)[0]),
                       "categorical": list(predictors(job.set, rung)[1])},
        "n_predictors": sum(len(x) for x in predictors(job.set, rung)),
        "dev_digest": _digest(dev.caseid), "held_digest": _digest(held_df.caseid),
        "versions": versions(), "written": time.strftime("%Y-%m-%d %H:%M:%S"),
        **meta,
    }
    meta.setdefault("dev_metrics", metrics.probability_metrics(y_dev, dev_oof, w_dev))
    meta["held_metrics"] = metrics.probability_metrics(y_held, held, w_held)
    meta.setdefault("threshold", float(metrics.youden_threshold(y_dev, dev_oof, w_dev)))
    path = cell_path(root, job.set, rung, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    with open(tmp, "wb") as fh:
        np.savez_compressed(fh, dev_oof=dev_oof, held=held,
                            meta=np.array(json.dumps(meta, default=_json_default)))
    os.replace(tmp, path)
    log(f"  wrote {job.set}/{rung}/{model}: dev AP {meta['dev_metrics']['AP']:.4f}, "
        f"held-out AP {meta['held_metrics']['AP']:.4f}")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ------------------------------------------------------------------ running a job
def run(job: Job, root, fold_jobs: int = 5):
    """Run one job. fold_jobs > 1 fits tuning folds in parallel processes."""
    t0 = time.time()
    log(f"{job.id} ({job.kind}, {zoo.DEVICE}, {sum(len(x) for x in predictors(job.set, RUNGS[-1] if job.rung == 'all' else job.rung))} predictors)")
    {"grid": _grid, "tune": _tune, "calib": _calib, "stack": _stack, "cumlink": _cumlink, "net": _net}[job.kind](
        job, root, fold_jobs, t0)
    log(f"{job.id} done in {(time.time() - t0) / 60:.1f} min")


def _tune(job, root, fold_jobs, t0):
    d = data(job.set, job.rung)
    tuning.TRIAL_LOG = log
    n = tuning.TRIALS[job.base]
    params, best = tuning.tune(job.base, d.X_dev, d.y_dev, d.w_dev, d.splits,
                               d.numeric, d.categorical, n_trials=n, n_jobs=fold_jobs)
    oof = tuning.oof_predict(job.base, params, d.X_dev, d.y_dev, d.w_dev, d.splits,
                             d.numeric, d.categorical, n_jobs=fold_jobs)
    pipe = tuning.fit_final(job.base, params, d.X_dev, d.y_dev, d.w_dev, d.numeric, d.categorical)
    held = pipe.predict_proba(d.X_held)[:, 1]
    save_cell(root, job, job.rung, job.model, oof, held,
              {"params": params, "n_trials": n, "tune_best_ap": best,
               "seconds": round(time.time() - t0, 1)},
              d.y_dev, d.w_dev, d.y_held, d.w_held)


def _grid(job, root, fold_jobs, t0):
    """Every setting of the model's grid, scored out of fold; the best refitted on all
    development women and scored once on the held-out women."""
    d = data(job.set, job.rung)
    tried = []
    for p in grid_settings(job.base):
        oof = tuning.oof_predict(job.base, p, d.X_dev, d.y_dev, d.w_dev, d.splits, d.numeric, d.categorical,
                                 n_jobs=fold_jobs)
        tried.append((float(average_precision_score(d.y_dev, oof, sample_weight=d.w_dev)), p, oof))
    best_ap, params, oof = max(tried, key=lambda t: t[0])
    pipe = tuning.fit_final(job.base, params, d.X_dev, d.y_dev, d.w_dev, d.numeric, d.categorical)
    held = pipe.predict_proba(d.X_held)[:, 1]
    save_cell(root, job, job.rung, job.model, oof, held,
              {"params": params, "grid": GRIDS[job.base], "n_settings": len(tried), "tune_best_ap": best_ap,
               "grid_ap": [t[0] for t in tried], "seconds": round(time.time() - t0, 1)},
              d.y_dev, d.w_dev, d.y_held, d.w_held)


def _logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def _calib(job, root, fold_jobs, t0):
    d = data(job.set, job.rung)
    method = "isotonic" if "isotonic" in job.model else "platt"
    base = load_cell(root, job.set, job.rung, job.base)
    params = base["meta"]["params"]
    dev_oof = tuning.nested_calibrated_oof(job.base, params, d.X_dev, d.y_dev, d.w_dev, d.splits,
                                           d.numeric, d.categorical, method=method)
    # The held-out map is learned on the base model's development out-of-fold
    # predictions and applied to its held-out predictions, as in run_evaluation.py.
    if method == "isotonic":
        cal = IsotonicRegression(out_of_bounds="clip").fit(base["dev_oof"], d.y_dev, sample_weight=d.w_dev)
        held = cal.predict(base["held"])
    else:
        cal = LogisticRegression(max_iter=1000).fit(_logit(base["dev_oof"]).reshape(-1, 1), d.y_dev,
                                                    sample_weight=d.w_dev)
        held = cal.predict_proba(_logit(base["held"]).reshape(-1, 1))[:, 1]
    save_cell(root, job, job.rung, job.model, dev_oof, held,
              {"params": params, "method": method, "seconds": round(time.time() - t0, 1)},
              d.y_dev, d.w_dev, d.y_held, d.w_held)


def _tuned(root, set_, rung, members=None):
    """The set's tuned models at this rung, best development AP first."""
    cells = {f: load_cell(root, set_, rung, f) for f in (members or FAMILIES)}
    order = sorted(cells, key=lambda f: -cells[f]["meta"]["dev_metrics"]["AP"])
    return cells, order


def _stack(job, root, fold_jobs, t0):
    d = data(job.set, job.rung)
    cells, order = _tuned(root, job.set, job.rung, job.members)
    # a lineup blends all its models; the every-family ensemble takes the best five
    top = order if job.lineup else order[:STACK_TOP]
    Z_dev = np.column_stack([cells[f]["dev_oof"] for f in top])
    Z_held = np.column_stack([cells[f]["held"] for f in top])
    meta = LogisticRegression(max_iter=2000).fit(Z_dev, d.y_dev, sample_weight=d.w_dev / d.w_dev.mean())
    save_cell(root, job, job.rung, job.model, meta.predict_proba(Z_dev)[:, 1],
              meta.predict_proba(Z_held)[:, 1],
              {"base_models": top, "weights": meta.coef_.ravel().tolist(),
               "seconds": round(time.time() - t0, 1)},
              d.y_dev, d.w_dev, d.y_held, d.w_held)


def _cumlink(job, root, fold_jobs, t0):
    d = data(job.set, job.rung)
    dev, held = partitions()
    cells, order = _tuned(root, job.set, job.rung, job.members)
    champ = order[0]
    params = cells[champ]["meta"]["params"]
    counts = dev.anc_contacts.to_numpy()
    target = outcomes.OUTCOMES[job.rung]["threshold"]
    pooled, _ = tuning.cumulative_link_oof(champ, params, d.X_dev, counts, d.w_dev, d.splits,
                                           d.numeric, d.categorical, target=target)
    iso = IsotonicRegression(out_of_bounds="clip").fit(pooled, d.y_dev, sample_weight=d.w_dev)
    ks, cols = [], []
    for k in tuning.LADDER_THRESHOLDS:
        yk = (counts >= k).astype(int)
        if yk.min() == yk.max():
            continue
        fk = tuning.fit_final(champ, params, d.X_dev, yk, d.w_dev, d.numeric, d.categorical)
        ks.append(k)
        cols.append(fk.predict_proba(d.X_held)[:, 1])
    mono = tuning._isotonic_decreasing(np.column_stack(cols))
    wts = np.array([1.0 / (1.0 + abs(k - target)) for k in ks])
    held_p = iso.predict((mono * wts).sum(axis=1) / wts.sum())
    save_cell(root, job, job.rung, job.model, iso.predict(pooled), held_p,
              {"base_model": champ, "params": params, "thresholds": ks,
               "seconds": round(time.time() - t0, 1)},
              d.y_dev, d.w_dev, d.y_held, d.w_held)


def _net(job, root, fold_jobs, t0):
    from . import deep

    dev, held = partitions()
    rung_for_set = RUNGS[-1] if job.rung == "all" else job.rung
    num, cat = (list(x) for x in predictors(job.set, rung_for_set))
    splits = cohorts.folds(dev)
    cfg = deep.TrainConfig()
    w_dev = (dev.v005 / 1e6).to_numpy()
    P = np.zeros((len(NET_SEEDS), len(dev), 3))
    for s, seed in enumerate(NET_SEEDS):
        for k, (fi, vi) in enumerate(splits):
            model, prep, info = deep.fit(job.base, dev.iloc[fi].reset_index(drop=True), num, cat,
                                         seed + 100 * k, cfg)
            P[s, vi] = deep.predict(model, prep, dev.iloc[vi].reset_index(drop=True))
            log(f"  {job.base} seed {seed} fold {k}: {info['epochs']} epochs")
    model, prep, info = deep.fit(job.base, dev, num, cat, NET_SEEDS[0], cfg)
    H = deep.predict(model, prep, held)
    seconds = round(time.time() - t0, 1)
    for rung, name in job.cells:
        j = RUNGS.index(rung)
        y = dev[rung].astype(int).to_numpy()
        per_seed = [metrics.probability_metrics(y, P[s, :, j], w_dev)["AP"] for s in range(len(NET_SEEDS))]
        dev_oof = P[:, :, j].mean(0)
        dm = metrics.probability_metrics(y, dev_oof, w_dev)
        dm["AP_seed_mean"] = float(np.mean(per_seed))
        save_cell(root, job, rung, name, dev_oof, H[:, j],
                  {"network": {"epochs": cfg.epochs, "batch": cfg.batch, "lr": cfg.lr,
                               "weight_decay": cfg.weight_decay, "patience": cfg.patience,
                               "val_share": cfg.val_share, "seeds": list(NET_SEEDS),
                               "layers": 2 if job.base == "ladder" else 1, "width": 32, "heads": 4},
                   "dev_ap_seeds": per_seed, "dev_metrics": dm, "seconds": seconds},
                  y, w_dev, held[rung].astype(int).to_numpy(), (held.v005 / 1e6).to_numpy())
