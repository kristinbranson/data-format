#!/usr/bin/env python3
"""
Diagnostic: do the question labels (qids) still mean the same thing in every
file that records ratings for a dataset?

Compares, per dataset:

  - dossier  <dataset>/<CODE>/<agent>_trial<N>.md   qid → title, qid → rating
  - summary  <dataset>/<CODE>/summary.md            qid → title, qid → rating
  - manual   manual/<dataset>/DECISIONS.md          qid → title

and reports (a) qids whose titles disagree between files, and (b) ratings that
disagree once the questions are matched by title instead of by qid.

Usage::

    python3 check_alignment.py [--rater LZ] [--dataset sosa2024]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import raters as R
from compare import build_qid_map

MANUAL_DIR = Path("/groups/zhang/home/zhangl5/Data-Format/manual")

_SUMMARY_SEC = re.compile(
    r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+|\Z)",
    re.DOTALL | re.MULTILINE,
)
_ROW = re.compile(r"^\|\s*(claude-code|codex)\s*/\s*trial([1-3])\s*\|\s*([^|]*?)\s*\|")


def parse_summary_md(path: Path) -> tuple[dict[str, str], dict[tuple[str, str, int], str]]:
    """summary.md → (qid → title, (qid, agent, trial) → rating)."""
    if not path.exists():
        return {}, {}
    titles, ratings = {}, {}
    for m in _SUMMARY_SEC.finditer(path.read_text()):
        qid, title, body = m.group(1), m.group(2).strip(), m.group(3)
        titles[qid] = title
        for line in body.splitlines():
            rm = _ROW.match(line)
            if rm:
                ratings[(qid, rm.group(1), int(rm.group(2)))] = rm.group(3)
    return titles, ratings


def parse_reference(dataset: str) -> dict[str, str]:
    path = MANUAL_DIR / dataset / "DECISIONS.md"
    if not path.exists():
        return {}
    return {m.group(1): m.group(2).strip() for m in
            re.finditer(r"^##\s+(\d+(?:-[a-z])?)\.\s+(.+?)$",
                        path.read_text(), re.MULTILINE)}


def check(dataset: str, code: str) -> int:
    problems = 0
    rdir = R.rater_dir(dataset, code)
    if not rdir.is_dir():
        return 0

    dossier_titles = R.collect_titles(dataset, [code])
    sum_titles, sum_ratings = parse_summary_md(R.summary_path(dataset, code))
    ref_titles = parse_reference(dataset)

    print(f"── {dataset} / {code}: "
          f"{len(dossier_titles)} dossier questions, "
          f"{len(sum_titles)} in summary.md, "
          f"{len(ref_titles) or '—'} in reference")

    # 1. Reference vs dossier numbering. rate.py pairs these by content, so
    #    a shifted number is only a problem when the content match *fails*.
    if ref_titles:
        ref_d = {q: {"title": t} for q, t in ref_titles.items()}
        dos_d = {q: {"title": t} for q, t in dossier_titles.items()}
        qmap = build_qid_map(ref_d, dos_d, dataset=dataset)
        renumbered = [(q, qmap[q]) for q in sorted(ref_titles)
                      if qmap.get(q) and qmap[q] != q]
        unmapped = [q for q in sorted(ref_titles) if not qmap.get(q)]
        if renumbered:
            print(f"   · {len(renumbered)} question(s) numbered differently in the "
                  f"dossiers; rate.py pairs them by content "
                  f"({', '.join(f'{a}→{b}' for a, b in renumbered[:6])}"
                  f"{', …' if len(renumbered) > 6 else ''})")
        for q in unmapped:
            print(f"   ✗ Q {q} ({ref_titles[q]!r}) has no matching dossier section — "
                  f"rate.py will refuse to run until this is aliased or fixed")
            problems += 1

    # 2. summary.md vs dossier numbering. Nothing pairs these by content, so any
    #    drift here does silently corrupt a merge — repair with renumber_summary.py.
    drift = []
    for qid, dt in dossier_titles.items():
        st = sum_titles.get(qid)
        if st and R.normalize_title(st) != R.normalize_title(dt):
            drift.append((qid, dt, st))
    for qid, dt, st in drift:
        print(f"   ✗ Q {qid}: dossier {dt!r} vs summary.md {st!r} "
              f"— run: python3 renumber_summary.py {dataset} --apply")
        problems += 1

    # 3. Rating drift, matched by title (immune to renumbering).
    by_title_dossier: dict[str, dict[tuple[str, int], str]] = {}
    for (agent, n), name in zip(R.TRIAL_KEYS, R.DOSSIER_NAMES):
        for qid, v in R.parse_ratings(rdir / name).items():
            if v["rating"]:
                key = R.normalize_title(v["title"])
                by_title_dossier.setdefault(key, {})[(agent, n)] = v["rating"]

    mismatched = 0
    for (qid, agent, n), rating in sum_ratings.items():
        title = sum_titles.get(qid, "")
        d = by_title_dossier.get(R.normalize_title(title), {}).get((agent, n))
        if d is None:
            continue
        if d != rating and rating not in ("—", ""):
            print(f"   ✗ Q {qid} ({agent}/trial{n}): summary.md says {rating!r}, "
                  f"dossier says {d!r} for the same question text")
            mismatched += 1
            problems += 1
    if drift and not mismatched:
        print(f"   → labels shifted, but every rating matches once questions are "
              f"paired by text: the ratings are intact, only the numbering is stale")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--rater", help="Evaluator code (default: primary)")
    ap.add_argument("--dataset")
    args = ap.parse_args()

    code = (args.rater or R.primary_code()).upper()
    ds_list = [args.dataset] if args.dataset else R.datasets()
    total = sum(check(d, code) for d in ds_list)
    print(f"\n{total} problem(s) across {len(ds_list)} dataset(s).")


if __name__ == "__main__":
    main()
