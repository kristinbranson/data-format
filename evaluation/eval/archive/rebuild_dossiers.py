#!/usr/bin/env python3
"""
Revise the dossiers so they carry exactly the reference's questions.

The dossiers were built two ways. Four datasets copied their question list from
`manual/<dataset>/DECISIONS.md`; the other four predate their reference and were
built by enumerating each trial's own outputs, so they cover outputs only, word
questions per trial, and ask "quality filtering" where the reference asks
"alignment". Meanwhile the references have all been revised. The result is that
question *numbers* no longer mean the same thing on both sides.

This rewrites every dossier onto the reference's numbering and wording without
re-doing ratings. A section that answers a reference question keeps its body
verbatim and moves under the reference's qid — its rating travels with it, so
each carried rating still sits beside the text the evaluator actually read.
Questions the dossiers never asked are inserted with a placeholder body for a
later extraction pass; sections the reference no longer asks are dropped.

Pairing, in order:

  1. exact title match (`raters.normalize_title`);
  2. same `compare.fingerprint` — same kind, direction, variable and role. A
     differing variable or role is a NON-match, never a fallback: pairing
     "input time_from_go_cue aligned" with "output lick_direction filtered"
     because both are numbered 3-c is exactly the corruption this replaces;
  3. an explicit entry in `<dataset>/rebuild_overrides.json`, for questions only
     a human can pair up ({"<trial or '*'>": {"<reference qid>": "<old qid>"}}).

Usage::

    python3 rebuild_dossiers.py                    # dry run, every dataset
    python3 rebuild_dossiers.py --dataset chen2024 # dry run, one dataset
    python3 rebuild_dossiers.py --apply            # write the revised dossiers
    python3 rebuild_dossiers.py --verbose          # list every pairing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import sys
from pathlib import Path

# Archived: still runnable — the rating tools are the `ratings` package
# one level up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ratings import raters as R
from ratings.compare import fingerprint

PLACEHOLDER_BODY = "_(section not yet extracted — run the extraction pass)_"

# A dossier section, captured whole: heading, body, and the `---` that closes it.
_SECTION = re.compile(
    r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$\n(.*?)(?=^##\s+Q\s+\d+(?:-[a-z])?\.|\Z)",
    re.DOTALL | re.MULTILINE,
)


# ---------- reading ----------

def split_dossier(path: Path) -> tuple[str, dict[str, dict]]:
    """Return (header_text, {qid: {title, body}}) for one dossier file."""
    text = path.read_text()
    matches = list(_SECTION.finditer(text))
    if not matches:
        return text, {}
    header = text[: matches[0].start()]
    out = {}
    for m in matches:
        body = m.group(3)
        # Drop the trailing `---` separator; it is re-added on write.
        body = re.sub(r"\n---\s*\n?\s*$", "\n", body)
        out[m.group(1)] = {"title": m.group(2).strip(), "body": body.rstrip() + "\n"}
    return header, out


def load_overrides(dataset: str) -> dict[str, dict[str, str]]:
    p = R.dataset_dir(dataset) / "rebuild_overrides.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text())


# ---------- pairing ----------

def pair(ref: dict[str, str], old: dict[str, dict], dataset: str,
         overrides: dict[str, str]) -> tuple[dict[str, str | None], dict[str, str]]:
    """
    Map reference qid -> old qid.

    Returns (mapping, how) where `how` records "title" / "fingerprint" /
    "override" per paired question. Each old section is claimed at most once.
    """
    by_title: dict[str, str] = {}
    by_fp: dict[tuple, str] = {}
    for q, v in old.items():
        by_title.setdefault(R.normalize_title(v["title"]), q)
        by_fp.setdefault(fingerprint(q, v["title"], dataset=dataset), q)

    mapping: dict[str, str | None] = {}
    how: dict[str, str] = {}
    claimed: set[str] = set()

    def take(rq: str, oq: str | None, kind: str) -> bool:
        if not oq or oq in claimed or oq not in old:
            return False
        mapping[rq] = oq
        how[rq] = kind
        claimed.add(oq)
        return True

    for rq, title in ref.items():
        if take(rq, overrides.get(rq), "override"):
            continue
        if take(rq, by_title.get(R.normalize_title(title)), "title"):
            continue
        fp = fingerprint(rq, title, dataset=dataset)
        # ("unknown", qid) fingerprints carry no information — refuse them, or
        # every unclassifiable question would pair with the first other one.
        if fp[0] != "unknown" and take(rq, by_fp.get(fp), "fingerprint"):
            continue
        mapping[rq] = None
    return mapping, how


# ---------- writing ----------

def render(header: str, ref: dict[str, str], old: dict[str, dict],
           mapping: dict[str, str | None]) -> str:
    """Build a dossier holding exactly `ref`'s questions, in reference order."""
    parts = [header.rstrip() + "\n\n"]
    for rq in sorted(ref, key=_qid_key):
        oq = mapping.get(rq)
        body = old[oq]["body"].strip() if oq else _render_placeholder()
        parts.append(f"## Q {rq}. {ref[rq]}\n\n{body}\n\n---\n\n")
    return "".join(parts).rstrip() + "\n"


