#!/usr/bin/env python3
"""Compare the output classes an instruction.md declares against the reference's.

The verifier compares each output variable's range to `reference_stats_full.json` at ZERO
tolerance, so a conversion emitting a different number of classes fails outright. Nothing
checks that the instruction actually asks for the number the reference produces. When it
does not, an agent that follows the prompt exactly cannot pass -- the failure looks like
an agent error and is a task defect.

This has bitten three tasks:
  * zhong2025 -- a trailing 'none' padding symbol made the reference emit 3/5/5 classes
    while the instruction had always specified 2/4/4.
  * chen2024  -- the reference gave `choice` a third 'no lick' class and
    `tongue_y_position` a fourth 'not visible' class; the instruction named neither, and
    an agent run lost both output categories for doing what it was told.
  * hasnain2024 -- ordering was right but the per-trial outputs listed names with no
    codes, so nothing pinned left=0 against right=0. A permuted labelling scores
    identically: same class count, near-identical fractions, and balanced accuracy is
    invariant to relabelling.

Reference side is read from `reference_stats_full.json` rather than parsed out of
`reference_convert_data.py`: only one task defines a literal OUTPUT_VALUES list, the rest
build it from dicts, and the stats file is what the verifier actually grades against.

Instruction side is parsed from prose, so it is best effort. Anything it cannot read is
reported as UNKNOWN for a human to check rather than guessed at.

Usage:
    python3 check_output_classes.py <task-dir> [<task-dir> ...]

Exit status is 1 if any task has a definite mismatch, 0 otherwise (UNKNOWN does not fail).
"""

import json
import os
import re
import sys

WORD_NUMBERS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10}


def reference_nclasses(task_dir):
    """Class count per output variable, from the stats the verifier compares against.

    Args:
        task_dir: str, task directory holding tests/reference_stats_full.json.

    Returns:
        dict of output name -> int class count, taken as max(range) + 1. Empty if the
        file or its output_range field is missing.
    """
    path = os.path.join(task_dir, "tests", "reference_stats_full.json")
    try:
        with open(path) as handle:
            ranges = json.load(handle)["data_summary"]["output_range"]
    except (OSError, KeyError, ValueError):
        return {}
    return {name: int(hi) + 1 for name, (_lo, hi) in ranges.items()}


def instruction_bullets(task_dir):
    """Top-level bullets of the instruction's Decoder Outputs section, with sub-bullets.

    Args:
        task_dir: str, task directory holding instruction.md.

    Returns:
        list of str, one entry per output variable, sub-bullets folded into the parent so
        that a discretization spelled as `- 0: ...` lines is visible to the parser.
    """
    path = os.path.join(task_dir, "instruction.md")
    with open(path) as handle:
        lines = handle.read().splitlines()

    out, collecting = [], False
    for line in lines:
        if re.match(r"^#+\s", line):
            collecting = bool(re.match(r"^#+\s*Decoder Outputs?\b", line, re.I))
            continue
        if not collecting:
            continue
        if re.match(r"^\s*-\s", line) and not line.startswith((" ", "\t")):
            out.append(line)
        elif out and line.strip():
            out[-1] += " " + line.strip()
    return out


