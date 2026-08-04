#!/usr/bin/env python3
"""
Re-key summary-style files to the question numbering the dossiers use.

``summary.md`` and ``eval_summary.md`` are written with the question numbers
that the *reference* had at rating time. When the reference is later renumbered
(sosa2024 gained two "thresholded into categories" sub-questions, which pushed
"aligned with the neural data" from ``7-c`` to ``7-d``), those files keep the
old numbers while the dossiers move on. Anything that then joins the two by qid
— folding in a second evaluator's ratings, for instance — silently pairs one
question's rating with another question's judges.

This rewrites the ``## Q <qid>.`` headings of the summary files so each section
carries the qid its *title* has in the dossiers. Section contents are untouched.

Usage::

    python3 renumber_summary.py <dataset>            # dry run
    python3 renumber_summary.py <dataset> --apply
"""

from __future__ import annotations

import argparse
import re
import sys

import sys
from pathlib import Path

# Archived: still runnable — the rating tools are the `ratings` package
# one level up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ratings import raters as R

_HEADING = re.compile(r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$", re.MULTILINE)


def plan(path, dossier_by_title: dict[str, str]) -> list[tuple[str, str, str]]:
    """Return [(old_qid, new_qid, title)] for headings whose number is stale."""
    if not path.exists():
        return []
    out = []
    for m in _HEADING.finditer(path.read_text()):
        old, title = m.group(1), m.group(2).strip()
        new = dossier_by_title.get(R.normalize_title(title))
        if new and new != old:
            out.append((old, new, title))
        elif new is None:
            print(f"   ? {path.parent.name}/{path.name} Q {old}: no dossier section "
                  f"matches {title!r} — left alone")
    return out


def apply_changes(path, changes: list[tuple[str, str, str]]):
    text = path.read_text()
    # Rewrite in one pass so a swap (7-c→7-d while 7-d→7-e) can't clobber itself.
    by_old = {old: new for old, new, _ in changes}

    def sub(m):
        old, title = m.group(1), m.group(2)
        return f"## Q {by_old.get(old, old)}. {title}"

    R.atomic_write(path, _HEADING.sub(sub, text))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("dataset")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    titles = R.collect_titles(args.dataset)
    if not titles:
        sys.exit(f"No dossiers found for {args.dataset}")
    dossier_by_title = {R.normalize_title(t): qid for qid, t in titles.items()}

    paths = [R.eval_summary_path(args.dataset)]
    paths += [R.summary_path(args.dataset, c)
              for c in R.active_rater_codes(args.dataset)]

    total = 0
    for path in paths:
        changes = plan(path, dossier_by_title)
        if not changes:
            continue
        print(f"── {path.parent.name}/{path.name}")
        for old, new, title in changes:
            print(f"   Q {old} → Q {new}   ({title[:70]})")
        total += len(changes)
        if args.apply:
            apply_changes(path, changes)

    if not total:
        print(f"{args.dataset}: numbering already matches the dossiers.")
    elif args.apply:
        print(f"\nRenumbered {total} heading(s). "
              f"Now re-run:  python3 raters.py merge {args.dataset} --apply")
    else:
        print(f"\n{total} heading(s) would change. Re-run with --apply.")


if __name__ == "__main__":
    main()
