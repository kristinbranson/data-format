"""Rerun just `test_data_stats` against a trial's snapshot and merge the
new metrics into metrics.json.

Unlike `rerun_decoder_accuracy.py`, this script does NOT rerun
`test_decoder_accuracy` — so no decoder training, no GPU, no several-minute
wait per trial. Useful when you change `test_outputs.py`'s
variable-matching logic (e.g., the Hungarian range-cost normalisation)
and want to refresh the recorded match costs / range errors / fraction
errors across all trials cheaply.

We call the same test function `pytest test_outputs.py` would, by
fresh-importing the task's `tests/test_outputs.py` — so changes to that
file flow through here automatically.

Default behaviour overwrites the data-stats fields when they differ
(because that's the point of running this script). Use `--no-overwrite`
to only add missing keys.

Usage:
    conda activate decoder-data-format
    # Dry-run: list candidate trials (those with a reference and snapshot)
    python rerun_data_stats.py
    # Rerun one trial
    python rerun_data_stats.py --trial harbor-jobs/lee2025/.../trial1 --write
    # Rerun every candidate
    python rerun_data_stats.py --all --write
"""

import argparse
import importlib.util
import json
import pickle
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")
HARBOR_TASKS = REPO_ROOT / "harbor-tasks"
HARBOR_JOBS = REPO_ROOT / "harbor-jobs"

# Fields that test_data_stats writes (top-level only; per-variable
# input_range_error_<var>, output_range_error_<var>, output_fraction_error_<var>
# are handled by prefix below).
DATA_STATS_FIELDS = (
    "nsessions", "ntrials_total", "T_median", "nsubjects", "nneurons_total",
    "nsessions_ratio", "ntrials_total_ratio", "T_median_ratio",
    "nsubjects_ratio", "nneurons_total_ratio",
    "input_matches", "input_range_mean_cost",
    "output_matches", "output_fraction_mean_cost",
)
DATA_STATS_PREFIXES = (
    "input_range_error_",
    "output_range_error_",
    "output_fraction_error_",
)


