#!/usr/bin/env python3
"""Check the file pairs a neurodata-reuse task must keep in sync.

Several files exist twice in each task: once where the agent sees them
(instruction.md, environment/) and once where the verifier and judges see them
(tests/). Nothing in the task or in terminal-bench-science's CI compares them, and
each half is individually valid, so drift produces no error anywhere -- it just
silently changes what the agent is graded against.

Both known instances were found by accident, months apart:

  * instruction.md and tests/instruction_reference.md drifted twice. The judges grade
    the agent against the tests/ copy, so a stale one grades against instructions the
    agent never received.
  * solution/convert_data.py and tests/reference_convert_data.py drifted when the
    fetch marker moved out of the release directory. The solution was updated, the
    reference was not, so the judges read a path that had not existed for weeks.

Run this before committing a task, and after any edit to a file listed below.

Usage:
    python3 check_task_pairs.py <task-dir> [<task-dir> ...]

Exits 1 if any pair differs.
"""

import argparse
import hashlib
import pathlib
import re
import tomllib
import sys

# The canary script deliberately stamps only the tests/ copy of a shared file: a
# canary in the agent-visible copy would be a hint. Lines matching this are dropped
# from both sides before comparing, so that intended difference is not reported.
CANARY_MARKER = "harbor-canary GUID"

# (agent-visible path, verifier-visible path). Every pair must be identical once
# canary lines are removed. Add to this list rather than special-casing a diff:
# a whitelisted exception is how a real difference hides.
PAIRS = [
    ("instruction.md", "tests/instruction_reference.md"),
    ("solution/convert_data.py", "tests/reference_convert_data.py"),
    ("environment/decoder.py", "tests/decoder.py"),
    ("environment/train_decoder.py", "tests/train_decoder.py"),
]

# environment/Dockerfile and tests/Dockerfile diverge on purpose below a marker line:
# the verifier image adds grading dependencies and the judge CLIs. Only the prefix
# above that line must match, and it must match BYTE for byte -- docker keys RUN
# layers on instruction text, so an identical prefix is what makes the second image
# reuse the first's layers instead of rebuilding torch. Diverging also silently
# diverges the numerics, since the decoder trains in the verifier.
DOCKERFILE_MARKER = "BYTE-IDENTICAL"


def normalized(path):
    """Read `path`, dropping canary lines.

    Args:
        path: pathlib.Path to read.

    Returns:
        str with canary lines removed, or None if the file does not exist.
    """
    if not path.is_file():
        return None
    return "".join(l for l in path.read_text().splitlines(keepends=True)
                   if CANARY_MARKER not in l)


def dockerfile_prefix(path):
    """Return the shared prefix of a Dockerfile, up to the divergence marker.

    Trailing blank lines are stripped so that whitespace before the marker comment
    does not count as a difference.

    Args:
        path: pathlib.Path to a Dockerfile.

    Returns:
        str prefix, or None if the file does not exist.
    """
    if not path.is_file():
        return None
    lines = path.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if DOCKERFILE_MARKER in line:
            lines = lines[:i]
            break
    while lines and not lines[-1].strip():
        lines.pop()
    return "".join(lines)


def check_record_destination(task_dir):
    """Check that the trial record has exactly one home.

    Two settings decide where the agent's output is preserved, and they have to agree:

      task.toml [verifier] environment_mode
        "separate" -> harbor tars /app into the verifier, so the `artifacts` block is
                      the record and tests/test.sh must NOT snapshot (it would copy the
                      artifact copy a second time).
        "shared"   -> nothing is transferred, so there is no artifacts block and the
                      snapshot in tests/test.sh IS the record.

      tests/test.sh VERIFIER_SHARES_AGENT_CONTAINER
        mirrors that choice, 1 for shared and 0 for separate.

    The dangerous combination is shared mode with the flag at 0 and no artifacts block:
    the trial then records nothing at all, and nothing errors. Duplication (separate
    with the flag at 1) is merely wasteful, so it is reported but described as such.

    Args:
        task_dir: pathlib.Path of the directory holding task.toml.

    Returns:
        list of str, one per problem found.
    """
    problems = []
    toml_path = task_dir / "task.toml"
    test_sh = task_dir / "tests" / "test.sh"
    if not toml_path.is_file() or not test_sh.is_file():
        return problems

    config = tomllib.loads(toml_path.read_text())
    # Harbor's default is shared when the key is absent.
    mode = config.get("verifier", {}).get("environment_mode", "shared")
    has_artifacts = "artifacts" in config

    match = re.search(r"^VERIFIER_SHARES_AGENT_CONTAINER=(\d)", test_sh.read_text(),
                      re.MULTILINE)
    if match is None:
        problems.append(
            "tests/test.sh: no VERIFIER_SHARES_AGENT_CONTAINER flag, so which of the "
            "artifacts block and the snapshot holds the record is unstated")
        return problems
    flag = int(match.group(1))

    expected_flag = 1 if mode == "shared" else 0
    if flag != expected_flag:
        problems.append(
            f'environment_mode = "{mode}" but VERIFIER_SHARES_AGENT_CONTAINER={flag} '
            f"(expected {expected_flag})")

    if mode == "shared" and has_artifacts:
        problems.append(
            "shared mode with an artifacts block: the verifier reads /app directly, so "
            "the archive duplicates the snapshot")
    if mode == "separate" and not has_artifacts:
        problems.append(
            "separate mode with no artifacts block: the verifier would grade an empty "
            "/app")

    # The combination that loses everything, called out on its own so it cannot be
    # mistaken for one of the milder mismatches above.
    if flag == 0 and not has_artifacts:
        problems.append(
            "NOTHING IS RECORDED: no artifacts block and the snapshot is disabled")

    return problems


def check_task(task_dir):
    """Compare every pair in one task directory.

    Args:
        task_dir: pathlib.Path of the directory holding task.toml.

    Returns:
        list of str, one per problem found. Empty means the task is consistent.
    """
    problems = []

    for left, right in PAIRS:
        a, b = normalized(task_dir / left), normalized(task_dir / right)
        # Only a genuine pair can drift. One side alone is the normal state for a task
        # that never had the tests/ copy, or one where it was removed with the LLM-judge
        # machinery that was its only reader -- there is nothing left to keep in step.
        if a is None or b is None:
            continue
        if a != b:
            problems.append(f"{left} != {right}")

    a, b = (dockerfile_prefix(task_dir / "environment/Dockerfile"),
            dockerfile_prefix(task_dir / "tests/Dockerfile"))
    if a is not None and b is not None and a != b:
        problems.append(
            f"environment/Dockerfile != tests/Dockerfile above the "
            f"{DOCKERFILE_MARKER} marker "
            f"({hashlib.sha256(a.encode()).hexdigest()[:12]} vs "
            f"{hashlib.sha256(b.encode()).hexdigest()[:12]})")

    problems.extend(check_record_destination(task_dir))

    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task_dirs", nargs="+",
                        help="task directories (the ones containing task.toml)")
    args = parser.parse_args()

    failed = False
    for raw in args.task_dirs:
        task_dir = pathlib.Path(raw)
        if not (task_dir / "task.toml").is_file():
            print(f"{task_dir}: no task.toml; is this a task directory?")
            failed = True
            continue
        problems = check_task(task_dir)
        if problems:
            failed = True
            print(f"FAIL {task_dir.name}")
            for p in problems:
                print(f"       {p}")
        else:
            print(f"ok   {task_dir.name}")

    if failed:
        print("\nPairs must match once canary lines are removed. Copy the agent-visible "
              "file over its tests/ counterpart, then re-run the canary script.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
