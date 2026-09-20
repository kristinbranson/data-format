#!/usr/bin/env python3
"""Check that a task's variants in harbor-tasks/ are consistent with each other.

Each benchmark task exists as up to three directories -- <task> (maximal prompt),
<task>_minimal and <task>_datalimit (minimal prompt, datalimit data) -- plus
several files that exist twice inside one directory. Nothing else stops them drifting
apart, and a drifted copy silently changes what an agent is given or graded against.

For every benchmark task this checks:

  1. Files that must be byte-identical across all of the task's variants: the reference
     solution, solve.sh, the decision notes the judges compare against, the Dockerfile and
     the decoder scripts. (Files shared by every task are checked by sync_template.py.)
  2. Pairs inside each variant: instruction.md == tests/instruction_reference.md, and
     solution/convert_data.py == tests/reference_convert_data.py.
  3. The maximal and minimal variants grade against the same full-data reference
     statistics.
  4. Every agent file listed in tests/expected_files.json is named in that variant's prompt.
  5. manual/<name>/convert_data.py, where the reference solution is developed, is identical
     to the copies in the task directories. It drifted twice without being noticed, in both
     directions: an improvement made in manual/ never reached the tasks, and changes made in
     the tasks never came back.
  6. The generated files are up to date: minimal prompts regenerate from prompt_v5,
     minimal tasks' derived files from their parent (generate_minimal_task.py --check),
     and datalimit tasks from their minimal task (generate_datalimit_task.py
     --check).

Usage:
    python check_task_variants.py            # every benchmark task
    python check_task_variants.py sosa2024   # one task

Exits 1 if anything is inconsistent.
"""

import argparse
import contextlib
import filecmp
import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "harbor-tasks"
sys.path.insert(0, str(REPO_ROOT / "harbor-scripts"))
sys.path.insert(0, str(REPO_ROOT / "download"))

import generate_datalimit_task  # noqa: E402
import generate_minimal_prompt  # noqa: E402
import generate_minimal_task  # noqa: E402

# Must be identical in <task>, <task>_minimal and <task>_datalimit.
FAMILY_FILES = [
    "solution/convert_data.py",
    "tests/reference_convert_data.py",
    "solution/solve.sh",
    "tests/reference_DECISIONS.md",
    "environment/Dockerfile",
    "environment/decoder.py",
    "environment/train_decoder.py",
    "tests/decoder.py",
    "tests/train_decoder.py",
]
# Must be identical within one variant.
PAIRS = [
    ("instruction.md", "tests/instruction_reference.md"),
    ("solution/convert_data.py", "tests/reference_convert_data.py"),
]
# Graded against full data in both prompt variants.
FULL_DATA_STATS = "tests/reference_stats_full.json"
# Where each task's reference solution is developed. The directory is named after the task's
# first author, which for two tasks is not the task name.
MANUAL_DIR = REPO_ROOT / "manual"
MANUAL_NAME = {"map": "chen2024", "mouseland": "zhong2025"}
# Version of the minimal prompts currently in the minimal tasks.
MINIMAL_PROMPT_VERSION = 2


def benchmark_tasks() -> list[str]:
    """Parent tasks: those with a <task>_minimal directory."""
    return sorted(p.name.removesuffix("_minimal") for p in TASKS_DIR.glob("*_minimal") if p.is_dir())


def same(a: Path, b: Path) -> bool:
    """Whether two files exist and have identical bytes."""
    return a.is_file() and b.is_file() and filecmp.cmp(a, b, shallow=False)


def check_task(task: str) -> list[str]:
    """All consistency problems for one benchmark task.

    Args:
        task: parent task name, e.g. 'sosa2024'.

    Returns:
        list of str, one per problem; empty when consistent.
    """
    problems = []
    variants = [TASKS_DIR / name
                for name in (task, f"{task}_minimal", f"{task}_datalimit", f"{task}_api")
                if (TASKS_DIR / name).is_dir()]
    parent = variants[0]

    # 1. identical across variants
    for rel in FAMILY_FILES:
        for other in variants[1:]:
            if not same(parent / rel, other / rel):
                problems.append(f"{other.name}/{rel} differs from {parent.name}/{rel}")

    # 2. pairs within each variant
    for variant in variants:
        for left, right in PAIRS:
            if (variant / right).exists() and not same(variant / left, variant / right):
                problems.append(f"{variant.name}: {left} != {right}")

    # 3. full-data reference statistics shared by the two prompt variants
    if not same(parent / FULL_DATA_STATS, TASKS_DIR / f"{task}_minimal" / FULL_DATA_STATS):
        problems.append(f"{task}_minimal/{FULL_DATA_STATS} differs from {task}/{FULL_DATA_STATS}")

    # 4. expected files are named in the prompt
    for variant in variants:
        spec_path = variant / "tests" / "expected_files.json"
        if not spec_path.is_file():
            problems.append(f"{variant.name}: no tests/expected_files.json")
            continue
        spec = json.loads(spec_path.read_text())
        prompt = (variant / "instruction.md").read_text()
        for name in spec["required"] + spec.get("expected", []):
            if name not in prompt:
                problems.append(f"{variant.name}: {name} is in expected_files.json but not in the prompt")

    # 5. the working copy the solution is developed in
    manual = MANUAL_DIR / MANUAL_NAME.get(task, task) / "convert_data.py"
    if not manual.is_file():
        problems.append(f"{manual.relative_to(REPO_ROOT)} is missing")
    elif not same(manual, parent / "solution/convert_data.py"):
        problems.append(f"{manual.relative_to(REPO_ROOT)} differs from "
                        f"{parent.name}/solution/convert_data.py")

    # 6. generated files are current (the generators print their own reports; keep quiet)
    with contextlib.redirect_stdout(io.StringIO()):
        prompt = generate_minimal_task.find_prompt(task, MINIMAL_PROMPT_VERSION)
        for rel in generate_minimal_task.stale_derived_files(parent, TASKS_DIR / f"{task}_minimal", prompt):
            problems.append(f"{task}_minimal/{rel} is out of date (generate_minimal_task.py --update)")
        source = generate_minimal_prompt.resolve_source(task, MINIMAL_PROMPT_VERSION)
        stem = source.name.split("_prompt_v")[0]
        destination = generate_minimal_prompt.MINIMAL_DIR / f"{stem}_prompt_minimal_v{MINIMAL_PROMPT_VERSION}.md"
        if not generate_minimal_prompt.generate(source, destination, MINIMAL_PROMPT_VERSION, check=True):
            problems.append(f"{destination.name} does not regenerate from {source.name}")
        if (TASKS_DIR / f"{task}_datalimit").is_dir():
            stale, extra, has_stats = generate_datalimit_task.stale_files(task)
            problems += [f"{task}_datalimit/{rel} is out of date (generate_datalimit_task.py)" for rel in stale]
            problems += [f"{task}_datalimit/{rel} is not produced by generate_datalimit_task.py" for rel in extra]
            if not has_stats:
                problems.append(f"{task}_datalimit has no {FULL_DATA_STATS}")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*", help="parent task names (default: every benchmark task)")
    args = parser.parse_args()

    failed = False
    for task in args.tasks or benchmark_tasks():
        problems = check_task(task)
        failed |= bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {task}")
        for problem in problems:
            print(f"       {problem}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
