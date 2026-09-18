#!/usr/bin/env python3
"""Generate a task's `<task>_datalimit` version: the minimal-prompt task on the capped data.

`<task>_datalimit` is the minimal-prompt task, `<task>_minimal`, run on the
datalimit data in `data/<task>_datalimit/`. Every file in it is derived, so the
directory is never edited by hand. To change it, edit one of its inputs and rerun:

    harbor-tasks/<task>_minimal/          every file, copied unchanged, except the two below
    download/datalimit/<task>_prompt.md   the "Data subset" section and Consistency bullet
                                          added to instruction.md and its judge copy
    (this script)                         the data mount in environment/docker-compose.yaml

The one file that is not derived is `tests/reference_stats_full.json`: it has to describe the
datalimit data, so it is kept when present and has to be generated when it is not:

    harbor-scripts/generate_reference_stats.sh <task>_datalimit
    harbor-scripts/rerun_verifier.sh --decoder-stats --task <task>_datalimit <oracle trial dir>

Only tasks whose data was actually reduced get a `_datalimit` task. A task whose manifest
(`download/datalimit/<task>.csv`) lists no entries was already under the size cap; its
`_minimal` task serves as its datalimit version in the analysis.

The subset itself is decided by `download/select_datalimit.py` and built by
`download/make_datalimit.py` or fetched by `download/download.py --datalimit`; this script
only wires the result into harbor.

Usage:
    python generate_datalimit_task.py sosa2024           # create, or bring up to date
    python generate_datalimit_task.py --all              # every task with a reduced dataset
    python generate_datalimit_task.py --all --check      # report files that are out of date
    python generate_datalimit_task.py sosa2024 --dry-run # report what would be written
"""

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "harbor-tasks"

sys.path.insert(0, str(REPO_ROOT / "harbor-scripts"))
sys.path.insert(0, str(REPO_ROOT / "download"))

from generate_minimal_task import _walk, make_ignore  # noqa: E402
from select_datalimit import MANIFEST_DIR, read_manifest  # noqa: E402

SUFFIX = "_datalimit"
SOURCE_SUFFIX = "_minimal"

# The agent's prompt, and the copies the LLM judges read to learn what the agent was asked.
PROMPT_FILES = ["instruction.md", "tests/instruction_reference.md", "tests/reference_instruction.md"]
COMPOSE_FILE = "environment/docker-compose.yaml"
# Describes the datalimit data, so never copied from the full-data source task.
REFERENCE_STATS_FILE = "tests/reference_stats_full.json"

# download/datalimit/<task>_prompt.md: the section, then this marker, then the bullet.
PROMPT_TEXT_FILE = "{task}_prompt.md"
BULLET_MARKER = "<!-- CONSISTENCY BULLET -->"
# Where the pieces go in the minimal prompt.
SECTION_BEFORE = "## Decoder Task"
LAST_CONSISTENCY_ITEM_RE = re.compile(r"^- Curation of data:.*$", re.M)

# Inside the container the subset list is always /app/data/DATALIMIT_SUBSET.csv. allen2p
# mounts only its release subdirectory at /app/data/visual-behavior-ophys-1.1.0, so the list,
# which download/make_datalimit.py writes at the dataset root, is mounted as a single file.
SUBSET_LIST_NAME = "DATALIMIT_SUBSET.csv"
MOUNTS_SUBSET_LIST_SEPARATELY = {"allen2p"}


def reduced_tasks() -> list[str]:
    """Parent tasks whose datalimit dataset differs from the full one.

    Returns:
        Sorted task names with a non-empty manifest in download/datalimit/.
    """
    tasks = []
    for manifest in sorted(MANIFEST_DIR.glob("*.csv")):
        entries, _ = read_manifest(manifest)
        if not entries.empty:
            tasks.append(manifest.stem)
    return tasks


