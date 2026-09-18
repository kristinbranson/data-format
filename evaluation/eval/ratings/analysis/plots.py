"""The figures that are not the big rating grid.

The views that used to be written out cell by cell in `analysis.ipynb`, moved
here so a notebook cell is one line and so they read whichever rater is asked
for — the originals were hardwired to a `best_rating` column that no longer
exists and could only ever show one human.

    format_scatter(r)                    per-trial correctness, grouped by
                                         the raw data's format
    confusion_grid(df, ("KB", "claude")) where a rater drifts from the reference
    rater_confusion(df)                  the two human evaluators against each
                                         other, five levels and collapsed
    rating_levels(df)                    how often each agent earned each rating
    score_scatter(df)                    per-trial scores, judge and second
                                         human against the reference human
    trial_variability(df)                how much three trials of the same
                                         agent disagree with each other
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .. import figure
from .agreement import RATING_LEVELS, confusion
from .loading import DATASET_FORMAT, DATASET_ORDER
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
    ax.set_ylim(0.5, 1.02)
    ax.set_ylabel("Proportion Correct")
    ax.legend(loc="lower right")
    _format_brackets(ax, order)
    ax.figure.tight_layout()
    return ax.figure, ax


def _format_brackets(ax, order):
    """Bracket and name each run of columns that share a source format.

    Above the axes, not below it: the dataset names are rotated and their
    height depends on the font, so anything under them collides sooner or
    later.
    """
    runs, start = [], 0
    for i in range(1, len(order) + 1):
        if i == len(order) or DATASET_FORMAT[order[i]] != DATASET_FORMAT[order[start]]:
            runs.append((start, i - 1, DATASET_FORMAT[order[start]]))
            start = i

    for first, last, name in runs:
        ax.plot([first - 0.35, last + 0.35], [1.02, 1.02], transform=ax.get_xaxis_transform(),
                color="#999", linewidth=0.8, clip_on=False)
        ax.text((first + last) / 2, 1.05, name, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=9, fontstyle="italic", color="#555")


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

    names = [LEVEL_NAMES[v] for v in levels]
    for col, rater in enumerate(raters):
        ax = axes[col]
        cm = confusion(df, rater, truth).reindex(index=list(levels),
                                                 columns=list(levels), fill_value=0)
        _annotated_matrix(ax, cm.to_numpy(), names, names, skip_zero=True)
        ax.set_title(rater, fontsize=10, fontweight="bold")
        ax.set_xlabel(f"{truth} (reference)", fontsize=9)
        if col == 0:
            ax.set_ylabel("rater rating", fontsize=9)
    fig.tight_layout()
    return fig, axes


# Okabe-Ito, which is designed so deutan, protan and tritan readers can all tell
# the hues apart. Yellow and black are skipped: the inline counts are drawn
# white-on-color and need the contrast. MISC is neutral gray on purpose — it is
# the "other" bucket and should recede.
CATEGORY_COLORS = {
    "FILTER": "#0072B2",     # blue
    "TIME_RES": "#E69F00",   # orange
    "PROCESS": "#009E73",    # bluish green
    "ASSUME": "#D55E00",     # vermillion
    "VARNAME": "#CC79A7",    # reddish purple
    "MISC": "#999999",       # neutral gray
}


def category_breakdown(summary: pd.DataFrame, *, label_thresh: int = 3):
    """Stacked bars of the difference-category tallies, per dataset.

    `summary` is a `categories.difference_categories()` table. The top panel is
    every dataset summed, on its own x-scale so the shape of the whole is
    readable next to the parts; the bottom panel is one bar per dataset in
    `DATASET_ORDER`, reading top to bottom.
    """
    from .categories import CATEGORY_ORDER

    cats = [c for c in CATEGORY_ORDER if c in summary.index]
    order = [ds for ds in DATASET_ORDER if ds in summary.columns]
    matrix = (summary.drop(index="TOTAL", columns="TOTAL", errors="ignore")
              .T.reindex(index=order, columns=cats).fillna(0).astype(int))
    total = matrix.sum(axis=0)

    def stack(ax, mat, ys):
        left = np.zeros(len(ys))
        for cat in cats:
            vals = mat[cat].to_numpy(dtype=float)
            ax.barh(ys, vals, left=left, height=0.62, color=CATEGORY_COLORS[cat],
                    edgecolor="white", linewidth=0.8, label=cat)
            for y, x, v in zip(ys, left, vals):
                if v >= label_thresh:
                    ax.text(x + v / 2, y, str(int(v)), ha="center", va="center",
                            fontsize=7.5, color="white", fontweight="bold")
            left += vals
        return left

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(6.0, 4.4),
        gridspec_kw={"height_ratios": [1, len(order)], "hspace": 0.45})

    top_left = stack(ax_top, total.to_frame().T, [0])
    ax_top.set_yticks([0], ["Overall"])
    ax_top.set_xlim(0, top_left[0] * 1.02)

    ys = np.arange(len(order))[::-1]          # DATASET_ORDER reads top to bottom
    bot_left = stack(ax_bot, matrix, ys)
    ax_bot.set_yticks(ys, [display_name(ds) for ds in order])
    ax_bot.set_xlim(0, bot_left.max() * 1.02)
    ax_bot.set_xticks(np.arange(0, bot_left.max() + 1, 5))
    ax_bot.set_xlabel("Number of Instances")

    for ax in (ax_top, ax_bot):
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)

    handles, labels = ax_top.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.97),
               ncol=len(cats), frameon=False, fontsize=8,
               handlelength=1.0, handletextpad=0.5, columnspacing=1.2)
    return fig, (ax_top, ax_bot)


# The row column a figure splits on, and how to order/label/color its values.
# Defaults describe the two agents the human evaluation covers; the condition
# analysis passes `group="condition"` with `experiments.CONDITION_ORDER` /
# `CONDITION_LABEL` / `CONDITION_COLOR` to draw the same figures for all six.
def _grouping(df, group, order, labels, colors):
    order = [g for g in (order or AGENT_ORDER) if g in set(df[group])]
    labels = labels or AGENT_LABEL
    colors = colors or AGENT_COLOR
    return order, labels, colors


def _grouped_bars(ax, x, counts, order, labels, colors, *, span=0.8,
                  annotate=True):
    """One bar per group at each x, evenly spread over `span`.

    With two groups and the default span this is the +/- width/2 layout the
    agent figures have always used.
    """
    width = span / len(order)
    starts = (np.arange(len(order)) - (len(order) - 1) / 2) * width
    for dx, g in zip(starts, order):
        ax.bar(x + dx, counts[g], width * 0.92, label=labels.get(g, g),
               color=colors.get(g), alpha=0.8)
        if annotate:
            for i, n in enumerate(counts[g]):
                ax.text(i + dx, n, str(n), ha="center", va="bottom", fontsize=8)


def rating_levels(df: pd.DataFrame, rater: str = "LZ", *, ax=None,
                  group: str = "agent", order=None, labels=None, colors=None):
    """How many (question, trial) rows each group earned at each rating level."""
    order, labels, colors = _grouping(df, group, order, labels, colors)
    levels = list(RATING_LEVELS)
    counts = {g: np.array([int((df.loc[df[group] == g, rater] == lv).sum())
                           for lv in levels])
              for g in order}

    x = np.arange(len(levels))
    ax = ax or plt.subplots(figsize=(5.5, 4))[1]
    _grouped_bars(ax, x, counts, order, labels, colors)

    ax.set_xticks(x)
    ax.set_xticklabels([LEVEL_NAMES[lv] for lv in levels])
    ax.set_xlabel(f"Rating ({rater})")
    ax.set_ylabel("Number of Trials")
    ax.legend()
    ax.figure.tight_layout()
    return ax.figure, ax


SPREAD_LEVELS = [-3, -2, -1, 0]


def question_spread(df: pd.DataFrame, rater: str = "LZ") -> pd.Series:
    """Per question, the worst rating any trial got minus the best.

    0 when every trial of that question agreed; negative otherwise. The one
    definition, shared by the bar chart and the histograms — they disagreed on
    nothing, but two copies of a groupby is one too many.
    """
    g = df.groupby(["dataset", "qid"])[rater]
    return (g.min() - g.max()).dropna()


def spread_bars(df: pd.DataFrame, rater: str = "LZ", *, ax=None,
                levels=SPREAD_LEVELS, group: str = "agent", order=None,
                labels=None, colors=None):
    """Per-question spread (worst trial minus best), the groups side by side.

    0 means all three trials of that group were rated the same; -3 means one
    trial was three levels worse than another. Same denominator for every group
    — each question is counted once per group — so the bars are directly
    comparable and the counts are on them.
    """
    order, labels, colors = _grouping(df, group, order, labels, colors)
    counts = {}
    for g in order:
        spread = question_spread(df[df[group] == g], rater)
        counts[g] = np.array([int((spread == lv).sum()) for lv in levels])

    x = np.arange(len(levels))
    ax = ax or plt.subplots(figsize=(5.5, 4))[1]
    _grouped_bars(ax, x, counts, order, labels, colors)

    ax.set_xticks(x)
    ax.set_xticklabels([str(lv) for lv in levels])
    ax.set_xlabel(f"Per-question spread, min $-$ max ({rater})")
    ax.set_ylabel("Number of Questions")
    ax.legend()
    ax.figure.tight_layout()
    return ax.figure, ax


def trial_variability(df: pd.DataFrame, rater: str = "LZ", *,
                      kind: str = "spread", group: str = "agent",
                      order=None, labels=None, colors=None):
    """How much the three trials of one agent disagree on the same question.

    `kind="spread"`  one point per question: its worst rating minus its best.
    `kind="delta"`   one point per trial: that trial minus the question's best.

    Both are ≤ 0, and both answer "is a trial's rating a property of the agent
    or a roll of the dice?" — mass at 0 means the trials agree.
    """
    order, labels, colors = _grouping(df, group, order, labels, colors)

    def values(sub):
        if kind == "spread":
            return question_spread(sub, rater).to_numpy()
        best = sub.groupby(["dataset", "qid"])[rater].transform("max")
        return (sub[rater] - best).dropna().to_numpy()

    panels = [("Combined", values(df), "gray")]
    panels += [(labels.get(g, g), values(df[df[group] == g]), colors.get(g))
               for g in order]

    bins = np.arange(-3.5, 1.5, 1)
    fig, axes = plt.subplots(1, len(panels), figsize=(3.5 * len(panels), 4),
                             sharey=True)
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


def _annotated_matrix(ax, counts, xlabels, ylabels, *, cmap="Blues", fontsize=9,
                      skip_zero=False):
    """Counts as a heatmap with the number written in each cell.

    `pcolormesh` rather than `imshow`: an image goes into an exported PDF as
    one raster block a few pixels across, which Illustrator blurs. Row 0 at the
    top and square cells, i.e. `imshow`'s layout.
    """
    nrow, ncol = counts.shape
    ax.pcolormesh(np.arange(ncol + 1) - 0.5, np.arange(nrow + 1) - 0.5, counts,
                  cmap=cmap, edgecolors="white", linewidth=0.5)
    ax.set_aspect("equal")
    ax.set_xlim(-0.5, ncol - 0.5)
    ax.set_ylim(nrow - 0.5, -0.5)

    vmax = counts.max() or 1
    for i in range(nrow):
        for j in range(ncol):
            v = int(counts[i, j])
            if v or not skip_zero:
                ax.text(j, i, str(v), ha="center", va="center", fontsize=fontsize,
                        color="white" if v > 0.55 * vmax else "black")
    ax.set_xticks(range(len(xlabels)))
    ax.set_yticks(range(len(ylabels)))
    ax.set_xticklabels(xlabels, rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.tick_params(length=0)


def rater_confusion(df: pd.DataFrame, a: str = "LZ", b: str = "KB", *,
                    levels=CONFUSION_LEVELS, figsize=(7.6, 3.8)):
    """The two human evaluators against each other, at both resolutions.

    Left: the five rating levels. Right: the same rows collapsed at the
    `concerning` boundary. `a` runs along x and `b` up y, as counts — neither
    is truth here, so TP/FP/FN/TN would not name anything.
    """
    from .binary import BINARY_NAMES, confusion as binary_confusion

    fig, axes = plt.subplots(1, 2, figsize=figsize,
                             gridspec_kw={"width_ratios": [5, 2]})

    ratings = confusion(df, b, a).reindex(index=list(levels), columns=list(levels),
                                       fill_value=0)
    names = [LEVEL_NAMES[v] for v in levels]
    _annotated_matrix(axes[0], ratings.to_numpy(), names, names)
    axes[0].set_title("Ratings", fontsize=10)

    two = binary_confusion(df, b, a)
    _annotated_matrix(axes[1], two.to_numpy(), list(BINARY_NAMES),
                      list(BINARY_NAMES))
    axes[1].set_title("Binary Category", fontsize=10)

    for ax in axes:
        ax.set_xlabel(a, fontsize=10)
        ax.set_ylabel(b, fontsize=10)
    fig.tight_layout()
    # Both panels have square cells, so the 2x2 would otherwise be drawn with
    # cells 2.5x the size of the 5x5's. Match the cell size and hang the small
    # panel from the top of the tall one.
    _match_cell_size(axes[0], axes[1], len(levels), 2)
    return fig, axes


def _match_cell_size(ref, ax, n_ref: int, n: int, *, pad: float = 0.1):
    """Resize `ax` so its `n` cells come out the size of `ref`'s `n_ref` cells.

    A fixed aspect shrinks each axes inside its gridspec slot, so the box has
    to be drawn before it can be measured, and `ax` is repositioned `pad` past
    `ref` rather than left where the gridspec put it.
    """
    ax.figure.canvas.draw()
    ref_box = ref.get_position(original=False)
    side = ref_box.height * n / n_ref
    ax.set_position([ref_box.x1 + pad, ref_box.y1 - side,
                     ref_box.width * n / n_ref, side])


def trial_frac_ok(df: pd.DataFrame, rater: str, *, level: float = 0.0) -> pd.DataFrame:
    """Per (dataset, agent, trial): the share of `rater`'s ratings at `level` or better.

    The tidy-frame counterpart of `figure.compute_trial_scores`, which reads
    the nested dict and so cannot see `combined`. Unrated rows leave both
    numerator and denominator, so a rater scores the questions it answered.
    """
    sub = df[df[rater].notna()]
    out = (sub.groupby(["dataset", "agent", "trial"], dropna=False)[rater]
              .agg(n_questions="size", n_ok=lambda s: int((s >= level).sum()))
              .reset_index())
    out["frac_ok"] = out["n_ok"] / out["n_questions"]
    return out


# Okabe-Ito again. One marker for both panels: they are separate axes, so the
# color is a label for the panel rather than something to tell apart at a
# glance, and a single shape keeps the two clouds directly comparable.
SCORE_STYLE = {"KB": ("#009E73", "o"), "combined": ("#D55E00", "o")}
SCORE_LABEL = {"LZ": "Evaluator 1", "KB": "Evaluator 2",
               "combined": "Combined judge"}


def score_scatter(df: pd.DataFrame, raters=("KB", "combined"), *,
                  truth: str = "LZ", level: float = 0.0,
                  labels=None, colors=None, lim=(0.35, 1.05)):
    """One panel per rater: its per-trial score against `truth`'s for the same trial.

    One point per (dataset, agent, trial), scored as section 5 scores a trial:
    the proportion of its questions rated at least ok. Asks whether a judge
    could stand in for a human when *scoring* a run, a weaker requirement than
    agreeing question by question.

    Dashed line is equality, not a fit: below it the rater is harsher than
    `truth`. The solid line is the least-squares fit, over the range with data.
    A panel apiece so the judge's cloud does not hide under the human's; both
    share one range.
    """
    ref = trial_frac_ok(df, truth, level=level)
    key = ["dataset", "agent", "trial"]
    label_of = labels or SCORE_LABEL
    truth_label = label_of.get(truth, truth)

    fig, axes = plt.subplots(1, len(raters), figsize=(4.0 * len(raters), 4.0),
                             sharex=True, sharey=True, squeeze=False)
    axes = axes[0]

    stats = {}
    for ax, rater in zip(axes, raters):
        color, marker = SCORE_STYLE.get(rater, ("C0", "o"))
        color = (colors or {}).get(rater, color)
        pair = ref.merge(trial_frac_ok(df, rater, level=level), on=key,
                         suffixes=("_truth", ""))
        r = pair["frac_ok_truth"].corr(pair["frac_ok"])
        stats[rater] = {"n": len(pair), "pearson": r}

        ax.plot([0, 1], [0, 1], color="#bbb", linestyle="--", linewidth=1, zorder=0)
        ax.scatter(pair["frac_ok_truth"], pair["frac_ok"], color=color,
                   marker=marker, s=32, alpha=0.8, edgecolor="white",
                   linewidth=0.5)
        # Least squares of rater on truth, drawn only across the range that has
        # data — every trial scores > 0.6 with `truth`, so the fit says nothing
        # about the rest of the axes and should not be extended into it.
        x = pair["frac_ok_truth"].to_numpy()
        slope, intercept = np.polyfit(x, pair["frac_ok"].to_numpy(), 1)
        span = np.array([x.min(), x.max()])
        ax.plot(span, slope * span + intercept, color=color, linewidth=1.5,
                zorder=1)
        stats[rater].update(slope=slope, intercept=intercept)
        ax.text(0.04, 0.96, f"$r$ = {r:.2f}   $n$ = {len(pair)}",
                transform=ax.transAxes, ha="left", va="top", fontsize=9)
        ax.set_title(f"{truth_label} vs {label_of.get(rater, rater)}", fontsize=10)
        ax.set_xlabel(f"{truth_label} score")
        # Every trial scores well above chance, so the full 0-1 square would be
        # mostly empty. Both axes get the same range, so equality stays the
        # 45-degree line and the two directions are read the same way.
        ax.set_xlim(*lim)
        ax.set_ylim(*lim)
        ax.set_aspect("equal")

    axes[0].set_ylabel("Rater score")
    fig.tight_layout()
    return fig, axes, pd.DataFrame(stats).T
