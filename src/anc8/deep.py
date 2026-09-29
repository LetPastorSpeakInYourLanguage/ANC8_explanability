"""Neural networks for the ANC ladder (PyTorch, CPU).

Two networks, each built where a network can do something the tree models cannot:

LadderTransformer
    A feature-token transformer (FT-Transformer style: every predictor becomes one
    token, a [CLS] token reads them all through self-attention). Its head predicts
    the ladder as a chain of continuations:
        P(ANC1+) = s1,  P(ANC4+) = s1 * s2,  P(ANC8+) = s1 * s2 * s3
    so the three probabilities can never contradict each other (P8 <= P4 <= P1),
    which three separate classifiers do not guarantee. The [CLS] attention over the
    predictor tokens is recorded for every woman.

ContactSequenceNet
    An encoder-decoder over the contact count itself. The encoder reads the woman's
    predictors into tokens; a GRU decoder then steps through contacts 1, 2, ..., 9,
    and at each step attends back over the predictor tokens (cross-attention) and
    outputs the probability that a woman who reached contact k goes on to k+1. The
    product of those continuation probabilities is her whole predicted
    distribution of contacts, so ANC1+, ANC4+ and ANC8+ all fall out of one model,
    and the per-step attention says which predictors matter for continuing at each
    contact. The count is right-censored at 9 ("nine or more").

Both are trained with survey weights, on the study's own PSU-grouped folds, and are
reported against the tree models on the same folds and the same held-out women.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import torch
from torch import nn

torch.set_num_threads(max(1, torch.get_num_threads()))

MAX_CONTACT = 9  # counts of 9 or more are one class, "nine or more"


# ------------------------------------------------------------------ preprocessing
@dataclass
class Prep:
    """Fitted on training rows only: medians and scales for numeric predictors, an
    integer code per level for categorical ones (0 = unseen or missing)."""

    numeric: list[str]
    categorical: list[str]
    med: dict = field(default_factory=dict)
    mean: dict = field(default_factory=dict)
    std: dict = field(default_factory=dict)
    levels: dict = field(default_factory=dict)

    def fit(self, df: pd.DataFrame) -> "Prep":
        for c in self.numeric:
            x = pd.to_numeric(df[c], errors="coerce").astype(float)
            m = float(np.nanmedian(x)) if x.notna().any() else 0.0
            xf = x.fillna(m)
            self.med[c] = m
            self.mean[c] = float(xf.mean())
            self.std[c] = float(xf.std()) or 1.0
        for c in self.categorical:
            vals = sorted(df[c].dropna().astype(str).unique())
            self.levels[c] = {v: i + 1 for i, v in enumerate(vals)}
        return self

    def transform(self, df: pd.DataFrame):
        n = len(df)
        xn = np.zeros((n, len(self.numeric)), np.float32)
        xm = np.zeros((n, len(self.numeric)), np.float32)
        for j, c in enumerate(self.numeric):
            x = pd.to_numeric(df[c], errors="coerce").astype(float).to_numpy()
            miss = np.isnan(x)
            xm[:, j] = miss
            x = np.where(miss, self.med[c], x)
            xn[:, j] = (x - self.mean[c]) / self.std[c]
        xc = np.zeros((n, len(self.categorical)), np.int64)
        for j, c in enumerate(self.categorical):
            mp = self.levels[c]
            xc[:, j] = [mp.get(v, 0) for v in df[c].astype(str).where(df[c].notna(), "__na__")]
        return torch.from_numpy(xn), torch.from_numpy(xm), torch.from_numpy(xc)

    @property
    def cardinalities(self) -> list[int]:
        return [len(self.levels[c]) + 1 for c in self.categorical]

    def to_dict(self) -> dict:
        return {"numeric": self.numeric, "categorical": self.categorical, "med": self.med,
                "mean": self.mean, "std": self.std, "levels": self.levels}


# ------------------------------------------------------------------------ modules
class Tokenizer(nn.Module):
    """One d-dimensional token per predictor. A numeric token is x*w + b (+ a learned
    'missing' vector when the value was imputed); a categorical token is an
    embedding of its level."""

    def __init__(self, n_num: int, cards: list[int], d: int):
        super().__init__()
        self.w = nn.Parameter(torch.randn(n_num, d) * 0.1)
        self.b = nn.Parameter(torch.zeros(n_num, d))
        self.miss = nn.Parameter(torch.zeros(n_num, d))
        self.emb = nn.ModuleList([nn.Embedding(c, d) for c in cards])
        for e in self.emb:
            nn.init.normal_(e.weight, std=0.1)

    def forward(self, xn, xm, xc):
        num = xn.unsqueeze(-1) * self.w + self.b + xm.unsqueeze(-1) * self.miss
        cat = torch.stack([e(xc[:, j]) for j, e in enumerate(self.emb)], dim=1) if self.emb else None
        return num if cat is None else torch.cat([num, cat], dim=1)


class AttentionBlock(nn.Module):
    """Pre-norm transformer block that returns its attention weights."""

    def __init__(self, d: int, heads: int, ffn: int, dropout: float):
        super().__init__()
        self.n1 = nn.LayerNorm(d)
        self.att = nn.MultiheadAttention(d, heads, dropout=dropout, batch_first=True)
        self.n2 = nn.LayerNorm(d)
        self.ff = nn.Sequential(nn.Linear(d, ffn), nn.GELU(), nn.Dropout(dropout), nn.Linear(ffn, d))
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        h = self.n1(x)
        a, w = self.att(h, h, h, need_weights=True, average_attn_weights=True)
        x = x + self.drop(a)
        x = x + self.drop(self.ff(self.n2(x)))
        return x, w  # w: (batch, tokens, tokens), averaged over heads


class LadderTransformer(nn.Module):
    def __init__(self, n_num, cards, d=32, layers=2, heads=4, ffn=64, dropout=0.15):
        super().__init__()
        self.tok = Tokenizer(n_num, cards, d)
        self.cls = nn.Parameter(torch.zeros(1, 1, d))
        self.blocks = nn.ModuleList([AttentionBlock(d, heads, ffn, dropout) for _ in range(layers)])
        self.norm = nn.LayerNorm(d)
        self.head = nn.Linear(d, 3)

    def forward(self, xn, xm, xc, return_attention=False):
        t = self.tok(xn, xm, xc)
        x = torch.cat([self.cls.expand(t.shape[0], -1, -1), t], dim=1)
        att = []
        for b in self.blocks:
            x, w = b(x)
            att.append(w[:, 0, 1:])  # what [CLS] attends to, over predictor tokens
        a = self.head(self.norm(x[:, 0]))
        s = torch.sigmoid(a)
        p1 = s[:, 0]
        p4 = p1 * s[:, 1]
        p8 = p4 * s[:, 2]
        out = torch.stack([p1, p4, p8], dim=1)
        if return_attention:
            return out, torch.stack(att, 0).mean(0)
        return out


class ContactSequenceNet(nn.Module):
    """Encoder over predictor tokens; GRU decoder over contacts with cross-attention."""

    def __init__(self, n_num, cards, d=32, layers=1, heads=4, ffn=64, dropout=0.15, steps=MAX_CONTACT):
        super().__init__()
        self.steps = steps
        self.tok = Tokenizer(n_num, cards, d)
        self.cls = nn.Parameter(torch.zeros(1, 1, d))
        self.blocks = nn.ModuleList([AttentionBlock(d, heads, ffn, dropout) for _ in range(layers)])
        self.norm = nn.LayerNorm(d)
        self.step_emb = nn.Embedding(steps, d)
        self.gru = nn.GRUCell(2 * d, d)
        self.q = nn.Linear(d, d)
        self.k = nn.Linear(d, d)
        self.out = nn.Sequential(nn.Linear(2 * d, d), nn.GELU(), nn.Linear(d, 1))
        self.drop = nn.Dropout(dropout)

    def forward(self, xn, xm, xc, return_attention=False):
        t = self.tok(xn, xm, xc)
        x = torch.cat([self.cls.expand(t.shape[0], -1, -1), t], dim=1)
        for b in self.blocks:
            x, _ = b(x)
        x = self.norm(x)
        h = x[:, 0]
        mem = x[:, 1:]
        keys = self.k(mem)
        scale = 1.0 / math.sqrt(keys.shape[-1])
        hazards, atts = [], []
        ctx = torch.zeros_like(h)
        for k in range(self.steps):
            e = self.step_emb.weight[k].expand(h.shape[0], -1)
            h = self.gru(torch.cat([e, ctx], dim=1), h)
            a = torch.softmax((keys @ self.q(h).unsqueeze(-1)).squeeze(-1) * scale, dim=1)
            ctx = (a.unsqueeze(-1) * mem).sum(1)
            hazards.append(self.out(self.drop(torch.cat([h, ctx], dim=1))).squeeze(-1))
            atts.append(a)
        cont = torch.sigmoid(torch.stack(hazards, dim=1))  # P(reach k+1 | reached k), k = 0..8
        if return_attention:
            return cont, torch.stack(atts, dim=1)  # (batch, steps, predictors)
        return cont


def survival(cont: torch.Tensor) -> torch.Tensor:
    """S[:, k] = P(count >= k) for k = 0..steps, from the continuation probabilities."""
    ones = torch.ones(cont.shape[0], 1, dtype=cont.dtype)
    return torch.cat([ones, torch.cumprod(cont, dim=1)], dim=1)


def sequence_nll(cont: torch.Tensor, counts: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
    """Weighted negative log-likelihood of observed counts, censored at MAX_CONTACT."""
    eps = 1e-7
    logc = torch.log(cont.clamp(eps, 1 - eps))
    log1m = torch.log((1 - cont).clamp(eps, 1 - eps))
    csum = torch.cat([torch.zeros(cont.shape[0], 1), torch.cumsum(logc, dim=1)], dim=1)
    c = counts.clamp(max=cont.shape[1]).long()
    ll = csum.gather(1, c.unsqueeze(1)).squeeze(1)
    stop = c < cont.shape[1]
    ll = ll + torch.where(stop, log1m.gather(1, c.clamp(max=cont.shape[1] - 1).unsqueeze(1)).squeeze(1),
                          torch.zeros_like(ll))
    return -(w * ll).sum() / w.sum()


def ladder_bce(p: torch.Tensor, y: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
    eps = 1e-7
    p = p.clamp(eps, 1 - eps)
    l = -(y * torch.log(p) + (1 - y) * torch.log(1 - p))
    return (l.mean(1) * w).sum() / w.sum()


# ----------------------------------------------------------------------- training
@dataclass
class TrainConfig:
    epochs: int = 80
    batch: int = 512
    lr: float = 3e-3
    weight_decay: float = 1e-4
    patience: int = 10
    val_share: float = 0.12


def _batches(n, size, rng):
    idx = rng.permutation(n)
    for i in range(0, n, size):
        yield idx[i:i + size]


def train_one(kind: str, prep: Prep, fit_df: pd.DataFrame, val_df: pd.DataFrame, seed: int,
              cfg: TrainConfig, arch: dict | None = None):
    """Train one network with early stopping on a PSU-grouped validation slice."""
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    arch = arch or {}
    Model = LadderTransformer if kind == "ladder" else ContactSequenceNet
    model = Model(len(prep.numeric), prep.cardinalities, **arch)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)

    def tensors(df):
        xn, xm, xc = prep.transform(df)
        y = torch.tensor(df[["anc1plus", "anc4plus", "anc8plus"]].to_numpy(np.float32))
        c = torch.tensor(df["anc_contacts"].fillna(0).to_numpy(np.float32))
        w = torch.tensor((df["v005"] / 1e6).to_numpy(np.float32))
        return xn, xm, xc, y, c, w

    tr, va = tensors(fit_df), tensors(val_df)

    def loss_of(batch):
        xn, xm, xc, y, c, w = batch
        if kind == "ladder":
            return ladder_bce(model(xn, xm, xc), y, w)
        return sequence_nll(model(xn, xm, xc), c, w)

    best, best_state, bad = float("inf"), None, 0
    for epoch in range(cfg.epochs):
        model.train()
        for b in _batches(len(fit_df), cfg.batch, rng):
            opt.zero_grad()
            loss = loss_of(tuple(t[b] for t in tr))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        with torch.no_grad():
            v = float(loss_of(va))
        if v < best - 1e-5:
            best, bad = v, 0
            best_state = {k: t.detach().clone() for k, t in model.state_dict().items()}
        else:
            bad += 1
            if bad >= cfg.patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, {"best_val_loss": best, "epochs": epoch + 1}


@torch.no_grad()
def predict(model, prep: Prep, df: pd.DataFrame, attention=False):
    """Ladder probabilities (n, 3) for ANC1+/4+/8+, plus attention if asked.

    For the sequence net the attention is (n, steps, predictors) and the survival
    curve S (n, steps + 1) is returned as well."""
    xn, xm, xc = prep.transform(df)
    model.eval()
    if isinstance(model, LadderTransformer):
        p, a = model(xn, xm, xc, return_attention=True)
        return (p.numpy(), a.numpy()) if attention else p.numpy()
    cont, a = model(xn, xm, xc, return_attention=True)
    S = survival(cont)
    p = torch.stack([S[:, 1], S[:, 4], S[:, 8]], dim=1)
    return (p.numpy(), a.numpy(), S.numpy()) if attention else p.numpy()


def export_weights(model: nn.Module) -> dict:
    """Plain nested lists, for the browser's forward pass."""
    return {k: v.detach().cpu().numpy().round(6).tolist() for k, v in model.state_dict().items()}
