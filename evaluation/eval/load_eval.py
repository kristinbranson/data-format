"""Load eval_summary.md files into a structured representation for analysis.

Per dataset → per main qid ("1", "2", ...) → per sub-qid ("a", "b", ..., or "" if
the question has no sub-letter):

    data["sosa2024"]["1"]["a"] = {
        "title": "How are all the data ... loaded in?",
        "human":  [1, 1, 1, 1, 1, 1],          # length 6 (3 claude-code + 3 codex)
        "claude": [0, 1, 1, 1, 1, 1],
        "codex":  [1, 1, 1, 0, 0, 1],
        "best":   [None, None, None, None, None, None],   # or "Human" / "Claude judge"
        "agents": ["claude-code", "claude-code", "claude-code", "codex", "codex", "codex"],
        "trials": [1, 2, 3, 1, 2, 3],
        "overall": "...",                       # may be empty
    }

Rating scale: incorrect=-2, concerning=-1, ok=0, match=1, better=2; "—"/blank → None.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple, Optional

import numpy as np


class TrialRating(NamedTuple):
    dataset: str
    qid: str
    agent: str
    trial: int
    human: Optional[int]
    claude: Optional[int]
    codex: Optional[int]
    best_who: Optional[str]
    best_rating: Optional[int]

EVAL_DIR = Path(__file__).resolve().parent

RATING_SCALE = {
    "incorrect": -2,
    "concerning": -1,
    "ok": 0,
    "match": 1,
    "better": 2,
}

_QID_RE = re.compile(r"^##\s+Q\s+([0-9]+)(?:-([a-z]))?\.\s+(.*)$")
_TRIAL_RE = re.compile(r"^\|\s*([a-z\-]+)\s*/\s*trial(\d+)\s*\|")


def _norm(cell: str) -> str:
    """Strip whitespace and the placeholder em-dash."""
    s = cell.strip()
    return "" if s in {"—", "-", ""} else s


def _to_score(cell: str) -> int | None:
    s = _norm(cell).lower()
    return RATING_SCALE.get(s)  # None if not a known rating


def _parse_eval_summary(path: Path) -> dict[str, dict[str, dict]]:
    """Parse one eval_summary.md → {main_qid: {sub_qid: {...}}}."""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    cur: dict | None = None  # the question dict currently being filled

    for line in path.read_text().splitlines():
        m = _QID_RE.match(line)
        if m:
            main, sub, title = m.group(1), (m.group(2) or ""), m.group(3).strip()
            cur = {
                "title": title,
                "human": [], "claude": [], "codex": [],
                "best": [], "best_rating": [],
                "agents": [], "trials": [],
                "overall": "",
            }
            out[main][sub] = cur
            continue

        if cur is None:
            continue

        if line.startswith("**Overall comment:**"):
            cur["overall"] = line.split("**Overall comment:**", 1)[1].strip()
            continue

        # Trial row: | claude-code / trial1 | match | match | match | — | ... |
        tm = _TRIAL_RE.match(line)
        if not tm:
            continue
        agent, trial = tm.group(1), int(tm.group(2))
        # Skip header / separator rows that happen to start with | but aren't trial rows
        cells = [c for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        cur["agents"].append(agent)
        cur["trials"].append(trial)
        h = _to_score(cells[1])
        jc = _to_score(cells[2])
        jx = _to_score(cells[3])
        best_who = _norm(cells[4]) or None
        cur["human"].append(h)
        cur["claude"].append(jc)
        cur["codex"].append(jx)
        cur["best"].append(best_who)
        # Combined "best" rating: pick the rating from whichever evaluator was
        # marked Best (defaulting to human). This is the user's final call on
        # what the correct rating should have been.
        cur["best_rating"].append(_pick_best_rating(best_who, h, jc, jx))

    # Convert numerical fields to numpy arrays (None → NaN, dtype=float).
    for subs in out.values():
        for q in subs.values():
            for key in ("human", "claude", "codex", "best_rating"):
                q[key] = np.array(
                    [np.nan if v is None else v for v in q[key]],
                    dtype=float,
                )
            q["trials"] = np.array(q["trials"], dtype=int)
    return {k: dict(v) for k, v in out.items()}


def _pick_best_rating(best_who: str | None, h, jc, jx):
    if best_who is None or best_who.lower() == "human":
        return h
    if best_who.lower().startswith("claude"):
        return jc
    if best_who.lower().startswith("codex"):
        return jx
    return h  # unknown label → fall back to human


def load_all(eval_dir: Path = EVAL_DIR) -> dict[str, dict[str, dict[str, dict]]]:
    """Load every eval_summary.md under eval_dir → {dataset: {main: {sub: {...}}}}."""
    datasets: dict[str, dict[str, dict[str, dict]]] = {}
    for path in sorted(eval_dir.glob("*/eval_summary.md")):
        datasets[path.parent.name] = _parse_eval_summary(path)
    return datasets


def load_dataset(dataset: str, eval_dir: Path = EVAL_DIR) -> dict[str, dict[str, dict]]:
    return _parse_eval_summary(eval_dir / dataset / "eval_summary.md")


def iter_trials(data):
    """Flatten the nested dict to one record per (dataset, qid, trial).

    Yields plain dicts so it composes with anything (DataFrames, csv.DictWriter, etc.):

        for r in iter_trials(load_all()):
            r["dataset"], r["qid"], r["agent"], r["trial"], r["human"], ...
    """
    for ds, mains in data.items():
        for main, subs in mains.items():
            for sub, q in subs.items():
                qid = f"{main}-{sub}" if sub else main
                for i, trial in enumerate(q["trials"]):
                    yield TrialRating(
                        dataset=ds, qid=qid,
                        agent=q["agents"][i], trial=trial,
                        human=q["human"][i],
                        claude=q["claude"][i],
                        codex=q["codex"][i],
                        best_who=q["best"][i],
                        best_rating=q["best_rating"][i],
                    )


def iter_questions(data):
    """One record per (dataset, qid). Ratings come back as length-6 lists."""
    for ds, mains in data.items():
        for main, subs in mains.items():
            for sub, q in subs.items():
                qid = f"{main}-{sub}" if sub else main
                yield {
                    "dataset": ds, "qid": qid, "main": main, "sub": sub,
                    **q,
                }


def to_dataframe(data):
    """Long-format DataFrame, one row per trial. Requires pandas."""
    import pandas as pd
    return pd.DataFrame(iter_trials(data))


if __name__ == "__main__":
    import json
    data = load_all()
    for ds, qs in data.items():
        n_subs = sum(len(s) for s in qs.values())
        print(f"{ds}: {len(qs)} main questions, {n_subs} sub-questions")
    # Sanity print one entry
    sample_ds = next(iter(data))
    sample_main = next(iter(data[sample_ds]))
    sample_sub = next(iter(data[sample_ds][sample_main]))
    print(f"\nSample — {sample_ds} Q {sample_main}-{sample_sub or '(no sub)'}:")
    print(json.dumps(data[sample_ds][sample_main][sample_sub], indent=2, default=str))
