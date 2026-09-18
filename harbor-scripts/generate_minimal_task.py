#!/usr/bin/env python3
"""Generate a minimal-prompt version of a harbor task.

Copies the task directory, then writes the files that differ from the parent task
because the prompt differs ("derived files"):

    instruction.md                  the minimal prompt from minimal_prompts/
    tests/instruction_reference.md  the same prompt, for the judges
    tests/expected_files.json       the agent files the minimal prompt asks for
    tests/judge_instructions*.md    the parent's judge instructions, describing only those files

Everything else (tests, solution, environment) is copied unchanged.

Usage:
    python generate_minimal_task.py sosa2024              # highest prompt version
    python generate_minimal_task.py sosa2024 --version 2  # pin to v2
    python generate_minimal_task.py --all --version 1     # all tasks with a v1 prompt
    python generate_minimal_task.py sosa2024 --dry-run
    python generate_minimal_task.py sosa2024 --force      # regenerate in place
    python generate_minimal_task.py --all --update        # rewrite derived files only
    python generate_minimal_task.py --all --check         # report stale derived files
"""

import argparse
import json
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

# The agent files the minimal prompt asks for, read by test_outputs.py (which files
# fail the test) and by the judge instructions. The minimal prompt asks for no notes,
# README, sample pickle or logs, so this is exactly CORE_FILES in
# template-harbor-task/tests/test_outputs.py, which refuses a list missing any of them.
EXPECTED_FILES_FILE = "tests/expected_files.json"
MINIMAL_EXPECTED_FILES = {
    "_comment": [
        "Agent files test_outputs.py checks for this task, matching what its instruction.md asks for.",
        "required: missing or empty fails the test. expected: only warned about.",
        "Minimal-prompt list, written by harbor-scripts/generate_minimal_task.py.",
    ],
    "required": ["convert_data.py", "converted_data.pkl"],
    "expected": [],
}

# The LLM judges' instructions. Written by hand for the maximal task, which describes the
# agent's notes, README and logs; the minimal task's copies describe only the files its
# prompt asks for (MINIMAL_EXPECTED_FILES). Everything else, including every question, is
# copied unchanged.
JUDGE_INSTRUCTION_FILES = ["tests/judge_instructions.md", "tests/judge_instructions_unsupervised.md"]
# One entry of the "Agentic AI Outputs" file tree, plus the continuation lines of its comment.
TREE_ENTRY_RE = re.compile(r"^  ├── (?P<name>\S+).*\n(?:^  │ .*\n)*", re.M)
TREE_BLOCK_RE = re.compile(r"(?<=\*\*Agentic AI Outputs\*\* \(the code/files the AI created are in `/app`\):\n  /app/\n)"
                           r"(?:^  [├│].*\n)+", re.M)
JUSTIFICATION = ("Summarize the AI's justification for its decisions (from CONVERSION_NOTES.md or trajectory).",
                 "Summarize the AI's justification for its decisions (from the agent trajectory).")

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


def judge_instructions_for(text: str, agent_files: set[str]) -> str:
    """Rewrite a maximal task's judge instructions for a task that asks for fewer files.

    Args:
        text: the maximal task's judge instructions.
        agent_files: names of the agent files the task asks for (required and expected).

    Returns:
        str, the instructions with the "Agentic AI Outputs" tree limited to agent_files, and
        the justification question pointed at the trajectory when there are no notes.

    Raises:
        ValueError: if the file tree or the justification question is not found exactly once,
            so instructions whose layout has changed are not silently left describing files
            the agent was never asked for.
    """
    blocks = TREE_BLOCK_RE.findall(text)
    if len(blocks) != 1:
        raise ValueError(f"expected one 'Agentic AI Outputs' file tree, found {len(blocks)}")
    kept = "".join(entry.group(0) for entry in TREE_ENTRY_RE.finditer(blocks[0])
                   if entry.group("name") in agent_files)
    text = TREE_BLOCK_RE.sub(lambda _: kept, text)
    if "CONVERSION_NOTES.md" not in agent_files:
        if text.count(JUSTIFICATION[0]) != 1:
            raise ValueError("expected one justification question naming CONVERSION_NOTES.md")
        text = text.replace(*JUSTIFICATION)
    return text


