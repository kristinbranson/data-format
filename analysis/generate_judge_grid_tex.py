"""Generate a LaTeX visual grid of supervised-judge ratings.

Writes analysis/judge_grid.tex (one file, one table per agent).
Each cell is a TikZ grid of (n_questions x (n_trials * n_judges)) colored
squares. Within each trial, the judges appear adjacent in a fixed order
(claude, codex), with a small extra gap between trials.

Row categories are grouped under italic section headers (Data loading,
Neural data, Decoder inputs, Outputs), with standalone rows Bad data
handling and Code efficiency.

Compile with: pdflatex judge_grid.tex
"""

import json
import os
import re
from collections import defaultdict

from summarize_judges import (
    HARBOR_ROOT,
    MODES,
    classify,
    is_bad_trial,
    is_duplicate,
    load_judge,
)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Agent groups: raw dir names → display label. Trials are pooled within a group.
AGENT_GROUPS = [
    ("Claude", ("claude", "claude-code")),
    ("Codex", ("codex",)),
]

# Judges appear in this order within each trial (left-to-right).
JUDGES = ("claude", "codex")

# Category grouping. None => standalone row. Leaves whose name is a key in
# METRIC_ROWS are rendered by tikz_cell_metric from metrics.json instead of
# from judge ratings.
CATEGORY_GROUPS = [
    ("Data loading", [
        "Overall",
        "Split into subjects",
        "Split into sessions",
        "Split into trials",
        "Trial filtering",
    ]),
    ("Neural data", [
        "Source variables",
        "Processing",
        "Filtering",
        "Alignment",
        "Temporal resolution",
    ]),
    ("Decoder inputs", [
        "Source variables",
        "Processing",
        "Thresholding",
        "Alignment",
    ]),
    ("Outputs", [
        "Source variables",
        "Processing",
        "Thresholding",
        "Alignment",
    ]),
    (None, ["Bad data handling"]),
    (None, ["Code efficiency"]),
    ("Data counts", [
        "Subjects",
        "Sessions",
        "Trials",
        "Neurons",
        "Time length",
    ]),
    (None, ["Decoder accuracy"]),
]

# sub-name -> (kind, metrics.json key or None). kind="simple" -> one ratio
# scalar per trial; kind="acc" -> per-output dict (validation_balanced_accuracy_ratio).
METRIC_ROWS = {
    "Subjects":    ("simple", "nsubjects_ratio"),
    "Sessions":    ("simple", "nsessions_ratio"),
    "Trials":      ("simple", "ntrials_total_ratio"),
    "Neurons":     ("simple", "nneurons_total_ratio"),
    "Time length": ("simple", "T_median_ratio"),
    "Decoder accuracy": ("acc", None),
}


def full_category_name(group: str | None, sub: str) -> str:
    """Match the names used by summarize_supervised_judges.classify()."""
    return f"{group} - {sub}" if group else sub


# LaTeX color name keyed by decision_correctness value.
RATING_COLORS = {
    "BETTER": "ratingBetter",
    "MATCH": "ratingMatch",
    "OK": "ratingOk",
    "CONCERNING": "ratingConcerning",
    "INCORRECT": "ratingIncorrect",
}
MISSING_COLOR = "ratingMissing"


# Geometry (points).
SQUARE = 6.0
GAP = 0.6        # gap between same-trial judge squares
TRIAL_GAP = 1.8  # extra gap between trials
ROW_PAD = 3.0    # vertical padding above & below each tikz grid, so adjacent
                 # rows don't touch even when the grid fills the row height


def qid_sort_key(qid: str):
    m = re.match(r"(\d+)(?:-(.*))?", qid)
    if m:
        return (int(m.group(1)), m.group(2) or "")
    return (10**6, qid)


def iter_trials_for(task: str, agent_dirs: tuple[str, ...]):
    task_dir = os.path.join(HARBOR_ROOT, task)
    if not os.path.isdir(task_dir):
        return
    for agent in agent_dirs:
        agent_dir = os.path.join(task_dir, agent)
        if not os.path.isdir(agent_dir):
            continue
        for trial_name in sorted(os.listdir(agent_dir)):
            if is_bad_trial(trial_name):
                continue
            trial_dir = os.path.join(agent_dir, trial_name)
            if os.path.isdir(trial_dir):
                yield agent, trial_name, trial_dir


