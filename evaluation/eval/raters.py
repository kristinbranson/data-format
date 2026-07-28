#!/usr/bin/env python3
"""
Shared helpers for multi-evaluator rating.

Layout under ``evaluation/eval/<dataset>/``::

    claude-code_trial1.md ...   master dossiers: content only, ratings blank
    LZ/                         one working copy per rater
      claude-code_trial1.md     master content + LZ's **Rating:** / **Note:**
      summary.md                LZ's per-question table + solution comment
    KB/
      ...
    eval_summary.md             combined: one rating column per rater + judges
    report.md

The master dossiers at the dataset root are the single source of the *content*
(notes excerpt, code, "what this does"). Each rater's folder holds a copy of
that content plus their own ratings, so raters never see each other's calls and
never write to the same file.

Rater codes are registered in ``raters.json`` next to this module.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = EVAL_DIR / "raters.json"

PLACEHOLDER_RATING = "_(to be filled by evaluator)_"
PLACEHOLDER_NOTE = "_(to be filled by evaluator)_"
NO_NOTE = "_(no note)_"

TRIAL_KEYS = [("claude-code", n) for n in (1, 2, 3)] + [("codex", n) for n in (1, 2, 3)]

DOSSIER_NAMES = [f"{agent}_trial{n}.md" for agent, n in TRIAL_KEYS]

# `## Q <qid>. <title>` up to the next such heading (or EOF).
SECTION_RE = re.compile(
    r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+|\Z)",
    re.DOTALL | re.MULTILINE,
)


# ---------- registry ----------

class Rater:
    def __init__(self, code: str, name: str = "", primary: bool = False, note: str = ""):
        self.code = code
        self.name = name
        self.primary = primary
        self.note = note

    @property
    def label(self) -> str:
        return f"{self.code} ({self.name})" if self.name else self.code

    def __repr__(self):
        return f"Rater({self.code!r}, primary={self.primary})"


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Rater]:
    if not path.exists():
        sys.exit(f"Rater registry not found: {path}")
    data = json.loads(path.read_text())
    out = {}
    for entry in data.get("raters", []):
        r = Rater(
            code=entry["code"].strip().upper(),
            name=entry.get("name", "").strip(),
            primary=bool(entry.get("primary", False)),
            note=entry.get("note", ""),
        )
        out[r.code] = r
    if not out:
        sys.exit(f"No raters registered in {path}")
    return out


def primary_code(registry: dict[str, Rater] | None = None) -> str:
    registry = registry or load_registry()
    for code, r in registry.items():
        if r.primary:
            return code
    return next(iter(registry))


def rater_codes(registry: dict[str, Rater] | None = None) -> list[str]:
    """Registered codes, primary first, then registration order."""
    registry = registry or load_registry()
    order = {c: i for i, c in enumerate(registry)}
    return sorted(order, key=lambda c: (not registry[c].primary, order[c]))


def resolve_rater(code: str | None = None,
                  registry: dict[str, Rater] | None = None) -> Rater:
    """Resolve a rater code from the CLI arg, $DATAFORMAT_RATER, or a prompt."""
    registry = registry or load_registry()
    code = code or os.environ.get("DATAFORMAT_RATER")
    known = ", ".join(r.label for r in registry.values())
    while True:
        if not code:
            try:
                code = input(f"  Evaluator code [{known}]: ").strip()
            except (EOFError, KeyboardInterrupt):
                sys.exit("\nNo evaluator code given.")
        code = code.strip().upper()
        if code in registry:
            return registry[code]
        print(f"  Unknown evaluator code: '{code}'. Registered: {known}.")
        print(f"  (add new evaluators to {REGISTRY_PATH})")
        code = None


# ---------- section-level rating I/O ----------

def parse_ratings(path: Path) -> dict[str, dict]:
    """{qid: {title, rating, note}} from a dossier. Placeholders → None."""
    if not path.exists():
        return {}
    out = {}
    for m in SECTION_RE.finditer(path.read_text()):
        qid, title, body = m.group(1), m.group(2).strip(), m.group(3)
        rm = re.search(r"^\*\*Rating:\*\*\s*(.*?)\s*$", body, re.MULTILINE)
        nm = re.search(r"^\*\*Note:\*\*\s*(.*?)\s*$", body, re.MULTILINE)
        rating = rm.group(1).strip() if rm else None
        note = nm.group(1).strip() if nm else None
        if rating in ("", PLACEHOLDER_RATING):
            rating = None
        if note in ("", PLACEHOLDER_NOTE):
            note = None
        out[qid] = {"title": title, "rating": rating, "note": note}
    return out


def _sub_section(text: str, qid: str, fn) -> str:
    """Apply `fn` to the body of one qid section and splice it back in."""
    for m in SECTION_RE.finditer(text):
        if m.group(1) != qid:
            continue
        body = m.group(3)
        return text[:m.start(3)] + fn(body) + text[m.end(3):]
    raise RuntimeError(f"Could not find Q {qid} section")


def set_rating(text: str, qid: str, rating: str | None,
               note: str | None = None) -> str:
    """Return `text` with the Rating (and optionally Note) line of `qid` replaced."""
    def edit(body: str) -> str:
        new, n = re.subn(r"^\*\*Rating:\*\*.*$",
                         f"**Rating:** {rating if rating else PLACEHOLDER_RATING}",
                         body, count=1, flags=re.MULTILINE)
        if n == 0:
            raise RuntimeError(f"No **Rating:** field in Q {qid} section")
        if note is not None:
            new, n2 = re.subn(r"^\*\*Note:\*\*.*$", f"**Note:** {note}",
                              new, count=1, flags=re.MULTILINE)
            if n2 == 0:
                # Some dossiers only carry a Rating line; add the Note under it.
                new = re.sub(r"^(\*\*Rating:\*\*.*)$", rf"\1\n\n**Note:** {note}",
                             new, count=1, flags=re.MULTILINE)
        return new
    return _sub_section(text, qid, edit)


def blank_ratings(text: str) -> str:
    """Reset every Rating/Note line in a dossier back to the placeholder."""
    text = re.sub(r"^\*\*Rating:\*\*.*$", f"**Rating:** {PLACEHOLDER_RATING}",
                  text, flags=re.MULTILINE)
    text = re.sub(r"^\*\*Note:\*\*.*$", f"**Note:** {PLACEHOLDER_NOTE}",
                  text, flags=re.MULTILINE)
    return text


def atomic_write(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_rating(path: Path, qid: str, rating: str, note: str | None = None):
    """Persist one rating into a rater's dossier copy (atomically)."""
    atomic_write(path, set_rating(path.read_text(), qid, rating, note))