def _render_placeholder() -> str:
    return (f"**Notes excerpt** (CONVERSION_NOTES.md / README.md):\n> (none)\n\n"
            f"**Code**:\n{PLACEHOLDER_BODY}\n\n"
            f"**What this does:** {PLACEHOLDER_BODY}\n\n"
            f"**Rating:** {R.PLACEHOLDER_RATING}\n\n"
            f"**Note:** {R.PLACEHOLDER_NOTE}")


def _qid_key(q: str):
    m = re.match(r"(\d+)", q)
    return (int(m.group(1)) if m else 999, q.split("-")[1] if "-" in q else "")


# ---------- per dataset ----------

def process(dataset: str, apply: bool, verbose: bool) -> dict:
    ref = R.reference_titles(dataset)
    if not ref:
        print(f"── {dataset}: no reference DECISIONS.md — skipped")
        return {}
    all_overrides = load_overrides(dataset)
    codes = R.active_rater_codes(dataset)
    stats = {"new": 0, "carried": 0, "dropped": 0, "ratings_kept": 0,
             "ratings_dropped": 0, "trials": {}}
    plan: dict[str, dict] = {}

    for (agent, n), name in zip(R.TRIAL_KEYS, R.DOSSIER_NAMES):
        master = R.dataset_dir(dataset) / name
        if not master.exists():
            continue
        trial = f"{agent}/trial{n}"
        ov = {**all_overrides.get("*", {}), **all_overrides.get(trial, {})}
        header, old = split_dossier(master)
        mapping, how = pair(ref, old, dataset, ov)

        new_qs = [q for q in ref if not mapping.get(q)]
        used = {v for v in mapping.values() if v}
        dropped = [q for q in old if q not in used]

        stats["new"] += len(new_qs)
        stats["carried"] += len(used)
        stats["dropped"] += len(dropped)
        stats["trials"][trial] = {"new": new_qs, "dropped": dropped,
                                  "map": {k: v for k, v in mapping.items() if v},
                                  "how": how}
        plan[name] = mapping

        # Ratings only exist in the rater folders. Pair each rater's file on
        # its OWN sections rather than reusing the master's mapping: a rater
        # can be a rebuild behind (rated in a checkout made before the
        # reference was renumbered, then merged in), in which case the master
        # no longer has the numbers their file uses and reusing its mapping
        # would drop every rating that moved.
        for code in codes:
            rpath = R.rater_dir(dataset, code) / name
            if not rpath.exists():
                continue
            rheader, rold = split_dossier(rpath)
            rmap, _how = pair(ref, rold, dataset, ov)
            rused = {v for v in rmap.values() if v}
            rated = {q for q, v in R.parse_ratings(rpath).items() if v["rating"]}
            stats["ratings_kept"] += len(rated & rused)
            stats["ratings_dropped"] += len(rated - rused)
            if apply:
                R.atomic_write(rpath, render(rheader, ref, rold, rmap))

        if apply:
            R.atomic_write(master, render(header, ref, old, mapping))

    print(f"── {dataset}: {len(ref)} reference questions | "
          f"carried {stats['carried']} sections, {stats['new']} to extract, "
          f"{stats['dropped']} dropped | ratings kept {stats['ratings_kept']}, "
          f"lost {stats['ratings_dropped']}")
    for trial, t in stats["trials"].items():
        if verbose or t["new"] or t["dropped"]:
            renum = [f"{k}<-{v}" for k, v in t["map"].items() if k != v]
            print(f"     {trial:<22} new: {','.join(t['new']) or '-':<28} "
                  f"dropped: {','.join(t['dropped']) or '-'}")
            if verbose and renum:
                print(f"     {'':<22} renumbered: {' '.join(renum)}")

    if apply:
        (R.dataset_dir(dataset) / "rebuild_map.json").write_text(
            json.dumps({k: v for k, v in plan.items()}, indent=2, sort_keys=True) + "\n")
    return stats


