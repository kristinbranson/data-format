"""Analysis of the evaluation ratings.

Four raters rate the same questions — two humans (LZ, KB) and two LLM judges
(Claude, Codex) — and this package loads them into one table and analyses them:

    from analysis import load_ratings, agreement, binary, summary_table

    r = load_ratings()                       # all 8 datasets, supervised judges
    summary_table(r, rater="LZ")             # the per-question rating grid
    agreement.pairwise(r.tidy)               # how much the raters agree
    binary.table(r.tidy, "LZ", ("KB", "claude", "codex"))

`rater` always means who gave the rating (LZ / KB / claude / codex); `agent`
always means the system under evaluation (claude-code / codex).
"""

from . import agreement, binary, display, judges, loading, render
from .binary import collapse, confusion_counts, metrics
from .loading import (ALL_RATERS, DATASET_ORDER, EXCLUDED_TITLE_PATTERNS,
                      HUMAN_RATERS, JUDGE_MODES, JUDGE_RATERS,
                      PERFORMANCE_CATEGORY, RATERS, UNSUP_RATERS, Ratings,
                      add_null, correctness_only, coverage_summary,
                      judge_columns, load_ratings, uniform_variables,
                      unanswered_by_judges)
from .render import summary_table

__all__ = [
    "load_ratings", "Ratings", "coverage_summary", "unanswered_by_judges",
    "correctness_only", "uniform_variables", "add_null", "judge_columns",
    "EXCLUDED_TITLE_PATTERNS", "PERFORMANCE_CATEGORY",
    "summary_table", "agreement", "binary", "display", "judges", "loading",
    "render",
    "collapse", "confusion_counts", "metrics",
    "RATERS", "ALL_RATERS", "HUMAN_RATERS", "JUDGE_RATERS", "UNSUP_RATERS",
    "JUDGE_MODES", "DATASET_ORDER",
]
