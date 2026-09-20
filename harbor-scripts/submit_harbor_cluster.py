#!/usr/bin/env python3
"""Submit harbor trials to the Janelia cluster.

One bsub job per (task, agent, trial), each taking a whole gpu_l4_large node:
64 slots + 1 GPU is an entire l4_larges host (64 physical cores, 1006 GB, one
L4). Whole-node allocation is deliberate — podman on this cluster does not
enforce --cpus/--memory (measured: /sys/fs/cgroup/memory.max reads "max"), so
owning the node is the only way to bound a trial.

Usage:
    python submit_harbor_cluster.py --check          # validate, submit nothing
    python submit_harbor_cluster.py --dry-run        # print the bsub commands
    python submit_harbor_cluster.py                  # every task, both variants
    python submit_harbor_cluster.py --minimal        # only the minimal-prompt tasks
    python submit_harbor_cluster.py --maximal        # only the full-prompt tasks
    python submit_harbor_cluster.py --tasks sosa2024_minimal --agents claude --trials 1
    python submit_harbor_cluster.py --start 0 --limit 1

Scope defaults to every benchmark task in both prompt variants. <task> and
<task>_minimal read the SAME dataset and differ only in how much the instruction
tells the agent, so a full sweep is 2x the jobs for the same data. `debug` is a
harness smoke test, not a benchmark task, so it is never swept -- name it
explicitly (--tasks debug) to run it.
"""

import argparse
import json
import re
import os
import json
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

# Queue geometry, from the Janelia cluster docs (GPU Queues table). The slot count
# is each queue's slots-per-GPU ratio, so requesting it alongside -gpu "num=1" asks
# for exactly one GPU's share and LSF never raises its over-ratio prompt.
#
# These are NOT interchangeable between queues, which is why this is a table rather
# than one constant: gpu_l4_large hosts carry 64 slots and gpu_t4 hosts 48, so a
# 64-slot request on gpu_t4 cannot be satisfied by any node in the queue and the job
# sits PENDING forever rather than failing.
#
# For the single-GPU queues (gpu_l4_large, gpu_t4) one GPU's share IS the whole node,
# which is deliberate: podman on this cluster does not enforce --cpus/--memory
# (measured: /sys/fs/cgroup/memory.max reads "max"), so owning the node is the only
# way to bound a trial. The dense queues (gpu_l4, gpu_l4_16) put several GPUs on a
# node and give no such isolation -- usable, but trials will contend.
QUEUE_SPECS = {
    # queue:        (slots per GPU, RAM per slot in GB)
    "gpu_l4_large": (64, 15),
    "gpu_t4":       (48, 15),
    "gpu_l4":       (8, 15),
    "gpu_l4_16":    (16, 15),
    "gpu_a100":     (12, 40),
    "gpu_h100":     (12, 40),
    "gpu_h200":     (12, 40),
}
DEFAULT_QUEUE = "gpu_l4_large"
GPUS = 1


def queue_geometry(queue: str, slots: int | None = None) -> tuple[int, int]:
    """Return the slot count and per-slot memory to request on a queue.

    Args:
        queue: LSF GPU queue name; must be a key of QUEUE_SPECS.
        slots: explicit slot count that overrides the queue's ratio, or None to
            use the ratio. Overriding is for the rare case of wanting less than a
            whole node; going above the ratio makes the job unschedulable.

    Returns:
        (slots, ram_per_slot_gb) -- the second is informational, used to report
        the resulting node memory.
    """
    ratio_slots, ram_per_slot_gb = QUEUE_SPECS[queue]
    return (ratio_slots if slots is None else slots), ram_per_slot_gb


# Long enough that every per-phase timeout in task.toml can expire inside it:
# build_timeout_sec 0.5 h, [agent] timeout_sec 24 h, [verifier] timeout_sec 4 h, which is
# 28.5 h, plus headroom.
#
# The two kinds of timeout are not interchangeable. harbor's agent timeout stops the agent
# and still runs the verifier, so the trial is graded and records that the agent ran out of
# time -- a result. LSF's wall clock kills the job outright: no verifier, no judges, no
# reward file, and the whole trial is lost after being paid for in full. At 24:00 the wall
# was no longer than the agent's own limit, so the agent timeout could never fire first and
# every runaway became the second kind.
#
# For scale, observed agent+verify is 1.25 h median and 6.06 h max (mouseland), and the two
# judges add roughly another hour. Nothing approaches these limits; the point is which
# failure you get when something does. gpu_* queues allow up to 14 days.
WALL = "29:00"

