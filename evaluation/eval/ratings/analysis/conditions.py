"""Judge ratings for every experimental condition, read straight from the run tree.

`loading.load_ratings` covers the two conditions the human evaluation covers —
claude-code and codex at the full prompt — because those are the only ones
mirrored into `eval/<dataset>/judge_supervised/`. The experiment tree holds four
more conditions that were never analyzed:

    claude-code / minimal      codex / minimal        the prompt was cut down
    terminus-opus / full       terminus-gpt / full    a different harness

A **condition** is `(agent, prompt)`. This module loads all six of them, from
`data-format-experiments/` directly, into a frame with the same column names
`loading` produces, so `agreement.pairwise`, `binary.table`, `add_combined` and
the plotting functions work on it unchanged.

Two things it does not have, and one warning:

* **No human ratings.** LZ and KB rated the mirrored conditions only, so the rating
  columns here are the two judges and nothing else. Every number is a judge's
  opinion.
* **No truth column**, therefore no accuracy. Against the human reference the
  supervised judges run at recall 0.74-0.85 but precision 0.24-0.31, so the
  *level* of any condition is inflated by roughly the same unknown amount. Read
  differences between conditions scored by the same judge; do not read the level.
* The two conditions `load_ratings` also covers must come out identical here —
  `validate_against_load_ratings` checks exactly that, and is the reason to
  trust the four new ones.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .. import experiments, paths
from ..experiments import (CONDITION_COLOR, CONDITION_LABEL, CONDITION_ORDER,
                           condition_key)
from . import judges as judges_mod
from . import loading
from .loading import (DATASET_ORDER, EXCLUDED_TITLE_PATTERNS, judge_columns,
                      question_rows)
from .render import display_name

DEFAULT_MODE = "supervised"


@dataclass
class ConditionRatings:
    """Judge ratings for every condition, in the shapes the analysis needs."""

    tidy: pd.DataFrame            # one row per (dataset, qid, condition, trial)
    coverage: pd.DataFrame        # per (dataset, condition, trial, mode, judge)
    inventory: pd.DataFrame       # one row per trial folder found
    skipped: dict = field(default_factory=dict)
    conditions: tuple[str, ...] = ()
    raters: tuple[str, ...] = ()

    @property
    def process_only(self) -> pd.DataFrame:
        """`tidy` with the Code Efficiency questions dropped."""
        return self.tidy[self.tidy["category"] != loading.PERFORMANCE_CATEGORY]

    def rated(self, rater: str) -> pd.DataFrame:
        return self.tidy[self.tidy[rater].notna()]

    def __repr__(self) -> str:
        got = {r: int(self.tidy[r].notna().sum()) for r in self.raters}
        return (f"ConditionRatings({self.tidy['dataset'].nunique()} datasets, "
                f"{len(self.conditions)} conditions, {len(self.tidy)} rows, "
                + ", ".join(f"{k}={v}" for k, v in got.items()) + ")")


def load_condition_ratings(datasets: list[str] | None = None,
                     conditions: tuple[tuple[str, str], ...] = experiments.CONDITIONS,
                     judge_modes: tuple[str, ...] = (DEFAULT_MODE,),
                     max_trial: int | None = experiments.MAX_TRIAL,
                     exclude_titles=EXCLUDED_TITLE_PATTERNS,
                     root=paths.EXPERIMENTS_DIR) -> ConditionRatings:
    """Read judge ratings for `conditions` out of the experiment tree.

    The rows come from the *reference* question list, not from the judge files:
    every question appears once per (condition, trial) whether or not a judge answered
    it, so a gap is NaN and the frame stays a full grid. That is what makes the
    two overlapping conditions comparable cell for cell with `load_ratings`.

    `max_trial` defaults to 3, which drops zhang2025/codex's stray fourth run —
    it is reported in `skipped` rather than silently making one condition n=4.
    """
    wanted = {condition_key(a, p) for a, p in conditions}
    runs, skipped = experiments.discover_runs(
        datasets=datasets, agents={a for a, _ in conditions},
        prompts=tuple({p for _, p in conditions}), modes=judge_modes,
        max_trial=max_trial, root=root)
    runs = [r for r in runs if r.condition in wanted]

    # column -> (mode, judge), e.g. claude_unsup -> (unsupervised, claude)
    judge_cols = {col: (mode, j)
                  for mode in judge_modes
                  for j, col in zip(loading.JUDGE_RATERS, judge_columns(mode))}

    # (dataset, agent, prompt, trial) -> {(mode, judge): JudgeFile}. Built from
    # every requested mode at once, so a trial missing its unsupervised run
    # keeps its supervised row instead of vanishing.
    cells: dict[tuple, dict] = {}
    coverage: list[dict] = []
    inventory: dict[tuple, dict] = {}
    for r in runs:
        parsed = judges_mod.map_judge_file(
            r.json, r.dataset, ref=judges_mod.reference_stub(r.dataset))
        cells.setdefault((r.dataset, r.agent, r.prompt, r.trial), {})[
            (r.mode, r.judge)] = parsed
        n_ref = len(judges_mod.reference_stub(r.dataset))
        coverage.append({
            "dataset": r.dataset, "condition": r.condition, "agent": r.agent,
            "prompt": r.prompt, "trial": r.trial, "mode": r.mode,
            "judge": r.judge, "questions": n_ref,
            "mapped": len(parsed.ratings), "unmapped": len(parsed.unmapped),
            "judge_only": len(parsed.extra), "by_number": len(parsed.by_number),
            "unmapped_qids": ",".join(parsed.unmapped),
            "by_number_qids": ",".join(parsed.by_number),
        })
        inventory.setdefault((r.dataset, r.condition, r.trial), {
            "dataset": r.dataset, "condition": r.condition, "agent": r.agent,
            "prompt": r.prompt, "trial": r.trial,
            "path": str(r.trial_dir),
        })

    have = {ds for ds, _a, _p, _t in cells}
    order = [d for d in DATASET_ORDER if d in have]
    order += [d for d in sorted(have) if d not in DATASET_ORDER]

    rows: list[dict] = []
    for ds in order:
        kept, _dropped = question_rows(ds, exclude_titles)
        if not kept:
            continue
        ds_cells = sorted((k for k in cells if k[0] == ds),
                          key=lambda k: (_condition_rank(k[1], k[2]), k[3]))
        for base in kept:
            for key in ds_cells:
                _ds, agent, prompt, trial = key
                rec = {**base, "agent": agent, "prompt": prompt,
                       "condition": condition_key(agent, prompt), "trial": trial}
                for col, (mode, judge) in judge_cols.items():
                    parsed = cells[key].get((mode, judge))
                    v = parsed.ratings.get(base["qid"], {}) if parsed else {}
                    rec[col] = v.get("rating")
                    rec[f"{col}_code"] = v.get("code")
                rows.append(rec)

    tidy = pd.DataFrame(rows)
    cov = pd.DataFrame(coverage)
    _check_uniform_mapping(cov)
    present = tuple(a for a in CONDITION_ORDER if a in set(tidy.get("condition", [])))
    return ConditionRatings(tidy=tidy, coverage=cov,
                      inventory=pd.DataFrame(inventory.values()),
                      skipped=skipped, conditions=present,
                      raters=tuple(judge_cols))


def _condition_rank(agent: str, prompt: str) -> int:
    """Display position of a condition, unknown ones last."""
    key = condition_key(agent, prompt)
    return CONDITION_ORDER.index(key) if key in CONDITION_ORDER else len(CONDITION_ORDER)


def _check_uniform_mapping(coverage: pd.DataFrame) -> None:
    """Warn if a dataset's judge question list depends on the condition.

    It does not today: every judge file for a dataset maps the same number of
    questions, whichever harness or prompt produced the trial, because the
    question list is a property of the task. If that ever stops being true the
    conditions are no longer being asked the same thing, and comparing them silently
    stops meaning what it means here — so say so rather than average over it.
    """
    if coverage.empty:
        return
    spread = coverage.groupby("dataset")["mapped"].agg(["min", "max"])
    odd = spread[spread["min"] != spread["max"]]
    for ds, row in odd.iterrows():
        sub = coverage[coverage["dataset"] == ds]
        by_condition = sub.groupby("condition")["mapped"].unique().to_dict()
        warnings.warn(
            f"{ds}: judge files map different numbers of questions depending "
            f"on the condition ({int(row['min'])}-{int(row['max'])}): {by_condition}. "
            "Arm comparisons for this dataset are not like-for-like.",
            stacklevel=3)


# ---------- reading it ----------

# The five bands the summary figure splits its rows into: two categories whole,
# and Data Variables broken into what the question asks about. Missing-Data
# Handling (8 questions) and Thresholding (2, sosa2024 only) are too thin to
# read as their own column.
QUESTION_GROUPS = ("Data Loading", "Neural Data",
                   "Source variables", "Processing", "Alignment")


def question_group(df: pd.DataFrame) -> pd.Series:
    """Category, with Data Variables replaced by its sub-type.

    "Processing" as a column means the same thing whichever variable it was
    asked about, while "Data Variables" as one column would average a question
    about where a value came from together with one about how it was aligned.
    Neural Data keeps its own sub-types folded in — it is one variable, asked
    about five ways.
    """
    return df["category"].where(df["category"] != "Data Variables", df["subtype"])


def condition_scores(df: pd.DataFrame, rater: str = "combined", *,
                     level: float = 0.0, by: str = "dataset",
                     unit: str = "trial") -> pd.DataFrame:
    """Per (`by`, condition, `unit`): how much was rated at least `level`.

    `level=0` is "ok or better", the same cut `format_scatter` uses for the
    human ratings. Rows the rater left unrated are dropped from both numerator
    and denominator, so `frac_ok` is a share of what was actually judged.

    `by` is the column the figure splits on; `unit` is what one point is. The
    two combinations we use:

    * `by="dataset", unit="trial"` — a point is one run. Three per condition per
      dataset, and their spread is run-to-run variability.
    * `by="group", unit="dataset"` — a point is one dataset's questions in that
      band, its three trials pooled. Eight per condition per band, and their
      spread is between datasets.

    Do not pool datasets *by trial index*: trial 1 of allen2p and trial 1 of
    chen2024 are unrelated runs, so a "trial 1" point across datasets averages
    things that share only a label.
    """
    sub = df[df[rater].notna()]
    out = (sub.groupby([by, "condition", unit], dropna=False)[rater]
              .agg(n_questions="size", n_ok=lambda s: int((s >= level).sum()))
              .reset_index())
    out["frac_ok"] = out["n_ok"] / out["n_questions"]
    return out


def pooled_stat(scores: pd.DataFrame, *, stat: str = "se") -> pd.DataFrame:
    """Per condition: the mean of all its points, and how noisy that mean is.

    Every point counts as one sample, so the spread collapses both sources of
    variation at once — run to run within a dataset, and dataset to dataset:

    * `stat="se"` — `sd / sqrt(n)` over the points. How tightly the overall mean
      is pinned down given all the noise in the estimate.
    * `stat="sd"` — the plain sd of the points, i.e. how far one of them
      scatters rather than how well their mean is known.

    `n` is every point in the panel: 24 per condition for the per-dataset
    figures (8 datasets x 3 trials), 40 for the question bands (8 x 5). Treating
    them as independent understates the true uncertainty, since trials within a
    dataset are repeats of one task — read it as a floor on the noise.
    """
    if stat not in ("se", "sd"):
        raise ValueError(f"stat must be 'se' or 'sd', got {stat!r}")
    out = (scores.groupby("condition")["frac_ok"]
                 .agg(mean="mean", sd="std", n="size").reset_index())
    out["spread"] = out["sd"] / np.sqrt(out["n"]) if stat == "se" else out["sd"]
    out["label"] = out.apply(
        lambda r: f"{r['mean']:.2f} ± {r['spread']:.2f}", axis=1)
    return out.set_index("condition")


def condition_summary(scores: pd.DataFrame) -> pd.DataFrame:
    """Arm ranking as the mean of per-dataset means.

    Not a mean over rows: the datasets carry 20 to 39 questions each, so
    pooling rows would let sosa2024 and zhong2025 outvote lee2025 two to one.
    """
    per_ds = (scores.groupby(["condition", "dataset"])["frac_ok"].mean()
                    .reset_index())
    out = (per_ds.groupby("condition")["frac_ok"]
                 .agg(frac_ok="mean", sd="std", datasets="size")
                 .reset_index())
    out["arm_label"] = out["condition"].map(CONDITION_LABEL)
    return out.set_index("condition").reindex([a for a in CONDITION_ORDER
                                         if a in set(out["condition"])]).reset_index()


def prompt_pairs(df: pd.DataFrame, rater: str = "combined") -> pd.DataFrame:
    """Full vs minimal on the same question, for the agents that ran both.

    The **question** is the paired unit, not the trial: a trial is an
    independent run, so trial 1 of the full prompt has nothing to do with trial
    1 of the minimal one and pairing them would invent a correspondence. Each
    question is averaged over its three trials within a prompt first, and the
    two averages are what get compared.

    Returns per (dataset, agent): how many questions the full prompt won, lost
    and tied, and the mean difference in rating levels.
    """
    agents = sorted({a for a, p in experiments.CONDITIONS if p == "full"}
                    & {a for a, p in experiments.CONDITIONS if p == "minimal"})
    sub = df[df["agent"].isin(agents)]
    wide = sub.pivot_table(index=["dataset", "agent", "qid"],
                           columns="prompt", values=rater, aggfunc="mean")
    wide = wide.dropna(subset=["full", "minimal"])
    wide["diff"] = wide["full"] - wide["minimal"]
    g = wide.reset_index().groupby(["dataset", "agent"])
    out = g.agg(questions=("diff", "size"),
                full_better=("diff", lambda s: int((s > 0).sum())),
                minimal_better=("diff", lambda s: int((s < 0).sum())),
                tied=("diff", lambda s: int((s == 0).sum())),
                mean_diff=("diff", "mean")).reset_index()
    return out


def pair_table(scores: pd.DataFrame, conditions: tuple[str, str]) -> pd.DataFrame:
    """Two conditions side by side, per dataset, with the gap between them.

    The companion to a two-condition `condition_scatter`: the figure shows the trial
    spread, this says which way each dataset went and by how much. The last row
    is the mean over datasets, which is what the conditions should be ranked on —
    each dataset counts once regardless of how many questions it carries.
    """
    a, b = conditions
    wide = (scores[scores.condition.isin(conditions)]
            .pivot_table(index="dataset", columns="condition", values="frac_ok",
                         aggfunc="mean"))
    order = [d for d in DATASET_ORDER if d in wide.index]
    wide = wide.reindex(order)[list(conditions)]      # given order, not alphabetical
    wide["gap"] = wide[a] - wide[b]
    wide.loc["mean"] = wide.mean()
    labels = condition_labels(conditions)
    return wide.rename(columns={a: labels[a], b: labels[b],
                                "gap": f"{labels[a]} − {labels[b]}"})


# ---------- figures ----------

def condition_labels(conditions) -> dict:
    """Labels for `conditions`, carrying only the half that varies.

    Comparing harnesses that all ran the full prompt, "(maximal)" on every entry
    is a word saying nothing; comparing one agent's two prompts, the agent name
    is the repeated half and the title already carries it. Whichever of the two
    is constant gets dropped, and both are kept when both vary.
    """
    agents = {c.split("/")[0] for c in conditions}
    prompts = {c.split("/")[1] for c in conditions}
    if len(prompts) == 1:
        return {c: experiments.AGENT_LABEL.get(c.split("/")[0], c) for c in conditions}
    if len(agents) == 1:
        return {c: experiments.PROMPT_LABEL[c.split("/")[1]] for c in conditions}
    return {c: CONDITION_LABEL[c] for c in conditions}


def condition_scatter(scores: pd.DataFrame, *,
                      conditions: tuple[str, ...] | None = None,
                      x: str = "dataset", order: list | None = None,
                      title: str | None = None, labels: dict | None = None,
                      xlabels=None, box: bool = True, box_title: str = "Overall",
                      box_stat: str | None = "se", ylim=(0, 1.02), figsize=None):
    """One `condition_scores` point per replicate, per column, plus a box panel.

    The condition version of `plots.format_scatter`: same question ("how much of
    the conversion did the rater accept?"), one point per replicate so the
    spread stays visible, and a bar at each condition's mean within the column.
    A dashed line joins those means so the direction of the comparison is
    readable at a glance.

    Points sit at fixed offsets rather than jittered — with a handful of them a
    random x carries no information and makes two columns look different when
    only the seed was.

    `box` adds a narrow right-hand panel: every point for each condition in one
    box, which is the pooled comparison the left panel is a breakdown of — every
    column at once, so it holds more points than any one column shows. It shares
    the y axis, so the two read together.

    `box_stat` writes `mean ± spread` under each box — see `pooled_stat`.
    `"se"` is the noise in the mean over every point in the panel, `"sd"` is how
    far one point scatters, `None` writes nothing.

    `x` is the column the left panel splits on, and must be whatever
    `condition_scores(by=...)` grouped by — `"dataset"` (points are trials) or
    `"group"` for the question bands (points are datasets).

    `ylim` defaults to the full 0-1 the fraction can take. Cropping it spends
    the height on the range the points actually occupy, at the cost of hiding
    anything below the floor — matplotlib clips silently, so check the minimum
    first.

    Returns `(fig, (ax, ax_box))`; `ax_box` is None when `box=False`.
    """
    conditions = conditions or tuple(c for c in CONDITION_ORDER
                                     if c in set(scores["condition"]))
    labels = labels or condition_labels(conditions)
    if order is None:
        order = ([d for d in DATASET_ORDER if d in set(scores[x])]
                 if x == "dataset" else list(dict.fromkeys(scores[x])))
    else:
        order = [c for c in order if c in set(scores[x])]
    if xlabels is None:
        xlabels = display_name if x == "dataset" else (lambda s: s)

    if figsize is None:
        figsize = (10.5 if box else 9, 4)
    if box:
        fig, (ax, ax_box) = plt.subplots(
            1, 2, figsize=figsize, sharey=True,
            gridspec_kw={"width_ratios": [6, 1.15], "wspace": 0.04})
    else:
        fig, ax = plt.subplots(figsize=figsize)
        ax_box = None

    # Each condition gets a slot within the column, and its points sit evenly
    # inside that slot. GAP is the distance between slot centers: wide enough
    # that the two groups being compared read as separate, narrow enough that
    # they still read as one column.
    GAP, STEP = 0.34, 0.05
    span = min(GAP * (len(conditions) - 1), 0.78)
    offsets = (np.linspace(-span / 2, span / 2, len(conditions))
               if len(conditions) > 1 else np.array([0.0]))

    def dot_span(n: int) -> float:
        """Width the n points spread over: STEP apart, capped short of the slot."""
        return min(STEP * (n - 1), 0.55 * GAP)

    for i, ds in enumerate(order):
        if i % 2:
            ax.axvspan(i - 0.5, i + 0.5, color="0.95", zorder=0, lw=0)

        centers = []
        for condition, dx in zip(conditions, offsets):
            vals = scores[(scores[x] == ds)
                          & (scores.condition == condition)]["frac_ok"].to_numpy()
            if not len(vals):
                centers.append(None)
                continue
            half = dot_span(len(vals)) / 2
            xs = i + dx + (np.linspace(-half, half, len(vals))
                           if len(vals) > 1 else np.array([0.0]))
            ax.scatter(xs, vals, s=26 if len(vals) <= 4 else 18, alpha=0.85,
                       color=CONDITION_COLOR[condition],
                       edgecolors="white", linewidths=0.5, zorder=3,
                       label=labels[condition] if i == 0 else None)
            ax.plot([i + dx - half - 0.02, i + dx + half + 0.02],
                    [vals.mean()] * 2, color=CONDITION_COLOR[condition],
                    lw=2.2, zorder=4)
            centers.append((i + dx, vals.mean()))

        # Join consecutive means: with two conditions this is the one line that
        # says which way the dataset went.
        drawn = [c for c in centers if c is not None]
        if len(drawn) > 1:
            ax.plot(*zip(*drawn), color="0.45", lw=0.8, ls="--", zorder=2)

    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([xlabels(d) for d in order], rotation=30, ha="right")
    ax.set_ylabel("questions rated ≥ ok")
    ax.set_ylim(*ylim)
    ax.set_xlim(-0.5, len(order) - 0.5)

    if ax_box is not None:
        data = [scores[scores.condition == c]["frac_ok"].to_numpy()
                for c in conditions]
        bp = ax_box.boxplot(data, widths=0.6, patch_artist=True,
                            medianprops={"color": "0.2", "lw": 1.4},
                            flierprops={"marker": "o", "ms": 3, "mfc": "0.5",
                                        "mec": "none"})
        for patch, condition in zip(bp["boxes"], conditions):
            patch.set(facecolor=CONDITION_COLOR[condition], alpha=0.45,
                      edgecolor=CONDITION_COLOR[condition], lw=1.2)
        for key in ("whiskers", "caps"):
            for line in bp[key]:
                line.set(color="0.45", lw=1.0)
        if box_stat:
            stats = pooled_stat(scores[scores.condition.isin(conditions)],
                                stat=box_stat)
            for pos, condition in enumerate(conditions, start=1):
                # Inside the axes at the foot of the box, on a white patch: a
                # whisker or an outlier can reach this low.
                foot = ylim[0] + 0.015 * (ylim[1] - ylim[0])
                ax_box.text(pos, foot, stats.loc[condition, "label"],
                            ha="center", va="bottom", fontsize=6.5, zorder=5,
                            bbox={"facecolor": "white", "edgecolor": "none",
                                  "pad": 1.0, "alpha": 0.85})
        ax_box.set_xticks(range(1, len(conditions) + 1))
        ax_box.set_xticklabels([labels[c] for c in conditions],
                               rotation=30, ha="right", fontsize=8)
        ax_box.set_title(box_title, fontsize=9, pad=4)
        # The y axis is shared with the panel on the left; a second copy of its
        # spine and ticks would read as a frame around the boxes.
        ax_box.tick_params(axis="y", left=False)
        ax_box.spines["left"].set_visible(False)

    # Legend above the axes, title above the legend: with six conditions the
    # legend needs two rows, and a title placed the usual way lands underneath.
    ncol = min(len(conditions), 3)
    rows = -(-len(conditions) // ncol)
    ax.legend(frameon=False, fontsize=8, ncol=ncol,
              loc="lower left", bbox_to_anchor=(0, 1.0))
    if title:
        ax.set_title(title, pad=14 + 13 * rows, loc="left")
    return fig, (ax, ax_box)


# ---------- validation ----------

VALIDATE_KEYS = ["dataset", "qid", "agent", "trial"]
VALIDATE_COLS = ["claude", "claude_code", "codex", "codex_code"]


def validate_against_load_ratings(*, judge_modes: tuple[str, ...] = (DEFAULT_MODE,),
                                  verbose: bool = True) -> pd.DataFrame:
    """Check this loader against the mirrored-file loader on their shared conditions.

    `load_ratings` reads `eval/<dataset>/judge_supervised/`; this module reads
    the experiment tree those files were copied from. Restricted to the two
    evaluated agents at the full prompt they describe the same trials, so every
    judge cell must agree — including which cells are empty.

    Returns a per-dataset table; raises AssertionError on any difference.
    """
    old = loading.load_ratings(judge_modes=judge_modes)
    new = load_condition_ratings(judge_modes=judge_modes)

    cols = [c for c in VALIDATE_COLS if c in old.tidy.columns]
    o = (old.tidy[VALIDATE_KEYS + cols]
            .sort_values(VALIDATE_KEYS).reset_index(drop=True))
    mine = new.tidy[(new.tidy["prompt"] == "full")
                    & new.tidy["agent"].isin(sorted(experiments.EVAL_AGENTS))]
    n = (mine[VALIDATE_KEYS + cols]
         .sort_values(VALIDATE_KEYS).reset_index(drop=True))

    ok = set(map(tuple, o[VALIDATE_KEYS].to_numpy()))
    on = set(map(tuple, n[VALIDATE_KEYS].to_numpy()))
    if ok != on:
        raise AssertionError(
            f"key sets differ: {len(ok - on)} only in load_ratings "
            f"(e.g. {sorted(ok - on)[:3]}), {len(on - ok)} only here "
            f"(e.g. {sorted(on - ok)[:3]})")
    assert len(o) == len(n), f"row counts differ: {len(o)} vs {len(n)}"
    assert o[cols].isna().equals(n[cols].isna()), "NaN patterns differ"
    pd.testing.assert_frame_equal(o, n, check_exact=True)

    per_ds = []
    for ds, sub in o.groupby("dataset"):
        mine_ds = n[n["dataset"] == ds]
        per_ds.append({"dataset": ds, "rows": len(sub),
                       **{f"mismatch_{c}": int((sub[c].to_numpy() !=
                                                mine_ds[c].to_numpy()).sum()
                                               - (sub[c].isna().to_numpy()
                                                  & mine_ds[c].isna().to_numpy()).sum())
                          for c in cols}})
    out = pd.DataFrame(per_ds)
    if verbose:
        print(f"PASS — {len(o)} rows x {len(cols)} judge columns identical "
              f"across {o['dataset'].nunique()} datasets: {', '.join(cols)}")
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        description="Check the condition loader against the mirrored judge files.")
    ap.add_argument("--mode", choices=["supervised", "unsupervised"],
                    default=DEFAULT_MODE)
    args = ap.parse_args(argv)
    out = validate_against_load_ratings(judge_modes=(args.mode,))
    print(out.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
