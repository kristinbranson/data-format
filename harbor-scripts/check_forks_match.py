#!/usr/bin/env python3
"""Check the terminal-bench-science versions of the tasks against data-format.

Each benchmark task also exists as a terminal-bench-science task on its own branch,
neurodata-reuse-<name>, and the two copies share grading code, decoder scripts, reference
solutions, prompts and reference statistics. Nothing else keeps them in step, so a fix made
in one repository silently misses the other. This reports every difference.

A fork is compared with the data-format task it corresponds to: <task>_datalimit for the
tasks whose data was reduced, <task>_minimal for the rest (the forks use the minimal prompt
on the datalimit data, which for those tasks is the full data).

Compared, per task:
    grading code      tests/test_outputs.py, tests/write_reward_file.py   vs template-harbor-task/tests/
    decoder scripts   environment/ and tests/ decoder.py, train_decoder.py
    reference         solution/convert_data.py
    packages          environment/Dockerfile install lines (the fork's part above its
                      BYTE-IDENTICAL marker, data-format's part above its grading section)
    prompt            instruction.md, apart from the lines in PROMPT_ONLY_HERE / PROMPT_ONLY_FORK
    statistics        tests/reference_stats_full.json: data_summary equal, replicate mean
                      accuracies within ACCURACY_TOLERANCE
and across the forks: the grading files and tests/test.sh identical in all of them.

Differences deliberately ignored, each for the reason given where it is defined:
canary lines, and the prompt lines listed below. Nothing else is ignored -- a long
exception list is how a real difference hides.

Usage:
    python check_forks_match.py              # every task, forks read from their branches
    python check_forks_match.py sosa2024     # one task
    python check_forks_match.py --worktree   # read the forks' checked-out working files
    python check_forks_match.py --verbose    # print a diff for each difference

Exits 1 if anything differs.
"""

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "harbor-tasks"
TEMPLATE_TESTS = REPO_ROOT / "template-harbor-task" / "tests"
# The terminal-bench-science clone that holds every neurodata-reuse-<name> branch.
TBSCIENCE_REPO = REPO_ROOT.parent / "terminal-bench-science"
# Per-task working clones, for --worktree.
WORKTREE = Path.home() / "tb-science-{fork}"

# data-format task -> terminal-bench-science name
FORK_OF = {"allen2p": "allen2p", "hasnain2024": "hasnain2024", "lee2025": "lee2025",
           "majnik2025": "majnik2025", "map": "chen2024", "mouseland": "zhong2025",
           "sosa2024": "sosa2024", "zhang2025": "zhang2025"}
FORK_TASK_PATH = "tasks/life-sciences/neuroscience/neurodata-reuse-{fork}"

# terminal-bench-science requires a canary GUID in every file; data-format files have none.
CANARY_MARKER = "harbor-canary GUID"

GRADING_FILES = ["tests/test_outputs.py", "tests/write_reward_file.py"]
DECODER_FILES = ["environment/decoder.py", "environment/train_decoder.py",
                 "tests/decoder.py", "tests/train_decoder.py"]
ACROSS_FORK_FILES = GRADING_FILES + ["tests/test.sh"]

# Where each Dockerfile's package installation ends.
FORK_DOCKERFILE_END = "# EVERYTHING ABOVE THIS LINE MUST STAY BYTE-IDENTICAL"
HERE_DOCKERFILE_END = "# Grading runs in this same container"

# Prompt lines present only in data-format, by line prefix, and why:
PROMPT_ONLY_HERE = [
    # data-format grades decisions with LLM judges; the forks have no judges
    "- We will assess your work in two ways.",
    "7. Each decision about how to load, filter, process, align, and save the data",
    # data-format kept the preprint's wording for the data-reuse context
    "- Your goal is to load and reformat data from a neuroscience paper",
    "- To test that you have done this successfully, you will use provided code",
    "- All datasets must be converted into the following Python dictionary structure",
    # data-format kept the rule under the title
    "---",
]
# Prompt lines present only in the forks, by line prefix, and why:
PROMPT_ONLY_FORK = [
    "- We will assess your correctness by comparing statistics",   # outcome-only grading
    "- Reusing published data for a new computational analysis",   # data-reuse wording
    "- You are provided sample code to train a neural decoder",
    "- Many published datasets will be converted into the same format",
    "- Required Python dictionary structure:",
    "You have ",                                                   # tb-science's timeout sentence
]

# Largest allowed difference between the two copies' replicate mean accuracies. Both are
# 20-split means on the same data, so they should agree closely; GPU nondeterminism moves
# them slightly.
ACCURACY_TOLERANCE = 0.01


