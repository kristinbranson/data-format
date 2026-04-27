"""Rerun the relevant tests on a trial's snapshot and merge new metrics into metrics.json.

For trials where decoder / data-stats metrics are missing from metrics.json
(because the original pytest aborted before those fields were written, or
because the rerun/merge pipeline clobbered them), we can recover them by
loading the snapshot's converted_data.pkl and calling the test functions
directly. This avoids duplicating the logic in test_outputs.py — any changes
to the test functions flow through here automatically.

We call:
  * test_outputs.test_data_stats  (populates count ratios, range/fraction
    matches, input/output_range errors)
  * test_outputs.test_decoder_accuracy  (populates validation_balanced_accuracy
    and, when a reference exists, _reference + _ratio)

Each call is wrapped so that pytest assertion failures or pytest.skip calls
don't prevent the metrics that were recorded *before* the failure from being
merged into metrics.json.

Usage:
    conda activate decoder-data-format
    # dry run — just list candidates:
    python rerun_decoder_accuracy.py
    # rerun one trial locally:
    python rerun_decoder_accuracy.py --trial allen2p/claude-code/... --write
    # rerun all missing locally (slow + RAM-heavy on big pkls):
    python rerun_decoder_accuracy.py --all --write

    # Submit each missing trial as its own job to Janelia gpu_a100 queue:
    # (preview)
    python rerun_decoder_accuracy.py --all --cluster
    # (actually submit)
    python rerun_decoder_accuracy.py --all --cluster --write
"""

import argparse
import importlib.util
import json
import os
import pickle
import sys
import traceback
from pathlib import Path
import numpy as np

REPO = Path("/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format")
DEFAULT_HARBOR_JOBS = REPO / "harbor-jobs"
HARBOR_TASKS = REPO / "harbor-tasks"


def _import_task_tests(task: str):
    """Fresh-import the task's decoder.py + test_outputs.py.

    Uses sys.path + module cache eviction so `from decoder import ...` inside
    test_outputs.py resolves to THIS task's decoder (the decoder files are
    functionally identical across tasks today, but we shouldn't assume that).
    """
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


def _invoke(fn, *args, label: str) -> tuple[bool, str]:
    """Call a test function, catching any exception (AssertionError, pytest.skip
    Skipped, matcher errors, ...). Returns (raised?, short message)."""
    try:
        fn(*args)
        return False, "passed"
    except BaseException as e:
        msg = f"{type(e).__name__}: {e}".strip()
        # pytest.skip raises _pytest.outcomes.Skipped; call it "skipped".
        if type(e).__name__ == "Skipped":
            msg = f"skipped: {e}"
        return True, msg


def rerun_trial(trial_dir: Path, task: str, write: bool) -> dict:
    report = {"trial": str(trial_dir), "ok": False, "events": [], "keys_added": []}

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
    submitted_data_stats = _build_submitted_data_stats(test_mod, submitted_data_full)
    reference_data_stats = _build_reference_data_stats(task)

    # DEBUG: confirm reference_data_stats is being loaded.
    if reference_data_stats is None:
        print(f"  DEBUG: reference_data_stats is None for task={task}")
    else:
        print(f"  DEBUG: reference_data_stats loaded for task={task}, "
              f"top-level keys: {sorted(reference_data_stats.keys())}")

    # Fresh metrics dict — we merge into the existing file at the end so we
    # don't lose pre-existing keys (judge rewards, etc.).
    new_metrics: dict = {}

    raised, msg = _invoke(
        test_mod.test_data_stats,
        new_metrics, submitted_data_stats, reference_data_stats,
        label="test_data_stats",
    )
    report["events"].append(f"test_data_stats: {msg}")

    raised, msg = _invoke(
        test_mod.test_decoder_accuracy,
        new_metrics, submitted_data_full, submitted_data_stats, reference_data_stats,
        label="test_decoder_accuracy",
    )
    report["events"].append(f"test_decoder_accuracy: {msg}")

    if not new_metrics:
        report["events"].append("nothing was written to metrics — nothing to merge")
        return report

    report["ok"] = True
    report["keys_added"] = sorted(k for k in new_metrics if k not in existing)
    report["keys_updated"] = sorted(k for k in new_metrics if k in existing)

    if write:
        merged = dict(existing)
        merged.update(new_metrics)
        with open(metrics_path, "w") as f:
            json.dump(merged, f, indent=2)

    # Stash the per-output accuracy for easy display.
    report["acc"] = new_metrics.get("validation_balanced_accuracy")
    return report


