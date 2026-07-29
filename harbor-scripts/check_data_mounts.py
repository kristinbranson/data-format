#!/usr/bin/env python3
"""Verify each task's /app/data bind source exists and holds data, before running.

The tasks' own tests already assert this (test_data_dir_accessible in
tests/test_outputs.py), but they run in the verifier -- i.e. after the agent has
already spent its whole timeout. The 2026-07-27 cluster sweep is the cautionary
case: 47 trials ran to completion against an empty /app/data, because compose
resolved the then-relative mount inside the harbor checkout and the container
runtime silently CREATED the missing source. This is the same check, moved to
the host and to before the run, where it costs seconds instead of a sweep.

Reads the mount out of each task's docker-compose.yaml rather than hardcoding a
task -> dataset mapping, so a new task is covered the moment its compose file is.

Usage:
    python check_data_mounts.py                  # every task
    python check_data_mounts.py sosa2024 debug   # only these
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "harbor-tasks"

# A compose volume line, e.g.
#   - "${DATA_ROOT:?...}/sosa2024:/app/data:ro"
# Group `source` is the host side, `target` the container side. Both the quotes
# and the trailing :ro / :rw mode are optional in the compose format.
VOLUME_RE = re.compile(
    r'^\s*-\s*"?(?P<source>[^":]*?(?:\$\{[^}]*\})?[^":]*?):(?P<target>/app/data[^":]*?)'
    r'(?::(?P<mode>ro|rw))?"?\s*$'
)

# ${DATA_ROOT} or ${DATA_ROOT:?message} -- the `:?` form is what the compose files
# use so an unset variable fails loudly rather than mounting an empty directory.
VAR_RE = re.compile(r"\$\{(?P<name>\w+)(?::[?-][^}]*)?\}")


def substitute(source: str, env: dict[str, str]) -> tuple[str | None, str | None]:
    """Expand ${VAR} references in a compose volume source.

    Args:
        source: host side of a compose volume entry, possibly containing ${VAR}.
        env: mapping to resolve variables from (normally os.environ).

    Returns:
        (expanded, error). `expanded` is the resolved path, or None if a variable
        was unset, in which case `error` names it. Exactly one is None.
    """
    missing: list[str] = []

    def replace(match: re.Match) -> str:
        name = match["name"]
        if name not in env or not env[name]:
            missing.append(name)
            return ""
        return env[name]

    expanded = VAR_RE.sub(replace, source)
    if missing:
        return None, f"{', '.join(sorted(set(missing)))} is unset in the environment"
    return expanded, None


def data_mounts(compose_path: Path) -> list[str]:
    """Return the host-side sources of every /app/data mount in a compose file.

    Args:
        compose_path: path to a task's environment/docker-compose.yaml.

    Returns:
        List of unexpanded host paths (may contain ${VAR}). Empty if the task
        mounts nothing at /app/data, which is legitimate for a task whose data is
        baked into the image.
    """
    sources = []
    for line in compose_path.read_text().splitlines():
        match = VOLUME_RE.match(line)
        if match:
            sources.append(match["source"])
    return sources


def first_file_under(root: Path, max_entries: int = 200_000) -> Path | None:
    """Return the first regular file found beneath `root`, or None if there is none.

    Walks breadth-first and stops at the first hit, so the common case costs one
    directory read rather than a full traversal -- these trees reach tens of
    thousands of files (zhang2025's ONE cache) and live on NFS.

    Args:
        root: directory to search. Symlinks are followed, since several dataset
            directories are symlinks into /nrs.
        max_entries: give up after visiting this many entries, so a pathological
            tree of empty directories cannot hang a pre-flight check.

    Returns:
        Path of the first file found, or None if the tree holds no files (or the
        budget ran out, which is reported as "no files" -- the conservative
        answer for a check whose job is to refuse to start).
    """
    queue = [root]
    visited = 0
    while queue:
        current = queue.pop(0)
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            visited += 1
            if visited > max_entries:
                return None
            if entry.is_file():  # follows symlinks
                return Path(entry.path)
            if entry.is_dir():
                queue.append(Path(entry.path))
    return None


def check(task: str, env: dict[str, str]) -> list[str]:
    """Check one task's data mounts.

    Args:
        task: task directory name under harbor-tasks/.
        env: environment used to expand ${VAR} in the compose source.

    Returns:
        List of human-readable problems; empty means the task is fine. Prints one
        status line per mount as a side effect.
    """
    compose_path = TASKS_DIR / task / "environment" / "docker-compose.yaml"
    if not compose_path.is_file():
        return [f"{task}: no {compose_path.relative_to(REPO_ROOT)}"]

    problems = []
    for source in data_mounts(compose_path):
        expanded, error = substitute(source, env)
        if error:
            problems.append(f"{task}: {error}")
            print(f"  FAIL  {task:<20} {error}")
            continue

        path = Path(expanded)
        # Resolved, because several data dirs are symlinks into /nrs and a bare
        # exists() on a dangling link is a confusing way to fail.
        if not path.exists():
            problems.append(f"{task}: {path} does not exist")
            print(f"  FAIL  {task:<20} missing: {path}")
        elif not path.is_dir():
            problems.append(f"{task}: {path} is not a directory")
            print(f"  FAIL  {task:<20} not a directory: {path}")
        else:
            # An actual file, not just a directory entry: a nested mount like
            # allen2p's leaves an intermediate directory behind, so counting
            # entries would pass on a tree of empty directories.
            first_file = first_file_under(path)
            if first_file is None:
                problems.append(f"{task}: {path} contains no files")
                print(f"  FAIL  {task:<20} NO FILES: {path}")
            else:
                print(f"  ok    {task:<20} {path}")
                print(f"        {' ':<20} e.g. {first_file}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*",
                        help="task names to check (default: all tasks)")
    args = parser.parse_args()

    tasks = args.tasks or sorted(
        p.parent.parent.name
        for p in TASKS_DIR.glob("*/environment/docker-compose.yaml"))
    if not tasks:
        sys.exit("no tasks found")

    problems = []
    for task in tasks:
        problems.extend(check(task, os.environ))

    if problems:
        print(f"\n{len(problems)} data mount problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        print("\nAn empty or missing bind source is CREATED by the container runtime\n"
              "and mounted without error, so the run would silently produce nothing.")
        sys.exit(1)
    print(f"\nall data mounts ok ({len(tasks)} task(s))")


if __name__ == "__main__":
    main()
