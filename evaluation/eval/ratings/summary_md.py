"""Reader for the per-dataset ``eval_summary.md`` tables.

`eval_summary.md` is the *derived* view: `raters merge` regenerates it from the
dossiers, and `report.py` renders from it. The analysis path does not go through
this file — `analysis.loading` reads each evaluator's dossier copies through
`raters.collect_ratings`, which is the source of truth. This module stays for
the tools and notebooks that want the flat combined table (`examples.ipynb`).

Per dataset -> per main qid ("1", "2", ...) -> per sub-qid ("a", "b", ..., or ""
when the question has no sub-letter):

    data["sosa2024"]["1"]["a"] = {
        "title": "How are all the data ... loaded in?",
        "human":  [1, 1, 1, 1, 1, 1],   # 6 trials: 3 claude-code + 3 codex
        "humans": {"LZ": [...], "KB": [...]},
        "claude": [0, 1, 1, 1, 1, 1],
        "codex":  [1, 1, 1, 0, 0, 1],
        "agents": ["claude-code", ..., "codex"],
        "trials": [1, 2, 3, 1, 2, 3],
        "overall": "...",               # may be empty
    }

Rating scale: incorrect=-2, concerning=-1, ok=0, match=1, better=2; "—"/blank
becomes None.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple, Optional

import numpy as np

from .paths import EVAL_DIR
from .questions import RATING_SCALE  # noqa: F401  (re-exported for callers)


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


EVAL_SUMMARY_MD = 'eval_summary.md'


_QID_RE = re.compile(r"^##\s+Q\s+([0-9]+)(?:-([a-z]))?\.\s+(.*)$")
_TRIAL_RE = re.compile(r"^\|\s*([a-z\-]+)\s*/\s*trial(\d+)\s*\|")


def _norm(cell: str) -> str:
    """Strip whitespace and the placeholder em-dash."""
    s = cell.strip()
    return "" if s in {"—", "-", ""} else s


def _to_score(cell: str) -> int | None:
    s = _norm(cell).lower()
    return RATING_SCALE.get(s)  # None if not a known rating


def _pick_best_rating(best_who: str | None, h, jc, jx):
    """The rating to treat as correct for a trial: the primary evaluator's.

    eval_summary.md used to carry a `Best` column naming whichever of the
    evaluator or the two judges was right where they disagreed. The handful of
    rows where a judge won have since been folded into the evaluator's own
    rating, so the evaluator column is the answer everywhere and the column is
    gone. `best_who` is accepted (and ignored) so files written before the
    change still parse.
    """
    return h


def _parse_header(line: str) -> dict[str, int] | None:
    """Map an eval_summary table header → {field: column index}.

    Evaluator columns are keyed by their code; the legacy single-evaluator
    ``Human`` column is keyed ``"human"``. Returns None for non-header lines.
    """
    if not line.strip().startswith("|"):
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if not cells or not cells[0].lower().startswith("agent"):
        return None
    cols: dict[str, int] = {}
    for i, name in enumerate(cells):
        key = name.lower()
        if key in ("claude judge", "claude"):
            cols["claude"] = i
        elif key in ("codex judge", "codex"):
            cols["codex"] = i
        elif key == "best":
            cols["best"] = i
        elif key == "why":
            cols["why"] = i
        elif key == "human":
            cols["human"] = i
        elif re.fullmatch(r"[A-Z]{2,4}", name):
            cols[name] = i
    return cols


# Column layout of files written before evaluators were named.
_LEGACY_COLS = {"human": 1, "claude": 2, "codex": 3, "best": 4, "why": 5}


def _parse_eval_summary(path: Path) -> dict[str, dict[str, dict]]:
    """Parse one eval_summary.md → {main_qid: {sub_qid: {...}}}."""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    cur: dict | None = None  # the question dict currently being filled
    cols: dict[str, int] = dict(_LEGACY_COLS)
    raters: list[str] = []   # evaluator codes seen in this file, in column order

    for line in path.read_text().splitlines():
        m = _QID_RE.match(line)
        if m:
            main, sub, title = m.group(1), (m.group(2) or ""), m.group(3).strip()
            cur = {
                "title": title,
                "human": [], "claude": [], "codex": [],
                "humans": defaultdict(list),
                "best": [], "best_rating": [],
                "agents": [], "trials": [],
                "overall": "",
            }
            out[main][sub] = cur
            continue

        if cur is None:
            continue

        header = _parse_header(line)
        if header:
            cols = header
            raters = [k for k in header
                      if k not in ("claude", "codex", "best", "why", "human")]
            continue

        if line.startswith("**Overall comment:**"):
            cur["overall"] = line.split("**Overall comment:**", 1)[1].strip()
            continue

        # Trial row: | claude-code / trial1 | match | ... | match | — | ... |
        tm = _TRIAL_RE.match(line)
        if not tm:
            continue
        agent, trial = tm.group(1), int(tm.group(2))
        cells = [c for c in line.strip().strip("|").split("|")]
        # Column count varies: one rating column per evaluator, and the Best/Why
        # pair is gone. The header decided the indices, so bound-check per cell
        # (see `cell` below) rather than against a fixed width.
        if len(cells) < 2:
            continue
        cell = lambda key: (cells[cols[key]] if key in cols and cols[key] < len(cells)
                            else "")
        cur["agents"].append(agent)
        cur["trials"].append(trial)
        # Primary human series: the first evaluator column, or the legacy one.
        per_rater = {code: _to_score(cell(code)) for code in raters}
        h = per_rater[raters[0]] if raters else _to_score(cell("human"))
        jc = _to_score(cell("claude"))
        jx = _to_score(cell("codex"))
        best_who = _norm(cell("best")) or None
        cur["human"].append(h)
        for code, v in per_rater.items():
            cur["humans"][code].append(v)
        cur["claude"].append(jc)
        cur["codex"].append(jx)
        cur["best"].append(best_who)
        cur["best_rating"].append(_pick_best_rating(best_who, h, jc, jx))

    # Convert numerical fields to numpy arrays (None → NaN, dtype=float).
    def _arr(vals):
        return np.array([np.nan if v is None else v for v in vals], dtype=float)

    for subs in out.values():
        for q in subs.values():
            for key in ("human", "claude", "codex", "best_rating"):
                q[key] = _arr(q[key])
            q["humans"] = {code: _arr(v) for code, v in q["humans"].items()}
            q["trials"] = np.array(q["trials"], dtype=int)
    return {k: dict(v) for k, v in out.items()}


def load_all(eval_dir: Path = EVAL_DIR, filename: str = EVAL_SUMMARY_MD) -> dict[str, dict[str, dict[str, dict]]]:
    """Load every eval_summary.md under eval_dir → {dataset: {main: {sub: {...}}}}."""
    datasets: dict[str, dict[str, dict[str, dict]]] = {}
    for path in sorted(eval_dir.glob(f"*/{filename}")):
        datasets[path.parent.name] = _parse_eval_summary(path)
    return datasets


def iter_trials(data):
    """Flatten the nested dict to one record per (dataset, qid, trial)."""
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


if __name__ == "__main__":
    import json

    data = load_all()
    for ds, qs in data.items():
        n_subs = sum(len(s) for s in qs.values())
        print(f"{ds}: {len(qs)} main questions, {n_subs} sub-questions")
    sample_ds = next(iter(data))
    sample_main = next(iter(data[sample_ds]))
    sample_sub = next(iter(data[sample_ds][sample_main]))
    print(f"\nSample — {sample_ds} Q {sample_main}-{sample_sub or '(no sub)'}:")
    print(json.dumps(data[sample_ds][sample_main][sample_sub], indent=2, default=str))