def read_prompt_text(task: str) -> tuple[str, str]:
    """Read the task's Data subset section and Consistency bullet.

    Args:
        task: parent task name.

    Returns:
        (section, bullet): the "## Data subset" section text without trailing blank lines,
        and the single bullet line.

    Raises:
        SystemExit: if the file is missing or not in the expected layout.
    """
    path = MANIFEST_DIR / PROMPT_TEXT_FILE.format(task=task)
    if not path.is_file():
        sys.exit(f"Error: no prompt text for {task} at {path}")
    text = path.read_text()
    if text.count(BULLET_MARKER) != 1:
        sys.exit(f"Error: {path} must contain the marker {BULLET_MARKER} exactly once")
    head, tail = text.split(BULLET_MARKER)
    # The heading at the start of a line; the file's own header comment also names it.
    heading = re.search(r"^## Data subset$", head, re.M)
    if heading is None:
        sys.exit(f"Error: {path} has no '## Data subset' section before the marker")
    section = head[heading.start():].rstrip()
    bullet = tail.strip()
    if not bullet.startswith("- ") or "\n" in bullet:
        sys.exit(f"Error: {path} must have exactly one bullet line after the marker")
    return section, bullet


def datalimit_prompt(minimal_prompt: str, section: str, bullet: str) -> str:
    """Insert the subset section and Consistency bullet into a minimal prompt.

    Args:
        minimal_prompt: text of the <task>_minimal prompt.
        section: the "## Data subset" section (no trailing newline).
        bullet: the Consistency bullet line.

    Returns:
        str, the datalimit task's prompt.

    Raises:
        ValueError: if the insertion points are not found exactly once.
    """
    if minimal_prompt.count(SECTION_BEFORE) != 1:
        raise ValueError(f"expected one '{SECTION_BEFORE}' heading")
    text = minimal_prompt.replace(SECTION_BEFORE, f"{section}\n\n{SECTION_BEFORE}")
    items = LAST_CONSISTENCY_ITEM_RE.findall(text)
    if len(items) != 1:
        raise ValueError(f"expected one '- Curation of data:' consistency item, found {len(items)}")
    return LAST_CONSISTENCY_ITEM_RE.sub(lambda m: f"{m.group(0)}\n{bullet}", text)


def datalimit_compose(compose: str, task: str) -> str:
    """Point a minimal task's compose file at the datalimit data.

    Args:
        compose: text of the <task>_minimal docker-compose.yaml.
        task: parent task name.

    Returns:
        str, the compose text with `${DATA_ROOT...}/<task>` sources replaced by
        `${DATA_ROOT...}/<task>_datalimit`, plus, for allen2p, a read-only file mount of
        the subset list at /app/data/DATALIMIT_SUBSET.csv.

    Raises:
        ValueError: if no `${DATA_ROOT...}/<task>` mount source is found.
    """
    # Match the mount source only: "...}/allen2p/visual-behavior..." or "...}/map:".
    # Anchoring on the closing brace of ${DATA_ROOT...} avoids touching anything else.
    pattern = re.compile(rf"(\$\{{DATA_ROOT[^}}]*\}})/{re.escape(task)}(?=[/:])")
    if not pattern.search(compose):
        raise ValueError(f"no ${{DATA_ROOT}}/{task} mount found")
    text = pattern.sub(lambda m: f"{m.group(1)}/{task}{SUFFIX}", compose)
    if task in MOUNTS_SUBSET_LIST_SEPARATELY:
        mount = re.search(rf'^(\s*- ")(\$\{{DATA_ROOT[^}}]*\}})/{re.escape(task)}{SUFFIX}/[^"]*"\s*$',
                          text, re.M)
        if not mount:
            raise ValueError("no quoted release-directory mount to add the subset list after")
        line = (f'{mount.group(1)}{mount.group(2)}/{task}{SUFFIX}/{SUBSET_LIST_NAME}'
                f':/app/data/{SUBSET_LIST_NAME}:ro"')
        text = text[:mount.end()] + "\n" + line + text[mount.end():]
    return text


def planned_files(task: str) -> tuple[dict[str, str], dict[str, Path]]:
    """Everything the <task>_datalimit directory should contain.

    Args:
        task: parent task name.

    Returns:
        (written, copied): written maps relative path -> text for the files this script
        changes; copied maps relative path -> source Path for files copied unchanged from
        <task>_minimal. Neither includes tests/reference_stats_full.json.
    """
    src = TASKS_DIR / f"{task}{SOURCE_SUFFIX}"
    if not (src / "tests").is_dir():
        sys.exit(f"Error: {src} does not exist; generate the minimal task first")
    section, bullet = read_prompt_text(task)
    ignore, _ = make_ignore(src)

    written, copied = {}, {}
    for directory, _, filenames in _walk(src, ignore):
        for name in filenames:
            source = directory / name
            rel = source.relative_to(src).as_posix()
            if rel == REFERENCE_STATS_FILE:
                continue
            if rel in PROMPT_FILES:
                written[rel] = datalimit_prompt(source.read_text(), section, bullet)
            elif rel == COMPOSE_FILE:
                written[rel] = datalimit_compose(source.read_text(), task)
            else:
                copied[rel] = source
    return written, copied


