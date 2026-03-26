#!/usr/bin/env python3
"""Generate an unsupervised version of a harbor task.

Copies the task directory, removing files that come from a manual solution
in the tests directory and renaming the unsupervised judge instructions.

Usage:
    python generate_unsupervised_task.py sosa2024
    python generate_unsupervised_task.py harbor-tasks/sosa2024
    python generate_unsupervised_task.py harbor-tasks/sosa2024 --output harbor-tasks/sosa2024_unsupervised
"""

import argparse
import shutil
import sys
from pathlib import Path

# Files in tests/ that come from the manual solution and should be excluded
EXCLUDE_TEST_FILES = {
    "judge_instructions.md",
    "reference_DECISIONS.md",
    "reference_convert_data.py",
    "reference_stats_full.json",
}

# File to rename: old name -> new name
RENAME_TEST_FILES = {
    "judge_instructions_unsupervised.md": "judge_instructions.md",
}


def generate_unsupervised_task(src: Path, dst: Path, dry_run: bool = False) -> None:
    if dst.exists():
        print(f"Error: output directory already exists: {dst}", file=sys.stderr)
        sys.exit(1)

    # Verify source has expected structure
    tests_dir = src / "tests"
    if not tests_dir.is_dir():
        print(f"Error: no tests/ directory found in {src}", file=sys.stderr)
        sys.exit(1)

    unsupervised_file = tests_dir / "judge_instructions_unsupervised.md"
    if not unsupervised_file.exists():
        print(
            f"Error: {unsupervised_file} not found -- this task may not support unsupervised mode",
            file=sys.stderr,
        )
        sys.exit(1)

    prefix = "[dry run] " if dry_run else ""

    # Collect files that will be excluded/renamed
    exclude_names = EXCLUDE_TEST_FILES | set(RENAME_TEST_FILES.keys())
    excluded = [name for name in sorted(EXCLUDE_TEST_FILES) if (tests_dir / name).exists()]
    renamed = {old: new for old, new in RENAME_TEST_FILES.items() if (tests_dir / old).exists()}

    print(f"{prefix}copytree {src} -> {dst}")
    for name in excluded:
        print(f"{prefix}  excluding tests/{name}")
    for old_name in renamed:
        print(f"{prefix}  excluding tests/{old_name}")
    for old_name, new_name in renamed.items():
        print(f"{prefix}copy tests/{old_name} -> {dst / 'tests' / new_name}")

    if dry_run:
        return

    # Copy the entire directory tree, excluding the specific files
    def ignore_in_tests(directory, contents):
        dir_path = Path(directory)
        if dir_path == tests_dir:
            ignored = set()
            for name in contents:
                if name in EXCLUDE_TEST_FILES:
                    ignored.add(name)
                # Also exclude the unsupervised file; we'll copy it with the new name
                if name in RENAME_TEST_FILES:
                    ignored.add(name)
            return ignored
        return set()

    shutil.copytree(src, dst, ignore=ignore_in_tests)

    # Copy renamed files
    for old_name, new_name in renamed.items():
        shutil.copy2(tests_dir / old_name, dst / "tests" / new_name)

    print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate an unsupervised version of a harbor task."
    )
    parser.add_argument(
        "task",
        help="Task name (e.g. sosa2024) or path to task directory (e.g. harbor-tasks/sosa2024)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: <task>_unsupervised in same parent dir)",
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true",
        help="Print what would be done without copying anything",
    )
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent.parent
    src = (repo_dir / "harbor-tasks" / args.task).resolve()

    if not src.is_dir():
        print(f"Error: task directory not found: {src}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        dst = Path(args.output).resolve()
    else:
        dst = src.parent / f"{src.name}_unsupervised"

    generate_unsupervised_task(src, dst, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
