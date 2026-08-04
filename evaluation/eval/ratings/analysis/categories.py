"""What *kind* of disagreement each question showed, tallied from the reports.

Every `eval/<dataset>/report.md` carries a **Difference categories** column that
the evaluator fills in by hand, tagging each question with entries like
``VARNAME=6`` or ``MISC=1`` — the number being how many of the six trials showed
that kind of difference. It is the one part of the evaluation that is a
*judgement about the mistake* rather than a rating of it, and the only place the
taxonomy below exists.

Only the ``LABEL=N`` form counts. A bare ``MISC`` or ``SEMANTIC`` with no number
is an informal note and is skipped deliberately.

    FILTER    which data to keep — trials, neurons, sessions, and on what cutoff
    TIME_RES  temporal representation — bin width, sampling rate, alignment
    PROCESS   the derivation itself was wrong or sub-optimal
    ASSUME    a belief about what the data means, never checked against it
    VARNAME   ASSUME's special case: the variable's *name* was taken at face value
    MISC      everything else, used sparingly
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from ..paths import EVAL_DIR
from .loading import DATASET_ORDER

# LABEL=N, inside backticks or not. The "=<int>" is what separates a real tally
# from a bare label.
TAG_RE = re.compile(r"([A-Z_][A-Z0-9_]*)=(\d+)")

# Spellings that predate the settled names; both mean TIME_RES.
TAG_ALIASES = {"RESAMP": "TIME_RES", "TIMERES": "TIME_RES"}

# Display order, roughly most to least common.
CATEGORY_ORDER = ["FILTER", "TIME_RES", "PROCESS", "ASSUME", "VARNAME", "MISC"]


def _category_cells(report_path: Path):
    """Yield the raw Difference-categories cell of every question row."""
    in_table = False
    header_cols = None
    for line in report_path.read_text().splitlines():
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header_cols is None or not in_table:
            if any("Difference" in c for c in cells):
                header_cols = cells
                in_table = True
            continue
        if all(set(c) <= set("-: ") for c in cells):      # the |---|---| rule
            continue
        try:
            idx = header_cols.index(next(c for c in header_cols if "Difference" in c))
        except (ValueError, StopIteration):
            continue
        if idx < len(cells):
            yield cells[idx]


def difference_categories(datasets: list[str] | None = None,
                          eval_dir: Path = EVAL_DIR) -> pd.DataFrame:
    """Tag counts per category per dataset, with TOTAL row and column.

    Rows are categories, sorted by their total; columns are datasets in
    `DATASET_ORDER`. A dataset whose report has no tags contributes zeros
    rather than disappearing.
    """
    datasets = datasets or [ds for ds in DATASET_ORDER
                            if (eval_dir / ds / "report.md").exists()]

    per_dataset: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ds in datasets:
        for cell in _category_cells(eval_dir / ds / "report.md"):
            for label, n in TAG_RE.findall(cell):
                per_dataset[ds][TAG_ALIASES.get(label, label)] += int(n)

    table = (pd.DataFrame(per_dataset)
             .reindex(columns=datasets)
             .fillna(0).astype(int))
    table["TOTAL"] = table.sum(axis=1)
    table = table.sort_values("TOTAL", ascending=False)
    table.loc["TOTAL"] = table.sum(axis=0)
    return table
