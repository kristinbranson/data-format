"""How repeatable is a judge? The judge-variability replicates.

Each of the six allen2p trials (3 claude-code + 3 codex, full prompt) was
re-judged five times by each supervised judge, nothing else changed:

    <trial>/judge_replicates/<config>/judgerep<k>/judge/<judge>/llm_judge_eval.json

`config_20260728` is the judges the paper used (claude-opus-4-6, gpt-5.4);
`config_20260919` the newer ones (claude-opus-5, gpt-5.6-sol). Only the judge
was re-run, so any disagreement between two replicates is the judge's own
run-to-run noise -- a ceiling on how well it can agree with anyone else.

    r = load_replicates()          # allen2p rows, LZ / KB / claude / codex +
                                   #   one column per replicate: claude_r1..r5
    retest_table(r)                # re-run vs re-run, next to judge vs human
    consistency(r)                 # per-cell spread across the five re-runs
    spread_bars(r)                 # that spread as a figure

    harshness({OLD_JUDGES: r, NEW_JUDGES: r2})   # old model vs new: severity, bias
    version_shift(r, r2)                         # the same, paired cell by cell
    level_bars({OLD_JUDGES: r, NEW_JUDGES: r2})  # rating distributions
"""

from __future__ import annotations

import itertools
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..experiments import (AGENT_ALIAS, DATASET_ALIAS, EVAL_AGENTS,
                           EXPERIMENTS_DIR, JUDGE_FILE, TRIAL_RE)
from . import judges as judges_mod
from .agreement import pair_stats
from .loading import drop_efficiency, load_ratings

REPLICATE_DATASET = "allen2p"
OLD_JUDGES = "config_20260728"
NEW_JUDGES = "config_20260919"
REPLICATE_JUDGES = ("claude", "codex")

JUDGE_LABEL = {"claude": "Claude", "codex": "Codex"}
# The model behind each judge in each replicate config.
MODEL_LABEL = {OLD_JUDGES: {"claude": "Opus 4.6", "codex": "GPT-5.4"},
               NEW_JUDGES: {"claude": "Opus 5", "codex": "GPT-5.6"}}
LEVEL_NAMES = {-2: "incorrect", -1: "concerning", 0: "ok", 1: "match", 2: "better"}
# Same convention as the agents: Claude orange, Codex blue.
JUDGE_COLOR = {"claude": "C1", "codex": "C0"}
HUMAN_LABEL = {"LZ": "Human #1", "KB": "Human #2"}

# A rating at or below this is a mistake -- the same cut as section 4.
MISTAKE_MAX = -1


def rep_column(judge: str, k: int) -> str:
    return f"{judge}_r{k}"


def rep_columns(df: pd.DataFrame, judge: str) -> list[str]:
    """The replicate columns of one judge, in replicate order."""
    cols = [c for c in df.columns if re.fullmatch(rf"{judge}_r\d+", c)]
    return sorted(cols, key=lambda c: int(c.rsplit("_r", 1)[1]))


def load_replicates(config: str = OLD_JUDGES, *, dataset: str = REPLICATE_DATASET,
                    root=EXPERIMENTS_DIR, process_only: bool = True) -> pd.DataFrame:
    """The dataset's `load_ratings` rows, plus one column per judge replicate.

    Replicates are mapped onto our question numbering by the same
    `map_judge_file` every other judge file goes through, so a replicate column
    lines up with `claude` / `codex` (the run the paper used) and with LZ / KB
    row for row. `process_only` drops the Code Efficiency block, as section 3 does.
    """
    base = load_ratings(datasets=[dataset], judge_modes=("supervised",)).tidy
    ref = judges_mod.reference_stub(dataset)
    task = {v: k for k, v in DATASET_ALIAS.items()}.get(dataset, dataset)

    cells: dict = {}
    for agent_dir in sorted((root / task).iterdir()):
        agent = AGENT_ALIAS.get(agent_dir.name, agent_dir.name)
        if agent not in EVAL_AGENTS:
            continue
        for trial_dir in sorted(agent_dir.iterdir()):
            m = TRIAL_RE.search(trial_dir.name)
            if not m or "badtrial" in trial_dir.name:
                continue
            reps = trial_dir / "judge_replicates" / config
            for rep_dir in sorted(reps.glob("judgerep*")):
                k = int(rep_dir.name.removeprefix("judgerep"))
                for judge_dir in sorted((rep_dir / "judge").iterdir()):
                    path = judge_dir / JUDGE_FILE
                    if not path.exists():
                        continue
                    parsed = judges_mod.map_judge_file(path, dataset, ref=ref)
                    col = rep_column(judge_dir.name, k)
                    for qid, v in parsed.ratings.items():
                        cells[(qid, agent, int(m.group(1)), col)] = v["rating"]

    if not cells:
        raise FileNotFoundError(f"no {config} replicates under {root / task}")
    keys = list(zip(base["qid"], base["agent"], base["trial"]))
    for judge in REPLICATE_JUDGES:
        ks = sorted({int(c.rsplit("_r", 1)[1]) for *_, c in cells
                     if c.startswith(f"{judge}_r")})
        for k in ks:
            col = rep_column(judge, k)
            base[col] = pd.to_numeric(
                pd.Series([cells.get((*key, col)) for key in keys], index=base.index),
                errors="coerce")
    out = drop_efficiency(base) if process_only else base
    out.attrs["config"] = config
    return out


