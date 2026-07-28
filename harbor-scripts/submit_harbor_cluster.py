#!/usr/bin/env python3
"""Submit harbor trials for the _minimal tasks to the Janelia cluster.

One bsub job per (task, agent, trial), each taking a whole gpu_l4_large node:
64 slots + 1 GPU is an entire l4_larges host (64 physical cores, 1006 GB, one
L4). Whole-node allocation is deliberate — podman on this cluster does not
enforce --cpus/--memory (measured: /sys/fs/cgroup/memory.max reads "max"), so
owning the node is the only way to bound a trial.

Usage:
    python submit_harbor_cluster.py --check          # validate, submit nothing
    python submit_harbor_cluster.py --dry-run        # print the bsub commands
    python submit_harbor_cluster.py                  # all 8 tasks x 2 agents x 3 trials
    python submit_harbor_cluster.py --tasks sosa2024_minimal --agents claude --trials 1
    python submit_harbor_cluster.py --start 0 --limit 1
"""

import argparse
import os
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path

# Exit quietly when stdout is closed early (e.g. `--dry-run | head`), the way
# standard Unix tools do, instead of raising BrokenPipeError.
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_HARBOR = REPO_ROOT / "harbor-scripts" / "run_harbor.sh"

# Queue geometry, matching rerun_decoder_accuracy.py:197-221. l4_larges hosts
# carry exactly one GPU, so 64 slots at the queue's 64-slots/GPU ratio is the
# whole machine and LSF never raises its over-ratio prompt.
QUEUE = "gpu_l4_large"
SLOTS = 64
GPUS = 1
RAM_PER_SLOT_GB = 15
# Observed agent+verify time: 1.25 h median, 6.06 h max (mouseland). The two LLM
# judges add roughly another hour on top of that (measured: ~25 min for the Claude
# judge alone on sosa2024), which left almost no headroom at the previous 8:00.
# LSF kills at the wall clock, so an overrun loses a trial that has already been
# paid for in full. gpu_* queues allow up to 14 days.
WALL = "24:00"

# Must resolve identically on the workstation and on compute nodes, so /groups
# rather than $HOME (workstation /home/<user>@hhmi.org vs cluster
# /groups/branson/home/<user>).
CLUSTER_LOG_DIR = Path("/groups/branson/home/bransonk/cluster_logs/harbor")
CLUSTER_JOBS_DIR = Path("/groups/branson/home/bransonk/harbor-cluster-jobs")

AGENTS = ["claude", "codex"]
DEFAULT_TRIALS = 3


def discover_tasks() -> list[str]:
    return sorted(p.name for p in (REPO_ROOT / "harbor-tasks").iterdir()
                  if p.is_dir() and p.name.endswith("_minimal"))


def build_job(task: str, agent: str, trial: int) -> tuple[str, str, Path]:
    """Return (job_name, bsub command line, log path) for one trial."""
    job_name = f"hb_{task}_{agent}_t{trial}"
    log_path = CLUSTER_LOG_DIR / f"{job_name}.log"
    jobs_dir = CLUSTER_JOBS_DIR / job_name

    inner = (
        f"bash {shlex.quote(str(RUN_HARBOR))} "
        f"--task {shlex.quote(task)} --agent {shlex.quote(agent)} "
        f"--ntrials 1 --nconcurrent 1 --podman --apikeys "
        f"--jobs-dir {shlex.quote(str(jobs_dir))}"
    )
    bsub = (
        f'bsub -n {SLOTS} -gpu "num={GPUS}" -q {QUEUE} -W {WALL} '
        f'-J {job_name} -o {shlex.quote(str(log_path))} '
        f'"{inner}"'
    )
    return job_name, bsub, log_path


def submit(bsub_cmd: str, login_host: str = "login1") -> int:
    """Submit via ssh when bsub is not local (i.e. from the workstation).

    ssh joins everything after the hostname with spaces before handing it to the
    remote shell, so the whole command must arrive as ONE argument; otherwise
    bsub's flags become arguments of `-c` and bsub blocks reading a jobspec from
    stdin. DEVNULL guarantees it can never wait on a terminal.
    """
    if shutil.which("bsub") is not None:
        cmd = ["bash", "-l", "-c", bsub_cmd]
    else:
        cmd = ["ssh", login_host, f"bash -l -c {shlex.quote(bsub_cmd)}"]
    return subprocess.call(cmd, stdin=subprocess.DEVNULL)


