#!/usr/bin/env python3
"""
Rebuild each dataset's ``eval_summary.md`` so it carries one rating column per
evaluator.

The judge columns (Claude judge / Codex judge), the Best / Why adjudication and
the per-question overall comments are read back from the existing file and
preserved verbatim; only the evaluator columns are regenerated, straight from
each rater's dossier copies under ``<dataset>/<CODE>/``.

That makes this both the one-off migration (``Human`` → ``LZ``) and the routine
"KB finished a dataset, fold their ratings in" step.

Usage::

    python3 merge_eval.py                 # dry run over every dataset
    python3 merge_eval.py --apply
    python3 merge_eval.py --apply --dataset allen2p
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

import raters as R
from compare import parse_summary, write_summary


def rebuild(dataset: str, apply: bool = False, context: int = 2) -> bool:
    """Rewrite one dataset's eval_summary.md. Returns True if it changed."""
    path = R.eval_summary_path(dataset)
    if not path.exists():
        print(f"── {dataset}: no eval_summary.md, skipped")
        return False

    before = path.read_text()
    entries, overalls = parse_summary(path)
    if not entries:
        print(f"── {dataset}: no parsable rows, skipped")
        return False
    titles = {qid: v["title"] for (qid, _, _), v in entries.items() if v.get("title")}

    # "Best: Human" predates named evaluators — it always meant the evaluator
    # who ran the judge comparison, i.e. the primary one.
    primary = R.primary_code()
    for v in entries.values():
        if (v.get("best") or "").strip().lower() == "human":
            v["best"] = primary

    codes = R.active_rater_codes(dataset)
    counts = {c: 0 for c in codes}
    disk = R.collect_ratings(dataset, codes)
    for per_trial in disk.values():
        for cell in per_trial.values():
            for c in codes:
                counts[c] += bool(cell.get(c))

    print(f"── {dataset}: evaluators {', '.join(codes) or '(none)'}  "
          + "  ".join(f"{c}={counts[c]} ratings" for c in codes))

    # write_summary writes atomically; for a dry run, render into a temp copy.
    target = path if apply else path.with_suffix(".md.preview")
    write_summary(target, entries, titles, overalls)
    after = target.read_text()
    if not apply:
        target.unlink()

    if after == before:
        print("   (unchanged)")
        return False

    diff = list(difflib.unified_diff(
        before.splitlines(), after.splitlines(),
        fromfile=f"{dataset}/eval_summary.md (before)",
        tofile=f"{dataset}/eval_summary.md (after)",
        lineterm="", n=context,
    ))
    for line in diff[:40]:
        print("   " + line)
    if len(diff) > 40:
        print(f"   … {len(diff) - 40} more diff lines")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--dataset", help="Only rebuild one dataset")
    ap.add_argument("--apply", action="store_true", help="Actually write the files")
    args = ap.parse_args()

    ds_list = [args.dataset] if args.dataset else R.datasets()
    changed = 0
    for dataset in ds_list:
        if rebuild(dataset, apply=args.apply):
            changed += 1
        print()

    verb = "rewritten" if args.apply else "would change"
    print(f"{changed}/{len(ds_list)} eval_summary.md {verb}.")
    if not args.apply and changed:
        print("Re-run with --apply to write them.")


if __name__ == "__main__":
    main()