def _summarize(df: pd.DataFrame, label: str, pairs) -> dict:
    """Mean and range of Pearson / kappa over a set of rater pairs."""
    s = pd.DataFrame([pair_stats(df, a, b) for a, b in pairs])
    return {"comparison": label, "pairs": len(s), "n": int(s["n"].median()),
            "pearson": s["pearson"].mean(), "pearson_min": s["pearson"].min(),
            "pearson_max": s["pearson"].max(),
            "kappa": s["kappa"].mean(), "kappa_min": s["kappa"].min(),
            "kappa_max": s["kappa"].max()}


def retest_table(df: pd.DataFrame, *, judges=REPLICATE_JUDGES,
                 reference: str = "LZ", second: str = "KB") -> pd.DataFrame:
    """Re-run against re-run, set beside the agreements it bounds.

    Each row pools every pair of its kind -- ten replicate pairs for a judge
    against itself, 25 for Claude against Codex, five for a judge against a
    human -- and reports the mean with the range across pairs. The human rows
    are the same allen2p rows, so the comparison is like for like.
    """
    reps = {j: rep_columns(df, j) for j in judges}
    rows = [_summarize(df, f"{JUDGE_LABEL[j]} vs {JUDGE_LABEL[j]} (re-runs)",
                       itertools.combinations(reps[j], 2)) for j in judges]
    if len(judges) == 2:
        a, b = judges
        rows.append(_summarize(df, f"{JUDGE_LABEL[a]} vs {JUDGE_LABEL[b]} (re-runs)",
                               itertools.product(reps[a], reps[b])))
    rows += [_summarize(df, f"{JUDGE_LABEL[j]} (re-runs) vs {HUMAN_LABEL[reference]}",
                        [(c, reference) for c in reps[j]]) for j in judges]
    rows.append(_summarize(df, f"{HUMAN_LABEL[second]} vs {HUMAN_LABEL[reference]}",
                           [(second, reference)]))
    # The run the paper reports, against its own re-runs: is it a typical draw?
    # Only for the paper's judges -- another model's re-runs are not re-runs of it.
    if df.attrs.get("config") == OLD_JUDGES:
        rows += [_summarize(df, f"{JUDGE_LABEL[j]} paper run vs its re-runs",
                            [(j, c) for c in reps[j]]) for j in judges if j in df]
    return pd.DataFrame(rows)


def consistency(df: pd.DataFrame, *, judges=REPLICATE_JUDGES) -> pd.DataFrame:
    """Per judge, how the five re-runs of one cell spread.

    A cell is one (question, trial). `unanimous` is the share of cells all five
    re-runs rated identically; `binary unanimous` the same after collapsing to
    mistake / not-mistake, i.e. how often the section-4 verdict would not flip
    whichever run you happened to use. `range` is max - min across re-runs.
    """
    out = []
    for j in judges:
        vals = df[rep_columns(df, j)].dropna()
        rng = vals.max(axis=1) - vals.min(axis=1)
        flagged = (vals <= MISTAKE_MAX).sum(axis=1)
        out.append({
            "judge": JUDGE_LABEL[j], "cells": len(vals),
            "unanimous": float((rng == 0).mean()),
            "binary unanimous": float(((flagged == 0) | (flagged == vals.shape[1])).mean()),
            "mean range": float(rng.mean()),
            "flagged by any run": float((flagged > 0).mean()),
            "flagged by every run": float((flagged == vals.shape[1]).mean()),
        })
    return pd.DataFrame(out)


