#!/usr/bin/env python3
"""Generate the 50 GB-capped `<task>_datalimit` version of a harbor task.

Copies the task directory, repoints its data mount at `data/<task>_datalimit`,
and documents the subsample in the prompt.

This is **first-time scaffolding, not the whole story**. Two things about a
`_datalimit` task are maintained by hand afterwards:

  * `solution/convert_data.py` and its copy `tests/reference_convert_data.py`
    (which must stay byte-identical -- the first is what the oracle runs, the
    second is what the LLM judge reads as the human reference). For tasks whose
    conversion enumerates data from an api index rather than from disk -- allen2p
    via `get_ophys_experiment_table()`, zhang2025 via `one.search()` -- the
    reference has to be edited to restrict itself to `DATALIMIT_SUBSET.csv`.
    Without that it would enumerate the whole release and fetch, over the
    network, every recording the subset deliberately leaves out.
  * `tests/reference_DECISIONS.md`, so the decisions the judge compares against
    describe the same subset the reference code actually loads.

Re-running is therefore safe by default: existing files are **preserved**, and
only files missing from the destination are copied in. `--force` restores the old
behaviour of replacing the directory wholesale, and will discard those hand
edits -- it lists what differs from the parent before doing so.

Companion to `generate_minimal_task.py`, which produces the `<task>_minimal`
prompt-ablation variants, and shares its copy scaffolding.

The subsample itself is decided by `download/select_datalimit.py` and built by
`download/make_datalimit.py`; this script only wires the result into harbor.

Usage:
    python generate_datalimit_task.py sosa2024             # create, or fill gaps
    python generate_datalimit_task.py --all
    python generate_datalimit_task.py sosa2024 --dry-run
    python generate_datalimit_task.py sosa2024 --force     # replace, losing hand edits

After generating, the reference statistics still describe the FULL dataset and
must be regenerated against the capped data before the task can be scored:

    harbor-scripts/generate_reference_stats.sh <task>_datalimit
    cp <oracle stats_full.json> harbor-tasks/<task>_datalimit/tests/reference_stats_full.json
"""

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "harbor-tasks"

sys.path.insert(0, str(REPO_ROOT / "harbor-scripts"))
sys.path.insert(0, str(REPO_ROOT / "download"))

from generate_minimal_task import (  # noqa: E402
    _walk, check_data_mounts, human, make_ignore, tree_size,
)
from select_datalimit import MANIFEST_DIR, read_manifest  # noqa: E402

SUFFIX = "_datalimit"

# The agent's prompt, and the copy the LLM judge reads to learn what the agent
# was asked to do. Both must describe the same dataset.
INSTRUCTION_FILE = "instruction.md"
JUDGE_REFERENCE_FILES = ["tests/instruction_reference.md", "tests/reference_instruction.md"]

# The subset note is inserted directly after this bullet in the "Reference
# Information" section, which every task's prompt has (wording varies slightly:
# "the paper" / "the papers" / "the data paper").
DATA_BULLET_PREFIX = "- **Data**"

# task.toml settings that only made sense at full scale. mouseland is the sole
# entry: it asks for 240 GB of RAM where every other task asks for 64, because the
# full dataset loads 4.1M neurons' worth of trial arrays (~112 GB) into memory at
# once. At 9.8% of cells that falls to ~11 GB, so keeping the exception would make
# the capped variant need a 240 GB machine -- defeating much of the point of it.
RESOURCE_OVERRIDES = {
    "mouseland": {"memory_mb": 65536},
}


# Inserted verbatim into the prompt, with {rule} and {list_path} filled in. This
# note is the ONLY thing keeping a run inside the 50 GB cap: the downloaded caches
# are never edited, so AllenSDK's metadata tables and ONE's release index still
# describe the full release, and every task.toml sets allow_internet = true. It
# also heads off a false alarm -- the workflow asks the agent to record dataset
# totals (Step 2) and reconcile them against the paper (Step 4), which would
# otherwise read as a discrepancy to chase.
SUBSET_NOTE = """- **Dataset subset — use only the data listed in `{list_path}`.** \
This task uses a reduced version of the published dataset: {rule} No *type* of data was \
removed — every variable, signal, and auxiliary array the full release contains is still \
present — only samples were dropped. The files in `data` are an unmodified download, so \
metadata tables and release indexes there still describe the **full** release and will refer \
to recordings that are not present. Read `{list_path}` and process exactly the \
sessions/experiments it lists. Do **not** download any data that is missing locally, even if \
the metadata, reference code, or paper refers to it. Dataset totals you measure (subjects, \
sessions, trials, neurons) will therefore be smaller than the numbers reported in the paper; \
that difference is expected and is **not** a discrepancy to investigate or resolve."""

