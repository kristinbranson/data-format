#!/usr/bin/env python3
"""Generate a minimal version of a maximal task prompt.

Strips the procedural scaffolding (critical constraints, python environment,
13-step conversion workflow, CONVERSION_NOTES template, key considerations) from a
maximal prompt, leaving the task specification and format requirements, and writes
minimal_prompts/<task>_prompt_minimal_v<N>.md.

Each minimal version has one maximal source (MINIMAL_SOURCES):

    minimal v1  <-  prompt_v4/<task>_prompt_v4.md   (the preprint's prompts)
    minimal v2  <-  prompt_v5/<task>_prompt_v5.md

v2 additionally drops what only a prompt with the step-by-step workflow needs: the
consistency paragraphs about sanity checks and verifying every step, the "Pipe the output"
instruction, and the long Success Criteria list, which becomes a short list requiring
only convert_data.py and converted_data.pkl (the files tests/expected_files.json requires
for minimal tasks).

The v1 transform reproduces the hand-written minimal_prompts/sosa2024_prompt_minimal_v1.md
byte-for-byte; run with --check to verify that regression.

Usage:
    python generate_minimal_prompt.py --all                # every prompt, minimal v1
    python generate_minimal_prompt.py --all --version 2    # every prompt, minimal v2
    python generate_minimal_prompt.py sosa2024             # one task
    python generate_minimal_prompt.py --all --check        # verify only, write nothing
    python generate_minimal_prompt.py --all --force        # overwrite existing outputs
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MINIMAL_DIR = REPO_ROOT / "minimal_prompts"

# minimal version -> maximal prompt version it is generated from
MINIMAL_SOURCES = {1: 4, 2: 5}

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

# --- additional v2 edits (minimal prompt generated from prompt_v5) ---

# The consistency paragraphs from "To check consistency" through the "You will be assessed
# on whether the decisions" paragraph, which ends the Consistency requirements section.
# They tell the agent to invent sanity checks and verify every step, which belongs with the
# step-by-step workflow. The discrepancy sentence and the sentence about how the reference
# decoder is run are kept, as one paragraph.
V2_CONSISTENCY_RE = re.compile(
    r"^To check consistency, you must compare statistics.*?"
    r"^(?P<discrepancy>Discrepancies are only allowed if required by .*?)\n.*?"
    r"^You will be assessed on whether the decisions you make .*?(?P<testing>During testing, .*?)[ \t]*$",
    re.M | re.S)
V2_TESTING_SENTENCE = (
    "During testing, a reference copy of `/app/train_decoder.py` will be run on your converted "
    "data. Data statistics and decoder accuracy will be compared to those achieved by "
    "human-written conversion code.")
V2_PIPE_OUTPUT_RE = re.compile(r"^- Pipe the output to the designated file so that the user can examine it\.[ \t]*\n",
                               re.M)
# The whole Success Criteria section, which is the end of the prompt.
V2_SUCCESS_RE = re.compile(r"^## Success Criteria\n.*\Z", re.M | re.S)
# Items 1-6 are the terminal-bench-science minimal list; item 7 is the decision-rating
# criterion, the same text as item 11 of the maximal prompt, read from it.
V2_SUCCESS_HEAD = """## Success Criteria

A successful conversion should:
1. All required files must be created:
  - `/app/convert_data.py`
  - `/app/converted_data.pkl`
2. Match the target data structure exactly
3. Have consistent dimensions across trials/sessions
4. Include all relevant data from the source
5. Match information provided in the reference texts, code, and these instructions
6. Outputs must match expert-written conversion code in:
  - Dataset size and distribution statistics
  - Decoder accuracy