def unstable_questions(df: pd.DataFrame, *, judges=REPLICATE_JUDGES,
                       top: int = 10) -> pd.DataFrame:
    """The questions whose verdicts move most between re-runs, both judges pooled.

    Mean range across re-runs, averaged over the six trials of the question.
    """
    parts = []
    for j in judges:
        vals = df[rep_columns(df, j)]
        parts.append(df[["qid", "title"]].assign(
            judge=JUDGE_LABEL[j], range=vals.max(axis=1) - vals.min(axis=1)))
    long = pd.concat(parts)
    table = long.pivot_table(index=["qid", "title"], columns="judge",
                             values="range", aggfunc="mean")
    table["both"] = table.mean(axis=1)
    return table.sort_values("both", ascending=False).head(top).round(2)


def spread_bars(df: pd.DataFrame, *, judges=REPLICATE_JUDGES, ax=None):
    """Share of cells by how far apart the five re-runs landed (max - min).

    0 means every re-run gave the same rating; 4 means one said `better` and
    another `incorrect`. Same denominator per judge, so the bars compare directly.
    """
    levels = np.arange(5)
    ax = ax or plt.subplots(figsize=(5, 3.5))[1]
    width = 0.8 / len(judges)
    for i, j in enumerate(judges):
        vals = df[rep_columns(df, j)].dropna()
        rng = (vals.max(axis=1) - vals.min(axis=1)).astype(int)
        share = np.array([(rng == lv).mean() for lv in levels])
        x = levels + (i - (len(judges) - 1) / 2) * width
        bars = ax.bar(x, share, width, color=JUDGE_COLOR[j],
                      label=f"{JUDGE_LABEL[j]} judge (n = {len(vals)})")
        ax.bar_label(bars, labels=[f"{s:.2f}" if s else "" for s in share],
                     fontsize=7, padding=1)
    ax.set_xticks(levels)
    ax.set_xlabel("Spread across five re-runs (max $-$ min rating)")
    ax.set_ylabel("Proportion of cells")
    ax.legend(frameon=False)
    ax.figure.tight_layout()
    return ax.figure, ax


# ---------- old judges against new ----------

def _binary(pred: pd.Series, truth: pd.Series) -> dict:
    """Mistake-catching against `truth`, mistake = rating <= MISTAKE_MAX."""
    ok = pred.notna() & truth.notna()
    p, t = pred[ok] <= MISTAKE_MAX, truth[ok] <= MISTAKE_MAX
    tp, fp = int((p & t).sum()), int((p & ~t).sum())
    fn, tn = int((~p & t).sum()), int((~p & ~t).sum())
    recall = tp / (tp + fn) if tp + fn else np.nan
    spec = tn / (tn + fp) if tn + fp else np.nan
    return {"recall": recall, "precision": tp / (tp + fp) if tp + fp else np.nan,
            "balanced acc": (recall + spec) / 2}


def harshness(frames: dict[str, pd.DataFrame], *, judges=REPLICATE_JUDGES,
              reference: str = "LZ") -> pd.DataFrame:
    """How severe each judge is, per replicate config, pooled over its re-runs.

    `frames` maps a config (OLD_JUDGES / NEW_JUDGES) to its `load_replicates`
    frame. `bias` is the mean of judge - reference on the -2..2 scale, so
    negative is harsher than the reference; `mistake rate` the share of cells
    flagged (<= concerning), with the reference's own rate as the first row.
    Recall / precision / balanced accuracy are against the reference, averaged
    over the five re-runs.
    """
    any_df = next(iter(frames.values()))
    truth = any_df[reference]
    rows = [{"judge": HUMAN_LABEL.get(reference, reference), "model": "",
             "mean rating": truth.mean(), "bias": 0.0,
             "mistake rate": float((truth <= MISTAKE_MAX).mean())}]
    for j in judges:
        for config, df in frames.items():
            cols = rep_columns(df, j)
            vals = df[cols]
            per_rep = pd.DataFrame([_binary(df[c], df[reference]) for c in cols])
            rows.append({
                "judge": JUDGE_LABEL[j], "model": MODEL_LABEL[config][j],
                "mean rating": float(vals.stack().mean()),
                "bias": float(vals.sub(df[reference], axis=0).stack().mean()),
                "mistake rate": float((vals.stack() <= MISTAKE_MAX).mean()),
                "kappa vs " + reference: float(np.mean(
                    [pair_stats(df, c, reference)["kappa"] for c in cols])),
                **per_rep.mean().to_dict(),
            })
    return pd.DataFrame(rows)