def derived_files(src: Path, prompt: Path) -> dict[str, str]:
    """Contents of every file a minimal task derives from its prompt.

    Args:
        src: the parent (maximal) task directory; decides whether the zhang2025-style
            reference alias is also written.
        prompt: the minimal prompt file.

    Returns:
        dict mapping path relative to the minimal task directory -> file text.
    """
    prompt_text = prompt.read_text()
    files = {INSTRUCTION_FILE: prompt_text, JUDGE_REFERENCE_FILE: prompt_text}
    for alias in JUDGE_REFERENCE_ALIASES:
        if (src / alias).exists():
            files[alias] = prompt_text
    files[EXPECTED_FILES_FILE] = json.dumps(MINIMAL_EXPECTED_FILES, indent=2) + "\n"
    agent_files = set(MINIMAL_EXPECTED_FILES["required"]) | set(MINIMAL_EXPECTED_FILES["expected"])
    for rel in JUDGE_INSTRUCTION_FILES:
        if (src / rel).exists():
            files[rel] = judge_instructions_for((src / rel).read_text(), agent_files)
    return files


def write_derived_files(src: Path, dst: Path, prompt: Path, dry_run: bool = False) -> None:
    """Write the prompt-derived files into an existing minimal task directory.

    Args:
        src: parent task directory.
        dst: minimal task directory (must exist unless dry_run).
        prompt: the minimal prompt file.
        dry_run: print what would be written, write nothing.

    Side effects: overwrites the files listed by derived_files() under dst.
    """
    prefix = "[dry run] " if dry_run else ""
    for alias in JUDGE_REFERENCE_ALIASES:
        if (src / alias).exists():
            print(f"WARNING: {src.name} uses {alias} instead of {JUDGE_REFERENCE_FILE}; "
                  f"writing both (judge_instructions.md reads {JUDGE_REFERENCE_FILE})")
    for rel, text in derived_files(src, prompt).items():
        print(f"{prefix}write {dst.name}/{rel}")
        if not dry_run:
            (dst / rel).write_text(text)


def stale_derived_files(src: Path, dst: Path, prompt: Path) -> list[str]:
    """Derived files in dst that are missing or differ from what would be generated.

    Returns:
        list of str paths relative to dst; empty when everything is current.
    """
    stale = []
    for rel, text in derived_files(src, prompt).items():
        path = dst / rel
        if not path.is_file() or path.read_text() != text:
            stale.append(rel)
    return stale


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

    write_derived_files(src, dst, prompt, dry_run=dry_run)

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
    parser.add_argument(
        "--update", action="store_true",
        help="Rewrite only the derived files (prompt copies, expected_files.json) in an "
             "existing minimal task, leaving everything else untouched",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Report derived files that are missing or out of date; write nothing. "
             "Exits 1 if any are",
    )
    args = parser.parse_args()
    if args.update and args.check:
        parser.error("--update and --check are mutually exclusive")

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

    n_stale = 0
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

        if args.update or args.check:
            if not dst.is_dir():
                print(f"Error: {dst} does not exist; generate it first", file=sys.stderr)
                sys.exit(1)
            if args.check:
                stale = stale_derived_files(src, dst, prompt)
                n_stale += len(stale)
                for rel in stale:
                    print(f"STALE: {dst.name}/{rel} (from {prompt.name})")
            else:
                write_derived_files(src, dst, prompt, dry_run=args.dry_run)
            continue

        generate_minimal_task(src, dst, prompt, force=args.force, dry_run=args.dry_run)

    if args.check:
        print(f"{n_stale} stale derived file(s)")
        sys.exit(1 if n_stale else 0)


if __name__ == "__main__":
    main()
