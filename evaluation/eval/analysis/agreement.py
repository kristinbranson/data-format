"""How much do two raters agree?

Four measures, because they answer different questions and disagree in
informative ways:

    pearson   treats -2..2 as an interval scale — linear agreement
    spearman  rank-based, so it only assumes the scale is ordered
    exact     fraction of rows where the two gave the identical rating
    kappa     Cohen's kappa, linearly weighted — chance-corrected, and the
              weighting means "match vs ok" counts as a near miss while
              "match vs incorrect" counts as a real disagreement

Exact agreement looks impressive on this data simply because most ratings are
"match"; kappa is the one that discounts that.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from .loading import RATERS

RATING_LEVELS = [-2, -1, 0, 1, 2]


def _weighted_kappa(a: pd.Series, b: pd.Series) -> float:
    """Cohen's kappa with linear weights over the five rating levels."""
    levels = RATING_LEVELS
    idx = {v: i for i, v in enumerate(levels)}
    k = len(levels)
    obs = np.zeros((k, k))
    for x, y in zip(a, b):
        if x in idx and y in idx:
            obs[idx[x], idx[y]] += 1
    n = obs.sum()
    if n == 0:
        return float("nan")
    obs /= n
    row, col = obs.sum(axis=1), obs.sum(axis=0)
    exp = np.outer(row, col)
    w = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    den = (w * exp).sum()
    return float("nan") if den == 0 else 1.0 - (w * obs).sum() / den


def pair_stats(df: pd.DataFrame, a: str, b: str) -> dict:
    """All four measures for one rater pair, over rows where both rated."""
    pair = df[[a, b]].dropna()
    n = len(pair)
    if n < 2:
        return {"rater_a": a, "rater_b": b, "n": n, "pearson": float("nan"),
                "spearman": float("nan"), "exact": float("nan"),
                "kappa": float("nan")}
    x, y = pair[a], pair[b]
    # A rater who never varies has no correlation defined; report NaN rather
    # than letting scipy warn and hand back something meaningless.
    const = x.nunique() < 2 or y.nunique() < 2
    return {
        "rater_a": a, "rater_b": b, "n": n,
        "pearson": float("nan") if const else pearsonr(x, y).statistic,
        "spearman": float("nan") if const else spearmanr(x, y).statistic,
        "exact": float((x == y).mean()),
        "kappa": _weighted_kappa(x, y),
    }


# Shown by default. `spearman` tracks `pearson` closely on a five-level scale,
# and `exact` is dominated by how often "match" is the answer — the shuffled
# null scores higher on it than most real pairs — so neither earns a column.
DEFAULT_MEASURES = ("pearson", "kappa")


def pairwise(df: pd.DataFrame, raters: tuple[str, ...] = RATERS,
             by: str | list[str] | None = None,
             pairs: list[tuple[str, str]] | None = None,
             measures: tuple[str, ...] = DEFAULT_MEASURES) -> pd.DataFrame:
    """
    Every rater pair's agreement, optionally split by `by` (e.g. "dataset",
    "category", or ["dataset", "agent"]).

    `pairs` overrides the combinations of `raters` — pass e.g.
    `[("LZ", "LZ_null")]` to append a null row with the same columns.
    `measures` selects which of pearson / spearman / exact / kappa to keep;
    `pair_stats` always computes all four.
    """
    keep = ["rater_a", "rater_b", "n", *measures]
    pairs = pairs if pairs is not None else list(itertools.combinations(raters, 2))
    if by is None:
        return pd.DataFrame([pair_stats(df, a, b) for a, b in pairs])[keep]

    keys = [by] if isinstance(by, str) else list(by)
    out = []
    for key, sub in df.groupby(keys, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        for a, b in pairs:
            row = dict(zip(keys, key))
            row.update(pair_stats(sub, a, b))
            out.append(row)
    return pd.DataFrame(out)[keys + keep]


def confusion(df: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    """5x5 matrix of rater `a`'s rating against rater `b`'s."""
    pair = df[[a, b]].dropna()
    mat = pd.crosstab(pair[a], pair[b], dropna=False)
    return mat.reindex(index=RATING_LEVELS, columns=RATING_LEVELS, fill_value=0)


def disagreements(df: pd.DataFrame, a: str, b: str, *, min_gap: int = 2,
                  columns: tuple[str, ...] = ("dataset", "qid", "agent", "trial",
                                              "title")) -> pd.DataFrame:
    """Rows where two raters differ by at least `min_gap` scale steps.

    Worth reading directly: a 2+ step gap is a genuine disagreement about
    whether something is acceptable, not a borderline call.
    """
    pair = df[df[a].notna() & df[b].notna()].copy()
    pair["gap"] = (pair[a] - pair[b]).abs()
    hit = pair[pair["gap"] >= min_gap]
    keep = [c for c in columns if c in hit.columns]
    return hit[keep + [a, b, "gap"]].sort_values("gap", ascending=False)