def gather(task: str, agent_dirs: tuple[str, ...], judges: tuple[str, ...], judge_subdir: str):
    """Return (trial_ids, {judge: {cat: {qid: {tid: rating}}}}, metrics)
    where metrics = {tid: {simple_metric_name: value or None, 'acc': dict}}
    plus 'ref_vars' the sorted union of decoder-accuracy reference variables."""
    trial_ids = []
    per_judge = {j: defaultdict(lambda: defaultdict(dict)) for j in judges}
    per_trial_metrics = {}
    ref_vars = set()
    for agent, trial_name, trial_dir in iter_trials_for(task, agent_dirs):
        tid = f"{agent}/{trial_name}"
        any_found = False
        for j in judges:
            data = load_judge(trial_dir, judge_subdir, j)
            if data is None:
                continue
            any_found = True
            for qid, q in data.items():
                if is_duplicate(task, qid):
                    continue
                cat = classify(qid, q.get("question", ""))
                if cat is None:
                    continue
                per_judge[j][cat][qid][tid] = q.get("decision_correctness", "")
        if any_found:
            trial_ids.append(tid)

        mpath = os.path.join(trial_dir, "verifier", "metrics.json")
        if os.path.exists(mpath):
            with open(mpath) as f:
                m = json.load(f)
            per_trial_metrics[tid] = {
                "nsubjects_ratio": m.get("nsubjects_ratio"),
                "nsessions_ratio": m.get("nsessions_ratio"),
                "ntrials_total_ratio": m.get("ntrials_total_ratio"),
                "nneurons_total_ratio": m.get("nneurons_total_ratio"),
                "T_median_ratio": m.get("T_median_ratio"),
                "acc": m.get("validation_balanced_accuracy_ratio") or {},
            }
            if isinstance(per_trial_metrics[tid]["acc"], dict):
                ref_vars.update(per_trial_metrics[tid]["acc"].keys())
    metrics = {"per_trial": per_trial_metrics, "ref_vars": sorted(ref_vars)}
    return trial_ids, per_judge, metrics


def ratio_color(r) -> str:
    if r is None:
        return MISSING_COLOR
    if r > 1.05:
        return RATING_COLORS["BETTER"]
    if abs(r - 1.0) < 0.002:
        return RATING_COLORS["MATCH"]
    if 0.95 <= r <= 1.05:
        return RATING_COLORS["OK"]
    if 0.80 <= r <= 1.20:
        return RATING_COLORS["CONCERNING"]
    return RATING_COLORS["INCORRECT"]


def _trial_block_width(n_judges: int) -> float:
    return n_judges * SQUARE + (n_judges - 1) * GAP


def _tikz_from_rows(rows: list[list[tuple[float, float, str]]]) -> str:
    """Render a TikZ grid from per-row spans. Each row is a list of
    (x_start, x_end, color) tuples; each span becomes a filled rectangle of
    height SQUARE. Returns '--' placeholder when there is nothing to draw.

    The picture is wrapped in \\vcenter{} so it vertically centers inside its
    tabular cell, matching the m{} column used for the label column. A
    \\useasboundingbox extends the picture's bounding box by ROW_PAD above
    and below the drawn grid — this is what actually enforces the minimum
    vertical gap between adjacent tall rows (\\extrarowheight has no effect
    when the row is already taller than the strut)."""
    if not rows or not any(rows):
        return r"{\footnotesize--}"
    n_rows = len(rows)
    grid_h = (n_rows - 1) * (SQUARE + GAP) + SQUARE
    max_x = max(x_end for spans in rows for _, x_end, _ in spans)
    parts = [r"$\vcenter{\hbox{\begin{tikzpicture}[x=1pt,y=1pt,inner sep=0pt,outer sep=0pt]"]
    parts.append(
        f"\\useasboundingbox (0,{-ROW_PAD:.2f}) rectangle "
        f"({max_x:.2f},{grid_h + ROW_PAD:.2f});"
    )
    for r, spans in enumerate(rows):
        y_top = (n_rows - 1 - r) * (SQUARE + GAP)
        for x_start, x_end, color in spans:
            parts.append(
                f"\\fill[{color}] ({x_start:.2f},{y_top:.2f}) rectangle "
                f"({x_end:.2f},{y_top + SQUARE:.2f});"
            )
    parts.append(r"\end{tikzpicture}}}$")
    return "".join(parts)