def version_shift(old: pd.DataFrame, new: pd.DataFrame, *,
                  judges=REPLICATE_JUDGES) -> pd.DataFrame:
    """Paired old -> new change, cell by cell.

    Each cell's rating is averaged over its five re-runs, so the shift is not
    re-run noise. `shift` is new - old (negative = the new judge is harsher),
    with its SE over cells and a Wilcoxon signed-rank p. `harsher` / `milder`
    are the shares of cells whose mean moved down / up by at least half a level.
    `kappa old-new` pools all 25 old-replicate x new-replicate pairs: how much the
    new judge rates like the old one at all.
    """
    from scipy.stats import wilcoxon

    keys = ["dataset", "qid", "agent", "trial"]
    rows = []
    for j in judges:
        a = old[keys + rep_columns(old, j)].set_index(keys)
        b = new[keys + rep_columns(new, j)].set_index(keys)
        a.columns = [f"old_{c}" for c in a.columns]
        b.columns = [f"new_{c}" for c in b.columns]
        both = a.join(b, how="inner")
        m_old = both.filter(like="old_").mean(axis=1)
        m_new = both.filter(like="new_").mean(axis=1)
        d = (m_new - m_old).dropna()
        pairs = itertools.product(a.columns, b.columns)
        rows.append({
            "judge": JUDGE_LABEL[j],
            "old -> new": f"{MODEL_LABEL[OLD_JUDGES][j]} -> {MODEL_LABEL[NEW_JUDGES][j]}",
            "cells": len(d), "shift": d.mean(), "SE": d.std(ddof=1) / np.sqrt(len(d)),
            "p (Wilcoxon)": wilcoxon(d[d != 0]).pvalue if (d != 0).any() else np.nan,
            "harsher": float((d <= -0.5).mean()), "milder": float((d >= 0.5).mean()),
            "kappa old-new": float(np.mean(
                [pair_stats(both, x, y)["kappa"] for x, y in pairs])),
        })
    return pd.DataFrame(rows)


def level_bars(frames: dict[str, pd.DataFrame], *, judges=REPLICATE_JUDGES,
               reference: str = "LZ"):
    """Rating distribution per judge, old and new model side by side, with the
    reference's in gray. Pooled over the five re-runs, as shares of ratings."""
    levels = sorted(LEVEL_NAMES)
    fig, axes = plt.subplots(1, len(judges), figsize=(5 * len(judges), 3.6),
                             sharey=True)
    truth = next(iter(frames.values()))[reference].dropna()
    for ax, j in zip(np.atleast_1d(axes), judges):
        series = [(HUMAN_LABEL.get(reference, reference), truth, "0.6", 1.0)]
        for i, (config, df) in enumerate(frames.items()):
            series.append((MODEL_LABEL[config][j], df[rep_columns(df, j)].stack(),
                           JUDGE_COLOR[j], 0.45 if i == 0 else 1.0))
        width = 0.8 / len(series)
        for i, (label, vals, color, alpha) in enumerate(series):
            share = [(vals == lv).mean() for lv in levels]
            x = np.arange(len(levels)) + (i - (len(series) - 1) / 2) * width
            ax.bar(x, share, width, color=color, alpha=alpha, label=label)
        ax.set_xticks(np.arange(len(levels)))
        ax.set_xticklabels([LEVEL_NAMES[lv] for lv in levels], rotation=20)
        ax.set_title(f"{JUDGE_LABEL[j]} judge")
        ax.legend(frameon=False, fontsize=8)
    np.atleast_1d(axes)[0].set_ylabel("Proportion of ratings")
    fig.tight_layout()
    return fig, axes
