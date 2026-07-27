#!/usr/bin/env python3
"""
Sync shared files from template-harbor-task/ to all task directories.

Compares files in the template against copies in harbor-tasks/ and
harbor-staging/. Reports diffs and optionally copies the template
version to all destinations.

Usage:
    python sync_template.py              # dry-run: show what would change
    python sync_template.py --apply      # actually copy files
    python sync_template.py --diff       # show full diffs
"""

import argparse
import difflib
import hashlib
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "template-harbor-task"

TASK_DIRS = sorted((REPO_ROOT / "harbor-tasks").glob("*/"))
STAGING_DIRS = sorted((REPO_ROOT / "harbor-staging").glob("*/"))
ALL_DEST_DIRS = TASK_DIRS + STAGING_DIRS

# Files that are expected to be identical across all tasks.
# Paths are relative to the task directory.
SHARED_FILES = [
    "task.toml",
    "tests/compute_reward.py",
    "tests/decoder.py",
    "tests/test_outputs.py",
    "tests/test.sh",
    "tests/train_decoder.py",
    "environment/decoder.py",
    "environment/train_decoder.py",
    "environment/Dockerfile",
]

# Files that intentionally differ from the template for specific tasks.
# Maps task name -> set of relative paths to skip.
TASK_EXCLUDED = {
    "debug": {
        "tests/test_outputs.py",
        "tests/train_decoder.py",
        "environment/train_decoder.py",
    },
    "allen2p": {
        "environment/Dockerfile",
    },
    "mouseland": {
        "task.toml",
    },
}


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="Copy template files to all task directories")
    parser.add_argument("--diff", action="store_true",
                        help="Show full diffs for changed files")
    parser.add_argument("--override", action="store_true",
                        help="Overwrite destination files even if they are newer than the template")
    args = parser.parse_args()

    any_changes = False

    for rel_path in SHARED_FILES:
        template_file = TEMPLATE_DIR / rel_path
        if not template_file.exists():
            print(f"WARNING: template file missing: {rel_path}")
            continue

        template_hash = file_hash(template_file)

        for dest_dir in ALL_DEST_DIRS:
            dest_file = dest_dir / rel_path
            task_name = dest_dir.relative_to(REPO_ROOT)

            if not dest_file.exists():
                # File doesn't exist in this task — skip (may be intentional)
                continue

            # Skip files that intentionally differ for specific tasks. A variant
            # (e.g. sosa2024_minimal) inherits its parent's exclusions, and also
            # keeps its own task.toml, which is tuned to the cluster node it runs on.
            base_name = dest_dir.name.removesuffix("_minimal")
            excluded = (TASK_EXCLUDED.get(dest_dir.name, set())
                        | TASK_EXCLUDED.get(base_name, set()))
            if dest_dir.name != base_name:
                excluded |= {"task.toml"}
            if rel_path in excluded:
                continue

            dest_hash = file_hash(dest_file)
            if dest_hash == template_hash:
                continue

            any_changes = True
            dest_is_newer = dest_file.stat().st_mtime > template_file.stat().st_mtime
            newer_tag = " (destination is NEWER)" if dest_is_newer else ""
            if args.override or (not dest_is_newer):
                print(f"CHANGED: {task_name}/{rel_path}{newer_tag}")
            elif dest_is_newer:
                print(f"IGNORING: {task_name}/{rel_path}{newer_tag}")

            if args.diff:
                template_lines = template_file.read_text().splitlines(keepends=True)
                dest_lines = dest_file.read_text().splitlines(keepends=True)
                diff = difflib.unified_diff(
                    dest_lines, template_lines,
                    fromfile=f"{task_name}/{rel_path}",
                    tofile=f"template-harbor-task/{rel_path}",
                )
                print("".join(diff))

            if args.apply:
                if not args.override and dest_is_newer:
                    print(f"  -> SKIPPED (destination is newer; use --override to overwrite)")
                else:
                    shutil.copy2(template_file, dest_file)
                    print(f"  -> copied from template")

    if not any_changes:
        print("All shared files are in sync with the template.")
    elif not args.apply:
        print()
        print("Run with --apply to copy template files to all destinations.")
        print("Run with --diff to see full diffs.")


if __name__ == "__main__":
    main()