# Where the subset list appears from inside the container, and what it is.
# allen2p mounts only the release subdirectory, so its list lives there. allen2p
# and zhang2025 publish the subset as a filtered copy of the canonical table their
# own tooling already reads, which is far easier to consume than a list of ids.
SUBSET_LIST_PATH = {
    "allen2p": "data/visual-behavior-ophys-1.1.0/DATALIMIT_SUBSET.csv",
}
DEFAULT_SUBSET_LIST_PATH = "data/DATALIMIT_SUBSET.csv"

# Appended to the subset note, naming the schema so the agent knows how to read it.
SUBSET_LIST_FORMAT = {
    "allen2p": (" It has the same columns as "
                "`project_metadata/ophys_experiment_table.csv`, restricted to the "
                "experiments present here; use its `ophys_experiment_id` values."),
    "zhang2025": (" It has the same columns as the release freeze "
                  "`code/code_zhang2025/data/bwm_release.csv` (one row per probe "
                  "insertion), restricted to the sessions present here; use its "
                  "`eid` values."),
    "map": " Columns: `subject`, `nwb_path` (relative to `data`).",
    "sosa2024": " Columns: `subject`, `nwb_path` (relative to `data`).",
    "mouseland": (" Columns: `session`, `n_cells_total`, `n_cells_kept`. Every session "
                  "is present; each one's cells were subsampled."),
}


def load_rule(task: str) -> str | None:
    """Read the human-readable subsample rule for `task` from its manifest.

    Args:
        task: parent benchmark task name, e.g. 'sosa2024'.

    Returns:
        The `rule` header string, or None when the dataset was not subsampled
        (already under the cap) and so needs no note in the prompt.
    """
    manifest = MANIFEST_DIR / f"{task}.csv"
    if not manifest.exists():
        print(f"Error: no manifest at {manifest}\n"
              f"       run: python download/select_datalimit.py {task}", file=sys.stderr)
        sys.exit(1)
    entries, header = read_manifest(manifest)
    if entries.empty:
        return None  # passthrough: identical to the full dataset
    return header.get("rule")


def repoint_data_mount(dst: Path, task: str) -> None:
    """Rewrite the compose file so the task mounts `data/<task>_datalimit`.

    Args:
        dst: the generated `harbor-tasks/<task>_datalimit/` directory.
        task: parent task name.

    Side effects:
        Rewrites `environment/docker-compose.yaml` in place.

    Raises:
        SystemExit: if the expected `${DATA_ROOT}/<task>` source is not found,
            rather than silently leaving the variant pointed at the full data.
    """
    compose = dst / "environment" / "docker-compose.yaml"
    text = compose.read_text()
    # Match the mount source only: "...}/allen2p/visual-behavior..." or "...}/map:".
    # Anchoring on the closing brace of ${DATA_ROOT...} avoids touching anything else.
    needle_dir = f"}}/{task}/"
    needle_end = f"}}/{task}:"
    if needle_dir in text:
        updated = text.replace(needle_dir, f"}}/{task}{SUFFIX}/")
    elif needle_end in text:
        updated = text.replace(needle_end, f"}}/{task}{SUFFIX}:")
    else:
        print(f"Error: no ${{DATA_ROOT}}/{task} mount found in {compose}", file=sys.stderr)
        sys.exit(1)
    compose.write_text(updated)
    print(f"  data mount repointed to ${{DATA_ROOT}}/{task}{SUFFIX}")