def list_missing(harbor_jobs: Path):
    """Trials with a converted_data.pkl but no validation_balanced_accuracy."""
    import glob
    for f in sorted(glob.glob(str(harbor_jobs / "*" / "*" / "*" / "verifier" / "metrics.json"))):
        if "/oracle/" in f or "badtrial" in f:
            continue
        trial_dir = Path(f).parent.parent
        snap_pkl = trial_dir / "verifier" / "snapshot" / "converted_data.pkl"
        if not snap_pkl.exists():
            continue
        with open(f) as fh:
            m = json.load(fh)
        if m.get("validation_balanced_accuracy"):
            continue
        task = trial_dir.relative_to(harbor_jobs).parts[0]
        yield task, trial_dir


# --- Janelia cluster submission ----------------------------------------------
#
# A100 has 80GB VRAM, 12 slots/GPU, 40GB RAM/slot → 480GB RAM total. That's
# enough to deserialize even the 200GB mouseland pkls (which OOM'd a workstation).
#
# Submission goes through `ssh login1 'bsub ...'` so this script can be run from
# anywhere with NFS-mounted /home and /groups.

CLUSTER_QUEUE = "gpu_a100"
RAM_PER_SLOT_GB = {
    'gpu_a100': 40,
    'gpu_l4': 15,
    'gpu_l4_16': 15,
    'gpu_l4_large': 15,
    'gpu_h100': 40,
    'gpu_h200': 40,
    'gpu_t4': 15,
    'gpu_short': 15,
}
# Per-GPU slot ratio for each queue (slots per GPU per host). When we ask for
# more slots than this ratio per GPU, LSF treats it as over-subscribing and
# may print an interactive prompt that hangs ssh. We scale n_gpus alongside
# n_slots to stay at-or-below the ratio, even though the decoder only uses 1
# GPU — the extra GPU(s) get reserved-but-unused, which is fine.
SLOTS_PER_GPU = {
    'gpu_a100': 12,
    'gpu_l4': 8,
    'gpu_l4_16': 16,
    'gpu_l4_large': 64,
    'gpu_h100': 12,
    'gpu_h200': 12,
    'gpu_t4': 48,
    'gpu_short': 8,
}
# Empirical model of peak RSS during a rerun:
#   peak_rss_gb ≈ pkl_size_gb * PKL_RAM_FACTOR + BASE_OVERHEAD_GB
# Constants tuned upward after observing OOM kills on cluster runs. Empirical
# data (peak / pkl ratio) shows smaller pkls can hit ratios up to ~2.3× while
# bigger ones settle around 1.7-2.0× — so we set PKL_RAM_FACTOR=2.5 to give
# headroom for the worst case and keep BASE_OVERHEAD_GB=20 for the fixed
# Python/library/PCA overhead.
#   measured: hasnain2024 (3.11 GB → 10.75 GB peak)
#             allen2p     (8.27 GB → 17.23 GB peak)
#             mouseland   (138 GB → 320 GB peak — OOM at -n 8)
#             mouseland   (177 GB → 340 GB peak — fine at -n 10)
#             mouseland   (201 GB → 343 GB peak — fine at -n 11)
PKL_RAM_FACTOR = 2.5
BASE_OVERHEAD_GB = 20.0
CLUSTER_WALL_HHMM = "8:00"  # 8 hours; loading 200GB pkl is slow over NFS
# Path for log files. Must be a path that's the same on the workstation
# (where this script runs) and the cluster nodes (where the bsub job runs).
# /groups/ is mounted with identical paths on both, so we use that — not
# $HOME (which differs between the two: workstation /home/bransonk@hhmi.org/
# vs cluster /groups/branson/home/bransonk/).
CLUSTER_LOG_DIR = Path("/groups/branson/home/bransonk/cluster_logs/rerun_decoder")
CONDA_ACTIVATE = (
    "source $HOME/miniforge3/etc/profile.d/conda.sh && "
    "conda activate test-decoder-data-format"
)
SCRIPT_PATH = Path(__file__).resolve()

