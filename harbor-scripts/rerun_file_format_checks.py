"""Rerun the file/format/contamination tests on a trial's snapshot and merge
any newly-recorded metrics into metrics.json.

Some trials are missing the file-existence / contamination / data-format
fields in `metrics.json` — most likely because a previous rerun-merge
operation (rerun_verifier.sh + merge_rerun_verifier.sh) replaced
metrics.json with the rerun's partial output, dropping fields the original
verifier had recorded. Same-day trials from the same agent show
inconsistent field presence, which rules out an older test_outputs.py.

This script reruns just the *cheap* tests (no docker, no LLM judges, no
GPU decoder training) against the snapshot files the agent produced, and
merges the new fields into the existing `metrics.json`. Existing keys are
preserved.

We call the same test functions that `pytest test_outputs.py` would, by
fresh-importing the task's `tests/test_outputs.py` — so any future change
to the tests flows through here automatically.

Tests rerun:
  * test_required_files_exist
  * test_no_contamination
  * test_expected_files_exist
  * test_verify_data_format

Usage:
    conda activate decoder-data-format
    # Dry-run: list candidate trials (missing all cheap fields)
    python rerun_file_format_checks.py
    # Rerun one trial
    python rerun_file_format_checks.py --trial harbor-jobs/allen2p/.../trial1 --write
    # Rerun all candidates
    python rerun_file_format_checks.py --all --write
"""

import argparse
import importlib.util
import json
import os
import pickle
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")
HARBOR_TASKS = REPO_ROOT / "harbor-tasks"
HARBOR_JOBS = REPO_ROOT / "harbor-jobs"

# Fields the cheap tests write. If ALL of these are absent from metrics.json,
# the trial is a rerun candidate.
CHEAP_FIELDS = (
    "required_files_missing", "required_files_empty",
    "expected_files_missing", "expected_files_empty",
    "expected_files_found", "expected_files_total",
    "contamination_detected", "contaminated_files",
    "sample_data_format_valid", "sample_data_format_errors", "sample_data_format_warnings",
    "full_data_format_valid", "full_data_format_errors", "full_data_format_warnings",
)


def _import_task_tests(task: str, workdir: Path):
    """Fresh-import the task's decoder.py + test_outputs.py with WORKDIR set."""
    tests_dir = HARBOR_TASKS / task / "tests"
    os.environ["WORKDIR"] = str(workdir)
    os.environ["METRICS_PATH"] = "/dev/null"  # we capture via the passed-in dict
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


def rerun_trial(trial_dir: Path, task: str, write: bool, force: bool = False) -> dict:
    report = {"trial": str(trial_dir), "ok": False, "events": [],
              "keys_added": [], "keys_overwritten": []}

    snap = trial_dir / "verifier" / "snapshot"
    if not snap.is_dir():
        report["events"].append("no verifier/snapshot/")
        return report

    metrics_path = trial_dir / "verifier" / "metrics.json"
    try:
        with open(metrics_path) as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {}

    # Fresh-import so test_outputs.py picks up the right WORKDIR.
    test_mod = _import_task_tests(task, workdir=snap)

    # Load both pickles using the test module's subdir-aware finder, so an
    # agent that relocated them into `cache/` is still detected here.
    finder = getattr(test_mod, "_find_workdir_file", None)
    def _find(name):
        if finder is not None:
            return finder(name)
        p = snap / name
        return p if p.exists() else None

    pkl_full = _find("converted_data.pkl")
    pkl_sample = _find("sample_data.pkl")
    submitted_full = pickle.load(open(pkl_full, "rb")) if pkl_full else None
    submitted_sample = pickle.load(open(pkl_sample, "rb")) if pkl_sample else None

    new_metrics: dict = {}

    for label, fn, args in [
        ("test_required_files_exist", test_mod.test_required_files_exist, (new_metrics,)),
        ("test_no_contamination",     test_mod.test_no_contamination,     (new_metrics,)),
        ("test_expected_files_exist", test_mod.test_expected_files_exist, (new_metrics,)),
        ("test_verify_data_format",   test_mod.test_verify_data_format,
            (new_metrics, submitted_sample, submitted_full)),
    ]:
        if label == "test_verify_data_format" and (submitted_sample is None or submitted_full is None):
            report["events"].append(f"{label}: skipped (missing pickle)")
            continue
        raised, msg = _invoke(fn, *args, label=label)
        report["events"].append(f"{label}: {msg}")

    # Merge new metrics into existing.
    # Default: only ADD keys that aren't already present (safe).
    # --force:  also OVERWRITE keys that are already present, but only when
    #           the new value actually differs (avoids spurious writes).
    keys_added = []
    keys_overwritten = []
    for k, v in new_metrics.items():
        if k not in existing:
            existing[k] = v
            keys_added.append(k)
        elif force and existing[k] != v:
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


def find_candidates(force: bool = False) -> list[tuple[Path, str]]:
    """Trials needing a cheap-field rerun.

    Default: only trials where ALL cheap fields are absent.
    With force=True: every trial that has a snapshot (so we can re-evaluate
    even if the cheap fields are already present, e.g. after a test_outputs.py
    change that should update them).
    """
    out = []
    for trial_dir in sorted(HARBOR_JOBS.glob("*/*/*/")):
        if "oracle" in trial_dir.parts:
            continue
        mp = trial_dir / "verifier" / "metrics.json"
        if not mp.exists():
            continue
        try:
            m = json.loads(mp.read_text())
        except json.JSONDecodeError:
            continue
        if not force and any(k in m for k in CHEAP_FIELDS):
            continue        # at least some cheap fields present → up-to-date
        rel = trial_dir.relative_to(HARBOR_JOBS)
        task = rel.parts[0]
        out.append((trial_dir, task))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--trial", help="Path to one trial dir (relative to repo root or absolute)")
    g.add_argument("--all", action="store_true", help="Rerun every trial missing cheap fields")
    ap.add_argument("--write", action="store_true", help="Actually write metrics.json (default: dry-run)")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing cheap-field values in metrics.json "
                         "(useful after a test_outputs.py change). Without this "
                         "flag the script only ADDS missing keys.")
    args = ap.parse_args()

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
        candidates = find_candidates(force=args.force)
        scope = "with snapshots" if args.force else "missing cheap fields"
        print(f"Found {len(candidates)} trial(s) {scope}.")
    else:
        for trial, task in find_candidates(force=args.force):
            print(f"  {task:<15}  {trial.relative_to(REPO_ROOT)}")
        return

    for trial, task in candidates:
        print(f"\n=== {task} / {trial.name} ===")
        try:
            rep = rerun_trial(trial, task, write=args.write, force=args.force)
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
