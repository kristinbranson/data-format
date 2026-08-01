"""Pull per-trial verifier metrics into a single JSON file for analysis.

Two discovery modes, both emitting the same curated schema
(``dataset -> agent -> trial -> {metrics}``) so downstream consumers in
``utils.py`` / ``metrics.py`` work with either.

**Rating-driven (default).** For each rated trial we already have an eval
markdown file at ``eval/<dataset>/<agent>_trial<N>.md``. The first paragraph
of every such file contains a canonical ``Trial path:`` line pointing at the
verifier snapshot folder under ``harbor-jobs/...``. We reuse that pointer
(rather than guessing dataset / agent name remappings ourselves) to find the
matching ``verifier/metrics.json``.

    python eval/trial_metrics.py                  -> eval/trial_metrics.json

**Direct scan (``--jobs-root``).** Runs with no rating markdown -- e.g. the
minimal-prompt sweep -- are discovered by globbing job directories instead.
Needed because the rating files are hand-written and only exist for trials
someone has already evaluated.

    python eval/trial_metrics.py \\
        --jobs-root /groups/branson/home/bransonk/harbor-cluster-jobs \\
        --out trial_metrics_minimal.json

Run from anywhere.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
OUT_FILE = EVAL_DIR / "trial_metrics.json"

# Both analysis trees: harbor-jobs is the archive (a symlink to /nearline),
# harbor-jobs-new holds everything collected from the cluster. Results are split
# across them -- every terminus trial and the whole minimal-prompt sweep are in the
# second -- so scanning only the first silently drops most arms.
DEFAULT_JOBS_ROOTS = [
    EVAL_DIR.parents[1] / "harbor-jobs",
    EVAL_DIR.parents[1] / "harbor-jobs-new",
]

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


# Cluster sweeps put one trial in each job directory, and every trial inside is
# named `<timestamp>_trial1` regardless of which repeat it is -- the real trial
# number lives in the job directory name, e.g. `hb_sosa2024_minimal_codex_t3`.
# The same agent appears under two directory names across the archive: harbor wrote
# `claude` for the March/April runs and `claude-code` later. They are one arm, so
# canonicalise to the name evaluation/eval/report.py and raters.py match literally.
# check_trial_health.py:409 normalises the same pair, in the other direction.
AGENT_ALIASES = {"claude": "claude-code"}

# Task directories are named after the dataset; the manual reference and the human
# rating folders are named after the paper's first author. Both names refer to the
# same task, and the association exists only as a hand-carried `Trial path:` line in
# each rating file. Canonicalising to the manual vocabulary here means the metrics
# key matches manual/<name>/ and eval/<name>/, so ratings and metrics can be joined
# on the dataset name instead of by resolving those paths.
DATASET_ALIASES = {"map": "chen2024", "mouseland": "zhong2025"}

# Not agent arms. `oracle` runs the reference solution, so its ratios are ~1.0 by
# construction -- keeping it would put a column in every figure that measures
# nothing about an agent.
SKIP_AGENTS = {"oracle"}

_JOB_DIR_TRIAL_RE = re.compile(r"_t(\d+)$")
_TRIAL_SUFFIX_RE = re.compile(r"_trial(\d+)$")

# Two directory layouts, globbed relative to a jobs root:
#   cluster: <job_dir>/<task>/<agent>/<timestamp>_trialN/verifier/metrics.json
#   legacy:            <task>/<agent>/<timestamp>_trialN/verifier/metrics.json
_LAYOUT_GLOBS = (
    "*/*/*/*_trial*/verifier/metrics.json",
    "*/*/*_trial*/verifier/metrics.json",
)


def _identify_trial(metrics_path: Path, root: Path) -> tuple[str, str, int, str, str] | None:
    """Derive (dataset, agent, trial_num, timestamp) from a metrics.json path.

    Args:
        metrics_path: .../<task>/<agent>/<timestamp>_trialN/verifier/metrics.json
        root: the jobs root `metrics_path` was globbed under.

    Returns:
        (dataset, agent, trial_num, timestamp, prompt), or None if the path
        doesn't parse.

        `dataset` has any `_minimal` suffix stripped so the two prompt variants
        of a task share a dataset key and can be compared directly, and `prompt`
        records which variant this trial actually was ("minimal" or "full").
        `agent` is canonicalised through AGENT_ALIASES, and trials belonging to
        SKIP_AGENTS return None rather than entering the output at all.
        Keeping the variant is not cosmetic: <task> and <task>_minimal read the
        SAME data and differ only in how much the instruction says, so without
        it the merged key silently collapses two different conditions into one
        and the newest timestamp wins. That is invisible today only because the
        arms happen to be disjoint -- claude/codex ran minimal, terminus ran
        full -- and would start dropping trials the moment they overlap.
    """
    # parts[-1] is `verifier`, parts[-2] the trial dir, then agent, then task.
    parts = metrics_path.relative_to(root).parts[:-1]  # drop 'metrics.json'
    if len(parts) < 4:
        return None
    trial_dir, agent, task = parts[-2], parts[-3], parts[-4]
    if agent in SKIP_AGENTS:
        return None
    agent = AGENT_ALIASES.get(agent, agent)

    dataset = task.removesuffix("_minimal")
    dataset = DATASET_ALIASES.get(dataset, dataset)
    prompt = "minimal" if task.endswith("_minimal") else "full"
    timestamp = trial_dir.split("_trial")[0]

    # Prefer the job directory's `_tN`; fall back to the `_trialN` suffix, which
    # is what the legacy layout carries.
    trial_num = None
    if len(parts) >= 5:
        m = _JOB_DIR_TRIAL_RE.search(parts[-5])
        if m:
            trial_num = int(m.group(1))
    if trial_num is None:
        m = _TRIAL_SUFFIX_RE.search(trial_dir)
        trial_num = int(m.group(1)) if m else 1

    return dataset, agent, trial_num, timestamp, prompt


def collect_from_jobs_roots(roots: list[Path]) -> dict:
    """Discover trials by globbing job directories rather than rating markdown.

    Args:
        roots: jobs roots to scan, searched in order.

    Returns:
        {dataset: {agent: {trial_str: {curated metrics}}}}.

    A task/agent/trial can appear more than once -- a failed run that was
    resubmitted leaves both directories behind -- so the newest timestamp wins.
    """
    # (dataset, agent, trial) -> (timestamp, curated metrics)
    best: dict[tuple[str, str, int], tuple[str, dict]] = {}
    n_seen = n_skipped = 0

    for root in roots:
        root = Path(root).expanduser()
        if not root.is_dir():
            print(f"  ! jobs root not found, skipping: {root}")
            continue
        for pattern in _LAYOUT_GLOBS:
            for metrics_path in sorted(root.glob(pattern)):
                ident = _identify_trial(metrics_path, root)
                if ident is None:
                    continue
                dataset, agent, trial_num, timestamp, prompt = ident
                n_seen += 1
                try:
                    raw = json.loads(metrics_path.read_text())
                except (OSError, json.JSONDecodeError) as e:
                    # A trial that died mid-verification can leave truncated
                    # JSON; skip it rather than aborting the whole scan.
                    print(f"  ! unreadable {metrics_path}: {e}")
                    n_skipped += 1
                    continue
                # prompt is part of the key: the two variants of a task are
                # separate conditions, not duplicate runs of one.
                key = (dataset, agent, prompt, trial_num)
                if key not in best or timestamp > best[key][0]:
                    curated = _curate(raw)
                    curated["prompt"] = prompt
                    best[key] = (timestamp, curated)

    out: dict[str, dict[str, dict[str, dict]]] = {}
    # Nest by prompt variant so a dataset/agent pair can hold both without one
    # overwriting the other: dataset -> agent -> prompt -> trial -> metrics.
    for (dataset, agent, prompt, trial_num), (_ts, curated) in sorted(best.items()):
        variants = out.setdefault(dataset, {}).setdefault(agent, {})
        variants.setdefault(prompt, {})[str(trial_num)] = curated

    # Four levels now: dataset -> agent -> prompt -> trial.
    n_kept = sum(len(trials)
                 for agents in out.values()
                 for variants in agents.values()
                 for trials in variants.values())
    print(f"  found: {n_seen}, kept: {n_kept} (newest per task/agent/trial), "
          f"unreadable: {n_skipped}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--jobs-root", nargs="*", type=Path, default=None,
        help="Job directories to scan. Default: "
             + ", ".join(str(p) for p in DEFAULT_JOBS_ROOTS))
    parser.add_argument(
        "--out", type=Path, default=None,
        help=f"Output file; relative paths resolve under {EVAL_DIR}. "
             f"Default: {OUT_FILE.name}")
    args = parser.parse_args()

    # Always the jobs roots. The other collector, collect_trial_metrics(), indexes
    # trials through the human rating markdown under eval/<dataset>/ -- so it sees
    # only trials someone opened a rating file for, and only on the machine whose
    # paths those files record. It is kept for that purpose, not as a default.
    metrics = collect_from_jobs_roots(args.jobs_root or DEFAULT_JOBS_ROOTS)

    out_file = args.out or OUT_FILE
    if not out_file.is_absolute():
        out_file = EVAL_DIR / out_file
    out_file.write_text(json.dumps(metrics, indent=2, sort_keys=True))
    print(f"\nWrote {out_file}")


if __name__ == "__main__":
    main()
