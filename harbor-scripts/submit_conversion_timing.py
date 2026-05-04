#!/usr/bin/env python3
"""
Submit one bsub job per (task, source) to time convert_data.py runs.

Sources:
  - manual/<task>/convert_data.py            -> source id "manual"
  - harbor-jobs/<task>/<agent>/<trial>/verifier/snapshot/convert_data.py
                                              -> source id "<agent>__<trial>"

Tasks (supervised): allen2p, lee2025, majnik2025, sosa2024

Each job gets:
  -n 8 -q gpu_a100 -gpu "num=1" -W <minutes>

Result dir per job:
  <results_root>/<task>/<source_id>/{timing.txt, stdout.txt, bsub.log}

Usage:
    submit_conversion_timing.py [--dry-run] [--results-root DIR]
                                [--minutes N] [--tasks t1,t2,...]
                                [--manual-only|--trials-only]
"""

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")
RUNNER = REPO_ROOT / "harbor-scripts" / "run_one_conversion.py"
DEFAULT_RESULTS_ROOT = REPO_ROOT / "timing_results"
SUPERVISED_TASKS = ["allen2p", "lee2025", "majnik2025", "sosa2024"]

# Must match TASK_DATA_DIR in run_one_conversion.py
TASK_DATA_DIR = {
    "allen2p":    REPO_ROOT / "allen2p"   / "data",
    "lee2025":    REPO_ROOT / "lee2025"   / "data",
    "majnik2025": REPO_ROOT / "track2p"   / "data",
    "sosa2024":   REPO_ROOT / "sosa2024"  / "data",
}


def discover_sources(task: str, manual: bool, trials: bool):
    """Yield (source_id, convert_data_py_path)."""
    if manual:
        p = REPO_ROOT / "manual" / task / "convert_data.py"
        if p.exists():
            yield ("manual", p)

    if trials:
        for snap in sorted(
            (REPO_ROOT / "harbor-jobs" / task).glob(
                "*/*/verifier/snapshot/convert_data.py"
            )
        ):
            # path: harbor-jobs/<task>/<agent>/<trial>/verifier/snapshot/convert_data.py
            parts = snap.parts
            agent, trial = parts[-5], parts[-4]
            if agent == "oracle":
                continue
            yield (f"{agent}__{trial}", snap)


def check_global():
    """Check things common to all jobs. Returns list of error strings."""
    errs = []
    if not RUNNER.is_file():
        errs.append(f"runner missing: {RUNNER}")
    if not os.access(RUNNER, os.R_OK):
        errs.append(f"runner not readable: {RUNNER}")
    scratch = Path(f"/scratch/{os.environ.get('USER','')}")
    if not scratch.parent.is_dir():
        errs.append(f"/scratch parent missing: {scratch.parent}")
    # bsub on path?
    if shutil.which("bsub") is None:
        errs.append("bsub not on PATH (run from a host that can submit, e.g. login1)")
    # conda env exists?
    home = os.environ.get("HOME", "")
    env_dir = Path(home) / "miniforge3" / "envs" / "decoder-data-format"
    if not env_dir.is_dir():
        errs.append(f"conda env missing: {env_dir} "
                    "(NOTE: $HOME differs on login1/cluster from workstation; "
                    "this check uses the current host's $HOME)")
    return errs


def check_job(task, source_id, script, results_root):
    """Per-job preflight. Returns list of error strings."""
    errs = []
    data_dir = TASK_DATA_DIR[task]
    train_decoder = (REPO_ROOT / "harbor-tasks" / task /
                     "environment" / "train_decoder.py")
    result_dir = results_root / task / source_id

    for p, label in [(script, "convert_data.py"),
                     (data_dir, "data dir"),
                     (train_decoder, "train_decoder.py")]:
        if not p.exists():
            errs.append(f"{label} missing: {p}")
            continue
        if not os.access(p, os.R_OK):
            errs.append(f"{label} not readable: {p}")

    # data dir should be a directory and not empty
    if data_dir.is_dir() and not any(data_dir.iterdir()):
        errs.append(f"data dir empty: {data_dir}")

    # Quick sanity: convert_data.py is a non-empty python file
    if script.is_file() and script.stat().st_size == 0:
        errs.append(f"convert_data.py is empty: {script}")

    # Result dir parent writable?
    parent = result_dir.parent if result_dir.exists() else result_dir.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        errs.append(f"can't create result dir {parent}: {e}")

    return errs