# The decoder uses only one GPU, so we keep num=1 and scale slot count based
# on pkl size to give the in-process pkl + PCA + decoder enough RAM. The slot
# count is the lever for RAM (and CPU) — see RAM_PER_SLOT_GB above.
MIN_SLOTS = 4  # never request fewer than this, regardless of pkl size


def _slots_for_pkl(pkl_size_gb: float) -> int:
    """Pick a slot count based on pkl size, using an additive RAM model
    (PKL_RAM_FACTOR * pkl + BASE_OVERHEAD_GB) so the fixed Python/library
    overhead is accounted for separately from the per-byte data growth."""
    needed_gb = pkl_size_gb * PKL_RAM_FACTOR + BASE_OVERHEAD_GB
    slots = int(np.ceil(needed_gb / RAM_PER_SLOT_GB[CLUSTER_QUEUE]))
    return max(slots, MIN_SLOTS)

def _gpus_for_slots(n_slots: int) -> int:
    """Scale GPU count alongside slot count so we stay within the queue's
    slots/GPU ratio. The decoder only uses one GPU; extras are reserved-and-
    idle. This avoids LSF's over-ratio warning + interactive prompt."""
    ratio = SLOTS_PER_GPU[CLUSTER_QUEUE]
    return max(1, int(np.ceil(n_slots / ratio)))


def _build_cluster_command(task: str, trial_rel: str, harbor_jobs: Path) -> tuple[str, str, Path]:
    """Return (job_name, full bsub command line, log file path) for one
    trial. Slot count is chosen based on pkl size so giant trials get enough
    RAM; GPU count is scaled with slots so we don't trip LSF's over-ratio
    prompt (extra GPUs are reserved-but-unused)."""
    job_name = f"rerunacc_{task}_{trial_rel.replace('/', '_').replace(':', '_')}"
    log_path = CLUSTER_LOG_DIR / f"{job_name}.log"

    pkl_path = harbor_jobs / trial_rel / "verifier" / "snapshot" / "converted_data.pkl"
    pkl_gb = pkl_path.stat().st_size / 1024**3 if pkl_path.exists() else 0.0
    n_slots = _slots_for_pkl(pkl_gb)
    n_gpus = _gpus_for_slots(n_slots)

    inner = (
        f"{CONDA_ACTIVATE} && "
        f"python -u {SCRIPT_PATH} "
        f"--harbor-jobs {harbor_jobs} "
        f"--trial {trial_rel} --write"
    )
    bsub = (
        f'bsub -n {n_slots} -gpu "num={n_gpus}" -q {CLUSTER_QUEUE} '
        f'-W {CLUSTER_WALL_HHMM} -J {job_name} -o {log_path} '
        f'"{inner}"'
    )
    return job_name, bsub, log_path


