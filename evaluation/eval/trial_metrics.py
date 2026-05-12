"""Pull per-trial verifier metrics into a single JSON file for analysis.

For each rated trial we already have an eval markdown file at
``eval/<dataset>/<agent>_trial<N>.md``. The first paragraph of every such
file contains a canonical ``Trial path:`` line pointing at the verifier
snapshot folder under ``harbor-jobs/...``. We reuse that pointer (rather
than guessing dataset / agent name remappings ourselves) to find the
matching ``verifier/metrics.json`` and extract a curated subset of fields.

Output: ``eval/trial_metrics.json`` keyed dataset -> agent -> trial.

Run from anywhere:    python eval/pull_trial_metrics.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
OUT_FILE = EVAL_DIR / "trial_metrics.json"

# Fields kept from each metrics.json. Missing fields are silently skipped
# so the same curated list works for both supervised and unsupervised
# datasets. Nested dicts (validation_balanced_accuracy*) are kept whole;
# `trial_metrics_df` in utils.py flattens them on load.
CURATED_FIELDS = (
    # Raw dataset-scale stats (present on datasets that store raw counts).
    "nsessions", "ntrials_total", "T_median", "nsubjects", "nneurons_total",
    # Supervised-only ratios (agent vs reference solution).
    "nsessions_ratio", "ntrials_total_ratio", "T_median_ratio",
    "nsubjects_ratio", "nneurons_total_ratio",
    # Validation balanced accuracy: dict of {output_variable: score}.
    "validation_balanced_accuracy",            # always present
    "validation_balanced_accuracy_reference",  # supervised only
    "validation_balanced_accuracy_ratio",      # supervised only
    # Verifier-check fields (from test_outputs.py). Present whenever the
    # corresponding test reached the point of recording them; absent when
    # the test was skipped (e.g. for unsupervised datasets that have no
    # reference solution, test_data_stats skips early and the *_cost /
    # output_matches fields are not recorded).
    "required_files_missing", "required_files_empty",
    "expected_files_missing", "expected_files_empty",
    "expected_files_found", "expected_files_total",
    "contamination_detected",
    "sample_data_format_valid", "full_data_format_valid",
    "input_range_mean_cost",
    "output_fraction_mean_cost",
    "output_matches",
    # Variable counts recorded before the test_data_stats skip (so they're
    # present for unsupervised tasks too).
    "dinput", "doutput",
)

_TRIAL_FILE_RE = re.compile(r"^(claude-code|codex)_trial(\d+)\.md$")
_TRIAL_PATH_RE = re.compile(r"Trial path:\s*`([^`]+)`")


def _metrics_path_from_md(md_path: Path) -> Path | None:
    """Read the 'Trial path: `...`' line and return the metrics.json path.

    The Trial path line is not perfectly consistent — most files point at
    ``<trial_root>/verifier/snapshot/`` but a few point at ``<trial_root>``
    directly. We walk up from the given path until we find a parent that
    contains ``verifier/metrics.json``.
    """
    m = _TRIAL_PATH_RE.search(md_path.read_text())
    if not m:
        return None
    p = Path(m.group(1).rstrip("/"))
    for cand in (p, *p.parents):
        candidate = cand / "verifier" / "metrics.json"
        if candidate.exists():
            return candidate
    return None


# Per-variable error fields recorded by test_data_stats. Names are
# dataset-dependent (e.g. `output_fraction_error_running_speed`), so we
# keep them by prefix rather than enumerating every variable. None values
# in these fields are meaningful — they flag a mismatch in number of
# categories (output_fraction_error) or a missing variable.
CURATED_PREFIXES = (
    # `input_range_` (no `_error`) catches the per-input [lo, hi] fields
    # recorded before the skip, AND the existing `input_range_error_<var>`
    # fields recorded after the matcher runs.
    "input_range_",
    "output_range_error_",
    "output_fraction_error_",
    # Per-variable class counts (and the reference variant), recorded by
    # test_data_stats. Consumers derive chance = 1 / output_nclasses_<var>.
    "output_nclasses_",
)


def _curate(raw: dict) -> dict:
    out = {k: raw[k] for k in CURATED_FIELDS if k in raw}
    for k, v in raw.items():
        if k.startswith(CURATED_PREFIXES):
            out[k] = v
    # Derived: worst-case (max) per-variable range / fraction errors.
    # Useful for single-row "all output ranges match" / "all input ranges
    # match" checks without having to enumerate per-variable columns.
    for prefix, derived_name in (
        ("input_range_error_",     "input_range_error_max"),
        ("output_range_error_",    "output_range_error_max"),
        ("output_fraction_error_", "output_fraction_error_max"),
    ):
        vals = [v for k, v in raw.items()
                if k.startswith(prefix) and v is not None]
        if vals:
            out[derived_name] = float(max(vals))
    return out


def collect_trial_metrics(eval_dir: Path = EVAL_DIR) -> dict:
    """Return {dataset: {agent: {trial_str: {curated metrics}}}}."""
    out: dict[str, dict[str, dict[str, dict]]] = {}
    n_loaded = n_missing = 0

    for dataset_dir in sorted(eval_dir.iterdir()):
        if not dataset_dir.is_dir() or not (dataset_dir / "eval_summary.md").exists():
            continue
        ds = dataset_dir.name
        for md in sorted(dataset_dir.glob("*_trial*.md")):
            m = _TRIAL_FILE_RE.match(md.name)
            if not m:
                continue
            agent, trial = m.group(1), int(m.group(2))
            metrics_path = _metrics_path_from_md(md)
            if metrics_path is None or not metrics_path.exists():
                print(f"  ! no metrics.json for {ds}/{agent}/trial{trial} "
                      f"(looked at {metrics_path})")
                n_missing += 1
                continue
            raw = json.loads(metrics_path.read_text())
            out.setdefault(ds, {}).setdefault(agent, {})[str(trial)] = _curate(raw)
            n_loaded += 1

    print(f"  loaded: {n_loaded}, missing: {n_missing}")
    return out


def main() -> None:
    metrics = collect_trial_metrics()
    OUT_FILE.write_text(json.dumps(metrics, indent=2, sort_keys=True))
    print(f"\nWrote {OUT_FILE}")


if __name__ == "__main__":
    main()