# Must resolve identically on the workstation and on compute nodes, so /groups
# rather than $HOME (workstation /home/<user>@hhmi.org vs cluster
# /groups/branson/home/<user>).
# Which harbor a run uses, and so which conda env, comes from the versions config rather
# than from here; run_harbor.sh reads the same field. Kept in step with its gate.
HARBOR_CONDA_ENVS = {
    "0.23.0": "eval-data-format-podman-023",
    "0.1.45": "eval-data-format-podman",
}
DEFAULT_HARBOR_VERSION = "0.1.45"  # a config predating the field predates 0.23.0


def harbor_version_from_config(versions: Path | None) -> str:
    """Return the harbor version a run with this config would use.

    Args:
        versions: explicit config path, or None to take the newest dated one.

    Returns:
        The config's harbor_version, or DEFAULT_HARBOR_VERSION when it names none.
    """
    if versions is None:
        found = sorted((REPO_ROOT / "harbor-scripts").glob("config_*.json"))
        if not found:
            return DEFAULT_HARBOR_VERSION
        versions = found[-1]
    try:
        return json.loads(Path(versions).read_text()).get(
            "harbor_version", DEFAULT_HARBOR_VERSION)
    except Exception:
        return DEFAULT_HARBOR_VERSION


def conda_env_for_harbor(harbor_version: str) -> str:
    """Return the conda env that carries a given harbor, or the 0.1.45 env if unknown."""
    return HARBOR_CONDA_ENVS.get(harbor_version, HARBOR_CONDA_ENVS[DEFAULT_HARBOR_VERSION])


CLUSTER_LOG_DIR = Path("/groups/branson/home/bransonk/cluster_logs/harbor")
CLUSTER_JOBS_DIR = Path("/groups/branson/home/bransonk/harbor-cluster-jobs")

# Default arms come from the versions config rather than being hardcoded, so adding
# an arm there (a new agent, or the same agent on a different model) is enough to
# include it in a sweep. Falls back to the CLI arms if no config is present.
DEFAULT_AGENTS = ["claude", "codex"]


def config_arms() -> list[str]:
    """Arm names defined in the newest versions config, or DEFAULT_AGENTS."""
    cfg = newest_versions_config()
    if cfg is None:
        return DEFAULT_AGENTS
    try:
        return sorted(json.loads(cfg.read_text())["tools"])
    except (KeyError, ValueError, OSError):
        return DEFAULT_AGENTS
DEFAULT_TRIALS = 3


# Task directories that are not benchmark tasks and so never enter a sweep by
# default. `debug` is a harness smoke test on a small sosa2024 subset -- useful to
# submit deliberately (--tasks debug) after changing the environment, wasteful to
# submit as part of a sweep, since it takes a whole node like any other job.
NON_BENCHMARK_TASKS = {"debug"}

# Suffix marking the minimal-PROMPT variant of a task. The two variants read the
# SAME dataset -- only instruction.md, task.toml and tests/instruction_reference.md
# differ (sosa2024: 877 instruction lines vs 219). They measure how much the
# prompt's detail matters, not how much data the agent gets, so neither variant is
# cheaper to run than the other.
MINIMAL_SUFFIX = "_minimal"

# Suffix marking the datalimit variant: the minimal-prompt task run on the
# 50 GB-capped data. Only tasks whose data was actually reduced have one; for the rest,
# the <task>_minimal trials serve as the datalimit arm, so they are not rerun.
DATALIMIT_SUFFIX = "_datalimit"

# Suffix marking the API variant: the same task and the same data, with the agent required
# to read the files through the format's own library rather than parsing them directly --
# sosa2024_api demands pynwb instead of h5py, and carries pynwb's documentation in the
# image. It varies which interface the agent is told to use, where _minimal varies how much
# the prompt says and _datalimit how much data there is.
API_SUFFIX = "_api"


