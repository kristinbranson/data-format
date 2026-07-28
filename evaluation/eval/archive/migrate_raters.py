#!/usr/bin/env python3
"""
One-off migration: single-evaluator layout → per-rater subfolders.

Before::

    eval/<dataset>/claude-code_trial1.md   (content + LZ's ratings)
    eval/<dataset>/summary.md              (LZ's per-question tables)

After::

    eval/<dataset>/claude-code_trial1.md   (content, ratings reset to placeholder)
    eval/<dataset>/LZ/claude-code_trial1.md  (content + LZ's ratings)
    eval/<dataset>/LZ/summary.md

``eval_summary.md`` and ``report.md`` stay at the dataset root (they combine all
raters). Nothing is deleted: summary.md is *copied* into the rater folder, and
the root copy is removed only with --drop-root-summary.

Usage::

    python3 migrate_raters.py                 # dry run, prints the plan
    python3 migrate_raters.py --apply
    python3 migrate_raters.py --apply --rater LZ --dataset allen2p
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import raters as R


def plan_dataset(dataset: str, code: str) -> list[tuple[str, str]]:
    """Return a list of (action, detail) for one dataset."""
    actions = []
    ddir = R.dataset_dir(dataset)
    rdir = R.rater_dir(dataset, code)

    for name in R.DOSSIER_NAMES:
        master = ddir / name
        dest = rdir / name
        if not master.exists():
            actions.append(("skip", f"{name}: no master dossier"))
            continue
        rated = sum(1 for v in R.parse_ratings(master).values() if v["rating"])
        total = len(R.parse_ratings(master))
        if dest.exists():
            actions.append(("keep", f"{code}/{name}: already exists, left alone"))
        else:
            actions.append(("copy", f"{name} → {code}/{name}  ({rated}/{total} rated)"))
        if rated:
            actions.append(("blank", f"{name}: reset {rated} Rating/Note lines to placeholder"))

    src_summary = ddir / "summary.md"
    dst_summary = rdir / "summary.md"
    if src_summary.exists():
        if dst_summary.exists():
            actions.append(("keep", f"{code}/summary.md: already exists, left alone"))
        else:
            actions.append(("copy", f"summary.md → {code}/summary.md"))
    else:
        actions.append(("skip", "summary.md: not present"))
    return actions


def apply_dataset(dataset: str, code: str, drop_root_summary: bool = False):
    ddir = R.dataset_dir(dataset)
    rdir = R.rater_dir(dataset, code)
    rdir.mkdir(parents=True, exist_ok=True)

    for name in R.DOSSIER_NAMES:
        master = ddir / name
        if not master.exists():
            continue
        dest = rdir / name
        text = master.read_text()
        if not dest.exists():
            R.atomic_write(dest, text)          # rater copy keeps the ratings
        R.atomic_write(master, R.blank_ratings(text))  # master becomes a template

    src_summary = ddir / "summary.md"
    dst_summary = rdir / "summary.md"
    if src_summary.exists() and not dst_summary.exists():
        shutil.copy2(src_summary, dst_summary)
    if drop_root_summary and src_summary.exists() and dst_summary.exists():
        src_summary.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--rater", help="Rater code that owns the existing ratings "
                                    "(default: the primary rater in raters.json)")
    ap.add_argument("--dataset", help="Only migrate one dataset")
    ap.add_argument("--apply", action="store_true", help="Actually write changes")
    ap.add_argument("--drop-root-summary", action="store_true",
                    help="Delete the root summary.md after copying it into the "
                         "rater folder (default: leave it in place)")
    args = ap.parse_args()

    registry = R.load_registry()
    code = (args.rater or R.primary_code(registry)).upper()
    if code not in registry:
        sys.exit(f"Unknown rater code {code}. Registered: {', '.join(registry)}")

    ds_list = [args.dataset] if args.dataset else R.datasets()

    print(f"{'APPLYING' if args.apply else 'DRY RUN'} — existing ratings → rater '{code}'\n")
    for dataset in ds_list:
        print(f"── {dataset}")
        for action, detail in plan_dataset(dataset, code):
            mark = {"copy": "+", "blank": "~", "keep": "=", "skip": "·"}[action]
            print(f"   {mark} {detail}")
        if args.apply:
            apply_dataset(dataset, code, drop_root_summary=args.drop_root_summary)
        print()

    if args.apply:
        print("Done. Verify with:  git status --short  &&  python3 verify_migration.py")
    else:
        print("Nothing written. Re-run with --apply to perform the migration.")


if __name__ == "__main__":
    main()