# ---------- summary files ----------
#
# summary.md and eval_summary.md are keyed by the question numbers that were in
# force when they were written, so the rebuild leaves them pointing at the wrong
# questions. Re-key them by question text — and drop sections whose question the
# reference no longer asks, because leaving one behind parks a stale rating on a
# number that now means something else.

_SUMMARY_SEC = re.compile(
    r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+\d+(?:-[a-z])?\.|\Z)",
    re.DOTALL | re.MULTILINE,
)


def resummarize(dataset: str, apply: bool) -> tuple[int, int]:
    """Re-key a dataset's summary files onto the rebuilt numbering."""
    titles = R.collect_titles(dataset)
    by_title = {R.normalize_title(t): q for q, t in titles.items()}
    # Wording drifts between a summary and the dossier it describes — allen2p's
    # summary says "Image name" where the reference says "Image identity" — so
    # fall back to the same fingerprint the dossier rebuild pairs on.
    by_fp: dict[tuple, str] = {}
    for q, t in titles.items():
        by_fp.setdefault(fingerprint(q, t, dataset=dataset), q)

    paths = [R.summary_path(dataset, c) for c in R.active_rater_codes(dataset)]
    paths.append(R.eval_summary_path(dataset))
    moved = dropped = 0
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text()
        ms = list(_SUMMARY_SEC.finditer(text))
        if not ms:
            continue
        header = text[: ms[0].start()]
        keep: dict[str, str] = {}
        for m in ms:
            old_qid, title, body = m.group(1), m.group(2).strip(), m.group(3)
            new_qid = by_title.get(R.normalize_title(title))
            if new_qid is None:
                fp = fingerprint(old_qid, title, dataset=dataset)
                if fp[0] != "unknown":
                    new_qid = by_fp.get(fp)
            if new_qid is None or new_qid in keep:
                dropped += 1
                print(f"     drop {path.parent.name}/{path.name} Q {old_qid}: "
                      f"{title[:56]}")
                continue
            if new_qid != old_qid:
                moved += 1
            # Take the dossier's wording too, so the summary describes the
            # question the way the reference now asks it (allen2p's summary
            # still said "Image name" for what is now "Image identity").
            keep[new_qid] = f"## Q {new_qid}. {titles[new_qid]}\n{body}".rstrip()
        if apply:
            body = "\n\n".join(keep[q] for q in sorted(keep, key=_qid_key))
            R.atomic_write(path, header.rstrip() + "\n\n" + body + "\n")
    return moved, dropped


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--dataset")
    ap.add_argument("--apply", action="store_true", help="Write the revised dossiers")
    ap.add_argument("--verbose", action="store_true", help="Show every renumbering")
    ap.add_argument("--summaries", action="store_true",
                    help="Re-key summary.md / eval_summary.md onto the rebuilt "
                         "numbering instead of touching dossiers (run after the "
                         "dossier rebuild)")
    args = ap.parse_args()

    datasets = [args.dataset] if args.dataset else R.datasets()

    if args.summaries:
        print(f"{'APPLYING' if args.apply else 'DRY RUN'} — re-keying summary files\n")
        tm = td = 0
        for ds in datasets:
            m, d = resummarize(ds, args.apply)
            print(f"── {ds}: {m} sections renumbered, {d} dropped")
            tm += m; td += d
        print(f"\nTOTAL: {tm} renumbered, {td} dropped")
        if not args.apply:
            print("Nothing written. Re-run with --apply.")
        return
    print(f"{'APPLYING' if args.apply else 'DRY RUN'} — revising dossiers onto the reference\n")
    totals = {"new": 0, "carried": 0, "dropped": 0, "ratings_kept": 0, "ratings_dropped": 0}
    for ds in datasets:
        s = process(ds, args.apply, args.verbose)
        for k in totals:
            totals[k] += s.get(k, 0)
        print()
    print(f"TOTAL: {totals['carried']} sections carried, {totals['new']} to extract, "
          f"{totals['dropped']} dropped | ratings kept {totals['ratings_kept']}, "
          f"lost {totals['ratings_dropped']}")
    if not args.apply:
        print("\nNothing written. Re-run with --apply.")


if __name__ == "__main__":
    main()