def apply_resource_overrides(dst: Path, task: str) -> None:
    """Relax `task.toml` settings that were sized for the full dataset.

    Args:
        dst: the generated `harbor-tasks/<task>_datalimit/` directory.
        task: parent task name; only tasks in RESOURCE_OVERRIDES change.

    Side effects:
        Rewrites `task.toml` in place.

    Raises:
        SystemExit: if an overridden key is not present in the file, rather than
            silently leaving the full-scale value in place.
    """
    overrides = RESOURCE_OVERRIDES.get(task)
    if not overrides:
        return
    toml_path = dst / "task.toml"
    lines = toml_path.read_text().splitlines()
    for key, value in overrides.items():
        for index, line in enumerate(lines):
            if line.strip().startswith(f"{key} ") or line.strip().startswith(f"{key}="):
                old = line.split("=", 1)[1].strip()
                lines[index] = f"{key} = {value}"
                print(f"  task.toml {key}: {old} -> {value}")
                break
        else:
            print(f"Error: no '{key}' setting in {toml_path}", file=sys.stderr)
            sys.exit(1)
    toml_path.write_text("\n".join(lines) + "\n")


def copy_missing(src: Path, dst: Path, ignore) -> list[str]:
    """Copy only the files that do not already exist under `dst`.

    Lets the script be re-run safely over a task whose reference solution has been
    hand-edited: anything already there is left exactly as it is, and only genuinely
    new parent files are brought across.

    Args:
        src: parent task directory.
        dst: destination task directory (may or may not exist).
        ignore: the `copytree` ignore callback from `make_ignore`, so the same
            caches and `solution/*.pkl` leftovers are skipped.

    Returns:
        Relative paths (posix strings) of the files actually written.

    Side effects:
        Creates files and parent directories under `dst`.
    """
    created = []
    for directory, _, filenames in _walk(src, ignore):
        for name in filenames:
            source = directory / name
            relative = source.relative_to(src)
            target = dst / relative
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            created.append(relative.as_posix())
    return created


def local_changes(src: Path, dst: Path, ignore) -> list[str]:
    """Files in `dst` that differ from their `src` counterpart, or are new there.

    Used to say what a `--force` regeneration is about to discard, since that is
    where hand edits to the reference solution live.

    Args:
        src: parent task directory.
        dst: existing destination task directory.
        ignore: the `copytree` ignore callback from `make_ignore`.

    Returns:
        Sorted relative paths (posix strings) that differ.
    """
    differing = []
    for directory, _, filenames in _walk(src, ignore):
        for name in filenames:
            source = directory / name
            relative = source.relative_to(src)
            target = dst / relative
            if target.exists() and not filecmp.cmp(source, target, shallow=False):
                differing.append(relative.as_posix())
    return sorted(differing)


def insert_subset_note(dst: Path, task: str, rule: str,
                       only: list[str] | None = None) -> None:
    """Add the "Dataset subset" bullet to the agent prompt and the judge's copy.

    Args:
        dst: the generated `harbor-tasks/<task>_datalimit/` directory.
        task: parent task name, used to resolve where the subset list appears
            inside the container.
        rule: one-sentence description of what was kept, from the manifest.
        only: if given, restrict to files this run actually created. The note is
            inserted after the `- **Data**` bullet, so re-applying it to a prompt
            that already has one would add a second copy.

    Side effects:
        Rewrites `instruction.md` and any judge reference copy in place.
    """
    note = SUBSET_NOTE.format(
        rule=rule, list_path=SUBSET_LIST_PATH.get(task, DEFAULT_SUBSET_LIST_PATH))
    note += SUBSET_LIST_FORMAT.get(task, "")
    for relative in [INSTRUCTION_FILE] + JUDGE_REFERENCE_FILES:
        path = dst / relative
        if not path.exists():
            continue
        if only is not None and relative not in only:
            print(f"  preserved {relative} (subset note already present)")
            continue
        lines = path.read_text().splitlines()
        for index, line in enumerate(lines):
            if line.startswith(DATA_BULLET_PREFIX):
                lines.insert(index + 1, note)
                break
        else:
            print(f"WARNING: no '{DATA_BULLET_PREFIX}' bullet in {relative}; "
                  f"subset note NOT inserted", file=sys.stderr)
            continue
        path.write_text("\n".join(lines) + "\n")
        print(f"  subset note added to {relative}")


