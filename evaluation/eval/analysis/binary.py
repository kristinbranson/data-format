"""Binary accuracy: collapse the five-level rating into a two-level decision.

    incorrect = rating <= -1  (concerning / incorrect)    POSITIVE class
    correct   = rating >= 0   (ok / match / better)       negative class

"Incorrect" is the positive class because the question this analysis answers is
*does the rater catch the mistakes?* — mistakes are the event being detected,
and they are the rare one. With that framing the confusion cells read:

    TP  both call it a mistake        FP  rater flags a mistake, truth says fine
    FN  rater says fine, truth says mistake        TN  both call it fine

and the headline numbers say what you would want them to:

    recall     share of real mistakes the rater caught
    precision  share of its flags that were real mistakes
    f1         harmonic mean of the two
    d_prime    z(hit) - z(false alarm), the signal-detection separation, with
               the Hautus log-linear correction so rates of 0 or 1 stay finite

`accuracy` is reported but should not be quoted on its own: mistakes are rare,
so a rater that never flags anything scores well. `balanced_acc` and the
shuffled null (see `loading.add_null`) are the honest comparisons.
"""

from __future__ import annotations

import pandas as pd
from scipy.stats import norm


def collapse(values) -> pd.Series:
    """Five-level ratings -> True (a mistake) / False (fine); NaN stays NaN."""
    s = pd.Series(values, dtype="float")
    return s.where(s.isna(), s <= -1).astype("boolean")


def confusion_counts(df: pd.DataFrame, truth: str, pred: str) -> dict:
    """TP/FP/FN/TN with *incorrect* as the positive class."""
    pair = df[[truth, pred]].dropna()
    t = pair[truth] <= -1      # truth says mistake
    p = pair[pred] <= -1       # rater says mistake
    return {
        "TP": int((p & t).sum()),
        "FP": int((p & ~t).sum()),
        "FN": int((~p & t).sum()),
        "TN": int((~p & ~t).sum()),
    }


def metrics(df: pd.DataFrame, truth: str, pred: str) -> dict:
    """Confusion counts plus recall / precision / F1, accuracy and d-prime."""
    c = confusion_counts(df, truth, pred)
    TP, FP, FN, TN = c["TP"], c["FP"], c["FN"], c["TN"]
    n = TP + FP + FN + TN
    recall = TP / (TP + FN) if (TP + FN) else float("nan")        # = sensitivity
    precision = TP / (TP + FP) if (TP + FP) else float("nan")
    specificity = TN / (TN + FP) if (TN + FP) else float("nan")
    f1 = (2 * recall * precision / (recall + precision)
          if (recall + precision) else float("nan"))
    # Hautus log-linear correction: +0.5 per count so an empty or perfect cell
    # gives a finite d-prime instead of +/-inf.
    hit = (TP + 0.5) / (TP + FN + 1)
    fa = (FP + 0.5) / (FP + TN + 1)
    return {
        "truth": truth, "pred": pred, "n": n,
        "n_mistakes": TP + FN,
        "recall": recall, "precision": precision, "f1": f1,
        "accuracy": (TP + TN) / n if n else float("nan"),
        "balanced_acc": (recall + specificity) / 2 if n else float("nan"),
        "specificity": specificity,
        "d_prime": float(norm.ppf(hit) - norm.ppf(fa)) if n else float("nan"),
        **c,
    }


def table(df: pd.DataFrame, truth: str, preds: tuple[str, ...],
          by: str | list[str] | None = None) -> pd.DataFrame:
    """`metrics` for several predictors, optionally split by dataset/category/agent."""
    if by is None:
        return pd.DataFrame([metrics(df, truth, p) for p in preds])

    keys = [by] if isinstance(by, str) else list(by)
    out = []
    for key, sub in df.groupby(keys, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        for p in preds:
            row = dict(zip(keys, key))
            row.update(metrics(sub, truth, p))
            out.append(row)
    return pd.DataFrame(out)


# Display order: who, how much data, the overall scores, then the
# mistake-catching scores, then the counts everything is derived from.
HEADLINE = ["pred", "n",
            "accuracy", "balanced_acc", "d_prime",
            "recall", "precision", "f1",
            "n_mistakes", "TP", "FP", "FN", "TN"]
