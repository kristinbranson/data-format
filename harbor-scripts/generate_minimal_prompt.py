#!/usr/bin/env python3
"""Generate a minimal version of a v4 task prompt.

Strips the procedural scaffolding (critical constraints, python environment,
13-step conversion workflow, CONVERSION_NOTES template, key considerations) from
prompt_v4/<task>_prompt_v4.md, leaving the task specification and format
requirements, and writes minimal_prompts/<task>_prompt_minimal_v<N>.md.

The transform reproduces the hand-written minimal_prompts/sosa2024_prompt_minimal_v1.md
byte-for-byte; run with --check to verify that regression.

Usage:
    python generate_minimal_prompt.py --all           # every prompt in prompt_v4/
    python generate_minimal_prompt.py sosa2024        # one task
    python generate_minimal_prompt.py --all --check   # verify only, write nothing
    python generate_minimal_prompt.py --all --force   # overwrite existing outputs
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_V4_DIR = REPO_ROOT / "prompt_v4"
MINIMAL_DIR = REPO_ROOT / "minimal_prompts"

# Top-level sections removed wholesale: procedural scaffolding, not task content.
DROP_SECTIONS = {
    "## ⚠️ CRITICAL CONSTRAINTS — READ FIRST ⚠️",
    "## Python environment",
    "## Conversion Workflow",
    "## CONVERSION_NOTES.md Template",
    "## Key Considerations",
}

# Top-level sections kept. Anything outside these two sets is unrecognized and
# gets a warning, so a future prompt version adding a section is not silently
# swept into the minimal prompt.
KEEP_SECTIONS = {
    "## Project Context",
    "## Reference Information",
    "## Decoder Task",
    "## Target Data Format",
    "## Decoder Reference",
    "## Success Criteria",
}

# Line-level edits, applied after section filtering.
PERSONA = ("- You are a computational neuroscientist. Your goal is", "- Your goal is")
DOC_BULLET_RE = re.compile(r"^- \*\*Documentation\*\*.*\n", re.M)
# Horizontal rule orphaned by dropping the sections before Success Criteria.
ORPHAN_RULE_RE = re.compile(r"\n---\n\n(?=## Success Criteria)")


def minimalize(text: str) -> tuple[str, list[str]]:
    """Return (minimal prompt, notes describing what the transform did)."""
    kept, dropped, unknown = [], [], []
    dropping, in_fence = False, False

    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        # Track code fences: the CONVERSION_NOTES template is a fenced block full
        # of '##' headings that must not be read as section boundaries.
        if stripped.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and stripped.startswith("## "):
            dropping = stripped in DROP_SECTIONS
            if dropping:
                dropped.append(stripped)
            elif stripped not in KEEP_SECTIONS:
                unknown.append(stripped)
        if not dropping:
            kept.append(line)

    out = "".join(kept)
    notes = [f"dropped {s}" for s in dropped]

    if PERSONA[0] in out:
        out = out.replace(*PERSONA)
        notes.append("dropped the 'computational neuroscientist' persona")

    doc = DOC_BULLET_RE.search(out)
    if doc:
        out = DOC_BULLET_RE.sub("", out)
        notes.append(f"dropped documentation bullet: {doc.group().strip()}")

    out, n = ORPHAN_RULE_RE.subn("\n", out)
    if n:
        notes.append("collapsed the orphaned '---' before Success Criteria")

    for section in unknown:
        notes.append(f"WARNING: unrecognized section kept as-is: {section}")

    return out, notes


def generate(src: Path, dst: Path, force: bool = False,
             check: bool = False, dry_run: bool = False) -> bool:
    """Write the minimal prompt. Returns True on success/no-op, False on mismatch."""
    prefix = "[dry run] " if dry_run else ""
    text = src.read_text()
    out, notes = minimalize(text)

    n_in, n_out = len(text.splitlines()), len(out.splitlines())
    print(f"{prefix}{src.relative_to(REPO_ROOT)} ({n_in} lines) -> "
          f"{dst.relative_to(REPO_ROOT)} ({n_out} lines)")
    for note in notes:
        print(f"{prefix}  {note}")

    existing = dst.read_text() if dst.exists() else None

    if check:
        if existing is None:
            print(f"  CHECK: {dst.relative_to(REPO_ROOT)} does not exist")
            return False
        if existing == out:
            print("  CHECK: matches the existing file exactly")
            return True
        print(f"  CHECK: DIFFERS from the existing file", file=sys.stderr)
        sys.stderr.writelines(difflib.unified_diff(
            existing.splitlines(True), out.splitlines(True),
            f"existing/{dst.name}", f"generated/{dst.name}", n=2))
        return False

    if existing is not None:
        if existing == out:
            print("  unchanged (regenerates identically)")
            return True
        if not force:
            print(f"Error: {dst} exists and differs; use --force to overwrite",
                  file=sys.stderr)
            return False
        print(f"{prefix}  overwriting (--force)")

    if not dry_run:
        dst.write_text(out)
    return True


def resolve_source(task: str) -> Path:
    """Map a task name (or path) to its prompt_v4 file, case-insensitively."""
    candidate = Path(task)
    if candidate.is_file():
        return candidate.resolve()

    for path in sorted(PROMPT_V4_DIR.glob("*_prompt_v4.md")):
        stem = path.name[: -len("_prompt_v4.md")]
        if stem.lower() == task.lower():
            return path

    print(f"Error: no prompt for task '{task}' in {PROMPT_V4_DIR}", file=sys.stderr)
    print("Available:", file=sys.stderr)
    for path in sorted(PROMPT_V4_DIR.glob("*_prompt_v4.md")):
        print(f"  {path.name}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate minimal versions of the v4 task prompts.")
    parser.add_argument("task", nargs="*",
                        help="Task name(s), e.g. sosa2024. Omit and use --all for every prompt")
    parser.add_argument("--all", action="store_true",
                        help="Process every prompt in prompt_v4/")
    parser.add_argument("--version", "-v", default="1",
                        help="Version number for the output filename (default: 1)")
    parser.add_argument("--check", "-c", action="store_true",
                        help="Compare against existing minimal prompts and report; write nothing")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Overwrite existing minimal prompts that differ")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Print what would be done without writing anything")
    args = parser.parse_args()

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
        sources = sorted(PROMPT_V4_DIR.glob("*_prompt_v4.md"))
        if not sources:
            print(f"Error: no *_prompt_v4.md files in {PROMPT_V4_DIR}", file=sys.stderr)
            sys.exit(1)
    elif args.task:
        sources = [resolve_source(t) for t in args.task]
    else:
        parser.error("give at least one task name, or --all")

    ok = True
    for src in sources:
        stem = src.name[: -len("_prompt_v4.md")]
        dst = MINIMAL_DIR / f"{stem}_prompt_minimal_v{version}.md"
        ok &= generate(src, dst, force=args.force, check=args.check, dry_run=args.dry_run)

    if not ok:
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
