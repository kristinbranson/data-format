"""Read the LLM judges' ratings and line them up with our question numbering.

The judges answer their own question list, which is close to ours but not the
same: they ask 21-39 questions per dataset against our 21-40, including extra
"thresholded into categories" questions, and their numbering drifts from ours
wherever a reference has been renumbered since. Pairing on question *number*
would therefore attach ratings to the wrong questions — so every judge qid is
mapped onto ours by content, using the same fingerprint `compare.py` uses to
line human ratings up with judges.

One question is expected to go unmapped in every dataset: "How is memory usage
optimized?" (`X-e`), which the references gained after the judges ran. It comes
back as NaN rather than silently disappearing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .. import raters as R
from ..compare import build_qid_map
from ..questions import RATING_SCALE

# <agent>_trial<N>_<judge>-judge.json — the name carries everything that
# identifies a file, which is why `import-judges` writes them flat.
FILENAME_RE = re.compile(r"^(?P<agent>.+)_trial(?P<trial>\d+)_(?P<judge>.+)-judge\.json$")

MODES = ("supervised", "unsupervised")


def judge_dir(dataset: str, mode: str = "supervised") -> Path:
    return R.dataset_dir(dataset) / f"judge_{mode}"


def available(dataset: str, mode: str = "supervised") -> bool:
    d = judge_dir(dataset, mode)
    return d.is_dir() and any(d.glob("*.json"))


@dataclass
class JudgeFile:
    """What one judge said about one trial, on our question numbering."""

    ratings: dict = field(default_factory=dict)   # our_qid -> {"rating", "code"}
    unmapped: list = field(default_factory=list)  # our qids nothing answered
    extra: list = field(default_factory=list)     # judge qids nothing claimed
    by_number: list = field(default_factory=list) # our qids paired by number


@lru_cache(maxsize=None)
def reference_stub(dataset: str) -> dict:
    """`{qid: {"title": ...}}` for `build_qid_map`, cached per dataset.

    The reference is a file on disk that does not change mid-process, and the
    direct-from-experiments path maps a few hundred judge files against it.
    """
    return {q: {"title": t} for q, t in R.reference_titles(dataset).items()}


def map_judge_file(path: Path, dataset: str, *, ref: dict | None = None) -> JudgeFile:
    """One judge JSON -> its verdicts, keyed by *our* question numbers.

    The judges answer their own question list and number it their own way, so
    every qid is paired by content through `build_qid_map` rather than trusted
    as-is. This is the only place that translation happens: both the mirrored
    files under `eval/<dataset>/judge_<mode>/` and the experiment tree itself
    are read through this function, so the two paths cannot disagree about
    which answer belongs to which question.

    `rating` is the judge's `decision_correctness` on the -2..2 scale; `code`
    is its raw `code_correctness` verdict, carried through unused.
    """
    ref = reference_stub(dataset) if ref is None else ref
    raw = json.loads(path.read_text())
    llm = {qid: {"title": v.get("question", "")}
           for qid, v in raw.items() if isinstance(v, dict)}

    out = JudgeFile()
    qmap = build_qid_map(ref, llm, dataset=dataset,
                         on_number_fallback=lambda qid, *_: out.by_number.append(qid))

    for our_qid, judge_qid in qmap.items():
        if judge_qid is None:
            out.unmapped.append(our_qid)
            continue
        v = raw[judge_qid]
        decision = str(v.get("decision_correctness") or "").strip().lower()
        out.ratings[our_qid] = {
            "rating": RATING_SCALE.get(decision),
            "code": (str(v.get("code_correctness") or "").strip().upper() or None),
        }
    claimed = {q for q in qmap.values() if q}
    out.extra = sorted(set(llm) - claimed, key=_qid_key)
    return out


def load_judge_ratings(dataset: str, mode: str = "supervised") -> tuple[dict, dict]:
    """
    Returns (ratings, report).

    ratings: {(our_qid, agent, trial, judge): {"rating": float|None,
                                               "code": str|None}}
    report:  {"files": n, "judges": [...], "unmapped_ours": [qid, ...],
              "extra_judge_qids": {judge: [qid, ...]}}

    `rating` is the judge's `decision_correctness` on the -2..2 scale;
    `code` is its raw `code_correctness` verdict, carried through unused.
    """
    ref_stub = reference_stub(dataset)

    out: dict = {}
    unmapped: set[str] = set()
    extra: dict[str, set[str]] = {}
    judges: set[str] = set()
    files = 0

    for path in sorted(judge_dir(dataset, mode).glob("*.json")):
        m = FILENAME_RE.match(path.name)
        if not m:
            continue
        agent, trial, judge = m["agent"], int(m["trial"]), m["judge"]
        files += 1
        judges.add(judge)

        parsed = map_judge_file(path, dataset, ref=ref_stub)
        for our_qid, v in parsed.ratings.items():
            out[(our_qid, agent, trial, judge)] = v
        unmapped.update(parsed.unmapped)
        extra.setdefault(judge, set()).update(parsed.extra)

    report = {
        "files": files,
        "judges": sorted(judges),
        "unmapped_ours": sorted(unmapped, key=_qid_key),
        "extra_judge_qids": {j: sorted(v, key=_qid_key) for j, v in extra.items()},
    }
    return out, report


def _qid_key(q: str):
    m = re.match(r"(\d+)", q)
    return (int(m.group(1)) if m else 999, q.split("-")[1] if "-" in q else "")
