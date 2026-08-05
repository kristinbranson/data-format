"""Reading the ratings back: loading, agreement, accuracy, figures.

The package's own analysis internals. Everything here is re-exported by
`ratings`, which is what a notebook should import:

    from ratings import load_ratings, summary_table, agreement, binary

    r = load_ratings()                       # every rater, all 8 datasets
    summary_table(r, rater="LZ")             # the per-question rating grid
    agreement.pairwise(r.correctness)        # how much two raters agree
    binary.table(r.tidy, "LZ", ("KB", "claude", "codex"))

    loading    dossiers + judge JSON -> one tidy frame, one nested dict
    judges     the judge runs, mapped onto our question numbering by content
    agreement  pairwise correlation and chance-corrected agreement
    binary     five levels collapsed to caught-it / missed-it
    categories what kind of mistake each question showed, from report.md
    render     the multi-dataset rating grid
    plots      the other figures (by format, confusion, levels, variability)
    display    table presentation: rater labels, LaTeX and markdown

`rater` always means who gave the rating (LZ / KB / claude / codex, plus the
`_unsup` judge runs); `agent` always means the system under evaluation
(claude-code / codex).
"""

from . import (agreement, binary, categories, display, judges, loading,
               plots, render)
from .binary import collapse, confusion_counts, metrics
from .categories import difference_categories
from .loading import (ALL_RATERS, DATASET_FORMAT, DATASET_ORDER,
                      EXCLUDED_TITLE_PATTERNS, HUMAN_RATERS, JUDGE_MODES,
                      JUDGE_RATERS, PERFORMANCE_CATEGORY, RATERS, UNSUP_RATERS,
                      Ratings, add_combined, add_null, correctness_only,
                      coverage_summary,
                      judge_columns, load_ratings, uniform_variables,
                      unanswered_by_judges)
from .render import summary_table

__all__ = [
    "load_ratings", "Ratings", "coverage_summary", "unanswered_by_judges",
    "correctness_only", "uniform_variables", "add_null", "add_combined",
    "judge_columns",
    "EXCLUDED_TITLE_PATTERNS", "PERFORMANCE_CATEGORY",
    "summary_table", "agreement", "binary", "categories", "display", "judges",
    "loading", "plots", "render", "difference_categories",
    "collapse", "confusion_counts", "metrics",
    "RATERS", "ALL_RATERS", "HUMAN_RATERS", "JUDGE_RATERS", "UNSUP_RATERS",
    "JUDGE_MODES", "DATASET_ORDER", "DATASET_FORMAT",
]