def _submit_cluster_job(bsub_cmd: str, login_host: str = "login1") -> int:
    """Submit a bsub command to the cluster via ssh login1. Returns exit code."""
    import subprocess
    # NOTE: ssh concatenates the post-hostname args with spaces before sending
    # to the remote shell. So we must pass the whole bsub command line as a
    # SINGLE argument; otherwise the remote runs `bash -lc bsub` with the
    # bsub flags becoming positional args of `-c bsub`, and bsub blocks on
    # stdin waiting for a jobspec.
    full = ["ssh", login_host, bsub_cmd]
    return subprocess.call(full, stdin=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--harbor-jobs", type=Path, default=DEFAULT_HARBOR_JOBS)
    ap.add_argument("--trial", help="relative path under harbor-jobs/ (e.g. allen2p/claude-code/...)")
    ap.add_argument("--all", action="store_true", help="rerun all missing trials")
    ap.add_argument("--write", action="store_true",
                    help="actually run (locally) or submit (with --cluster)")
    ap.add_argument("--cluster", action="store_true",
                    help=f"submit each trial as a separate bsub job to {CLUSTER_QUEUE}")
    args = ap.parse_args()

    if args.trial and args.all:
        ap.error("pass --trial or --all, not both")

    harbor_jobs = args.harbor_jobs.expanduser().resolve()

    if args.trial:
        trial_dir = harbor_jobs / args.trial
        task = Path(args.trial).parts[0]
        trials = [(task, trial_dir)]
    else:
        trials = list(list_missing(harbor_jobs))
        print(f"Found {len(trials)} trials missing validation_balanced_accuracy:")
        for t, d in trials:
            print(f"  {t}: {d.relative_to(harbor_jobs)}")
        print()
        if not args.all:
            print("Pass --all to rerun, or --trial <path> to rerun one.")
            return

    if args.cluster:
        # Generate a bsub command per trial. With --write, actually submit; without,
        # just print so the user can review.
        if args.write:
            # /groups is mounted on both workstation and cluster, so we can
            # mkdir locally and the cluster nodes will see the same directory.
            CLUSTER_LOG_DIR.mkdir(parents=True, exist_ok=True)
            print(f"\nLogs will be written to {CLUSTER_LOG_DIR}")
        print(f"\n{'Submitting' if args.write else 'Would submit'} {len(trials)} bsub job(s) to {CLUSTER_QUEUE}:")
        n_submitted = 0
        for task, trial_dir in trials:
            trial_rel = str(trial_dir.relative_to(harbor_jobs))
            pkl = trial_dir / "verifier" / "snapshot" / "converted_data.pkl"
            pkl_gb = pkl.stat().st_size / 1024**3 if pkl.exists() else 0.0
            n_slots = _slots_for_pkl(pkl_gb)
            n_gpus = _gpus_for_slots(n_slots)
            ram_gb = n_slots * RAM_PER_SLOT_GB[CLUSTER_QUEUE]
            job_name, bsub_cmd, log_path = _build_cluster_command(task, trial_rel, harbor_jobs)
            print(f"\n  {job_name}  (pkl={pkl_gb:.1f}GB → {n_slots} slots, "
                  f"{n_gpus} GPU{'s' if n_gpus > 1 else ''}, {ram_gb}GB RAM)")
            print(f"    {bsub_cmd}")
            if args.write:
                rc = _submit_cluster_job(bsub_cmd)
                if rc == 0:
                    n_submitted += 1
                    print(f"    -> submitted; log: {log_path}")
                else:
                    print(f"    -> FAILED (ssh/bsub exit {rc})")
        if args.write:
            print(f"\n{n_submitted}/{len(trials)} submitted. Track with: ssh login1 'bjobs -J \"rerunacc_*\"'")
        else:
            print("\nAdd --write to actually submit these jobs.")
        return

    # Without --write, skip the actual (expensive) decoder training and just
    # print what would be run. This is the "list" dry-run mode.
    if not args.write:
        print(f"\nDry run — would rerun {len(trials)} trial(s):")
        for task, trial_dir in trials:
            print(f"  {trial_dir.relative_to(harbor_jobs)}")
        print("\nAdd --write to actually run the decoder and persist results.")
        return

    for task, trial_dir in trials:
        short = trial_dir.relative_to(harbor_jobs)
        print(f"\n=== {short} ===")
        try:
            report = rerun_trial(trial_dir, task, write=True)
        except BaseException as e:
            traceback.print_exc()
            print(f"  FATAL: {type(e).__name__}: {e}")
            continue
        for ev in report["events"]:
            print(f"  {ev}")
        if report["ok"]:
            acc = report.get("acc") or {}
            for k, v in acc.items():
                print(f"    {k}: {v:.4f}")
            n_added = len(report["keys_added"])
            n_updated = len(report["keys_updated"])
            print(f"  keys added: {n_added}; updated: {n_updated}")
            print("  [wrote metrics.json]")


if __name__ == "__main__":
    main()