"""
V2_DECISION_ITEM_RE = re.compile(r"^11\. (?P<text>Each decision about how to load.*)$", re.M)


def minimalize_v2_extra(text: str, maximal: str) -> tuple[str, list[str]]:
    """Apply the edits minimal v2 makes beyond the v1 transform.

    Args:
        text: the prompt after minimalize().
        maximal: the full prompt_v5 text, from which the decision-rating criterion is read.

    Returns:
        (edited text, notes describing what was done).

    Raises:
        ValueError: if a section these edits expect is missing, so a prompt that differs
            from the v5 layout fails loudly instead of being half edited.
    """
    notes = []
    match = V2_CONSISTENCY_RE.search(text)
    if not match:
        raise ValueError("v2: consistency paragraphs not found")
    if not match.group("testing").startswith("During testing"):
        raise ValueError("v2: testing sentence not found in the assessment paragraph")
    text = (text[:match.start()] + match.group("discrepancy").rstrip() + " "
            + V2_TESTING_SENTENCE + text[match.end():])
    notes.append("dropped the sanity-check, verify-every-step and decision-assessment paragraphs")

    text, n = V2_PIPE_OUTPUT_RE.subn("", text)
    if n != 1:
        raise ValueError(f"v2: expected one 'Pipe the output' line, found {n}")
    notes.append("dropped the 'Pipe the output' line")

    decision = V2_DECISION_ITEM_RE.search(maximal)
    if not decision:
        raise ValueError("v2: Success Criteria item 11 not found in the maximal prompt")
    success = V2_SUCCESS_HEAD + f"7. {decision.group('text')}\n"
    text, n = V2_SUCCESS_RE.subn(lambda _: success, text)
    if n != 1:
        raise ValueError("v2: Success Criteria section not found")
    notes.append("replaced Success Criteria with the minimal list (2 required files)")
    return text, notes


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


def generate(src: Path, dst: Path, version: int, force: bool = False,
             check: bool = False, dry_run: bool = False) -> bool:
    """Write the minimal prompt. Returns True on success/no-op, False on mismatch."""
    prefix = "[dry run] " if dry_run else ""
    text = src.read_text()
    out, notes = minimalize(text)
    if version >= 2:
        out, more = minimalize_v2_extra(out, text)
        notes += more

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


def source_dir_and_suffix(version: int) -> tuple[Path, str]:
    """Directory and filename suffix of the maximal prompts minimal `version` is made from."""
    if version not in MINIMAL_SOURCES:
        print(f"Error: no maximal source defined for minimal v{version} "
              f"(known: {sorted(MINIMAL_SOURCES)})", file=sys.stderr)
        sys.exit(1)
    maximal = MINIMAL_SOURCES[version]
    return REPO_ROOT / f"prompt_v{maximal}", f"_prompt_v{maximal}.md"


def resolve_source(task: str, version: int) -> Path:
    """Map a task name (or path) to its maximal prompt file, case-insensitively."""
    candidate = Path(task)
    if candidate.is_file():
        return candidate.resolve()

    source_dir, suffix = source_dir_and_suffix(version)
    for path in sorted(source_dir.glob(f"*{suffix}")):
        stem = path.name[: -len(suffix)]
        if stem.lower() == task.lower():
            return path

    print(f"Error: no prompt for task '{task}' in {source_dir}", file=sys.stderr)
    print("Available:", file=sys.stderr)
    for path in sorted(source_dir.glob(f"*{suffix}")):
        print(f"  {path.name}", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Generate minimal versions of the maximal task prompts.")
    parser.add_argument("task", nargs="*",
                        help="Task name(s), e.g. sosa2024. Omit and use --all for every prompt")
    parser.add_argument("--all", action="store_true",
                        help="Process every prompt in the maximal source directory for --version")
    parser.add_argument("--version", "-v", default="1",
                        help="Minimal prompt version to write (default: 1). v1 is made from prompt_v4, "
                             "v2 from prompt_v5")
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
        source_dir, suffix = source_dir_and_suffix(version)
        sources = sorted(source_dir.glob(f"*{suffix}"))
        if not sources:
            print(f"Error: no *{suffix} files in {source_dir}", file=sys.stderr)
            sys.exit(1)
    elif args.task:
        sources = [resolve_source(t, version) for t in args.task]
    else:
        parser.error("give at least one task name, or --all")

    ok = True
    for src in sources:
        stem = re.sub(r"_prompt_v\d+\.md$", "", src.name)
        dst = MINIMAL_DIR / f"{stem}_prompt_minimal_v{version}.md"
        ok &= generate(src, dst, version, force=args.force, check=args.check,
                       dry_run=args.dry_run)

    if not ok:
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
