"""The multi-dataset summary visualization, for whichever rater is asked for.

All the drawing lives in `ratings.figure` already — this only selects a rater's rating
series, assembles the columns, and sizes the figure. The geometry is the same
arithmetic `analysis.ipynb` worked out: the data axes are sized so cells come
out square once figure margins and subplot spacing are accounted for.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

from .. import figure
from .loading import DATASET_ORDER, Ratings

DISPLAY_NAME = {"allen2p": "Allen2P", "zhang2025": "Zhang2025 (IBL)"}

# Sub-blocks left out of the figure. "Thresholding" exists only in sosa2024
# (two questions), so it costs a row band across every column to show two
# cells. Dropped here rather than at load time — the numeric analyzes still
# see the questions.
DEFAULT_EXCLUDE_SUBTYPES = ("Thresholding",)


RATER_TITLE = {"LZ": "LZ", "KB": "KB",
               "claude": "Claude judge", "codex": "Codex judge",
               "claude_unsup": "Claude judge (unsupervised)",
               "codex_unsup": "Codex judge (unsupervised)"}

LEGEND_ENTRIES = [(-2, "incorrect"), (-1, "concerning"), (0, "ok"),
                  (1, "match"), (2, "better")]


def display_name(ds: str) -> str:
    return DISPLAY_NAME.get(ds, ds[:1].upper() + ds[1:])


def summary_table(ratings: Ratings, rater: str = "LZ", *,
                  datasets: list[str] | None = None,
                  fig_h_in: float = 11.0,
                  show_end_to_end: bool = True,
                  legend: bool = True,
                  exclude_subtypes: tuple[str, ...] = DEFAULT_EXCLUDE_SUBTYPES,
                  exclude_variables: dict[str, tuple[str, ...]] | None = None):
    """Draw the per-question rating grid for one rater. Returns (fig, axes).

    Every dataset gets a column of rating squares, with a shared row layout so
    a given (category, subtype, slot) sits at the same height in every column,
    a label column on the left and a per-subtype average on the right.

    `exclude_subtypes` drops whole sub-blocks; `exclude_variables` drops named
    Data Variables from one dataset, e.g. ``{"sosa2024": ("input: Trial number",)}``.
    Which variables to leave out is an editorial call, so it is made where the
    figure is drawn rather than defaulted here; `uniform_variables()` finds the
    candidates.
    """
    data = ratings.nested
    if datasets is None:
        datasets = [ds for ds in DATASET_ORDER if ds in data]
        datasets += [ds for ds in data if ds not in DATASET_ORDER]
    datasets = [ds for ds in datasets if ds in data]
    n = len(datasets)

    trial_scores = pd.DataFrame(
        figure.compute_trial_scores(data, rating_field=rater))

    exclude_variables = exclude_variables or {}
    all_rows = []
    for ds in datasets:
        rows = figure.collect_rows(data[ds], rating_field=rater)
        drop_vars = set(exclude_variables.get(ds, ()))
        rows = [r for r in rows
                if r["subtype"] not in exclude_subtypes
                and r.get("var_label") not in drop_vars]
        if show_end_to_end and not trial_scores.empty:
            rows = figure.insert_end_to_end(rows, figure.end_to_end_rows(ds, trial_scores))
        all_rows.append(rows)

    summary = figure.compute_subtype_summary(all_rows)
    layout = figure.compute_layout(
        all_rows, subtype_gap={"Data Variables": 0.5, "*": 0.15})

    # Size the figure so the natural axes box already matches the data range
    # ratio — that is what keeps the cells square without aspect="equal",
    # which would stop each column filling its gridspec slot.
    data_y_range = layout["y_top"] - layout["y_bot"] + 1.6 + 0.3
    data_x_range = 6 * layout["square"] + 0.35 + 0.4
    left, right, top, bottom, wspace = 0.02, 0.99, 0.97, 0.05, 0.05
    label_w_ratio, summary_w_ratio = 1.2, 0.7
    cell_aspect_fudge, cell_size_frac = 1.08, 0.925

    axes_h_in = fig_h_in * (top - bottom)
    data_axes_w = axes_h_in / (data_y_range / data_x_range) * cell_aspect_fudge
    fig_w_in = ((label_w_ratio + n + summary_w_ratio) * data_axes_w
                * (1 + wspace) / (right - left))

    fig, axes = plt.subplots(
        1, n + 2, figsize=(fig_w_in, fig_h_in), sharey=True,
        gridspec_kw={"width_ratios": [label_w_ratio] + [1.0] * n + [summary_w_ratio]},
    )
    fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom, wspace=wspace)

    figure.draw_label_column(axes[0], layout, category_label_x=0.3)
    for ax, ds, rows in zip(axes[1:-1], datasets, all_rows):
        figure.draw_dataset_column(ax, rows, layout, title=display_name(ds),
                                  show_labels=False, keep_aspect=False,
                                  cell_size_frac=cell_size_frac)
    figure.draw_summary_column(axes[-1], layout, summary, title="Average")

    fig.suptitle(f"Ratings by {RATER_TITLE.get(rater, rater)}", y=0.995, fontsize=13)
    if legend:
        _draw_legend(fig)
    return fig, axes


def _draw_legend(fig):
    ax = fig.add_axes([0.18, 0.005, 0.64, 0.035])
    ax.set_xlim(0, len(LEGEND_ENTRIES))
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    for i, (rating, name) in enumerate(LEGEND_ENTRIES):
        x, y, w, h = i + 0.08, 0.2, 0.105, 0.6
        ax.add_patch(Rectangle((x, y), w, h, facecolor=figure.RATING_COLORS[rating],
                               edgecolor="white", linewidth=0.5))
        glyph = figure.RATING_GLYPHS.get(rating)
        if glyph:
            ax.text(x + w / 2, y + h / 2, glyph, ha="center", va="center",
                    color="white", fontsize=8, fontweight="bold")
        ax.text(x + w + 0.05, y + h / 2, name, ha="left", va="center", fontsize=10)
