#!/usr/bin/env python3
"""Collect finished cluster trials into one analysis tree, grouped by task and arm.

Cluster results arrive one bsub job per trial:

    harbor-cluster-jobs/hb_<task>_<arm>_t<N>/<task>/<agent>/<timestamp>_trial1/

so every trial is called trial1 and the trials of one arm are scattered across N
job directories. This regroups them:

    harbor-jobs-new/<task>/<agent_dir>/<timestamp>_trial<K>/

run_harbor.sh already does this shape of move (lines ~280-305), but only inside a
single job at the end of its own run, so it cannot be re-run or applied across
jobs. This can, which also makes it the tool for rescuing trials whose job died
before reorganising.

Only trials with verifier/metrics.json are collected. A trial without one did not
produce a result -- the 2026-07-28 h06u02 crash left 29 such directories, each
with an exception.txt and an empty verifier/ -- and moving those into the analysis
tree would put wreckage where results are expected. Pass --include-failed to take
them anyway.

Moves rather than copies: source and destination are normally the same filesystem,
so this is a rename and costs nothing regardless of trial size (they reach 20 GB).

Usage:
    python collect_cluster_results.py                  # dry run: report, move nothing
    python collect_cluster_results.py --apply          # do it
    python collect_cluster_results.py --tasks sosa2024_minimal --apply
    python collect_cluster_results.py --include-failed --apply
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = Path("/groups/branson/home/bransonk/harbor-cluster-jobs")
DEFAULT_DEST = REPO_ROOT / "harbor-jobs-new"

# Job directory names are hb_<task>_<arm>_t<N>. Task names contain underscores
# (sosa2024_minimal) and arm names contain hyphens (terminus-opus), so the trial
# suffix is the only reliable anchor -- match it from the end.
JOB_DIR_RE = re.compile(r"^hb_(?P<rest>.+)_t(?P<trial>\d+)$")


def arm_to_agent_dir(versions_path: Path | None) -> dict[str, str]:
    """Map each arm name to the directory name its trials should be filed under.

    An arm is an agent plus a model (claude, codex, terminus-opus, terminus-gpt);
    harbor names the output directory after the *agent*, so both terminus arms
    write "terminus-2" and become indistinguishable once they leave their job
    directories.

    The rule: keep harbor's agent name when it identifies the arm uniquely, and
    fall back to the arm name only when it does not. That leaves claude ->
    claude-code and codex -> codex untouched, which matters because
    evaluation/eval/report.py and raters.py match those names literally, while
    splitting terminus-2 into terminus-opus and terminus-gpt.

    Args:
        versions_path: dated config defining the arms, or None to use the newest
            harbor-scripts/config_*.json. Missing or unreadable yields {}, in
            which case callers fall back to the on-disk agent directory name.

    Returns:
        {arm name: directory name}. Empty if no config could be read.
    """
    if versions_path is None:
        configs = sorted((REPO_ROOT / "harbor-scripts").glob("config_*.json"))
        versions_path = configs[-1] if configs else None
    if versions_path is None or not versions_path.is_file():
        return {}
    try:
        tools = json.loads(versions_path.read_text())["tools"]
    except (KeyError, ValueError, OSError):
        return {}

    arms_per_agent: dict[str, list[str]] = collections.defaultdict(list)
    for arm, spec in tools.items():
        harbor_agent = spec.get("harbor_agent")
        if harbor_agent:
            arms_per_agent[harbor_agent].append(arm)

    return {
        arm: (harbor_agent if len(arms) == 1 else arm)
        for harbor_agent, arms in arms_per_agent.items()
        for arm in arms
    }


def find_trials(source: Path) -> list[dict]:
    """Find every reorganised trial directory under a cluster jobs root.

    Args:
        source: directory holding hb_<task>_<arm>_t<N> job directories.

    Returns:
        One dict per trial, with keys:
            path      Path of the trial directory,
            task      task name, from the job directory name,
            arm       arm name, from the job directory name,
            agent     agent directory name harbor used (e.g. claude-code),
            stamp     timestamp string, e.g. 2026-07-28__21-46-08,
            has_metrics  whether verifier/metrics.json exists,
            raw       True if the trial is still where harbor wrote it.

        Both layouts are searched. run_harbor.sh normally moves a finished trial
        out of raw/ into <task>/<agent>/<stamp>_trialN/, but that step does not
        always run -- every terminus job on 2026-07-28 exited 0 with its results
        left in raw/, while claude and codex jobs in the same sweep reorganised
        normally. Keying on verifier/metrics.json instead of on directory position
        means a complete trial is collected wherever it ended up; an in-flight one
        has no metrics.json yet and is skipped, so there is no race with a job
        still writing.
    """
    trials = []
    for job_dir in sorted(p for p in source.iterdir() if p.is_dir()):
        match = JOB_DIR_RE.match(job_dir.name)
        if not match:
            continue
        # <task>_<arm> cannot be split on underscores (task names contain them,
        # e.g. sosa2024_minimal), so take the task from the directory tree and let
        # the arm be whatever remains of the job name.
        rest = match["rest"]

        def arm_for(task: str) -> str:
            return rest[len(task) + 1:] if rest.startswith(task + "_") else ""

        # Reorganised: <job>/<task>/<agent>/<stamp>_trialN/
        for task_dir in sorted(p for p in job_dir.iterdir() if p.is_dir()):
            if task_dir.name == "raw":
                continue
            for agent_dir in sorted(p for p in task_dir.iterdir() if p.is_dir()):
                for trial_dir in sorted(p for p in agent_dir.iterdir() if p.is_dir()):
                    if "_trial" not in trial_dir.name:
                        continue
                    trials.append({
                        "path": trial_dir,
                        "task": task_dir.name,
                        "arm": arm_for(task_dir.name),
                        "agent": agent_dir.name,
                        "stamp": trial_dir.name.split("_trial")[0],
                        "has_metrics": (trial_dir / "verifier" / "metrics.json").is_file(),
                        "raw": False,
                        # Being here at all means run_harbor.sh finished and moved it.
                        "finished": True,
                    })

        # Not reorganised: <job>/raw/<stamp>/<task>__<id>/. The trailing __<id> is
        # harbor's per-trial suffix; the task name itself may contain underscores,
        # so strip only that last segment.
        for stamp_dir in sorted(p for p in (job_dir / "raw").glob("*") if p.is_dir()):
            for trial_dir in sorted(p for p in stamp_dir.iterdir() if p.is_dir()):
                if "__" not in trial_dir.name:
                    continue
                task = trial_dir.name.rsplit("__", 1)[0]
                # The agent name is not in the path here; take it from the config
                # harbor wrote, falling back to the arm.
                agent = arm_for(task)
                config = trial_dir / "config.json"
                if config.is_file():
                    try:
                        agent = (json.loads(config.read_text())
                                 .get("agent", {}).get("name") or agent)
                    except (ValueError, OSError):
                        pass
                trials.append({
                    "path": trial_dir,
                    "task": task,
                    "arm": arm_for(task),
                    "agent": agent,
                    "stamp": stamp_dir.name,
                    "has_metrics": (trial_dir / "verifier" / "metrics.json").is_file(),
                    "raw": True,
                    # harbor writes result.json for the run only once it is done.
                    # metrics.json is NOT a completion marker: pytest creates it and
                    # each LLM judge then merges into it, so it appears well before
                    # the trial ends. Moving a live trial would break the job still
                    # writing to it.
                    "finished": (stamp_dir / "result.json").is_file(),
                })
    return trials


def next_trial_number(dest_dir: Path) -> int:
    """Return the trial number to assign next in a destination directory.

    Continues after whatever is already there, so re-running as a sweep drains
    appends rather than renumbering trials that have already been collected.

    Args:
        dest_dir: harbor-jobs-new/<task>/<agent_dir>, which need not exist.

    Returns:
        1 if the directory is absent or holds no numbered trials, else max+1.
    """
    if not dest_dir.is_dir():
        return 1
    numbers = [
        int(m.group(1))
        for p in dest_dir.iterdir()
        if p.is_dir() and (m := re.search(r"_trial(\d+)$", p.name))
    ]
    return max(numbers) + 1 if numbers else 1


def move(src: Path, dst: Path) -> None:
    """Move a trial directory, preferring a rename.

    os.rename is atomic and instant within a filesystem, which is the normal case
    here (both sides live under /groups) and matters because trials reach 20 GB.
    shutil.move handles the cross-filesystem case by copying.

    Args:
        src: trial directory to move.
        dst: destination path; its parent is created if needed.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(src, dst)
    except OSError:
        shutil.move(str(src), str(dst))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help=f"cluster jobs root (default: {DEFAULT_SOURCE})")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST,
                        help=f"collected results tree (default: {DEFAULT_DEST})")
    parser.add_argument("--apply", action="store_true",
                        help="actually move; without this it is a dry run")
    parser.add_argument("--include-failed", action="store_true",
                        help="also collect trials with no verifier/metrics.json")
    parser.add_argument("--tasks", nargs="*", default=None,
                        help="only these task names (default: all)")
    parser.add_argument("--versions", type=Path, default=None,
                        help="arm config for agent-dir naming (default: newest "
                             "harbor-scripts/config_*.json)")
    args = parser.parse_args()

    if not args.source.is_dir():
        sys.exit(f"source not found: {args.source}")

    agent_dir_for_arm = arm_to_agent_dir(args.versions)
    trials = find_trials(args.source)
    if args.tasks:
        trials = [t for t in trials if t["task"] in args.tasks]

    # Three outcomes, kept apart because they mean different things to the reader:
    # an in-flight trial will be collectable later and needs no action; a finished
    # one with no metrics is a real failure worth resubmitting.
    in_flight = [t for t in trials if not t["finished"]]
    done = [t for t in trials if t["finished"]]
    usable = [t for t in done if t["has_metrics"] or args.include_failed]
    skipped = [t for t in done if not t["has_metrics"] and not args.include_failed]

    # Number within (task, agent_dir), oldest run first, so trial order follows
    # the order the trials actually ran.
    usable.sort(key=lambda t: (t["task"], t["arm"], t["stamp"]))
    counters: dict[tuple[str, str], int] = {}
    moved = already = 0

    print(f"source: {args.source}")
    print(f"dest:   {args.dest}")
    print(f"mode:   {'APPLY' if args.apply else 'dry run (use --apply to move)'}\n")

    for trial in usable:
        # Prefer the config-derived name; fall back to whatever harbor wrote if
        # the arm is not in the config (e.g. an old job dir, or oracle).
        agent_dir = agent_dir_for_arm.get(trial["arm"], trial["agent"])
        key = (trial["task"], agent_dir)
        dest_dir = args.dest / trial["task"] / agent_dir
        if key not in counters:
            counters[key] = next_trial_number(dest_dir)
        number = counters[key]

        dst = dest_dir / f"{trial['stamp']}_trial{number}"
        if dst.exists():
            already += 1
            print(f"  have   {trial['task']}/{agent_dir}/{dst.name}")
            continue

        counters[key] = number + 1
        moved += 1
        rel_src = trial["path"].relative_to(args.source)
        print(f"  {'move  ' if args.apply else 'would '} {rel_src}")
        print(f"         -> {trial['task']}/{agent_dir}/{dst.name}")
        if args.apply:
            move(trial["path"], dst)

    print(f"\n{moved} trial(s) {'moved' if args.apply else 'to move'}, "
          f"{already} already collected")
    if in_flight:
        print(f"{len(in_flight)} still running (no result.json yet) -- left alone, "
              f"re-run this once they finish")
        for task, n in sorted(collections.Counter(t["task"] for t in in_flight).items()):
            print(f"    {task}: {n}")
    if skipped:
        print(f"{len(skipped)} FAILED: finished with no verifier/metrics.json "
              f"(--include-failed to take them anyway)")
        for task, n in sorted(collections.Counter(t["task"] for t in skipped).items()):
            print(f"    {task}: {n}")


if __name__ == "__main__":
    main()
