"""Load every rater's ratings for every question into one structure.

Four raters rate the same questions: the two human evaluators (LZ, KB) and the
two LLM judges (Claude, Codex). They live in different places and different
shapes — humans as `**Rating:**` lines in their dossier copies, judges as JSON
mirrored out of the experiment tree — so this module reads both and lines them
up on our reference question numbering.

Vocabulary, kept apart deliberately because the old notebook conflated them:

    rater   who produced a rating: LZ, KB, claude, codex
    agent   the system being evaluated: claude-code, codex

Missing ratings stay missing (NaN) — KB has not rated zhong2025 at all, and
that is a real gap, not a zero. The memory question is dropped outright: it
postdates the judges, so no judge ever answered it (see
`EXCLUDED_TITLE_PATTERNS`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import raters as R
import utils
from . import judges as judges_mod

# Questions left out of every analysis. "How is memory usage optimized?" was
# added to the references after the judges ran, so no judge ever answered it —
# keeping it would mean a row that is blank for two of the four raters in every
# dataset. Matched on the question text, not its number, because the numbers
# move (see the 2026-08 renumbering).
EXCLUDED_TITLE_PATTERNS = ("memory usage",)

# The category that asks about performance rather than correctness. Agreement
# between raters is about whether they judge the same code as correct, so the
# efficiency questions — advice, not a correctness check — are excluded there.
PERFORMANCE_CATEGORY = "Code Efficiency"

HUMAN_RATERS = ("LZ", "KB")
JUDGE_RATERS = ("claude", "codex")
RATERS = HUMAN_RATERS + JUDGE_RATERS

# Display order: supervised-behaviour datasets first, then the rest — the order
# the summary visualisation has always used.
DATASET_ORDER = [
    "allen2p", "lee2025", "majnik2025", "sosa2024",
    "chen2024", "hasnain2024", "zhang2025", "zhong2025",
]


@dataclass
class Ratings:
    """Every rater's ratings, in the two shapes the analyses need."""

    tidy: pd.DataFrame        # one row per (dataset, qid, agent, trial)
    nested: dict              # dataset -> main -> sub -> {...}, for utils' renderers
    coverage: pd.DataFrame    # per (dataset, rater): rated / missing counts
    judge_report: dict = field(default_factory=dict)
    excluded: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def correctness(self) -> pd.DataFrame:
        """`tidy` without the performance questions — correctness only."""
        return self.tidy[self.tidy["category"] != PERFORMANCE_CATEGORY]

    def rated(self, rater: str) -> pd.DataFrame:
        """Rows where `rater` gave a rating."""
        return self.tidy[self.tidy[rater].notna()]

    def __repr__(self) -> str:
        n = len(self.tidy)
        got = {r: int(self.tidy[r].notna().sum()) for r in RATERS}
        return (f"Ratings({self.tidy['dataset'].nunique()} datasets, {n} rows, "
                + ", ".join(f"{k}={v}" for k, v in got.items()) + ")")


def _split_qid(qid: str) -> tuple[str, str]:
    main, _, sub = qid.partition("-")
    return main, sub


def _is_excluded(title: str, patterns) -> bool:
    low = title.lower()
    return any(p in low for p in patterns)