def _import_task_tests(task: str):
    """Fresh-import the task's decoder.py + test_outputs.py."""
    tests_dir = HARBOR_TASKS / task / "tests"
    for mod_name in ("decoder", "test_outputs"):
        sys.modules.pop(mod_name, None)
    sys.path.insert(0, str(tests_dir))
    try:
        spec = importlib.util.spec_from_file_location("test_outputs", tests_dir / "test_outputs.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


def _build_submitted_data_stats(test_mod, data: dict) -> dict:
    """Replicate the submitted_data_stats fixture body."""
    stats = test_mod.print_data_summary(data)
    stats["nneurons_total"] = stats["nsessions"] * stats["nneurons_mean"]
    return stats


def _build_reference_data_stats(task: str):
    """Replicate the reference_data_stats fixture body (or return None)."""
    ref_path = HARBOR_TASKS / task / "tests" / "reference_stats_full.json"
    if not ref_path.exists():
        return None
    with open(ref_path) as f:
        stats = json.load(f)
    stats["data_summary"]["nneurons_total"] = (
        stats["data_summary"]["nsessions"] * stats["data_summary"]["nneurons_mean"]
    )
    return stats


def _invoke(fn, *args, label: str):
    """Call a test function, catching AssertionError + pytest.skip etc."""
    try:
        fn(*args)
        return False, "passed"
    except BaseException as e:
        msg = f"{type(e).__name__}: {e}".strip()
        if type(e).__name__ == "Skipped":
            msg = f"skipped: {e}"
        return True, msg


def rerun_trial(trial_dir: Path, task: str, write: bool, overwrite: bool = True) -> dict:
    report = {"trial": str(trial_dir), "ok": False, "events": [],
              "keys_added": [], "keys_overwritten": []}

    pkl = trial_dir / "verifier" / "snapshot" / "converted_data.pkl"
    if not pkl.exists():
        report["events"].append("no converted_data.pkl")
        return report

    metrics_path = trial_dir / "verifier" / "metrics.json"
    try:
        with open(metrics_path) as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {}

    with open(pkl, "rb") as f:
        submitted_data_full = pickle.load(f)

    test_mod = _import_task_tests(task)

    # Use the test module's subdir-aware finder if available, so an agent
    # that relocated converted_data.pkl into cache/ is still detected.
    finder = getattr(test_mod, "_find_workdir_file", None)
    if finder is not None:
        snap = trial_dir / "verifier" / "snapshot"
        p = finder("converted_data.pkl", workdir=snap)
        if p is not None and p != pkl:
            with open(p, "rb") as f:
                submitted_data_full = pickle.load(f)

    submitted_data_stats = _build_submitted_data_stats(test_mod, submitted_data_full)
    reference_data_stats = _build_reference_data_stats(task)

    if reference_data_stats is None:
        report["events"].append("no reference_stats_full.json (unsupervised task)")
        # test_data_stats will skip via pytest.skip when reference is None;
        # we still call it so it can record the un-skipped fields like the
        # raw counts. The skip is gracefully caught by _invoke.

    new_metrics: dict = {}
    raised, msg = _invoke(
        test_mod.test_data_stats,
        new_metrics, submitted_data_stats, reference_data_stats,
        label="test_data_stats",
    )
    report["events"].append(f"test_data_stats: {msg}")

    if not new_metrics:
        report["events"].append("nothing was written to metrics — nothing to merge")
        return report

    # Merge: add missing keys, optionally overwrite existing ones.
    keys_added = []
    keys_overwritten = []
    for k, v in new_metrics.items():
        if k not in existing:
            existing[k] = v
            keys_added.append(k)
        elif overwrite and existing[k] != v:
            existing[k] = v
            keys_overwritten.append(k)
    report["keys_added"] = sorted(keys_added)
    report["keys_overwritten"] = sorted(keys_overwritten)
    report["ok"] = True

    changed = bool(keys_added or keys_overwritten)
    if write and changed:
        with open(metrics_path, "w") as f:
            json.dump(existing, f, indent=2, sort_keys=True)
        report["events"].append(f"wrote {metrics_path}")
    elif write:
        report["events"].append("no changes; metrics.json untouched")
    return report


def find_candidates() -> list[tuple[Path, str]]:
    """Trials with a snapshot pickle and a supervised task's reference stats."""
    out = []
    for trial_dir in sorted(HARBOR_JOBS.glob("*/*/*/")):
        if "oracle" in trial_dir.parts or "badtrial" in str(trial_dir):
            continue
        pkl = trial_dir / "verifier" / "snapshot" / "converted_data.pkl"
        if not pkl.exists():
            continue
        rel = trial_dir.relative_to(HARBOR_JOBS)
        task = rel.parts[0]
        # Only supervised tasks have something useful to recompute
        if not (HARBOR_TASKS / task / "tests" / "reference_stats_full.json").exists():
            continue
        out.append((trial_dir, task))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--trial", help="Path to one trial dir (relative to repo root or absolute)")
    g.add_argument("--all", action="store_true",
                   help="Rerun every supervised trial with a converted_data.pkl")
    ap.add_argument("--write", action="store_true", help="Actually write metrics.json (default: dry-run)")
    ap.add_argument("--no-overwrite", action="store_true",
                    help="Only ADD missing keys; never overwrite existing values "
                         "(default: overwrite when values differ).")
    args = ap.parse_args()

    overwrite = not args.no_overwrite

    if args.trial:
        trial = Path(args.trial)
        if not trial.is_absolute():
            trial = (REPO_ROOT / trial).resolve()
        try:
            rel = trial.relative_to(HARBOR_JOBS)
            task = rel.parts[0]
        except ValueError:
            sys.exit(f"Trial path must be under {HARBOR_JOBS}")
        candidates = [(trial, task)]
    elif args.all:
        candidates = find_candidates()
        print(f"Found {len(candidates)} supervised trial(s) with snapshots.")
    else:
        for trial, task in find_candidates():
            print(f"  {task:<15}  {trial.relative_to(REPO_ROOT)}")
        return

    for trial, task in candidates:
        print(f"\n=== {task} / {trial.name} ===")
        try:
            rep = rerun_trial(trial, task, write=args.write, overwrite=overwrite)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            traceback.print_exc()
            continue
        for ev in rep["events"]:
            print(f"  {ev}")
        if rep["keys_added"]:
            print(f"  + added:       {', '.join(rep['keys_added'])}")
        if rep["keys_overwritten"]:
            print(f"  * overwritten: {', '.join(rep['keys_overwritten'])}")
        if not rep["keys_added"] and not rep["keys_overwritten"]:
            print("  (no changes)")


if __name__ == "__main__":
    main()