# ---------- rater working directories ----------

def dataset_dir(dataset: str, eval_dir: Path = EVAL_DIR) -> Path:
    return eval_dir / dataset


def rater_dir(dataset: str, code: str, eval_dir: Path = EVAL_DIR) -> Path:
    return eval_dir / dataset / code.upper()


def master_dossiers(dataset: str, eval_dir: Path = EVAL_DIR) -> dict[tuple[str, int], Path]:
    """Existing master dossiers at the dataset root, keyed by (agent, trial)."""
    out = {}
    for (agent, n), name in zip(TRIAL_KEYS, DOSSIER_NAMES):
        p = dataset_dir(dataset, eval_dir) / name
        if p.exists():
            out[(agent, n)] = p
    return out


def sync_rater_dir(dataset: str, code: str, eval_dir: Path = EVAL_DIR,
                   verbose: bool = True) -> dict[tuple[str, int], Path]:
    """
    Make sure <dataset>/<CODE>/ holds a copy of every master dossier.

    - Missing copy      → created from the master (ratings blank).
    - Content drifted   → re-copied from the master, with the rater's existing
                          ratings/notes re-applied per qid (nothing is lost).
    Returns {(agent, trial): path_in_rater_dir}.
    """
    masters = master_dossiers(dataset, eval_dir)
    if not masters:
        sys.exit(f"No master dossiers found under {dataset_dir(dataset, eval_dir)}")
    rdir = rater_dir(dataset, code, eval_dir)
    rdir.mkdir(parents=True, exist_ok=True)

    out = {}
    created, resynced = [], []
    for key, master in masters.items():
        dest = rdir / master.name
        master_text = master.read_text()
        if not dest.exists():
            atomic_write(dest, blank_ratings(master_text))
            created.append(dest.name)
        else:
            existing = parse_ratings(dest)
            # Compare content with ratings stripped on both sides.
            if blank_ratings(dest.read_text()) != blank_ratings(master_text):
                text = blank_ratings(master_text)
                kept = 0
                for qid, v in existing.items():
                    if v["rating"] is None and v["note"] is None:
                        continue
                    try:
                        text = set_rating(text, qid, v["rating"],
                                          v["note"] if v["note"] else None)
                        kept += 1
                    except RuntimeError:
                        print(f"  WARN: Q {qid} no longer in master {master.name}; "
                              f"its {code} rating was dropped", file=sys.stderr)
                atomic_write(dest, text)
                resynced.append(f"{dest.name} ({kept} ratings kept)")
        out[key] = dest

    if verbose and (created or resynced):
        if created:
            print(f"  [{code}] seeded from master: {', '.join(created)}")
        if resynced:
            print(f"  [{code}] re-synced to updated master: {', '.join(resynced)}")
    return out