def submit(task, source_id, script, results_root, minutes, dry_run):
    result_dir = results_root / task / source_id
    result_dir.mkdir(parents=True, exist_ok=True)

    job_name = f"convtime_{task}_{source_id}"
    bsub_log = result_dir / "bsub.log"

    cmd_inner = (
        f"source $HOME/miniforge3/etc/profile.d/conda.sh && "
        f"conda activate decoder-data-format && "
        f"python3 {shlex.quote(str(RUNNER))} "
        f"{shlex.quote(task)} "
        f"{shlex.quote(str(script))} "
        f"{shlex.quote(str(result_dir))}"
    )

    bsub_args = [
        "bsub",
        "-J", job_name,
        "-n", "8",
        "-q", "gpu_a100",
        "-gpu", "num=1:aff=yes",
        "-W", str(minutes),
        "-o", str(bsub_log),
        cmd_inner,
    ]

    if shutil.which("bsub") is None:
        # Workstation: wrap via ssh login1
        bsub_str = " ".join(shlex.quote(a) for a in bsub_args)
        cmd = ["ssh", "login1", f"bash -l -c {shlex.quote(bsub_str)}"]
    else:
        cmd = bsub_args

    if dry_run:
        print("DRY-RUN:", " ".join(shlex.quote(c) for c in cmd))
        return None

    print(f"Submitting {job_name}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(res.stdout)
    sys.stderr.write(res.stderr)
    return res.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="Verify prerequisites for every job; do not submit")
    ap.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    ap.add_argument("--minutes", type=int, default=240,
                    help="bsub -W (minutes); default 240 (4h)")
    ap.add_argument("--tasks", default=",".join(SUPERVISED_TASKS),
                    help="comma-separated subset of tasks")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--manual-only", action="store_true")
    g.add_argument("--trials-only", action="store_true")
    ap.add_argument("--limit", type=int, default=None,
                    help="Submit at most N jobs total (useful with --dry-run or for a smoke test)")
    ap.add_argument("--start", type=int, default=0,
                    help="Skip the first N jobs in the discovery order (0-indexed). "
                         "Combine with --limit 1 to step through one at a time.")
    args = ap.parse_args()

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    manual = not args.trials_only
    trials = not args.manual_only

    args.results_root.mkdir(parents=True, exist_ok=True)

    if args.check:
        ok = True
        global_errs = check_global()
        if global_errs:
            ok = False
            print("GLOBAL ERRORS:")
            for e in global_errs:
                print(f"  - {e}")
        else:
            print("Global checks: OK")

        n_jobs = 0
        n_bad = 0
        for task in tasks:
            for source_id, script in discover_sources(task, manual, trials):
                n_jobs += 1
                errs = check_job(task, source_id, script, args.results_root)
                if errs:
                    n_bad += 1
                    ok = False
                    print(f"FAIL  {task}/{source_id}")
                    for e in errs:
                        print(f"    - {e}")
                else:
                    print(f"OK    {task}/{source_id}")
        print(f"\nChecked {n_jobs} jobs; {n_bad} failed.")
        sys.exit(0 if ok else 1)

    # Flatten so --start / --limit index globally across tasks.
    all_jobs = [(task, source_id, script)
                for task in tasks
                for source_id, script in discover_sources(task, manual, trials)]

    selected = all_jobs[args.start:]
    if args.limit is not None:
        selected = selected[:args.limit]

    print(f"Discovered {len(all_jobs)} jobs; "
          f"skipping {args.start}, "
          f"submitting {len(selected)}.\n")

    n = 0
    for task, source_id, script in selected:
        submit(task, source_id, script, args.results_root,
               args.minutes, args.dry_run)
        n += 1

    print(f"\n{'Would submit' if args.dry_run else 'Submitted'} {n} jobs.")


if __name__ == "__main__":
    main()
