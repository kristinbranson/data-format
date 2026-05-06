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


def _curate(raw: dict) -> dict:
    return {k: raw[k] for k in CURATED_FIELDS if k in raw}


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