def stale_files(task: str) -> tuple[list[str], list[str], bool]:
    """Compare an existing <task>_datalimit directory with a fresh generation.

    Returns:
        (stale, extra, has_reference_stats): stale lists planned files that are missing or
        differ; extra lists files present that the generation would not produce (excluding
        the reference stats and ignored caches); has_reference_stats says whether
        tests/reference_stats_full.json exists.
    """
    dst = TASKS_DIR / f"{task}{SUFFIX}"
    written, copied = planned_files(task)
    stale = [rel for rel, text in written.items()
             if not (dst / rel).is_file() or (dst / rel).read_text() != text]
    stale += [rel for rel, source in copied.items()
              if not (dst / rel).is_file() or not filecmp.cmp(source, dst / rel, shallow=False)]
    extra = []
    if dst.is_dir():
        ignore, _ = make_ignore(dst)
        planned = set(written) | set(copied) | {REFERENCE_STATS_FILE}
        for directory, _, filenames in _walk(dst, ignore):
            for name in filenames:
                rel = (directory / name).relative_to(dst).as_posix()
                if rel not in planned:
                    extra.append(rel)
    return sorted(stale), sorted(extra), (dst / REFERENCE_STATS_FILE).is_file()


def generate(task: str, dry_run: bool = False) -> None:
    """Create or update harbor-tasks/<task>_datalimit.

    Args:
        task: parent task name.
        dry_run: report what would be written, write nothing.

    Side effects:
        Writes the planned files that are missing or out of date. Never deletes files, and
        never touches tests/reference_stats_full.json.
    """
    dst = TASKS_DIR / f"{task}{SUFFIX}"
    prefix = "[dry run] " if dry_run else ""
    written, copied = planned_files(task)
    stale, extra, has_stats = stale_files(task)
    print(f"\n=== {task}{SOURCE_SUFFIX} -> {dst.name}: {len(stale)} file(s) to write")
    for rel in stale:
        print(f"{prefix}  write {rel}")
        if dry_run:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel in written:
            target.write_text(written[rel])
        else:
            shutil.copy2(copied[rel], target)
    for rel in extra:
        print(f"  WARNING: {dst.name}/{rel} is not produced by the generation; left in place")
    if not has_stats:
        print(f"  NOTE: no {REFERENCE_STATS_FILE} yet. Generate it on the datalimit data:\n"
              f"        harbor-scripts/generate_reference_stats.sh {dst.name}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*", help="Parent task names, e.g. sosa2024.")
    parser.add_argument("--all", action="store_true",
                        help="Every task whose datalimit dataset is reduced.")
    parser.add_argument("--check", action="store_true",
                        help="Report out-of-date files; write nothing. Exits 1 if any.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be written without writing anything.")
    args = parser.parse_args()

    if args.all:
        if args.tasks:
            sys.exit("Pass either --all or explicit task names, not both.")
        tasks = reduced_tasks()
    else:
        if not args.tasks:
            parser.error("Specify at least one task, or pass --all.")
        tasks = args.tasks
        not_reduced = sorted(set(tasks) - set(reduced_tasks()))
        if not_reduced:
            sys.exit(f"Not reduced (already under the size cap; use the _minimal task): "
                     f"{', '.join(not_reduced)}")

    if args.check:
        n_problems = 0
        for task in tasks:
            stale, extra, has_stats = stale_files(task)
            for rel in stale:
                print(f"STALE: {task}{SUFFIX}/{rel}")
            for rel in extra:
                print(f"EXTRA: {task}{SUFFIX}/{rel}")
            if not has_stats:
                print(f"MISSING: {task}{SUFFIX}/{REFERENCE_STATS_FILE}")
            n_problems += len(stale) + len(extra) + (not has_stats)
        print(f"{n_problems} problem(s) in {len(tasks)} task(s)")
        sys.exit(1 if n_problems else 0)

    for task in tasks:
        generate(task, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