def discover_tasks(scope: str = "all") -> list[str]:
    """Return the benchmark task directory names for a scope.

    Args:
        scope: which variants to include --
            "all"       maximal and minimal prompt of every task on full data (the
                        default sweep),
            "minimal"   only the minimal-prompt <task>_minimal directories,
            "maximal"   only the full-prompt <task> directories,
            "datalimit" only the datalimit <task>_datalimit directories,
            "api"       only the <task>_api directories.

    Returns:
        Sorted task directory names, excluding NON_BENCHMARK_TASKS. A maximal task is one
        with a <task>_minimal twin, which keeps every variant out of the maximal list
        without naming them: an _api or _datalimit directory has no _minimal twin, so
        neither can be swept as though it were the full-prompt task.

        "all" is maximal plus minimal, so neither _datalimit nor _api joins a default
        sweep. Both vary a different dimension from the prompt detail those two compare,
        so their rows are not comparable to the ones they would sit beside. Ask for them
        by scope, or name them with --tasks.
    """
    names = sorted(p.name for p in (REPO_ROOT / "harbor-tasks").iterdir()
                   if p.is_dir() and p.name not in NON_BENCHMARK_TASKS)
    minimal = [n for n in names if n.endswith(MINIMAL_SUFFIX)]
    maximal = [n for n in names if n + MINIMAL_SUFFIX in names]
    datalimit = [n for n in names if n.endswith(DATALIMIT_SUFFIX)]
    api = [n for n in names if n.endswith(API_SUFFIX)]
    if scope == "minimal":
        return minimal
    if scope == "maximal":
        return maximal
    if scope == "datalimit":
        return datalimit
    if scope == "api":
        return api
    return sorted(maximal + minimal)


def newest_versions_config() -> Path | None:
    """Return the newest dated harness/model pin config, or None if there is none.

    Configs are named config_<YYYYMMDD>.json so a lexical sort is chronological.
    """
    configs = sorted((REPO_ROOT / "harbor-scripts").glob("config_*.json"))
    return configs[-1] if configs else None


