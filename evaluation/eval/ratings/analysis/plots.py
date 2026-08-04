"""The figures that are not the big rating grid.

Four views that used to be written out cell by cell in `analysis.ipynb`, moved
here so a notebook cell is one line and so they read whichever rater is asked
for — the originals were hardwired to a `best_rating` column that no longer
exists and could only ever show one human.

    format_scatter(r)                    per-trial correctness, grouped by
                                         the raw data's format
    confusion_grid(df, ("KB", "claude")) where a rater drifts from the reference
    rating_levels(df)                    how often each agent earned each rating
    trial_variability(df)                how much three trials of the same
                                         agent disagree with each other
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .. import figure
from .agreement import RATING_LEVELS, confusion
from .loading import DATASET_FORMAT
from .render import display_name

# Claude Code is orange and Codex is blue throughout this project — the
# opposite of what matplotlib's default cycle would give them, so both are
# named explicitly everywhere rather than relying on plot order.
AGENT_ORDER = ["claude-code", "codex"]
AGENT_LABEL = {"claude-code": "Claude Code", "codex": "Codex"}
AGENT_COLOR = {"claude-code": "C1", "codex": "C0"}

LEVEL_NAMES = {-2: "incorrect", -1: "concerning", 0: "ok",
               1: "match", 2: "better"}


def format_scatter(ratings, rater: str = "LZ", *, ax=None, seed: int = 64,
                   datasets: list[str] | None = None):
    """Per-trial fraction of questions rated ≥ ok, one column per dataset.

    Columns are ordered so datasets sharing a source format sit together (NWB,
    then IBL, then Numpy/custom), which is the comparison the figure exists to
    make: does the shape of the raw data decide how well the agents do?

    One point per trial, a bar at each agent's mean. Code Efficiency questions
    are excluded by `compute_trial_scores`, as everywhere else.
    """
    scores = pd.DataFrame(
        figure.compute_trial_scores(ratings.nested, rating_field=rater))
    scores["frac_ok"] = scores["n_ok"] / scores["n_questions"]

    order = [ds for ds in (datasets or DATASET_FORMAT)
             if ds in set(scores["dataset"])]
    offset = {"claude-code": -0.18, "codex": 0.18}
    rng = np.random.default_rng(seed)

    ax = ax or plt.subplots(figsize=(6.5, 4))[1]
    # Alternating bands: with 8 columns and two agents each, the dataset
    # boundaries are otherwise hard to see.
    for i in range(len(order)):
        if i % 2:
            ax.axvspan(i - 0.5, i + 0.5, facecolor="#f2f2f2", zorder=0)

    for i, ds in enumerate(order):
        for agent in AGENT_ORDER:
            vals = scores.loc[(scores.dataset == ds) & (scores.agent == agent),
                              "frac_ok"].to_numpy()
            if not len(vals):
                continue
            x = i + offset[agent] + rng.uniform(-0.1, 0.1, size=len(vals))
            ax.scatter(x, vals, color=AGENT_COLOR[agent], alpha=0.8, s=40,
                       edgecolor="white", linewidth=0.5,
                       label=AGENT_LABEL[agent] if i == 0 else None)
            ax.hlines(vals.mean(), i + offset[agent] - 0.13,
                      i + offset[agent] + 0.13,
                      color=AGENT_COLOR[agent], linewidth=2)

    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([display_name(ds) for ds in order], rotation=30, ha="right")
    ax.set_xlim(-0.5, len(order) - 0.5)
    ax.set_ylabel("Proportion Correct")
    ax.legend(loc="lower right")
    _format_brackets(ax, order)
    ax.figure.tight_layout()
    return ax.figure, ax


def _format_brackets(ax, order):
    """Label the format each run of columns belongs to, under the axis."""
    runs, start = [], 0
    for i in range(1, len(order) + 1):
        if i == len(order) or DATASET_FORMAT[order[i]] != DATASET_FORMAT[order[start]]:
            runs.append((start, i - 1, DATASET_FORMAT[order[start]]))
            start = i
    for first, last, name in runs:
        ax.text((first + last) / 2, -0.30, name, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=9, fontstyle="italic", color="#555")


# Both axes run better -> incorrect, so the agreeing-and-fine corner is at the
# top left and severity increases away from it, the way the rating scale reads.
CONFUSION_LEVELS = tuple(reversed(RATING_LEVELS))


def confusion_grid(df: pd.DataFrame, raters=("KB", "claude", "codex"), *,
                   truth: str = "LZ", levels=CONFUSION_LEVELS, title=None):
    """One rating-vs-reference matrix per rater, counts annotated.

    The diagonal is agreement; everything off it is where that rater reads the
    same code differently from `truth`. Worth looking at before any single
    agreement number, because it shows the *direction* of a disagreement —
    a judge that is systematically harsh looks nothing like one that is noisy.
    Above the diagonal the rater is kinder than the reference, below it harsher.
    """
    fig, axes = plt.subplots(1, len(raters),
                             figsize=(2.0 + 3.2 * len(raters), 4.0), squeeze=False)
    axes = axes[0]
    if title:
        fig.suptitle(title, fontsize=12, fontweight="bold", y=1.02)

    for col, rater in enumerate(raters):
        ax = axes[col]
        cm = confusion(df, rater, truth).reindex(index=list(levels),
                                                 columns=list(levels), fill_value=0)
        counts = cm.to_numpy()
        ax.imshow(counts, cmap="Blues")
        vmax = counts.max() or 1
        for i in range(len(levels)):
            for j in range(len(levels)):
                v = int(counts[i, j])
                if v:
                    ax.text(j, i, str(v), ha="center", va="center", fontsize=9,
                            color="white" if v > 0.55 * vmax else "black")
        names = [LEVEL_NAMES[v] for v in levels]
        ax.set_xticks(range(len(levels)))
        ax.set_yticks(range(len(levels)))
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        ax.set_yticklabels(names, fontsize=8)
        ax.set_title(rater, fontsize=10, fontweight="bold")
        ax.set_xlabel(f"{truth} (reference)", fontsize=9)
        if col == 0:
            ax.set_ylabel("rater rating", fontsize=9)
    fig.tight_layout()
    return fig, axes


def rating_levels(df: pd.DataFrame, rater: str = "LZ", *, ax=None):
    """How many (question, trial) rows each agent earned at each rating level."""
    levels = list(RATING_LEVELS)
    counts = {agent: np.array([int((df.loc[df.agent == agent, rater] == lv).sum())
                               for lv in levels])
              for agent in AGENT_ORDER}

    x = np.arange(len(levels))
    width = 0.4
    ax = ax or plt.subplots(figsize=(5.5, 4))[1]
    for sign, agent in zip((-1, 1), AGENT_ORDER):
        ax.bar(x + sign * width / 2, counts[agent], width,
               label=AGENT_LABEL[agent], color=AGENT_COLOR[agent], alpha=0.8)
        for i, n in enumerate(counts[agent]):
            ax.text(i + sign * width / 2, n, str(n), ha="center", va="bottom",
                    fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([LEVEL_NAMES[lv] for lv in levels])
    ax.set_xlabel(f"Rating ({rater})")
    ax.set_ylabel("Number of Trials")
    ax.legend()
    ax.figure.tight_layout()
    return ax.figure, ax


def trial_variability(df: pd.DataFrame, rater: str = "LZ", *, kind: str = "spread"):
    """How much the three trials of one agent disagree on the same question.

    `kind="spread"`  one point per question: its worst rating minus its best.
    `kind="delta"`   one point per trial: that trial minus the question's best.

    Both are ≤ 0, and both answer "is a trial's rating a property of the agent
    or a roll of the dice?" — mass at 0 means the trials agree.
    """
    def values(sub):
        g = sub.groupby(["dataset", "qid"])[rater]
        if kind == "spread":
            return (g.min() - g.max()).dropna().to_numpy()
        return (sub[rater] - g.transform("max")).dropna().to_numpy()

    panels = [("Combined", values(df), "gray")]
    panels += [(AGENT_LABEL[a], values(df[df.agent == a]), AGENT_COLOR[a])
               for a in AGENT_ORDER]

    bins = np.arange(-3.5, 1.5, 1)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4), sharey=True)
    for ax, (label, vals, color) in zip(axes, panels):
        ax.hist(vals, bins=bins, color=color, alpha=0.8, density=True)
        ax.set_xlabel("per question min - max" if kind == "spread"
                      else "per trial Δmax")
        ax.set_title(f"{label}  (n = {len(vals)})")
        ax.set_xticks(np.arange(-3, 1))
    axes[0].set_ylabel("Proportion of questions" if kind == "spread"
                       else "Proportion of trials")
    fig.tight_layout()
    return fig, axes