def fork_reader(fork: str, worktree: bool):
    """Return a function reading one of a fork's task files as text (None if absent).

    Args:
        fork: terminal-bench-science task name, e.g. 'chen2024'.
        worktree: read ~/tb-science-<fork> working files instead of the committed branch.
    """
    task_path = FORK_TASK_PATH.format(fork=fork)
    if worktree:
        root = Path(str(WORKTREE).format(fork=fork)) / task_path

        def read(rel):
            path = root / rel
            return path.read_text() if path.is_file() else None
        return read

    branch = f"neurodata-reuse-{fork}"

    def read(rel):
        result = subprocess.run(["git", "-C", str(TBSCIENCE_REPO), "show", f"{branch}:{task_path}/{rel}"],
                                capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else None
    return read


def without_canary(text):
    """Text with canary lines removed, or None."""
    if text is None:
        return None
    return "".join(l for l in text.splitlines(keepends=True) if CANARY_MARKER not in l)


def read_here(path: Path):
    """A data-format file as text, or None if absent."""
    return path.read_text() if path.is_file() else None


def install_block(text, end_marker):
    """The part of a Dockerfile above `end_marker`, trailing blank lines dropped; None if absent."""
    if text is None or end_marker not in text:
        return None
    return without_canary(text[:text.index(end_marker)]).rstrip() + "\n"


def prompt_core(text, drop_prefixes):
    """Prompt lines for comparison: canary, listed lines, trailing spaces and blank lines removed."""
    if text is None:
        return None
    lines = []
    for line in without_canary(text).splitlines():
        line = line.rstrip()
        if not line or any(line.startswith(prefix) for prefix in drop_prefixes):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def compare_text(label, here, fork, verbose):
    """One comparison result line (and optional diff) for two texts."""
    if here is None or fork is None:
        missing = "data-format" if here is None else "fork"
        return [f"differs  {label}  (missing in {missing})"]
    if here == fork:
        return []
    out = [f"differs  {label}"]
    if verbose:
        out += ["         " + l.rstrip("\n") for l in difflib.unified_diff(
            here.splitlines(True), fork.splitlines(True), "data-format", "fork", n=1)]
    return out


def compare_stats(here_text, fork_text):
    """Compare reference statistics. Returns a list of difference descriptions."""
    if here_text is None or fork_text is None:
        return ["missing in " + ("data-format" if here_text is None else "fork")]
    here, fork = json.loads(here_text), json.loads(fork_text)
    problems = []
    if here.get("data_summary") != fork.get("data_summary"):
        keys = sorted(k for k in set(here["data_summary"]) | set(fork["data_summary"])
                      if here["data_summary"].get(k) != fork["data_summary"].get(k))
        problems.append(f"data_summary differs in {keys}")
    here_mean = here.get("validation_balanced_accuracy_mean") or {}
    fork_mean = fork.get("validation_balanced_accuracy_mean") or {}
    if set(here_mean) != set(fork_mean):
        problems.append(f"replicate mean accuracy outputs differ: {sorted(here_mean)} vs {sorted(fork_mean)}")
    for name in sorted(set(here_mean) & set(fork_mean)):
        if abs(here_mean[name] - fork_mean[name]) > ACCURACY_TOLERANCE:
            problems.append(f"mean accuracy of {name}: {here_mean[name]:.4f} vs {fork_mean[name]:.4f}")
    return problems


def check_task(task, worktree, verbose):
    """All differences between one data-format task and its fork."""
    fork = FORK_OF[task]
    read_fork = fork_reader(fork, worktree)
    here_dir = TASKS_DIR / f"{task}_datalimit"
    if not here_dir.is_dir():
        here_dir = TASKS_DIR / f"{task}_minimal"
    lines = []
    for rel in GRADING_FILES:
        lines += compare_text(rel, read_here(TEMPLATE_TESTS / Path(rel).name),
                              without_canary(read_fork(rel)), verbose)
    for rel in DECODER_FILES + ["solution/convert_data.py"]:
        lines += compare_text(rel, read_here(here_dir / rel), without_canary(read_fork(rel)), verbose)
    lines += compare_text("environment/Dockerfile (package installation)",
                          install_block(read_here(here_dir / "environment/Dockerfile"), HERE_DOCKERFILE_END),
                          install_block(read_fork("environment/Dockerfile"), FORK_DOCKERFILE_END), verbose)
    lines += compare_text("instruction.md",
                          prompt_core(read_here(here_dir / "instruction.md"), PROMPT_ONLY_HERE),
                          prompt_core(read_fork("instruction.md"), PROMPT_ONLY_FORK), verbose)
    lines += [f"differs  tests/reference_stats_full.json: {p}" for p in
              compare_stats(read_here(here_dir / "tests/reference_stats_full.json"),
                            read_fork("tests/reference_stats_full.json"))]
    return here_dir.name, fork, lines


def check_across_forks(tasks, worktree):
    """Files that must be identical in every fork. Returns difference lines."""
    lines = []
    for rel in ACROSS_FORK_FILES:
        texts = {FORK_OF[t]: without_canary(fork_reader(FORK_OF[t], worktree)(rel)) for t in tasks}
        distinct = {}
        for fork, text in texts.items():
            distinct.setdefault(text, []).append(fork)
        if len(distinct) > 1:
            groups = "; ".join(", ".join(forks) for forks in distinct.values())
            lines.append(f"differs  {rel}: {len(distinct)} versions ({groups})")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*", help="data-format task names (default: all eight)")
    parser.add_argument("--worktree", action="store_true",
                        help="read ~/tb-science-<fork> working files instead of the branches")
    parser.add_argument("--verbose", action="store_true", help="print a diff for each difference")
    args = parser.parse_args()
    tasks = args.tasks or sorted(FORK_OF)

    failed = False
    for task in tasks:
        here, fork, lines = check_task(task, args.worktree, args.verbose)
        failed |= bool(lines)
        print(f"{'ok  ' if not lines else 'FAIL'} {here} vs tb-science {fork}")
        for line in lines:
            print(f"       {line}")
    if len(tasks) > 1:
        lines = check_across_forks(tasks, args.worktree)
        failed |= bool(lines)
        print(f"{'ok  ' if not lines else 'FAIL'} files shared by all forks")
        for line in lines:
            print(f"       {line}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