def tikz_cell(per_judge, cat: str, trial_ids: list[str], judges: tuple[str, ...]) -> str:
    """One mini-grid per (category, task, agent-group): rows=questions,
    cols=trials × judges. Two adjacent squares per trial (claude, codex)."""
    qid_set = set()
    for j in judges:
        qid_set |= set(per_judge[j].get(cat, {}).keys())
    qids = sorted(qid_set, key=qid_sort_key)
    if not qids or not trial_ids:
        return r"{\footnotesize--}"

    block_w = _trial_block_width(len(judges))
    rows = []
    for qid in qids:
        spans = []
        for t_idx, tid in enumerate(trial_ids):
            base = t_idx * (block_w + TRIAL_GAP)
            for j_idx, j in enumerate(judges):
                rating = per_judge[j].get(cat, {}).get(qid, {}).get(tid)
                color = RATING_COLORS.get(rating, MISSING_COLOR)
                x = base + j_idx * (SQUARE + GAP)
                spans.append((x, x + SQUARE, color))
        rows.append(spans)
    return _tikz_from_rows(rows)


def tikz_cell_metric(
    sub: str, metrics: dict, trial_ids: list[str], judges: tuple[str, ...]
) -> str:
    """Metric cell: one wide square per trial (no judge axis), spanning the
    full trial block so columns line up with the rating cells above. 'simple'
    rows draw one grid row; 'acc' rows draw one sub-row per reference output."""
    kind, key = METRIC_ROWS[sub]
    per_trial = metrics["per_trial"]
    if not trial_ids:
        return r"{\footnotesize--}"

    if kind == "simple":
        color_rows = [[ratio_color(per_trial.get(tid, {}).get(key)) for tid in trial_ids]]
    else:  # "acc"
        ref_vars = metrics["ref_vars"]
        if not ref_vars:
            return r"{\footnotesize--}"
        color_rows = [
            [ratio_color((per_trial.get(tid, {}).get("acc") or {}).get(v))
             for tid in trial_ids]
            for v in ref_vars
        ]

    block_w = _trial_block_width(len(judges))
    rows = []
    for colors in color_rows:
        spans = []
        for t_idx, color in enumerate(colors):
            x = t_idx * (block_w + TRIAL_GAP)
            spans.append((x, x + block_w, color))
        rows.append(spans)
    return _tikz_from_rows(rows)


def _escape(s: str) -> str:
    return s.replace("&", r"\&").replace("_", r"\_")


def render_table(agent_label: str, agent_dirs: tuple[str, ...], mode: str) -> str:
    cfg = MODES[mode]
    tasks = cfg["tasks"]
    per_task = {
        task: gather(task, agent_dirs, JUDGES, cfg["judge_subdir"][task])
        for task in tasks
    }

    # Category column: narrow ragged-right paragraph column. Short labels
    # ("Overall", "Time length") sit on one line; medium ones ("Split into
    # subjects") wrap to two lines; group headers use their own multicolumn row
    # so the width doesn't need to accommodate them.
    col_spec = (
        r"@{}>{\raggedright\arraybackslash}m{1.5in}@{\hspace{6pt}}"
        + "c" * len(tasks) + "@{}"
    )
    n_cols = 1 + len(tasks)

    out = [rf"Agent: {agent_label}"]
    out.append(rf"\begin{{longtable}}{{{col_spec}}}")
    out.append(r"\toprule")

    header = [r"\textbf{Category}"]
    for task in tasks:
        tids, _, _ = per_task[task]
        header.append(
            r"\begin{tabular}{@{}c@{}}\small\textbf{" + task + r"}\end{tabular}"
        )
    out.append(" & ".join(header) + r" \\")
    out.append(r"\midrule")
    out.append(r"\endhead")

    show_metrics = cfg.get("show_metrics", True)
    # Suppress whole groups that consist solely of metric rows (Data counts,
    # Decoder accuracy) when the mode doesn't want metrics.
    visible_groups = []
    for group, subs in CATEGORY_GROUPS:
        if not show_metrics:
            subs = [s for s in subs if s not in METRIC_ROWS]
        if subs:
            visible_groups.append((group, subs))

    first_group = True
    row_idx = 0  # counts only data rows, used to alternate shading
    for group, subs in visible_groups:
        if not first_group:
            out.append(r"\midrule")
        first_group = False
        if group is not None:
            out.append(rf"\multicolumn{{{n_cols}}}{{@{{}}l}}{{\textit{{{group}}}}} \\")
        for sub in subs:
            cat = full_category_name(group, sub)
            label = rf"\quad {_escape(sub)}" if group is not None else _escape(sub)
            row = [label]
            for task in tasks:
                trial_ids, per_judge, metrics = per_task[task]
                if sub in METRIC_ROWS:
                    row.append(tikz_cell_metric(sub, metrics, trial_ids, JUDGES))
                else:
                    row.append(tikz_cell(per_judge, cat, trial_ids, JUDGES))
            shade = r"\rowcolor{rowGray}" if row_idx % 2 == 0 else ""
            out.append(shade + " & ".join(row) + r" \\")
            row_idx += 1

    out.append(r"\bottomrule")
    out.append(r"\end{longtable}")
    return "\n".join(out)


