"""Human and LLM-judge ratings of the agent-produced conversion code.

Two things live here: the workflow that produces ratings (an evaluator rating
one question at a time, the judge results imported from an experiment run, the
tables those get merged into) and the analysis that reads them back.

**Analysis** — what the notebook uses:

    from ratings import load_ratings, summary_table, agreement, binary, display

    r = load_ratings()                    # every rater, all 8 datasets
    summary_table(r, rater="LZ")          # the per-question rating grid
    agreement.pairwise(r.correctness)     # how much two raters agree
    binary.table(r.tidy, "LZ", ("KB", "claude", "codex"))

`rater` always means who gave the rating — the humans LZ / KB, and the judges
`claude` / `codex` (which saw the reference solution) and `claude_unsup` /
`codex_unsup` (which did not). `agent` always means the system being evaluated,
claude-code or codex.

**Workflow** — normally driven from the command line (`python3 -m ratings`), but
the modules are importable for scripting:

    from ratings import raters, report, compare
    raters.collect_ratings("allen2p", ["LZ", "KB"])   # dossiers are the truth

Importing this package reads nothing from disk and draws nothing.
"""

from . import figure, paths, questions, raters
from .analysis import (agreement, binary, categories, display, judges,
                       loading, plots, render)
from .analysis.binary import collapse, confusion_counts, metrics
from .analysis.categories import difference_categories
from .analysis.loading import (ALL_RATERS, DATASET_FORMAT, DATASET_ORDER,
                               EXCLUDED_TITLE_PATTERNS, HUMAN_RATERS,
                               JUDGE_MODES, JUDGE_RATERS, PERFORMANCE_CATEGORY,
                               RATERS, UNSUP_RATERS, Ratings, add_null,
                               correctness_only, coverage_summary,
                               judge_columns, load_ratings,
                               unanswered_by_judges, uniform_variables)
from .analysis.render import summary_table

__all__ = [
    # analysis
    "load_ratings", "Ratings", "coverage_summary", "unanswered_by_judges",
    "correctness_only", "uniform_variables", "add_null", "judge_columns",
    "summary_table", "agreement", "binary", "categories", "display", "plots",
    "render", "difference_categories",
    "judges", "loading", "collapse", "confusion_counts", "metrics",
    "RATERS", "ALL_RATERS", "HUMAN_RATERS", "JUDGE_RATERS", "UNSUP_RATERS",
    "JUDGE_MODES", "DATASET_ORDER", "DATASET_FORMAT",
    "EXCLUDED_TITLE_PATTERNS", "PERFORMANCE_CATEGORY",
    # workflow
    "raters", "paths", "questions", "figure",
]


def __getattr__(name):
    """Load the interactive/CLI modules on first use.

    `compare` and `report` pull in `rich` and are only wanted when something
    actually drives the workflow, so they stay out of the import above — the
    notebook should not pay for them, and neither should `import ratings`.
    """
    if name in ("compare", "report", "session", "session_blind", "judge_import"):
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
