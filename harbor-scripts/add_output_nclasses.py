"""Just compute `output_nclasses_<var>` for each trial and merge into
metrics.json. No `print_data_summary` (which iterates every trial's neural
array), no Hungarian matching, no decoder. The pickle is loaded but we
only touch `output_names` / `output_values` / `output_range` / `output`.

For the supervised reference companion (`output_nclasses_reference_<var>`),
we read it from each task's `tests/reference_stats_full.json`.

Usage:
    conda activate decoder-data-format
    # Dry-run: list candidate trials
    python add_output_nclasses.py
    # One trial
    python add_output_nclasses.py --trial harbor-jobs/.../trial1 --write
    # All trials
    python add_output_nclasses.py --all --write
    # Subset by task
    python add_output_nclasses.py --all --task mouseland --write
"""

import argparse
import json
import pickle
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")
HARBOR_TASKS = REPO_ROOT / "harbor-tasks"
HARBOR_JOBS = REPO_ROOT / "harbor-jobs"


def n_classes_per_output(data: dict) -> dict:
    """Map output var name -> int n_classes. Uses the cheapest source available."""
    names = data.get("output_names", [])
    if "output_values" in data:
        return {name: len(vals) for name, vals in zip(names, data["output_values"])}
    if "output_range" in data:
        return {name: int(round(hi - lo + 1))
                for name, (lo, hi) in data["output_range"].items()}
    # Last resort: scan the output arrays.
    n = {}
    for i, name in enumerate(names):
        vals = set()
        for sess in data.get("output", []):
            for trial in sess:
                arr = trial[i] if hasattr(trial, "ndim") and trial.ndim > 0 else trial
                vals.update(arr.flatten().tolist())
        n[name] = len(vals)
    return n


_REF_NCLASSES_CACHE: dict[str, dict | None] = {}
def reference_nclasses(task: str) -> dict | None:
    """Map var name -> int n_classes from the task's reference_stats_full.json,
    or None for unsupervised tasks."""
    if task in _REF_NCLASSES_CACHE:
        return _REF_NCLASSES_CACHE[task]
    ref_path = HARBOR_TASKS / task / "tests" / "reference_stats_full.json"
    if not ref_path.exists():
        _REF_NCLASSES_CACHE[task] = None
        return None
    with open(ref_path) as f:
        stats = json.load(f)
    out_range = stats.get("data_summary", {}).get("output_range", {})
    nc = {name: int(round(hi - lo + 1)) for name, (lo, hi) in out_range.items()}
    _REF_NCLASSES_CACHE[task] = nc
    return nc


def update_trial(trial_dir: Path, task: str, write: bool, force: bool) -> dict:
    rep = {"trial": str(trial_dir), "ok": False, "events": [],
           "added": [], "overwritten": []}
    pkl = trial_dir / "verifier" / "snapshot" / "converted_data.pkl"
    if not pkl.exists():
        # Fallback: look for the file anywhere in the snapshot (cache/, etc.)
        snap = trial_dir / "verifier" / "snapshot"
        if snap.is_dir():
            for candidate in snap.rglob("converted_data.pkl"):
                pkl = candidate
                break
        if not pkl.exists():
            rep["events"].append("no converted_data.pkl in snapshot")
            return rep

    metrics_path = trial_dir / "verifier" / "metrics.json"
    try:
        with open(metrics_path) as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {}

    t0 = time.time()
    with open(pkl, "rb") as f:
        data = pickle.load(f)
    if time.time() - t0 > 2:
        rep["events"].append(f"loaded converted_data.pkl ({time.time()-t0:.1f}s)")

    submitted = n_classes_per_output(data)
    reference = reference_nclasses(task)

    new_fields: dict = {}
    for name, n in submitted.items():
        new_fields[f"output_nclasses_{name}"] = int(n)
    if reference is not None:
        for name, n in reference.items():
            new_fields[f"output_nclasses_reference_{name}"] = int(n)
    # Also record dinput / doutput and per-input range so the figure can
    # show variable counts for unsupervised tasks where test_data_stats
    # skips. These are cheap to derive from the data dict that's already
    # loaded.
    in_names = data.get("input_names")
    if in_names is not None:
        new_fields["dinput"] = int(len(in_names))
    out_names = data.get("output_names")
    if out_names is not None:
        new_fields["doutput"] = int(len(out_names))
    # Per-input range, recorded as [lo, hi] (parallel to output_nclasses_*).
    # Lets consumers count dinput via column-presence and gives the actual
    # range for chance-baseline / units-check work later.
    in_range = data.get("input_range")
    if in_range is not None:
        for name, (lo, hi) in in_range.items():
            new_fields[f"input_range_{name}"] = [float(lo), float(hi)]

    for k, v in new_fields.items():
        if k not in existing:
            existing[k] = v
            rep["added"].append(k)
        elif force and existing[k] != v:
            existing[k] = v
            rep["overwritten"].append(k)

    rep["added"].sort()
    rep["overwritten"].sort()
    rep["ok"] = True

    if write and (rep["added"] or rep["overwritten"]):
        with open(metrics_path, "w") as f:
            json.dump(existing, f, indent=2, sort_keys=True)
        rep["events"].append(f"wrote {metrics_path}")
    elif write:
        rep["events"].append("no changes")
    return rep


def find_candidates(only_tasks: set | None = None,
                    skip_tasks: set | None = None) -> list[tuple[Path, str]]:
    out = []
    for trial_dir in sorted(HARBOR_JOBS.glob("*/*/*/")):
        if "oracle" in trial_dir.parts or "badtrial" in str(trial_dir):
            continue
        if not (trial_dir / "verifier" / "snapshot").is_dir():
            continue
        rel = trial_dir.relative_to(HARBOR_JOBS)
        task = rel.parts[0]
        if only_tasks is not None and task not in only_tasks:
            continue
        if skip_tasks is not None and task in skip_tasks:
            continue
        out.append((trial_dir, task))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--trial", help="One trial dir (relative to repo root or absolute).")
    g.add_argument("--all", action="store_true", help="All trials with snapshots.")
    ap.add_argument("--write", action="store_true", help="Persist (default: dry-run).")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing fields if they differ.")
    ap.add_argument("--task", action="append", default=[],
                    help="Restrict to this task (repeatable).")
    ap.add_argument("--skip-task", action="append", default=[],
                    help="Skip this task (repeatable).")
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
    else:
        only_tasks = set(args.task) if args.task else None
        skip_tasks = set(args.skip_task) if args.skip_task else None
        cands = find_candidates(only_tasks=only_tasks, skip_tasks=skip_tasks)
        if args.all:
            candidates = cands
            print(f"Found {len(candidates)} trial(s).")
        else:
            for trial, task in cands:
                print(f"  {task:<15}  {trial.relative_to(REPO_ROOT)}")
            return

    for trial, task in candidates:
        print(f"=== {task} / {trial.name} ===")
        try:
            rep = update_trial(trial, task, write=args.write, force=args.force)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            traceback.print_exc()
            continue
        for ev in rep["events"]:
            print(f"  {ev}")
        if rep["added"]:
            print(f"  + added ({len(rep['added'])}): {', '.join(rep['added'])}")
        if rep["overwritten"]:
            print(f"  * overwritten ({len(rep['overwritten'])}): {', '.join(rep['overwritten'])}")
        if not rep["added"] and not rep["overwritten"]:
            print("  (no changes)")


if __name__ == "__main__":
    main()
