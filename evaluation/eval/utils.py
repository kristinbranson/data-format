"""Loading + plotting utilities for the eval summary notebook.

This module consolidates two concerns:

  1. Parsing the per-dataset ``eval_summary.md`` files into a structured
     in-memory representation: ``load_all``, ``iter_trials``,
     ``iter_questions``, ``to_dataframe``.

  2. Categorizing questions into a fixed taxonomy (Data Loading / Neural
     Data / Data Variables / Missing-Data Handling / End-to-End / Code
     Efficiency) and
     rendering the per-dataset rating heatmap used in ``analysis.ipynb``
     (``categorize``, ``collect_rows``, ``compute_layout``,
     ``draw_dataset_column``, ``draw_label_column``).

Per dataset → per main qid ("1", "2", ...) → per sub-qid ("a", "b", ..., or
"" if the question has no sub-letter):

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


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


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


def _pick_best_rating(best_who: str | None, h, jc, jx):
    if best_who is None or best_who.lower() == "human":
        return h
    if best_who.lower().startswith("claude"):
        return jc
    if best_who.lower().startswith("codex"):
        return jx
    return h  # unknown label → fall back to human


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


def load_all(eval_dir: Path = EVAL_DIR) -> dict[str, dict[str, dict[str, dict]]]:
    """Load every eval_summary.md under eval_dir → {dataset: {main: {sub: {...}}}}."""
    datasets: dict[str, dict[str, dict[str, dict]]] = {}
    for path in sorted(eval_dir.glob("*/eval_summary.md")):
        datasets[path.parent.name] = _parse_eval_summary(path)
    return datasets


def load_dataset(dataset: str, eval_dir: Path = EVAL_DIR) -> dict[str, dict[str, dict]]:
    return _parse_eval_summary(eval_dir / dataset / "eval_summary.md")


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


def iter_questions(data):
    """One record per (dataset, qid). Ratings come back as length-6 arrays."""
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


# ---------------------------------------------------------------------------
# Question taxonomy + categorization
# ---------------------------------------------------------------------------


CATEGORY_ORDER = [
    "Data Loading",
    "Neural Data",
    "Data Variables",
    "Missing-Data Handling",
    "End-to-End",
    "Code Efficiency",
]

SUBTYPE_ORDER = {
    "Data Loading": [
        "Overall",
        "Split into subjects",
        "Split into sessions",
        "Split into trials",
        "Trial filtering",
    ],
    "Neural Data": [
        "Source variables",
        "Processing",
        "Filtering",
        "Time resolution",
        "Alignment",
    ],
    "Data Variables": [
        "Source variables",
        "Processing",
        "Alignment",
    ],
    "Missing-Data Handling": [""],
    "End-to-End": [""],
    "Code Efficiency": [
        "Processing time",
        "Vectorization",
        "Repeated work",
        "Unnecessary work",
        "Memory usage",
    ],
}

_Q1_SUB = {
    "a": "Overall",
    "b": "Split into subjects",
    "c": "Split into sessions",
    "d": "Split into trials",
    "e": "Trial filtering",
}
_Q2_SUB = {
    "a": "Source variables",
    "b": "Processing",
    "c": "Filtering",
    "d": "Time resolution",
    "e": "Alignment",
}
_VAR_SUB = {
    "a": "Source variables",
    "b": "Processing",
    "c": "Alignment",
}
_EFF_KEYWORDS = [
    ("time-consuming", "Processing time"),
    ("vectorized", "Vectorization"),
    ("repeat", "Repeated work"),
    ("unnecessary", "Unnecessary work"),
    ("memory", "Memory usage"),
]

_VAR_TITLE_RE = re.compile(r"`(input|output)`\s*\*([^*]+)\*")


def categorize(qid, title):
    """Map (qid, title) -> (category, subtype, var_label) or None."""
    title_lower = title.lower()

    if qid.startswith("1-"):
        sub = _Q1_SUB.get(qid.split("-", 1)[1])
        if sub:
            return ("Data Loading", sub, None)

    if qid.startswith("2-"):
        sub = _Q2_SUB.get(qid.split("-", 1)[1])
        if sub:
            return ("Neural Data", sub, None)

    if "missing data" in title_lower:
        return ("Missing-Data Handling", "", None)

    for kw, sub in _EFF_KEYWORDS:
        if kw in title_lower:
            return ("Code Efficiency", sub, None)

    m = _VAR_TITLE_RE.search(title)
    if m and "-" in qid:
        kind, name = m.group(1), m.group(2).strip()
        sub_letter = qid.split("-", 1)[1]
        sub = _VAR_SUB.get(sub_letter)
        if sub:
            return ("Data Variables", sub, f"{kind}: {name}")

    return None


def collect_rows(dataset_data):
    """Walk one dataset's nested dict -> ordered list of row specs.

    Variables rows are ordered so vars-with-alignment come first within each
    sub-type, so the i-th row of Source variables / Processing / Alignment
    refers to the same variable for i < n_vars_with_alignment.
    """
    var_groups = {}      # main_qid -> {sub_letter: row}
    other_rows = []
    for main, subs in dataset_data.items():
        for sub_letter, q in subs.items():
            qid = f"{main}-{sub_letter}" if sub_letter else main
            cat = categorize(qid, q["title"])
            if cat is None:
                continue
            category, subtype, var_label = cat
            row = {
                "qid": qid,
                "category": category,
                "subtype": subtype,
                "var_label": var_label,
                "title": q["title"],
                "ratings": q["best_rating"],
                "agents": list(q["agents"]),
                "trials": q["trials"],
            }
            if category == "Data Variables":
                var_groups.setdefault(main, {})[sub_letter] = row
            else:
                other_rows.append(row)

    def main_key(m):
        try:
            return int(m)
        except ValueError:
            return m

    with_align = sorted([m for m, subs in var_groups.items() if "c" in subs], key=main_key)
    without_align = sorted([m for m, subs in var_groups.items() if "c" not in subs], key=main_key)
    var_order = with_align + without_align

    var_rows = []
    for sub_letter in ("a", "b", "c"):
        for main in var_order:
            if sub_letter in var_groups[main]:
                var_rows.append(var_groups[main][sub_letter])

    cat_idx = {c: i for i, c in enumerate(CATEGORY_ORDER)}

    def other_key(r):
        ci = cat_idx.get(r["category"], len(CATEGORY_ORDER))
        sub_list = SUBTYPE_ORDER.get(r["category"], [])
        si = sub_list.index(r["subtype"]) if r["subtype"] in sub_list else len(sub_list)
        return (ci, si, r["qid"])

    other_rows.sort(key=other_key)

    rows = []
    inserted_vars = False
    for r in other_rows:
        if not inserted_vars and cat_idx.get(r["category"], 99) > cat_idx["Data Variables"]:
            rows.extend(var_rows)
            inserted_vars = True
        rows.append(r)
    if not inserted_vars:
        rows.extend(var_rows)

    return rows


# ---------------------------------------------------------------------------
# Layout + plotting
# ---------------------------------------------------------------------------


def compute_layout(datasets_rows, *,
                   square=0.9, subtype_gap=0.5, category_gap=1.1):
    """Build a unified y-layout from one or more dataset row-lists.

    Pass a single rows list to lay out one dataset, or a list of rows lists to
    align categories/subtypes across datasets (each subtype slot is sized to
    the max row count seen across all datasets).

    `subtype_gap` is either a single float (uniform gap between sub-types
    inside every category) or a dict ``{category_name: gap}`` with optional
    ``"*"`` key for the default — e.g. ``{"Data Variables": 0.5, "*": 0.15}`` to
    use a tighter gap everywhere except inside the Variables block.
    """
    if datasets_rows and isinstance(datasets_rows[0], dict):
        datasets_rows = [datasets_rows]

    if isinstance(subtype_gap, dict):
        default_gap = subtype_gap.get("*", 0.5)
        gap_by_cat = subtype_gap
    else:
        default_gap = float(subtype_gap)
        gap_by_cat = {}

    def gap_for(cat):
        return gap_by_cat.get(cat, default_gap)

    max_per_subtype = {}
    for rows in datasets_rows:
        counts = {}
        for r in rows:
            key = (r["category"], r["subtype"])
            counts[key] = counts.get(key, 0) + 1
        for k, v in counts.items():
            max_per_subtype[k] = max(max_per_subtype.get(k, 0), v)

    y_pos = {}
    sub_extents = {}
    cat_extents = {}
    y = 0.0
    prev_cat = None
    prev_sub = None
    for cat in CATEGORY_ORDER:
        for sub in SUBTYPE_ORDER.get(cat, []):
            key = (cat, sub)
            if key not in max_per_subtype:
                continue
            if prev_cat is not None:
                if cat != prev_cat:
                    y -= category_gap
                elif sub != prev_sub:
                    y -= gap_for(cat)
            slot_top = y
            for slot in range(max_per_subtype[key]):
                y -= square
                y_pos[(cat, sub, slot)] = y
            sub_extents[key] = (slot_top, y)
            if cat not in cat_extents:
                cat_extents[cat] = [slot_top, y]
            else:
                cat_extents[cat][0] = max(cat_extents[cat][0], slot_top)
                cat_extents[cat][1] = min(cat_extents[cat][1], y)
            prev_cat, prev_sub = cat, sub

    return {
        "y_pos": y_pos,
        "sub_extents": sub_extents,
        "cat_extents": cat_extents,
        "y_top": 0.0,
        "y_bot": y,
        "square": square,
        "category_gap": category_gap,
    }


RATING_COLORS = {
     2: "#1f77b4",   # better — blue
     1: "#2ca02c",   # match — dark green
     0: "#86c98a",   # ok — light green
    -1: "#f0c419",   # concerning — yellow
    -2: "#d62728",   # incorrect — red
}
NAN_COLOR = "#e8e8e8"


def _rating_color(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return NAN_COLOR
    return RATING_COLORS.get(int(v), NAN_COLOR)


def draw_dataset_column(ax, rows, layout, *,
                        title=None,
                        agent_gap=0.35,
                        rating_colors=RATING_COLORS,
                        nan_color=NAN_COLOR,
                        show_labels=True,
                        keep_aspect=True,
                        cell_size_frac=1.0,
                        subtype_label_x=-0.6,
                        category_label_x=-6.5,
                        band_colors=("#f3f3f3", None)):
    """Draw one dataset column (rating squares + section bands + title) on `ax`.

    Set ``show_labels=False`` to draw only the data — no left margin reserved
    for labels — so multiple dataset axes can be packed tightly side-by-side.
    Set ``keep_aspect=False`` when packing many columns side-by-side: the cells
    become slightly rectangular but the axes box fills its gridspec slot, so
    rows align physically with a separate label axes.
    ``cell_size_frac`` shrinks each rendered cell within its layout slot
    (1.0 = touching cells, 0.9 = small gap between adjacent cells, etc.).
    """
    from matplotlib.patches import Circle, Rectangle

    square = layout["square"]
    category_gap = layout["category_gap"]
    cell_size = square * cell_size_frac
    cell_inset = (square - cell_size) / 2

    xs = []
    x = 0.0
    for i in range(6):
        if i == 3:
            x += agent_gap
        xs.append(x)
        x += square
    col_width = x

    y_pos = layout["y_pos"]
    sub_extents = layout["sub_extents"]
    cat_extents = layout["cat_extents"]

    slot_counters = {}
    row_ys = []
    for r in rows:
        key = (r["category"], r["subtype"])
        slot = slot_counters.get(key, 0)
        slot_counters[key] = slot + 1
        row_ys.append(y_pos[(r["category"], r["subtype"], slot)])

    if show_labels:
        x_lo = category_label_x - 0.8
    else:
        x_lo = -0.2
    x_hi = col_width + 0.2

    if band_colors:
        ordered_cats = sorted(cat_extents, key=lambda c: -cat_extents[c][0])
        for i, cat in enumerate(ordered_cats):
            band = band_colors[i % len(band_colors)]
            if band is None:
                continue
            y_hi, y_lo = cat_extents[cat]
            pad_top = category_gap / 2 if i > 0 else square / 3
            pad_bot = category_gap / 2 if i < len(ordered_cats) - 1 else square / 3
            ax.add_patch(Rectangle(
                (x_lo, y_lo - pad_bot),
                x_hi - x_lo,
                (y_hi + pad_top) - (y_lo - pad_bot),
                facecolor=band, edgecolor="none", zorder=-2,
            ))

    for r, y in zip(rows, row_ys):
        kind = r.get("render", "squares")
        if kind == "symbols":
            # Per-cell glyph colored by the underlying rating value:
            #   ≥ 0 → ✓, [-1, 0) → ○ (open circle patch), < -1 → ✗
            for i, rating in enumerate(r["ratings"]):
                if rating is None or (isinstance(rating, float) and np.isnan(rating)):
                    continue
                color = _rating_color(rating)
                cx = xs[i] + square / 2
                cy = y + square / 2
                if rating >= -1 and rating < 0:
                    ax.add_patch(Circle((cx, cy), radius=square * 0.22,
                                        fill=False, edgecolor=color,
                                        linewidth=1.6, zorder=2))
                else:
                    symbol = "✓" if rating >= 0 else "✗"
                    ax.text(cx, cy, symbol, ha="center", va="center",
                            color=color, fontsize=14, fontweight="bold",
                            zorder=2)
        elif kind == "text":
            # Text labels in r["text"]. Length 6 → one per cell; length 2 →
            # one per agent group (centered across that group's 3 cells).
            text = list(r.get("text", []))
            if len(text) == 2:
                positions = [
                    (xs[0] + xs[2] + square) / 2,   # claude group center
                    (xs[3] + xs[5] + square) / 2,   # codex group center
                ]
                fontsize = r.get("text_fontsize", 10)
            else:
                positions = [xs[i] + square / 2 for i in range(len(text))]
                fontsize = r.get("text_fontsize", 7)
            for x_center, label in zip(positions, text):
                if not label:
                    continue
                ax.text(x_center, y + square / 2, label,
                        ha="center", va="center", fontsize=fontsize,
                        color="#333333", zorder=2)
        else:  # "squares"
            for i, rating in enumerate(r["ratings"]):
                ax.add_patch(Rectangle((xs[i] + cell_inset, y + cell_inset),
                                       cell_size, cell_size,
                                       facecolor=_rating_color(rating),
                                       edgecolor="white", linewidth=0.5,
                                       zorder=1))

    if show_labels:
        for (c, s), (y_hi, y_lo) in sub_extents.items():
            label = c if c in {"Missing-Data Handling", "End-to-End"} else s
            ax.text(subtype_label_x, (y_hi + y_lo) / 2, label,
                    ha="right", va="center", fontsize=8)
        for cat, (y_hi, y_lo) in cat_extents.items():
            n_subs = sum(1 for (c2, _) in sub_extents if c2 == cat)
            if n_subs <= 1:
                continue
            ax.text(category_label_x, (y_hi + y_lo) / 2, cat,
                    ha="right", va="center", fontsize=9,
                    fontweight="bold", rotation=90)

    y_top_data = layout["y_top"]
    y_bot_data = layout["y_bot"]
    if title is not None:
        ax.text(col_width / 2, y_top_data + 0.6, title,
                ha="center", va="bottom",
                fontsize=11, fontweight="bold")

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_bot_data - 0.3, y_top_data + (1.6 if title else 0.3))
    if keep_aspect:
        ax.set_aspect("equal")
    for spine in ax.spines.values():
        spine.set_visible(False)


def draw_label_column(ax, layout, *,
                      subtype_label_x=1.0,
                      category_label_x=0.1,
                      ax_xlim=(0.0, 1.05),
                      title_pad=1.6):
    """Draw row/category labels on a standalone axes, aligned to `layout`.

    Use this as the leftmost axes when plotting multiple dataset columns: it
    occupies its own gridspec slot and does not constrain the data axes.
    No aspect ratio is forced, so this axes can be any physical width.
    """
    sub_extents = layout["sub_extents"]
    cat_extents = layout["cat_extents"]

    for (c, s), (y_hi, y_lo) in sub_extents.items():
        label = c if c in {"Missing-Data Handling", "End-to-End"} else s
        ax.text(subtype_label_x, (y_hi + y_lo) / 2, label,
                ha="right", va="center", fontsize=8,
                transform=ax.transData, clip_on=False)
    for cat, (y_hi, y_lo) in cat_extents.items():
        n_subs = sum(1 for (c2, _) in sub_extents if c2 == cat)
        if n_subs <= 1:
            continue
        ax.text(category_label_x, (y_hi + y_lo) / 2, cat,
                ha="left", va="center", fontsize=9,
                fontweight="bold", rotation=90,
                transform=ax.transData, clip_on=False)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(*ax_xlim)
    ax.set_ylim(layout["y_bot"] - 0.3, layout["y_top"] + title_pad)
    for spine in ax.spines.values():
        spine.set_visible(False)


# ---------------------------------------------------------------------------
# Per-trial overall score (used for the End-to-End summary row)
# ---------------------------------------------------------------------------


BUCKET_ORDER = ["≥ match", "≥ ok", "≥ concerning", "has incorrect"]


def bucket(min_rating):
    """Map the worst rating in a trial to a coarse bucket label."""
    if min_rating is None or (isinstance(min_rating, float) and np.isnan(min_rating)):
        return None
    if min_rating >= 1:  return "≥ match"
    if min_rating >= 0:  return "≥ ok"
    if min_rating >= -1: return "≥ concerning"
    return "has incorrect"


def compute_trial_scores(data, *, exclude_categories=("Code Efficiency",)):
    """Per-(dataset, agent, trial) overall score across questions in `data`.

    For each trial slot, gather the best_rating values of every question
    that is NOT in ``exclude_categories`` (Code Efficiency by default,
    since it is "soft" advice rather than a correctness check), and
    summarize:
      n_questions  count of valid (non-NaN) ratings
      n_ok         count of ratings ≥ 0
      min_rating   worst rating across the trial (drives the bucket)
      bucket       one of BUCKET_ORDER

    Returns a list of records (call ``pd.DataFrame(...)`` on the result).
    """
    excluded = set(exclude_categories)
    records = []
    for ds, mains in data.items():
        # 6 trial slots = 3 claude-code + 3 codex.
        trial_ratings = [[] for _ in range(6)]
        trial_meta = [None] * 6
        for main, subs in mains.items():
            for sub_letter, q in subs.items():
                qid = f"{main}-{sub_letter}" if sub_letter else main
                cat = categorize(qid, q["title"])
                if cat is None or cat[0] in excluded:
                    continue
                for i, r in enumerate(q["best_rating"]):
                    trial_ratings[i].append(r)
                    if trial_meta[i] is None:
                        trial_meta[i] = (q["agents"][i], int(q["trials"][i]))

        for i in range(6):
            if trial_meta[i] is None:
                continue
            rs = np.array(trial_ratings[i], dtype=float)
            valid = rs[~np.isnan(rs)]
            min_r = float(valid.min()) if valid.size else None
            n_ok = int((valid >= 0).sum())
            records.append({
                "dataset": ds,
                "agent": trial_meta[i][0],
                "trial": trial_meta[i][1],
                "n_questions": int(valid.size),
                "n_ok": n_ok,
                "min_rating": min_r,
                "bucket": bucket(min_r),
            })
    return records


def end_to_end_rows(ds, trial_scores, *, agents=("claude-code", "codex")):
    """Build the two End-to-End row specs for one dataset's column.

    `trial_scores` is the DataFrame returned by ``compute_trial_scores``.
    Returns a list of two row dicts ready to splice into a column's row list:
      [0] render="symbols" — worst rating per trial as ✓ / ○ / ✗
      [1] render="text"    — mean (n_ok / n_questions) per agent (one
                             number per agent group, e.g. "0.85")
    """
    sub = trial_scores[trial_scores.dataset == ds].sort_values(["agent", "trial"])
    common = {
        "category": "End-to-End",
        "subtype": "",
        "var_label": None,
        "agents": list(sub["agent"]),
        "trials": np.array(sub["trial"], dtype=int),
    }

    per_agent = []
    for agent in agents:
        ag = sub[sub.agent == agent]
        if len(ag) == 0:
            per_agent.append("")
            continue
        frac = (ag["n_ok"] / ag["n_questions"]).mean()
        per_agent.append(f"{frac:.3f}")

    return [
        {
            **common,
            "qid": "ete-symbol",
            "title": "End-to-End worst rating per trial",
            "ratings": np.array(sub["min_rating"].tolist(), dtype=float),
            "render": "symbols",
        },
        {
            **common,
            "qid": "ete-frac",
            "title": "End-to-End mean n_ok/n_questions per agent",
            "ratings": np.full(len(sub), np.nan),
            "text": per_agent,
            "render": "text",
        },
    ]


def insert_end_to_end(rows, e2e_rows):
    """Splice End-to-End rows into a dataset row list, just before any
    Code Efficiency rows (so the section ordering matches CATEGORY_ORDER).
    """
    pre = [r for r in rows if r["category"] != "Code Efficiency"]
    post = [r for r in rows if r["category"] == "Code Efficiency"]
    return pre + list(e2e_rows) + post


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