def build_job(task: str, agent: str, trial: int,
              versions: Path | None = None,
              queue: str = DEFAULT_QUEUE,
              slots: int | None = None,
              exclude_hosts: list[str] | None = None) -> tuple[str, str, Path]:
    """Return (job_name, bsub command line, log path) for one trial.

    Args:
        task: harbor task directory name.
        agent: arm name from the versions config (e.g. claude, terminus-opus).
        trial: 1-based repeat number, used only in the job name.
        versions: harness/model pin config to pass through to run_harbor.sh.
            Resolved once by the caller and passed explicitly to every job --
            run_harbor.sh would otherwise pick the newest config itself, so a new
            one appearing mid-sweep would silently split the run across two
            configurations.
        queue: LSF GPU queue; determines the slot count via QUEUE_SPECS.
        slots: explicit slot count overriding the queue's ratio, or None.
        exclude_hosts: node names to keep this job off, or None. A node whose
            /scratch is broken fails every trial in ~13 s, and since LSF then
            frees it and hands it the next pending job, one bad host can eat a
            whole sweep in minutes (h06u02 took out 29 of 48 on 2026-07-28).
    """
    job_name = f"hb_{task}_{agent}_t{trial}"
    log_path = CLUSTER_LOG_DIR / f"{job_name}.log"
    jobs_dir = CLUSTER_JOBS_DIR / job_name

    versions_flag = f" --versions {shlex.quote(str(versions))}" if versions else ""
    # Every job gets its own podman graphroot. The shared store at
    # /scratch/$USER/podman-storage is warm, which is why it was the default, but it is
    # shared SERIALLY: one GPU per node means no two jobs hold a host at once, yet job after
    # job reuses the same store. A job that exits badly leaves it broken, and podman_env.sh
    # rightly refuses to reset a shared store because it cannot prove no sibling is using
    # it -- so the node stays poisoned, fails each new job in under a second, frees itself,
    # and is handed the next one. Three such hosts destroyed 60+ jobs of the 2026-09-19
    # sweeps that way. A private store costs a few minutes of image build per job, which is
    # cheap against losing a whole sweep.
    inner = (
        f"PODMAN_PRIVATE_STORAGE=true "
        f"bash {shlex.quote(str(RUN_HARBOR))} "
        f"--task {shlex.quote(task)} --agent {shlex.quote(agent)} "
        f"--ntrials 1 --nconcurrent 1 --podman --apikeys "
        f"--jobs-dir {shlex.quote(str(jobs_dir))}{versions_flag}"
    )
    n_slots, _ = queue_geometry(queue, slots)
    # LSF has no "exclude host" flag, so exclusion is a resource requirement:
    # every named host must differ from the one the job lands on.
    exclude_flag = ""
    if exclude_hosts:
        conditions = " && ".join(f"hname!='{h}'" for h in exclude_hosts)
        exclude_flag = f'-R "select[{conditions}]" '
    bsub = (
        f'bsub -n {n_slots} -gpu "num={GPUS}" -q {queue} -W {WALL} '
        f'{exclude_flag}'
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


def check(scope: str = "all", queue: str = DEFAULT_QUEUE,
          slots: int | None = None) -> bool:
    errs = []
    if not RUN_HARBOR.is_file():
        errs.append(f"missing {RUN_HARBOR}")
    def report(ok, label, detail=""):
        print(f"  [{'OK  ' if ok else 'FAIL'}] {label}{'  ' + detail if detail else ''}")
        if not ok:
            errs.append(label)

    n_slots, ram_per_slot_gb = queue_geometry(queue, slots)
    print(f"queue {queue}: {n_slots} slots x {ram_per_slot_gb} GB = "
          f"{n_slots * ram_per_slot_gb} GB, {GPUS} GPU, -W {WALL}\n")

    # --- local ---
    report(RUN_HARBOR.is_file(), "run_harbor.sh present", str(RUN_HARBOR))
    cfg = newest_versions_config()
    report(cfg is not None, "harness/model pin config present",
           str(cfg) if cfg else "(none: versions would be unpinned)")
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

    for task in discover_tasks(scope):
        d = REPO_ROOT / "harbor-tasks" / task
        compose = d / "environment" / "docker-compose.yaml"
        ok = (d / "task.toml").is_file() and compose.is_file()
        detail = ""
        if ok:
            # the host side of the bind mount must exist, or the container starts empty
            # Split on the container side, not the first colon: the host side is
            # "${DATA_ROOT:?message}/<dataset>", whose :? default carries a colon of its
            # own, so splitting on the first one yields the literal "${DATA_ROOT and every
            # task reports a mount that does not exist. Expand DATA_ROOT the way
            # run_harbor.sh does, from the repository root, so the path checked is the one
            # a run would bind.
            data_root = str(REPO_ROOT / "data")
            mounts = [
                re.sub(r"\$\{DATA_ROOT[^}]*\}", data_root,
                       ln.strip()[2:].strip('"').rsplit(":/app/", 1)[0])
                for ln in compose.read_text().splitlines()
                if ln.strip().startswith("- ") and ":/app/" in ln
            ]
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
        # Check the env the run will actually use, not a fixed name: run_harbor.sh picks it
        # from the config's harbor_version, so a hardcoded check would pass while the env the
        # sweep needs was missing -- which is the one thing this check exists to catch.
        env_name = conda_env_for_harbor(harbor_version_from_config(None))
        probe = ("command -v bsub >/dev/null && echo BSUB_OK; "
                 f"[ -x $HOME/miniforge3/envs/{env_name}/bin/harbor ] && echo ENV_OK; "
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
        report("ENV_OK" in out, f"conda env {env_name} on the cluster")
        report("GROUPS_OK" in out, "/groups mounted on login1")
        report("NRS_OK" in out, "/nrs mounted on login1 (mouseland, zhang2025 data)")

    print()
    if errs:
        print(f"{len(errs)} check(s) FAILED", file=sys.stderr)
    else:
        n_tasks = len(discover_tasks(scope))
        print(f"all checks passed — ready to submit "
              f"{n_tasks} tasks ({scope}) x {len(config_arms())} arms x {DEFAULT_TRIALS} trials "
              f"= {n_tasks * len(config_arms()) * DEFAULT_TRIALS} jobs")
    return not errs


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", nargs="*",
                        help="explicit task names; overrides --minimal/--maximal/--datalimit "
                             "and may name a non-benchmark task such as debug "
                             "(default: every benchmark task, both variants)")
    # Mutually exclusive: a sweep is over one prompt variant or both, never a
    # contradictory pair. Both flags write the same `scope` destination.
    scope_group = parser.add_mutually_exclusive_group()
    scope_group.add_argument("--minimal", dest="scope", action="store_const",
                             const="minimal",
                             help="only the minimal-prompt *_minimal tasks")
    scope_group.add_argument("--maximal", dest="scope", action="store_const",
                             const="maximal",
                             help="only the full-prompt tasks (no *_minimal)")
    scope_group.add_argument("--datalimit", dest="scope", action="store_const",
                             const="datalimit",
                             help="only the datalimit *_datalimit tasks")
    scope_group.add_argument("--api", dest="scope", action="store_const",
                             const="api",
                             help="only the *_api tasks (library-required variant)")
    parser.set_defaults(scope="all")
    parser.add_argument("--queue", choices=sorted(QUEUE_SPECS), default=DEFAULT_QUEUE,
                        help=f"LSF GPU queue; sets the slot count from its "
                             f"slots-per-GPU ratio (default: {DEFAULT_QUEUE}). "
                             f"Use a second queue to run arms in parallel with a "
                             f"sweep -- the per-user GPU cap is per queue.")
    parser.add_argument("--slots", type=int, default=None,
                        help="override the queue's slot ratio; going above it "
                             "makes jobs permanently unschedulable")
    parser.add_argument("--exclude-hosts", nargs="*", default=None, metavar="HOST",
                        help="keep jobs off these nodes (e.g. a host with broken "
                             "/scratch, which otherwise fails every job in ~13s "
                             "and burns through the whole pending queue)")
    parser.add_argument("--jobs", nargs="*", default=None, metavar="JOB_NAME",
                        help="submit only these job names (hb_<task>_<arm>_t<N>); "
                             "use to resubmit an exact failed set without "
                             "colliding with trials that are still running")
    arms = config_arms()
    parser.add_argument("--agents", nargs="*", default=arms,
                        help=f"arms from the versions config; default: {arms}")
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--start", type=int, default=0, help="skip the first N jobs")
    parser.add_argument("--limit", type=int, default=None, help="submit at most N jobs")
    parser.add_argument("--versions", type=Path, default=None,
                        help="harness/model pin config (default: newest "
                             "harbor-scripts/config_*.json)")
    parser.add_argument("--check", action="store_true", help="validate only")
    parser.add_argument("--dry-run", "-n", action="store_true", help="print, do not submit")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check(args.scope, args.queue, args.slots) else 1)

    # Resolve once so every job in this sweep gets the same pins, even if a
    # newer config lands while the sweep is still submitting.
    versions = args.versions or newest_versions_config()
    if versions is None:
        print("WARNING: no harbor-scripts/config_*.json found -- harness and "
              "model versions will be unpinned", file=sys.stderr)
    elif not args.dry_run:
        # Apply here, once, before any job starts. The task Dockerfiles cannot
        # read the config and are baked into images built inside the jobs, so a
        # bumped config must reach them first. The jobs themselves only verify --
        # 48 of them share this checkout and would race as writers.
        rc = subprocess.call([sys.executable,
                              str(REPO_ROOT / "harbor-scripts" / "apply_versions.py"),
                              "--versions", str(versions)])
        if rc != 0:
            sys.exit(f"apply_versions.py failed ({rc}); not submitting")

    tasks = args.tasks or discover_tasks(args.scope)
    jobs = [(t, a, i) for t in tasks for a in args.agents
            for i in range(1, args.trials + 1)]
    if args.jobs:
        # Match on the job name build_job() would produce, so the names copied
        # out of a failure report can be pasted straight back in.
        wanted = set(args.jobs)
        jobs = [(t, a, i) for t, a, i in jobs if f"hb_{t}_{a}_t{i}" in wanted]
        missing = wanted - {f"hb_{t}_{a}_t{i}" for t, a, i in jobs}
        if missing:
            sys.exit(f"--jobs named {len(missing)} job(s) outside the selected "
                     f"tasks/agents/trials: {sorted(missing)}")
    jobs = jobs[args.start:]
    if args.limit is not None:
        jobs = jobs[:args.limit]

    if not args.dry_run:
        CLUSTER_LOG_DIR.mkdir(parents=True, exist_ok=True)
        CLUSTER_JOBS_DIR.mkdir(parents=True, exist_ok=True)

    n_slots, _ = queue_geometry(args.queue, args.slots)
    print(f"{'Would submit' if args.dry_run else 'Submitting'} {len(jobs)} jobs "
          f"to {args.queue} (-n {n_slots} -gpu num={GPUS} -W {WALL})")
    print(f"versions: {versions}")
    failed = 0
    for task, agent, trial in jobs:
        job_name, bsub_cmd, _ = build_job(task, agent, trial, versions,
                                          args.queue, args.slots,
                                          args.exclude_hosts)
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
