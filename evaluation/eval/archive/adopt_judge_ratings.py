#!/usr/bin/env python3
"""
One-off: adopt the judge's rating wherever the judge comparison concluded the
judge was right, so the primary evaluator's rating can stand alone as the
reference.

`eval_summary.md` used to carry a `Best` column recording, for each row where a
human and a judge disagreed, which one was correct. Almost always the human;
occasionally a judge. Keeping that as a separate column means every consumer has
to know to consult it. Folding those few judge wins into the human's own rating
makes the human column the single answer — after which `Best` carries no
information and is dropped.

The change is written where ratings live (the evaluator's dossier) and mirrored
into their `summary.md`; the reason recorded in the old `Why` cell is preserved
in the rating's note so the correction is not silent.

Usage::

    python3 adopt_judge_ratings.py            # dry run
    python3 adopt_judge_ratings.py --apply
"""

from __future__ import annotations

import argparse
import re

import sys
from pathlib import Path

# Archived: still runnable — the rating tools are the `ratings` package
# one level up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ratings import raters as R
from ratings.compare import parse_summary

NO_NOTE = "_(no note)_"


def judge_rating(row: dict, best: str) -> str | None:
    key = "claude" if best.lower().startswith("claude") else "codex"
    v = (row.get(key) or "").strip()
    return v or None


def find_rows() -> list[dict]:
    """Every row whose Best names a judge rather than an evaluator."""
    codes = set(R.rater_codes())
    out = []
    for ds in R.datasets():
        entries, _ = parse_summary(R.eval_summary_path(ds))
        for (qid, agent, trial), v in sorted(entries.items()):
            best = (v.get("best") or "").strip()
            if not best or best in ("—",) or best in codes:
                continue
            new = judge_rating(v, best)
            if not new:
                print(f"  WARN {ds}/{qid} {agent}/trial{trial}: Best={best} but that "
                      f"judge has no rating — skipped")
                continue
            out.append({"dataset": ds, "qid": qid, "agent": agent, "trial": trial,
                        "best": best, "new": new,
                        "old": (v["ratings"].get(R.primary_code()) or "").strip(),
                        "why": (v.get("why") or "").strip()})
    return out


def note_for(existing: str | None, row: dict) -> str:
    """Keep the old note, and append why the rating was corrected."""
    reason = f"adopted {row['best']} rating ({row['old']} → {row['new']})"
    if row["why"]:
        reason += f": {row['why']}"
    if existing and existing != NO_NOTE:
        return f"{existing} [{reason}]"
    return f"[{reason}]"


_SUMMARY_SEC = re.compile(
    r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+\d+(?:-[a-z])?\.|\Z)",
    re.DOTALL | re.MULTILINE,
)


def update_summary(path, qid: str, agent: str, trial: int, new: str, note: str):
    """Rewrite one cell of one row in a rater's summary.md table."""
    text = path.read_text()
    m = next((m for m in _SUMMARY_SEC.finditer(text) if m.group(1) == qid), None)
    if not m:
        return False
    body = m.group(3)
    row_re = re.compile(rf"^\|\s*{re.escape(agent)}\s*/\s*trial{trial}\s*\|[^|]*\|[^|]*\|",
                        re.MULTILINE)
    cell = note.replace("|", "\\|")
    new_body, n = row_re.subn(f"| {agent} / trial{trial} | {new} | {cell} |", body, count=1)
    if n:
        R.atomic_write(path, text[:m.start(3)] + new_body + text[m.end(3):])
    return bool(n)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    primary = R.primary_code()
    rows = find_rows()
    print(f"{'APPLYING' if args.apply else 'DRY RUN'} — "
          f"{len(rows)} rating(s) to adopt into {primary}\n")

    summaries_missed = 0
    for r in rows:
        dossier = R.rater_dir(r["dataset"], primary) / f"{r['agent']}_trial{r['trial']}.md"
        current = R.parse_ratings(dossier).get(r["qid"], {})
        note = note_for(current.get("note"), r)
        print(f"  {r['dataset']}/{r['qid']} {r['agent']}/trial{r['trial']}: "
              f"{r['old']} → {r['new']}   ({r['best']})")
        if not args.apply:
            continue
        R.write_rating(dossier, r["qid"], r["new"], note)
        if not update_summary(R.summary_path(r["dataset"], primary),
                              r["qid"], r["agent"], r["trial"], r["new"], note):
            summaries_missed += 1
            print(f"     note: no summary.md row for this question — dossier only")

    if args.apply:
        print(f"\nDone. {len(rows)} dossier rating(s) updated"
              + (f", {summaries_missed} without a summary.md row." if summaries_missed
                 else ", all mirrored into summary.md."))
        print("Next: python3 raters.py merge --apply, then report.py per dataset.")
    else:
        print("\nNothing written. Re-run with --apply.")


if __name__ == "__main__":
    main()
