"""Presentation of the result tables — column names, rater labels, LaTeX.

The analysis modules use the short internal names (`LZ`, `kappa`, `pred`); this
turns them into what belongs in a figure or a paper, in one place, so the
notebook cells stay one line each and the printed and LaTeX versions of a table
can never drift apart.
"""

from __future__ import annotations

import pandas as pd

# Internal rater name -> how it should read in a table.
RATER_LABELS = {
    "LZ": "Human #1",
    "KB": "Human #2",
    "claude": "Claude",
    "codex": "Codex",
    "LZ_null": "Human Null",
}

# Kappa gets a real kappa. The printed table uses the Unicode letter, which
# renders anywhere; the LaTeX table uses math mode.
AGREEMENT_COLUMNS = {
    "rater_a": "Rater A",
    "rater_b": "Rater B",
    "pearson": "Pearson r",
    "kappa": "Cohen's κ",
}
AGREEMENT_COLUMNS_LATEX = dict(AGREEMENT_COLUMNS, kappa=r"Cohen's $\kappa$")

BINARY_COLUMNS = {
    "pred": "Rater",
    "balanced_acc": "Balanced Acc",
    "recall": "Recall",
    "precision": "Precision",
    "f1": "F1",
    "TP": "TP", "FP": "FP", "FN": "FN", "TN": "TN",
}

FLOAT_FMT = "%.3f"

# Metrics shown to three decimals; everything else (the counts) stays integer.
FLOAT_KEYS = {"pearson", "kappa", "spearman", "exact", "accuracy",
              "balanced_acc", "recall", "precision", "f1", "d_prime"}

RATER_COLS = ("rater_a", "rater_b", "pred", "truth")

# Columns a caller may have grouped by; they stay in front because they are what
# the rows are keyed by. Anything else not asked for (n, d_prime, n_mistakes,
# specificity, ...) is dropped rather than trailing along.
GROUP_COLS = ("dataset", "category", "subtype", "agent", "trial", "qid")


def _prepare(df: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    """Relabel raters, then keep and rename `columns`, in their given order."""
    out = df.copy()
    for col in RATER_COLS:
        if col in out.columns:
            out[col] = out[col].map(lambda v: RATER_LABELS.get(v, v))
    lead = [c for c in GROUP_COLS if c in out.columns]
    keep = [c for c in columns if c in out.columns]
    return out[lead + keep].rename(columns=columns)


# `escape=False` is needed so the kappa header stays math, which means the cell
# text has to be escaped by hand — "Human #1" would otherwise comment out the
# rest of the line.
_LATEX_ESCAPES = {"#": r"\#", "&": r"\&", "%": r"\%", "_": r"\_"}


def _escape_cells(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(
                lambda v: "".join(_LATEX_ESCAPES.get(ch, ch) for ch in str(v))
                if isinstance(v, str) else v)
    return out


def _styled(df: pd.DataFrame, columns: dict[str, str]):
    prepared = _prepare(df, columns)
    floats = [label for key, label in columns.items()
              if key in FLOAT_KEYS and label in prepared.columns]
    return prepared.style.hide(axis="index").format({c: "{:.3f}" for c in floats})


def agreement(df: pd.DataFrame):
    """Agreement table, ready to display: no index, no `n`."""
    return _styled(df, AGREEMENT_COLUMNS)


def binary(df: pd.DataFrame):
    """Binary-accuracy table, ready to display: no index, no `n`, no accuracy.

    Raw accuracy is left out on purpose: mistakes are rare, so a rater that
    flags nothing scores ~0.9 on it — `balanced_acc` and the null row are the
    honest comparisons.
    """
    return _styled(df, BINARY_COLUMNS)


def agreement_latex(df: pd.DataFrame, **kwargs) -> str:
    return _to_latex(_escape_cells(_prepare(df, AGREEMENT_COLUMNS_LATEX)), **kwargs)


def binary_latex(df: pd.DataFrame, **kwargs) -> str:
    return _to_latex(_escape_cells(_prepare(df, BINARY_COLUMNS)), **kwargs)


def _to_latex(df: pd.DataFrame, *, caption: str | None = None,
              label: str | None = None) -> str:
    return df.to_latex(index=False, escape=False, float_format=FLOAT_FMT,
                       caption=caption, label=label)