def load_ratings(datasets: list[str] | None = None,
                 judge_mode: str = "supervised",
                 exclude_titles=EXCLUDED_TITLE_PATTERNS) -> Ratings:
    """
    Build the combined rating table.

    `datasets` defaults to every dataset with dossiers, in display order.
    `judge_mode` selects `judge_supervised/` or `judge_unsupervised/`; a
    dataset with no judge output for that mode simply contributes NaN judge
    columns, so the unsupervised half can be analysed as it arrives.
    """
    if datasets is None:
        have = set(R.datasets())
        datasets = [d for d in DATASET_ORDER if d in have]
        datasets += [d for d in sorted(have) if d not in DATASET_ORDER]

    rows: list[dict] = []
    excluded: list[dict] = []
    nested: dict = {}
    coverage: list[dict] = []
    judge_report: dict = {}

    for ds in datasets:
        ref = R.reference_titles(ds)
        if not ref:
            continue
        human_codes = [c for c in HUMAN_RATERS if R.rater_dir(ds, c).is_dir()]
        human = R.collect_ratings(ds, human_codes) if human_codes else {}

        if judges_mod.available(ds, judge_mode):
            judge, report = judges_mod.load_judge_ratings(ds, judge_mode)
        else:
            judge, report = {}, {"files": 0, "judges": [], "unmapped_ours": [],
                                 "extra_judge_qids": {}}
        judge_report[ds] = report

        per_rater_counts = {r: 0 for r in RATERS}
        ds_nested: dict = {}

        for qid in sorted(ref, key=_qid_sort_key):
            main, sub = _split_qid(qid)
            title = ref[qid]
            if _is_excluded(title, exclude_titles):
                excluded.append({"dataset": ds, "qid": qid, "title": title})
                continue
            cat = utils.categorize(qid, title)
            series = {r: [] for r in RATERS}
            agents, trials = [], []

            for (agent, trial) in R.TRIAL_KEYS:
                agents.append(agent)
                trials.append(trial)
                cell = human.get(qid, {}).get((agent, trial), {})
                rec = {
                    "dataset": ds, "qid": qid, "main": main, "sub": sub,
                    "title": title,
                    "category": cat[0] if cat else None,
                    "subtype": cat[1] if cat else None,
                    "var_label": cat[2] if cat else None,
                    "agent": agent, "trial": trial,
                }
                for r in HUMAN_RATERS:
                    val = utils.RATING_SCALE.get((cell.get(r) or "").lower())
                    rec[r] = val
                    series[r].append(val)
                for r in JUDGE_RATERS:
                    j = judge.get((qid, agent, trial, r), {})
                    rec[r] = j.get("rating")
                    rec[f"{r}_code"] = j.get("code")
                    series[r].append(j.get("rating"))
                for r in RATERS:
                    per_rater_counts[r] += rec[r] is not None
                rows.append(rec)

            q = {"title": title, "agents": agents,
                 "trials": np.array(trials, dtype=int)}
            for r in RATERS:
                q[r] = np.array([np.nan if v is None else v for v in series[r]],
                                dtype=float)
            ds_nested.setdefault(main, {})[sub] = q

        nested[ds] = ds_nested
        n_questions = sum(len(s) for s in ds_nested.values())
        n_cells = n_questions * len(R.TRIAL_KEYS)
        for r in RATERS:
            coverage.append({
                "dataset": ds, "rater": r,
                "rated": per_rater_counts[r],
                "missing": n_cells - per_rater_counts[r],
                "questions": n_questions,
            })

    tidy = pd.DataFrame(rows)
    return Ratings(tidy=tidy, nested=nested,
                   coverage=pd.DataFrame(coverage), judge_report=judge_report,
                   excluded=pd.DataFrame(excluded))


def _qid_sort_key(q: str):
    main, _, sub = q.partition("-")
    try:
        head = int(main)
    except ValueError:
        head = 999
    return (head, sub)


def coverage_summary(ratings: Ratings) -> pd.DataFrame:
    """Wide view of `ratings.coverage`: one row per dataset, one column per rater."""
    piv = ratings.coverage.pivot(index="dataset", columns="rater", values="rated")
    piv["cells"] = (ratings.coverage.groupby("dataset")["questions"].first()
                    * len(R.TRIAL_KEYS))
    order = [d for d in DATASET_ORDER if d in piv.index]
    return piv.loc[order, list(RATERS) + ["cells"]]


