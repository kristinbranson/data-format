#!/usr/bin/env python3
"""
Post-migration check: every rating that existed before the migration must still
be readable from the rater's folder, and the master dossiers must be blank.

Compares each ``<dataset>/<CODE>/<dossier>.md`` against the pre-migration
version of ``<dataset>/<dossier>.md`` taken from git (default: HEAD), and
verifies the master copy no longer carries ratings.

Usage::

    python3 verify_migration.py            # check the primary rater vs HEAD
    python3 verify_migration.py --rater LZ --rev HEAD
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import sys
from pathlib import Path

# Archived: still runnable — the rating tools are the `ratings` package
# one level up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ratings import raters as R

REPO_ROOT = Path("/groups/zhang/home/zhangl5/Data-Format")


def git_show(rev: str, path: Path) -> str | None:
    rel = path.resolve().relative_to(REPO_ROOT)
    try:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", f"{rev}:{rel}"],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None


def parse_ratings_text(text: str) -> dict[str, dict]:
    out = {}
    for m in R.SECTION_RE.finditer(text):
        qid, body = m.group(1), m.group(3)
        rm = re.search(r"^\*\*Rating:\*\*\s*(.*?)\s*$", body, re.MULTILINE)
        nm = re.search(r"^\*\*Note:\*\*\s*(.*?)\s*$", body, re.MULTILINE)
        rating = rm.group(1).strip() if rm else None
        note = nm.group(1).strip() if nm else None
        if rating in ("", R.PLACEHOLDER_RATING):
            rating = None
        if note in ("", R.PLACEHOLDER_NOTE):
            note = None
        out[qid] = {"rating": rating, "note": note}
    return out


_SUMMARY_SEC = re.compile(
    r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+|\Z)",
    re.DOTALL | re.MULTILINE,
)


def _sections_by_title(text: str) -> dict[str, str]:
    """{normalized title: section body} — ignores the question numbering."""
    return {R.normalize_title(m.group(2)): m.group(3).strip()
            for m in _SUMMARY_SEC.finditer(text)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--rater", help="Rater code (default: primary)")
    ap.add_argument("--rev", default="HEAD", help="Git rev holding the pre-migration state")
    args = ap.parse_args()

    code = (args.rater or R.primary_code()).upper()
    problems = 0
    checked = 0

    for dataset in R.datasets():
        for name in R.DOSSIER_NAMES:
            master = R.dataset_dir(dataset) / name
            copy = R.rater_dir(dataset, code) / name
            if not master.exists():
                continue
            before = git_show(args.rev, master)
            if before is None:
                print(f"  ? {dataset}/{name}: not in {args.rev}, skipped")
                continue
            if not copy.exists():
                print(f"  ✗ {dataset}/{code}/{name}: MISSING")
                problems += 1
                continue

            want = parse_ratings_text(before)
            got = R.parse_ratings(copy)
            checked += 1

            for qid, v in want.items():
                g = got.get(qid)
                if g is None:
                    print(f"  ✗ {dataset}/{code}/{name}: Q {qid} lost")
                    problems += 1
                elif g["rating"] != v["rating"] or g["note"] != v["note"]:
                    print(f"  ✗ {dataset}/{code}/{name}: Q {qid} "
                          f"{v['rating']!r}/{v['note']!r} → {g['rating']!r}/{g['note']!r}")
                    problems += 1

            # Content must be byte-identical once ratings are blanked out.
            if R.blank_ratings(before) != R.blank_ratings(copy.read_text()):
                print(f"  ✗ {dataset}/{code}/{name}: content differs from {args.rev}")
                problems += 1

            leftover = [q for q, v in R.parse_ratings(master).items()
                        if v["rating"] or v["note"]]
            if leftover:
                print(f"  ✗ {dataset}/{name}: master still carries ratings for "
                      f"{len(leftover)} questions")
                problems += 1

        # summary.md moved (or was copied) into the rater folder
        src = R.dataset_dir(dataset) / "summary.md"
        dst = R.summary_path(dataset, code)
        before = git_show(args.rev, src)
        if before is not None and not dst.exists():
            print(f"  ✗ {dataset}/{code}/summary.md: MISSING")
            problems += 1
        elif before is not None and dst.read_text() != before:
            # Section *numbers* may legitimately have moved since (see
            # renumber_summary.py); the content, keyed by question text, must not.
            if _sections_by_title(before) == _sections_by_title(dst.read_text()):
                print(f"  · {dataset}/{code}/summary.md: renumbered since {args.rev}, "
                      f"content unchanged")
            else:
                print(f"  ✗ {dataset}/{code}/summary.md: differs from {args.rev}")
                problems += 1

    print(f"\nChecked {checked} dossiers across {len(R.datasets())} datasets "
          f"for rater {code}.")
    if problems:
        print(f"FAILED: {problems} problem(s).")
        sys.exit(1)
    print("OK: all ratings preserved, all masters blank.")


if __name__ == "__main__":
    main()