def generate_datalimit_task(task: str, force: bool = False,
                            dry_run: bool = False) -> None:
    """Create `harbor-tasks/<task>_datalimit/` from `harbor-tasks/<task>/`.

    Args:
        task: parent benchmark task name.
        force: replace the destination wholesale, discarding hand edits. Without
            it, existing files are preserved and only missing ones are copied.
        dry_run: report the plan without writing anything.

    Side effects:
        Creates, fills gaps in, or (with `force`) replaces the `<task>_datalimit`
        task directory.
    """
    src = TASKS_DIR / task
    dst = TASKS_DIR / f"{task}{SUFFIX}"
    prefix = "[dry run] " if dry_run else ""

    if not (src / "tests").is_dir():
        print(f"Error: no tests/ directory in {src}", file=sys.stderr)
        sys.exit(1)

    rule = load_rule(task)
    print(f"\n=== {task} -> {task}{SUFFIX}")
    print(f"  rule: {rule or 'not subsampled (already under the cap)'}")

    ignore, skipped = make_ignore(src)

    if dry_run:
        # Walk the way copytree will, so the reported size excludes the ignored
        # files -- lee2025 alone leaves 13.8 GB of solution/*.pkl behind.
        n_files, nbytes, present = 0, 0, 0
        for directory, _, filenames in _walk(src, ignore):
            for name in filenames:
                n_files += 1
                nbytes += (directory / name).stat().st_size
                if (dst / (directory / name).relative_to(src)).exists():
                    present += 1
        if dst.exists() and not force:
            print(f"{prefix}update {dst.name}: copy {n_files - present} missing file(s), "
                  f"preserve {present}")
        else:
            print(f"{prefix}copytree {src.name} -> {dst.name} "
                  f"({n_files} files, {human(nbytes)}, {len(skipped)} skipped)")
        return

    if dst.exists() and force:
        # Name what is being thrown away. The reference solution and DECISIONS are
        # hand-edited after generation, so this is where real work would be lost.
        changed = local_changes(src, dst, ignore)
        if changed:
            print(f"  discarding local changes to: {', '.join(changed)}")
        shutil.rmtree(dst)

    if dst.exists():
        created = copy_missing(src, dst, ignore)
        total = sum(len(files) for _, _, files in _walk(src, ignore))
        print(f"  copied {len(created)} missing file(s), preserved {total - len(created)}")
    else:
        shutil.copytree(src, dst, ignore=ignore)
        created = None  # fresh tree: every derived edit applies
        n_files, nbytes = tree_size(dst)
        print(f"  copied {n_files} files ({human(nbytes)}), skipped {len(skipped)}")

    # Derived edits apply only to files this run wrote. Re-running over an
    # existing task must not repoint an already-repointed mount or insert the
    # subset note a second time.
    if created is None or "environment/docker-compose.yaml" in created:
        repoint_data_mount(dst, task)
    if created is None or "task.toml" in created:
        apply_resource_overrides(dst, task)
    if rule:
        insert_subset_note(dst, task, rule, only=created)
    check_data_mounts(dst)

    if rule:
        print(f"  NOTE: tests/reference_stats_full.json still describes the FULL dataset.\n"
              f"        Regenerate with: harbor-scripts/generate_reference_stats.sh "
              f"{task}{SUFFIX}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*",
                        help="Parent task names. Default with --all: every task "
                             "that has a datalimit manifest.")
    parser.add_argument("--all", action="store_true",
                        help="Generate for every task with a manifest.")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate over existing output directories.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report the plan without writing anything.")
    args = parser.parse_args()

    if args.all:
        if args.tasks:
            sys.exit("Pass either --all or explicit task names, not both.")
        tasks = sorted(path.stem for path in MANIFEST_DIR.glob("*.csv"))
    else:
        if not args.tasks:
            parser.error("Specify at least one task, or pass --all.")
        tasks = args.tasks

    unknown = [task for task in tasks if not (TASKS_DIR / task).is_dir()]
    if unknown:
        sys.exit(f"No such harbor task(s): {', '.join(unknown)}")

    for task in tasks:
        generate_datalimit_task(task, force=args.force, dry_run=args.dry_run)

    print(f"\nGenerated {len(tasks)} datalimit task(s). "
          f"Regenerate reference stats before scoring any subsampled task.")


if __name__ == "__main__":
    main()