def check() -> bool:
    errs = []
    if not RUN_HARBOR.is_file():
        errs.append(f"missing {RUN_HARBOR}")
    def report(ok, label, detail=""):
        print(f"  [{'OK  ' if ok else 'FAIL'}] {label}{'  ' + detail if detail else ''}")
        if not ok:
            errs.append(label)

    ram = SLOTS * RAM_PER_SLOT_GB
    print(f"queue {QUEUE}: {SLOTS} slots x {RAM_PER_SLOT_GB} GB = {ram} GB, "
          f"{GPUS} GPU, -W {WALL}\n")

    # --- local ---
    report(RUN_HARBOR.is_file(), "run_harbor.sh present", str(RUN_HARBOR))
    report("--jobs-dir" in RUN_HARBOR.read_text() if RUN_HARBOR.is_file() else False,
           "run_harbor.sh supports --jobs-dir",
           "(required: concurrent jobs must not share a jobs dir)")

    # --apikeys sources this; both keys must be defined or every job fails at startup
    env_file = REPO_ROOT / ".env"
    env_txt = env_file.read_text() if env_file.is_file() else ""
    report(env_file.is_file(), ".env readable (needed by --apikeys)", str(env_file))
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        report(f"{key}=" in env_txt.replace("export ", ""), f".env defines {key}")

    for d in (CLUSTER_LOG_DIR, CLUSTER_JOBS_DIR):
        report(d.is_dir() or os.access(d.parent, os.W_OK), f"writable: {d}")

    for task in discover_tasks():
        d = REPO_ROOT / "harbor-tasks" / task
        compose = d / "environment" / "docker-compose.yaml"
        ok = (d / "task.toml").is_file() and compose.is_file()
        detail = ""
        if ok:
            # the host side of the bind mount must exist, or the container starts empty
            mounts = [ln.strip()[2:].split(":")[0].strip()
                      for ln in compose.read_text().splitlines()
                      if ln.strip().startswith("- ") and ":/app/" in ln]
            # Existence here proves nothing about a compute node: only /groups,
            # /nrs and /misc are mounted on both. /nearline in particular is
            # visible from the workstation but NOT from compute nodes, so a
            # dataset moved there would pass a naive check and fail every job.
            problems = []
            for m in mounts:
                real = (compose.parent / m).resolve()
                if not real.exists():
                    problems.append(f"missing {m}")
                elif str(real).startswith("/nearline"):
                    problems.append(f"{m} -> {real} on /nearline, not mounted on compute nodes")
                elif not str(real).startswith(("/groups/", "/nrs/", "/misc/")):
                    problems.append(f"{m} -> {real} not on a cluster-visible filesystem")
            ok, detail = not problems, "; ".join(problems)
        report(ok, f"{task}: task.toml, compose, data mount", detail)

    # --- cluster, in one round trip ---
    if shutil.which("bsub") is not None:
        report(True, "bsub on PATH (running on a submit host)")
    elif shutil.which("ssh") is None:
        report(False, "neither bsub nor ssh available")
    else:
        probe = ("command -v bsub >/dev/null && echo BSUB_OK; "
                 "[ -x $HOME/miniforge3/envs/eval-data-format-podman/bin/harbor ] && echo ENV_OK; "
                 "[ -d /groups/branson ] && echo GROUPS_OK; [ -d /nrs/branson ] && echo NRS_OK")
        try:
            out = subprocess.run(["ssh", "-o", "BatchMode=yes", "login1",
                                  f"bash -l -c {shlex.quote(probe)}"],
                                 capture_output=True, text=True, timeout=90,
                                 stdin=subprocess.DEVNULL).stdout
        except Exception as e:
            out = ""
            print(f"  [FAIL] ssh login1 failed: {e}")
            errs.append("ssh login1")
        report("BSUB_OK" in out, "bsub available on login1")
        report("ENV_OK" in out, "conda env eval-data-format-podman on the cluster")
        report("GROUPS_OK" in out, "/groups mounted on login1")
        report("NRS_OK" in out, "/nrs mounted on login1 (mouseland, zhang2025 data)")

    print()
    if errs:
        print(f"{len(errs)} check(s) FAILED", file=sys.stderr)
    else:
        print(f"all checks passed — ready to submit "
              f"{len(discover_tasks())} tasks x {len(AGENTS)} agents x {DEFAULT_TRIALS} trials "
              f"= {len(discover_tasks()) * len(AGENTS) * DEFAULT_TRIALS} jobs")
    return not errs


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", nargs="*", help="task names (default: all *_minimal)")
    parser.add_argument("--agents", nargs="*", default=AGENTS, help=f"default: {AGENTS}")
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--start", type=int, default=0, help="skip the first N jobs")
    parser.add_argument("--limit", type=int, default=None, help="submit at most N jobs")
    parser.add_argument("--check", action="store_true", help="validate only")
    parser.add_argument("--dry-run", "-n", action="store_true", help="print, do not submit")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check() else 1)

    tasks = args.tasks or discover_tasks()
    jobs = [(t, a, i) for t in tasks for a in args.agents
            for i in range(1, args.trials + 1)]
    jobs = jobs[args.start:]
    if args.limit is not None:
        jobs = jobs[:args.limit]

    if not args.dry_run:
        CLUSTER_LOG_DIR.mkdir(parents=True, exist_ok=True)
        CLUSTER_JOBS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{'Would submit' if args.dry_run else 'Submitting'} {len(jobs)} jobs "
          f"to {QUEUE} (-n {SLOTS} -gpu num={GPUS} -W {WALL})")
    failed = 0
    for task, agent, trial in jobs:
        job_name, bsub_cmd, _ = build_job(task, agent, trial)
        if args.dry_run:
            print(f"  {bsub_cmd}")
            continue
        rc = submit(bsub_cmd)
        if rc != 0:
            failed += 1
            print(f"  FAILED ({rc}): {job_name}", file=sys.stderr)

    if not args.dry_run:
        print(f'\nTrack with: ssh login1 \'bash -l -c "bjobs -J \\"hb_*\\""\'')
        if failed:
            print(f"{failed} submission(s) failed", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