def summary_path(dataset: str, code: str, eval_dir: Path = EVAL_DIR) -> Path:
    return rater_dir(dataset, code, eval_dir) / "summary.md"


def eval_summary_path(dataset: str, eval_dir: Path = EVAL_DIR) -> Path:
    """The combined judge-comparison file (dataset level, shared by all raters)."""
    return dataset_dir(dataset, eval_dir) / "eval_summary.md"


def collect_ratings(dataset: str, codes: list[str] | None = None,
                    eval_dir: Path = EVAL_DIR) -> dict[str, dict[tuple[str, int], dict]]:
    """
    Every rater's ratings for one dataset, read from their dossier copies.

    Returns {qid: {(agent, trial): {code: rating_or_None}}}. Raters with no
    folder for this dataset simply contribute None everywhere.
    """
    codes = codes or rater_codes()
    out: dict[str, dict[tuple[str, int], dict]] = {}
    for code in codes:
        rdir = rater_dir(dataset, code, eval_dir)
        for (agent, n), name in zip(TRIAL_KEYS, DOSSIER_NAMES):
            for qid, v in parse_ratings(rdir / name).items():
                cell = out.setdefault(qid, {}).setdefault((agent, n), {})
                cell[code] = v["rating"]
    # Fill gaps so every cell has an entry for every rater.
    for per_trial in out.values():
        for cell in per_trial.values():
            for code in codes:
                cell.setdefault(code, None)
    return out


def normalize_title(title: str) -> str:
    """Loose title comparison key: drop markdown emphasis, backticks, spacing."""
    t = re.sub(r"[*_`]+", "", title or "").lower()
    return re.sub(r"\s+", " ", t).strip().rstrip("?.")


def collect_titles(dataset: str, codes: list[str] | None = None,
                   eval_dir: Path = EVAL_DIR) -> dict[str, str]:
    """{qid: title} as the dossiers currently label their sections."""
    codes = codes or rater_codes()
    out: dict[str, str] = {}
    for code in codes:
        rdir = rater_dir(dataset, code, eval_dir)
        for name in DOSSIER_NAMES:
            for qid, v in parse_ratings(rdir / name).items():
                out.setdefault(qid, v["title"])
    return out


def active_rater_codes(dataset: str, eval_dir: Path = EVAL_DIR) -> list[str]:
    """Registered raters that actually have a folder for this dataset."""
    return [c for c in rater_codes() if rater_dir(dataset, c, eval_dir).is_dir()]


def rating_columns(dataset: str, include: str | None = None,
                   eval_dir: Path = EVAL_DIR) -> list[str]:
    """
    Evaluator codes that deserve a column in this dataset's eval_summary.md:
    everyone with at least one rating on disk, plus `include` (the evaluator
    currently working) even if they have not rated anything yet.

    An evaluator who has only been seeded — a folder full of placeholders —
    contributes no column, so the combined table stays clean until they start.
    """
    codes = active_rater_codes(dataset, eval_dir)
    disk = collect_ratings(dataset, codes, eval_dir)
    rated = {c for c in codes
             if any(cell.get(c) for per_trial in disk.values()
                    for cell in per_trial.values())}
    out = [c for c in codes if c in rated or c == include]
    return out or [include or primary_code()]


def datasets(eval_dir: Path = EVAL_DIR) -> list[str]:
    """Dataset folders that contain master dossiers."""
    out = []
    for p in sorted(eval_dir.iterdir()):
        if p.is_dir() and any((p / n).exists() for n in DOSSIER_NAMES):
            out.append(p.name)
    return out


if __name__ == "__main__":
    reg = load_registry()
    print(f"Registry: {REGISTRY_PATH}")
    for code in rater_codes(reg):
        r = reg[code]
        print(f"  {code:<4} primary={r.primary}  {r.name or '(no name)'}")
    print(f"Datasets with master dossiers: {', '.join(datasets())}")
