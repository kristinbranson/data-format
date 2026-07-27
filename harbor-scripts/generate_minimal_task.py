#!/usr/bin/env python3
"""Generate a minimal-prompt version of a harbor task.

Copies the task directory and swaps in the stripped-down prompt from
minimal_prompts/, both as the agent's instruction.md and as the judge's
tests/instruction_reference.md. Everything else (tests, solution, environment)
is copied unchanged so the only difference from the parent task is the prompt.

Usage:
    python generate_minimal_task.py sosa2024              # highest prompt version
    python generate_minimal_task.py sosa2024 --version 2  # pin to v2
    python generate_minimal_task.py --all --version 1     # all tasks with a v1 prompt
    python generate_minimal_task.py sosa2024 --dry-run
    python generate_minimal_task.py sosa2024 --force      # regenerate in place
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "harbor-tasks"
PROMPTS_DIR = REPO_ROOT / "minimal_prompts"

# minimal_prompts/<task>_prompt_minimal_v<N>.md
PROMPT_RE = re.compile(r"^(?P<task>.+)_prompt_minimal_v(?P<version>\d+)$", re.IGNORECASE)

# The agent's prompt, and the copy the LLM judge reads to learn what the agent
# was asked to do. Both get the minimal prompt.
INSTRUCTION_FILE = "instruction.md"
JUDGE_REFERENCE_FILE = "tests/instruction_reference.md"
# zhang2025 uses the reversed name; keep it in sync if present.
JUDGE_REFERENCE_ALIASES = ["tests/reference_instruction.md"]

# Directories never worth copying: editor/interpreter caches and virtualenvs.
SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".vscode",
    ".ipynb_checkpoints",
    "venv",
    ".venv",
    ".claude",
}

# File patterns never worth copying, matched with Path.match anywhere in the tree.
SKIP_FILE_PATTERNS = ["*.pyc", "*~", ".nfs*"]

# Generated pickles left behind by solve.sh (lee2025 alone has 14 GB of them).
# Restricted to solution/ so vendored .pkl test fixtures under environment/code
# are preserved.
SKIP_PICKLES_UNDER = "solution"


def find_prompt(task: str, version: int | None, skip_missing: bool = False) -> Path | None:
    """Return the minimal prompt for `task`.

    Exits with a helpful message if there is none, unless `skip_missing` (used by
    --all, where one task without the requested version shouldn't abort the run).
    """
    available = {}
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        m = PROMPT_RE.match(path.stem)
        if m and m.group("task").lower() == task.lower():
            available[int(m.group("version"))] = path

    if not available:
        msg = f"no minimal prompt for task '{task}' in {PROMPTS_DIR}"
        if skip_missing:
            print(f"WARNING: skipping {task}: {msg}")
            return None
        print(f"Error: {msg}", file=sys.stderr)
        others = sorted(p.name for p in PROMPTS_DIR.glob("*.md"))
        if others:
            print("Available prompts:", file=sys.stderr)
            for name in others:
                print(f"  {name}", file=sys.stderr)
        sys.exit(1)

    if version is None:
        return available[max(available)]

    if version not in available:
        have = ", ".join(f"v{v}" for v in sorted(available))
        msg = f"no v{version} minimal prompt for task '{task}' (have: {have})"
        if skip_missing:
            print(f"WARNING: skipping {task}: {msg}")
            return None
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)

    return available[version]


def tasks_with_prompts() -> list[str]:
    """Task names (as they appear in harbor-tasks/) that have a minimal prompt."""
    task_dirs = {p.name.lower(): p.name for p in TASKS_DIR.iterdir() if p.is_dir()}
    found = set()
    for path in PROMPTS_DIR.glob("*.md"):
        m = PROMPT_RE.match(path.stem)
        if m:
            name = task_dirs.get(m.group("task").lower())
            if name:
                found.add(name)
    return sorted(found)


def make_ignore(src: Path):
    """shutil.copytree ignore callback; also records what was skipped."""
    skipped = []

    def ignore(directory, contents):
        dir_path = Path(directory)
        rel_dir = dir_path.relative_to(src)
        in_solution = rel_dir.parts[:1] == (SKIP_PICKLES_UNDER,)

        ignored = set()
        for name in contents:
            path = dir_path / name
            if path.is_dir():
                if name in SKIP_DIRS:
                    ignored.add(name)
            elif any(Path(name).match(pat) for pat in SKIP_FILE_PATTERNS):
                ignored.add(name)
            elif in_solution and name.endswith(".pkl"):
                ignored.add(name)
            if name in ignored:
                skipped.append(rel_dir / name)
        return ignored

    return ignore, skipped


def tree_size(path: Path) -> tuple[int, int]:
    """(number of files, total bytes) under `path`."""
    n, total = 0, 0
    for f in path.rglob("*"):
        if f.is_file() and not f.is_symlink():
            n += 1
            total += f.stat().st_size
    return n, total


def human(nbytes: int) -> str:
    size = float(nbytes)
    for unit in ("B", "K", "M", "G", "T"):
        if size < 1024 or unit == "T":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}T"


def check_data_mounts(dst: Path) -> None:
    """Warn if a docker-compose host volume path doesn't resolve from the new task dir."""
    compose = dst / "environment" / "docker-compose.yaml"
    if not compose.exists():
        print(f"WARNING: no {compose.relative_to(dst)} in the copied task")
        return

    for line in compose.read_text().splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        host = stripped[2:].split(":")[0].strip()
        if not host.startswith((".", "/")):
            continue
        resolved = (compose.parent / host).resolve() if host.startswith(".") else Path(host)
        if resolved.exists():
            print(f"  data mount OK: {host} -> {resolved}")
        else:
            print(f"WARNING: data mount does not exist: {host} -> {resolved}")


def generate_minimal_task(src: Path, dst: Path, prompt: Path,
                          force: bool = False, dry_run: bool = False) -> None:
    prefix = "[dry run] " if dry_run else ""

    if not (src / "tests").is_dir():
        print(f"Error: no tests/ directory found in {src}", file=sys.stderr)
        sys.exit(1)

    if dst.exists():
        if not force:
            if not dry_run:
                print(f"Error: output directory already exists: {dst}\n"
                      f"       use --force to regenerate it", file=sys.stderr)
                sys.exit(1)
            print(f"{prefix}WARNING: {dst} already exists; a real run would need --force")
        else:
            print(f"{prefix}rm -r {dst}")
            if not dry_run:
                shutil.rmtree(dst)

    print(f"{prefix}copytree {src} -> {dst}")
    print(f"{prefix}  prompt: {prompt.relative_to(REPO_ROOT)}")

    ignore, skipped = make_ignore(src)

    if dry_run:
        # Walk the tree the way copytree would, just to report what gets skipped.
        for _ in _walk(src, ignore):
            pass
        for rel in skipped:
            print(f"{prefix}  skipping {rel}")
    else:
        shutil.copytree(src, dst, ignore=ignore)
        for rel in skipped:
            print(f"  skipped {rel}")

    # Swap in the minimal prompt as both the agent instruction and the judge reference.
    targets = [INSTRUCTION_FILE, JUDGE_REFERENCE_FILE]
    for alias in JUDGE_REFERENCE_ALIASES:
        if (src / alias).exists():
            print(f"WARNING: {src.name} uses {alias} instead of {JUDGE_REFERENCE_FILE}; "
                  f"writing both (judge_instructions.md reads {JUDGE_REFERENCE_FILE})")
            targets.append(alias)

    for rel in targets:
        print(f"{prefix}write {rel} <- {prompt.name}")
        if not dry_run:
            shutil.copy2(prompt, dst / rel)

    if dry_run:
        return

    nfiles, nbytes = tree_size(dst)
    print(f"  copied {nfiles} files, {human(nbytes)}")
    check_data_mounts(dst)
    print(f"Done: {dst}")
    print(f"Run it with: harbor-scripts/run_harbor.sh --task {dst.name} --agent claude")


def _walk(src: Path, ignore):
    """Minimal os.walk equivalent that applies the copytree ignore callback."""
    contents = sorted(p.name for p in src.iterdir())
    ignored = ignore(str(src), contents)
    dirnames = [n for n in contents if (src / n).is_dir() and n not in ignored]
    filenames = [n for n in contents if not (src / n).is_dir() and n not in ignored]
    yield src, dirnames, filenames
    for name in dirnames:
        yield from _walk(src / name, ignore)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a minimal-prompt version of a harbor task.")
    parser.add_argument(
        "task", nargs="*",
        help="Task name(s), e.g. sosa2024. Omit and use --all for every task with a prompt",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Generate for every task in harbor-tasks/ that has a minimal prompt",
    )
    parser.add_argument(
        "--version", "-v",
        help="Minimal prompt version to use, e.g. 2 or v2 (default: highest available)",
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Path to a specific prompt file, overriding --version (single task only)",
    )
    parser.add_argument(
        "--suffix", default="minimal",
        help="Suffix for the generated task directory (default: minimal)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory, overriding --suffix (single task only)",
    )
    parser.add_argument(
        "--force", "-f", action="store_true",
        help="Remove and regenerate the output directory if it already exists",
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true",
        help="Print what would be done without copying anything",
    )
    args = parser.parse_args()

    version = None
    if args.version is not None:
        try:
            version = int(str(args.version).lstrip("vV"))
        except ValueError:
            print(f"Error: --version must be a number like 2 or v2, got '{args.version}'",
                  file=sys.stderr)
            sys.exit(1)

    if args.all:
        if args.task:
            print("Error: pass either task names or --all, not both", file=sys.stderr)
            sys.exit(1)
        tasks = tasks_with_prompts()
        if not tasks:
            print(f"Error: no task in {TASKS_DIR} has a prompt in {PROMPTS_DIR}",
                  file=sys.stderr)
            sys.exit(1)
        print(f"Tasks with minimal prompts: {', '.join(tasks)}")
    elif args.task:
        tasks = args.task
    else:
        parser.error("give at least one task name, or --all")

    if len(tasks) > 1 and (args.prompt or args.output):
        print("Error: --prompt/--output only make sense for a single task", file=sys.stderr)
        sys.exit(1)

    for task in tasks:
        # Accept a bare name, harbor-tasks/<name>, or an absolute path.
        candidate = Path(task)
        src = candidate.resolve() if candidate.is_absolute() else (REPO_ROOT / task).resolve()
        if not src.is_dir():
            src = (TASKS_DIR / task).resolve()
        if not src.is_dir():
            print(f"Error: task directory not found: {src}", file=sys.stderr)
            sys.exit(1)

        if args.prompt:
            prompt = Path(args.prompt).resolve()
            if not prompt.is_file():
                print(f"Error: prompt file not found: {prompt}", file=sys.stderr)
                sys.exit(1)
        else:
            prompt = find_prompt(src.name, version, skip_missing=args.all)
            if prompt is None:
                continue

        if args.output:
            dst = Path(args.output).resolve()
        else:
            dst = src.parent / f"{src.name}_{args.suffix}"

        generate_minimal_task(src, dst, prompt, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