def declared_nclasses(bullet):
    """Number of classes a single instruction bullet declares, or None if unreadable.

    Recognises, in order of trust:
      explicit codes   `left = 0, right = 1`, `0.2 -> 0`, `0 = not licking`
      sub-bullet codes `- 0: < 40th percentile`
      a bin count      `discretized into 4 bins`, `five equal percentile bins`
      `binary`         2

    Args:
        bullet: str, one output bullet with its sub-bullets folded in.

    Returns:
        int, or None when the bullet does not state a count.
    """
    # Arithmetic stating the total, e.g. "discretized into 3 x 3 = 9 spatial bins" -- the
    # product is the class count itself, not a code, and the factors describe the grid.
    # Checked first: the code patterns below would otherwise read `= 9` as a class label
    # and report ten classes.
    match = re.search(r"=\s*(\d+)\b[^.]{0,40}?\bbins\b", bullet, re.I)
    if match:
        return int(match.group(1))

    # `left = 0` and `0 = not licking` are both used, so read codes on either side of the
    # equals sign; `0.2 -> 0` for a mapping; `- 0: ...` for sub-bullet discretizations.
    # Both equals forms require a word on the non-numeric side, so that arithmetic between
    # two numbers is not mistaken for a label being assigned a code.
    codes = [int(n) for n in re.findall(r"[A-Za-z)\]]\s*=\s*(\d+)\b", bullet)]
    codes += [int(n) for n in re.findall(r"\b(\d+)\s*=\s*[A-Za-z]", bullet)]
    codes += [int(n) for n in re.findall(r"->\s*(\d+)\b", bullet)]
    codes += [int(n) for n in re.findall(r"(?:^|\s)-\s*(\d+)\s*:", bullet)]
    if codes:
        return max(codes) + 1

    # A parenthesised list naming the classes, e.g. `(left, right, no lick, per-trial)`.
    # Qualifiers describing the variable rather than a class are dropped, so this counts
    # 3 there and not 4. Requires two or more survivors, so a parenthetical aside with no
    # commas is not mistaken for a single class.
    paren = re.search(r"\(([^()]*)\)", bullet)
    if paren:
        parts = [p.strip() for p in paren.group(1).split(",")]
        parts = [p for p in parts if p and not re.fullmatch(
            r"(per[- ]trial|time[- ]varying|static(\s+per[- ]trial)?|binary|categorical"
            r"|continuous|per[- ]session)", p, re.I)]
        if len(parts) >= 2:
            return len(parts)

    # Any number of adjectives may sit between the count and the word "bins":
    # "5 bins", "five equal percentile bins", "4 equal-length, 1-m-long spatial bins".
    match = re.search(r"into\s+(\d+|[a-z]+)\b[^.]{0,60}?\bbins\b", bullet, re.I)
    if match:
        token = match.group(1).lower()
        if token.isdigit():
            return int(token)
        if token in WORD_NUMBERS:
            return WORD_NUMBERS[token]

    if re.search(r"\bbinary\b", bullet, re.I):
        return 2
    return None


def match_bullets(reference, bullets):
    """Pair each reference output with the instruction bullet that names it.

    Matching is by name, not position: `output_range` is keyed by the reference's own
    variable names and its order does not follow the instruction's bullet order (allen2p
    lists them in a different sequence entirely).

    Args:
        reference: dict of output name -> class count.
        bullets: list of str, the instruction's output bullets.

    Returns:
        dict of output name -> bullet str (empty string when nothing matched).
    """
    unused = list(bullets)
    pairs = {}
    # Highest-scoring pairs first, so a bullet naming every token of one output is not
    # stolen by another that shares only one word ("image change" vs "image name").
    scored = []
    for name in reference:
        tokens = [t for t in re.split(r"[_\s]+", name.lower()) if t]
        for bullet in bullets:
            text = bullet.lower()
            hits = sum(1 for t in tokens if t in text)
            if hits:
                scored.append((hits / len(tokens), hits, name, bullet))
    scored.sort(reverse=True)
    for _score, _hits, name, bullet in scored:
        if name not in pairs and bullet in unused:
            pairs[name] = bullet
            unused.remove(bullet)
    return {name: pairs.get(name, "") for name in reference}


def check(task_dir):
    """Report declared-vs-reference class counts for one task.

    Args:
        task_dir: str, path to the task directory.

    Returns:
        int count of definite mismatches (UNKNOWN entries are not counted).

    Side effects:
        Prints one line per output variable.
    """
    name = os.path.basename(os.path.normpath(task_dir))
    reference = reference_nclasses(task_dir)
    print(f"\n{name}")
    if not reference:
        print("  ! no output_range in tests/reference_stats_full.json; cannot check")
        return 0
    bullets = instruction_bullets(task_dir)
    if len(bullets) != len(reference):
        print(f"  ! {len(bullets)} instruction bullet(s) vs {len(reference)} reference "
              f"output(s)")
    paired = match_bullets(reference, bullets)

    mismatches = 0
    for out_name, n_ref in reference.items():
        bullet = paired[out_name]
        n_dec = declared_nclasses(bullet) if bullet else None
        label = re.sub(r"\s+", " ", bullet)[:70] or "(no matching bullet)"
        if n_dec is None:
            verdict = "UNKNOWN  (instruction states no count)"
        elif n_dec == n_ref:
            verdict = "ok"
        else:
            verdict = f"MISMATCH declared {n_dec}"
            mismatches += 1
        print(f"  {out_name:<26} reference {n_ref:>2}  {verdict}")
        if n_dec is None or n_dec != n_ref:
            print(f"      instruction: {label}")
    return mismatches


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    total = sum(check(d) for d in sys.argv[1:])
    print(f"\n{total} definite mismatch(es).")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