PREAMBLE = r"""\documentclass[9pt]{article}
\PassOptionsToPackage{table}{xcolor}
\usepackage[margin=0.5in]{geometry}
\usepackage{tikz}
\usepackage{xcolor}
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}

\definecolor{ratingBetter}{RGB}{30,120,230}
\definecolor{ratingMatch}{RGB}{0,110,40}
\definecolor{ratingOk}{RGB}{140,210,130}
\definecolor{ratingConcerning}{RGB}{245,210,60}
\definecolor{ratingIncorrect}{RGB}{210,40,50}
\definecolor{ratingMissing}{RGB}{220,220,220}
\definecolor{rowGray}{RGB}{238,238,238}

\newcommand{\ratingSwatch}[1]{%
  \begin{tikzpicture}[x=1pt,y=1pt]%
    \fill[#1] (0,0) rectangle (8,8);%
  \end{tikzpicture}%
}

\renewcommand{\arraystretch}{1.0}
\setlength{\tabcolsep}{1pt}
% Adds fixed vertical breathing room at the top of every tabular row. Unlike
% \arraystretch (which only enlarges short rows via the strut), this applies
% uniformly — including to rows whose height is driven by a tall tikz grid,
% preventing adjacent grids from butting up against each other.
\setlength{\extrarowheight}{3pt}

\begin{document}
"""

LEGEND = r"""
\noindent\textbf{Legend:}\quad
\ratingSwatch{ratingBetter}~BETTER \quad
\ratingSwatch{ratingMatch}~MATCH \quad
\ratingSwatch{ratingOk}~OK \quad
\ratingSwatch{ratingConcerning}~CONCERNING \quad
\ratingSwatch{ratingIncorrect}~INCORRECT \quad
\ratingSwatch{ratingMissing}~(missing)

\noindent\textbf{Cell layout:} rows = questions in category (natural qid order); columns = trials,
each trial rendered as two adjacent squares: \emph{left}=claude judge, \emph{right}=codex judge.
Extra gap separates trials.

\noindent\textbf{Metric rows (Data counts, Decoder accuracy):} coloured by the
\emph{submitted/reference ratio} $r$: $r\approx 1$~$\to$~MATCH, $|r-1|\leq 0.05$~$\to$~OK,
$|r-1|\leq 0.20$~$\to$~CONCERNING, otherwise INCORRECT, $r > 1.05$~$\to$~BETTER
(above reference; mostly meaningful for decoder accuracy). Each trial is a single
wide square (no judge axis), column-aligned with the trial blocks above.
\vspace{6pt}
"""

POSTAMBLE = r"""
\end{document}
"""


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=list(MODES), default="supervised",
                    help="which judge output to render (default: supervised)")
    args = ap.parse_args()
    mode = args.mode

    title = f"{mode.capitalize()}-judge ratings"
    parts = [PREAMBLE, rf"\section*{{{title}}}", LEGEND, r"\newpage"]
    for i, (label, dirs) in enumerate(AGENT_GROUPS):
        if i > 0:
            parts.append(r"\newpage")
        parts.append(render_table(label, dirs, mode))
    parts.append(POSTAMBLE)
    out = os.path.join(OUT_DIR, f"judge_grid_{mode}.tex")
    with open(out, "w") as f:
        f.write("\n".join(parts))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