def unanswered_by_judges(ratings: Ratings) -> pd.DataFrame:
    """Questions no judge rated, per dataset, among the questions we kept.

    Empty once the memory question is excluded — every remaining question maps
    onto a judge entry.
    """
    kept = set(zip(ratings.tidy["dataset"], ratings.tidy["qid"]))
    recs = []
    for ds, rep in ratings.judge_report.items():
        for qid in rep.get("unmapped_ours", []):
            if (ds, qid) not in kept:
                continue
            recs.append({"dataset": ds, "qid": qid,
                         "title": R.reference_titles(ds).get(qid, "")})
    return pd.DataFrame(recs)


def correctness_only(df: pd.DataFrame) -> pd.DataFrame:
    """Drop the performance questions — keep only correctness questions."""
    return df[df["category"] != PERFORMANCE_CATEGORY]


def add_null(df: pd.DataFrame, *, source: str = "LZ", name: str | None = None,
             seed: int = 0, within: str | list[str] | None = None) -> pd.DataFrame:
    """Add a frequency-matched null rater: `source`'s ratings, shuffled.

    The null keeps the rating *distribution* exactly — same count of every
    level — but destroys any link between a rating and the trial it describes.
    It is the floor the real raters should be read against: exact-agreement
    looks high on this data simply because most ratings are "match", and the
    null shows how much of that is the distribution alone. Chance-corrected
    measures (kappa) should sit at ~0 for it.

    Shuffling happens within whatever frame is passed, so call it on the subset
    being analysed and the marginals match that subset. `within` restricts the
    permutation further (e.g. `within="dataset"` keeps each dataset's own
    distribution). `seed` makes it reproducible.
    """
    name = name or f"{source}_null"
    out = df.copy()
    rng = np.random.default_rng(seed)

    def shuffled(col: pd.Series) -> np.ndarray:
        vals = col.to_numpy(dtype=float, copy=True)
        mask = ~np.isnan(vals)
        vals[mask] = rng.permutation(vals[mask])
        return vals

    if within is None:
        out[name] = shuffled(out[source])
    else:
        out[name] = np.nan
        for _, idx in out.groupby(within, dropna=False).groups.items():
            out.loc[idx, name] = shuffled(out.loc[idx, source])
    return out


def uniform_variables(df: pd.DataFrame, *, rater: str = "LZ",
                      subtypes=("Source variables", "Processing"),
                      level: float = 1.0,
                      datasets: list[str] | None = None) -> pd.DataFrame:
    """Data Variables whose `subtypes` rows are all rated `level`, per dataset.

    A variable every agent gets perfectly right in every trial carries no
    information in the summary figure — this is how to find those candidates
    rather than maintaining a hand-written list that goes stale when questions
    are renumbered. Returns one row per (dataset, variable) with the count of
    cells checked and, for context, what the variable's other sub-questions
    were rated.
    """
    d = df[df["category"] == "Data Variables"]
    if datasets is not None:
        d = d[d["dataset"].isin(datasets)]

    out = []
    for (ds, var), grp in d.groupby(["dataset", "var_label"], dropna=True):
        target = grp[grp["subtype"].isin(subtypes)]
        present = set(target["subtype"])
        vals = target[rater]
        if set(subtypes) - present or vals.isna().any() or not (vals == level).all():
            continue
        other = grp[~grp["subtype"].isin(subtypes)]
        summary = {st: sorted(set(g[rater].dropna()))
                   for st, g in other.groupby("subtype")}
        out.append({
            "dataset": ds, "variable": var,
            "n_cells": int(len(vals)),
            "subtypes_checked": ", ".join(sorted(present)),
            "other_subtypes": "; ".join(f"{k}={v}" for k, v in sorted(summary.items())) or "-",
        })
    # Always the same columns, so callers can index an empty result — KB has no
    # zhong2025 ratings, which makes an empty return entirely normal here.
    return pd.DataFrame(out, columns=["dataset", "variable", "n_cells",
                                      "subtypes_checked", "other_subtypes"])
