#!/usr/bin/env python3
"""
Generate a human-readable evaluation report (markdown) for one dataset.

Sources (all already produced by other tools):
  - evaluation/eval/<dataset>/<CODE>/summary.md  (rate.py output, per evaluator: solution ratings + per-Q overall comment about the SOLUTION)
  - evaluation/eval/<dataset>/eval_summary.md  (compare.py output: one column per evaluator + Claude-judge + Codex-judge ratings + per-Q overall comment about the JUDGES)

Output:
  - evaluation/eval/<dataset>/report.md

Usage:
    python3 report.py <dataset>
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path("/groups/zhang/home/zhangl5/Data-Format")
EVAL_DIR = REPO_ROOT / "evaluation" / "eval"

# Canonical 6-trial order: cc1, cc2, cc3, cx1, cx2, cx3
TRIAL_KEYS = [("claude-code", n) for n in (1, 2, 3)] + [("codex", n) for n in (1, 2, 3)]

# Visual mapping — colored squares chosen for at-a-glance scanning.
# A circle (same color) replaces the square when the LLM judge was picked
# as better than the human, so the cell width never changes.
# Default rating shapes are circles; squares (same color) mark cells where the
# LLM judge was deemed better than the human. Width unchanged either way.
RATING_DEFAULT = {   # circles
    "better":     "🟣",
    "match":      "🟢",
    "ok":         "🔵",
    "concerning": "🟡",
    "incorrect":  "🔴",
    "missing":    "⚪",
}
RATING_PICKED = {    # squares (LLM judge > human)
    "better":     "🟪",
    "match":      "🟩",
    "ok":         "🟦",
    "concerning": "🟨",
    "incorrect":  "🟥",
    "missing":    "⬜",
}
EMPTY_MARK = "⚫"   # black circle — matches the default-shape convention

LEGEND_LINE = (
    "🟣 better · 🟢 match · 🔵 ok · 🟡 concerning · 🔴 incorrect · ⚪ missing · ⚫ no rating"
)


# ---------- markdown table parsing ----------

def _split_md_row(line: str) -> list[str] | None:
    """Split a markdown table row into cells, respecting `\\|` escapes."""
    if not line.strip().startswith("|"):
        return None
    s = line.strip()
    cells, buf, i = [], [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    # Strip leading empty (from the line's leading `|`).
    # Do NOT strip the trailing empty: it's a legitimate empty cell
    # (the closing `|` does not produce a phantom cell since the loop ends on it).
    if cells and cells[0] == "":
        cells = cells[1:]
    return cells


def _qid_sort_key(q: str):
    m = re.match(r"(\d+)", q)
    return (int(m.group(1)) if m else 999, q.split("-")[1] if "-" in q else "")


# ---------- summary.md (rate.py) ----------

def parse_rate_summary(path: Path) -> tuple[dict, dict, dict]:
    """
    Returns (human_ratings, titles, solution_comments).
      human_ratings: {(qid, agent, n): rating}
      titles: {qid: title}
      solution_comments: {qid: text}  (from `**Overall comment:**`)
    """
    if not path.exists():
        return {}, {}, {}
    text = path.read_text()
    sec_re = re.compile(
        r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    ratings, titles, comments = {}, {}, {}
    for sec in sec_re.finditer(text):
        qid = sec.group(1)
        title = sec.group(2).strip()
        body = sec.group(3)
        titles[qid] = title
        for line in body.splitlines():
            cells = _split_md_row(line)
            if not cells or len(cells) != 3:
                continue
            trial, rating, note = cells
            m = re.match(r"^(claude-code|codex)\s*/\s*trial([1-3])$", trial)
            if not m:
                continue
            ratings[(qid, m.group(1), int(m.group(2)))] = rating.strip().lower()
        cm = re.search(r"^\*\*Overall comment:\*\*\s*(.+)$", body, re.MULTILINE)
        if cm:
            comments[qid] = cm.group(1).strip()
    return ratings, titles, comments


# ---------- eval_summary.md (compare.py) ----------

def _eval_header_cols(line: str, rater: str) -> dict[str, int] | None:
    """Map an eval_summary header row → {field: index}, or None if not a header.

    The evaluator columns are named by code ("LZ", "KB"); files written before
    evaluators were named use a single "Human" column.
    """
    cells = _split_md_row(line)
    if not cells or not cells[0].lower().startswith("agent"):
        return None
    cols = {}
    for i, name in enumerate(cells):
        key = name.strip().lower()
        if key in ("claude judge", "claude"):
            cols["claude"] = i
        elif key in ("codex judge", "codex"):
            cols["codex"] = i
        elif key == "best":
            cols["best"] = i
        elif key == "human" or name.strip() == rater:
            cols["human"] = i
    return cols


def parse_eval_summary(path: Path, rater: str = "") -> tuple[dict, dict, dict, dict, dict]:
    """
    Returns (human_ratings, claude_ratings, codex_ratings, judge_comments, best_picks).
      *_ratings:    {(qid, agent, n): rating}
      judge_comments: {qid: text}  (from `**Overall comment:**`)
      best_picks:   {(qid, agent, n): "<evaluator code>" | "Claude judge" | "Codex judge" | "—"}
    `rater` selects which evaluator's column is reported as the human one.
    """
    if not path.exists():
        return {}, {}, {}, {}, {}
    text = path.read_text()
    sec_re = re.compile(
        r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    h, c, x, comments, best = {}, {}, {}, {}, {}
    for sec in sec_re.finditer(text):
        qid = sec.group(1)
        body = sec.group(3)
        cols: dict[str, int] = {}
        for line in body.splitlines():
            header = _eval_header_cols(line, rater)
            if header:
                cols = header
                continue
            cells = _split_md_row(line)
            if not cells or not cols:
                continue
            m = re.match(r"^(claude-code|codex)\s*/\s*trial([1-3])$", cells[0])
            if not m:
                continue
            cell = lambda k: (cells[cols[k]].strip()
                              if k in cols and cols[k] < len(cells) else "")
            key = (qid, m.group(1), int(m.group(2)))
            h[key] = cell("human").lower()
            c[key] = cell("claude").lower()
            x[key] = cell("codex").lower()
            best[key] = cell("best")
        cm = re.search(r"^\*\*Overall comment:\*\*\s*(.+)$", body, re.MULTILINE)
        if cm:
            comments[qid] = cm.group(1).strip()
    return h, c, x, comments, best


def square(rating: str | None, picked: bool = False) -> str:
    """Return the colored marker for a rating.
    Default = circle. If `picked` is True (LLM judge > human), use a square."""
    if rating is None or rating in ("—", ""):
        return EMPTY_MARK
    table = RATING_PICKED if picked else RATING_DEFAULT
    return table.get(rating.lower(), EMPTY_MARK)


def six_squares(ratings: dict, qid: str,
                highlight: dict | None = None,
                judge_label: str | None = None) -> str:
    """
    Return cc1 cc2 cc3 cx1 cx2 cx3 as 6 colored squares.
    If `highlight` is provided (best_picks dict) and `judge_label` matches the
    user's pick for that trial, prepend a ⭐ to that square.
    """
    parts_cc, parts_cx = [], []
    for agent, n in TRIAL_KEYS:
        is_picked = (highlight and judge_label
                     and highlight.get((qid, agent, n)) == judge_label)
        sq = square(ratings.get((qid, agent, n)), picked=bool(is_picked))
        (parts_cc if agent == "claude-code" else parts_cx).append(sq)
    return "".join(parts_cc) + " " + "".join(parts_cx)


def truncate(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


# ---------- main report builder ----------

def extract_existing_comments(path: Path) -> str:
    """Pull the body of the `## Comments` section from a previously written report.md.
    Returns the raw markdown between `## Comments` and the next `## ` header,
    stripped of surrounding blank lines. Returns "" if not found or empty.
    """
    if not path.exists():
        return ""
    text = path.read_text()
    m = re.search(
        r"^##\s+Comments\s*$\n(.*?)(?=^##\s+|\Z)",
        text, re.DOTALL | re.MULTILINE,
    )
    if not m:
        return ""
    return m.group(1).strip()


def extract_difference_categories(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """
    Pull the hand-curated `Difference categories` cells out of a previous
    report.md → ({qid: value}, {normalized question text: value}).

    That column is written by hand, never generated, so it has to survive a
    regeneration. Questions are matched on their text first and their number
    second, so the values follow a question even if it is renumbered.
    """
    if not path.exists():
        return {}, {}
    by_qid, by_title = {}, {}
    col = None
    for line in path.read_text().splitlines():
        cells = _split_md_row(line)
        if not cells:
            continue
        if cells[0].strip().lower() == "q":
            names = [c.strip().lower() for c in cells]
            col = (names.index("difference categories")
                   if "difference categories" in names else None)
            continue
        if col is None or col >= len(cells):
            continue
        qid = cells[0].strip()
        if not re.match(r"^\d+(-[a-z])?$", qid):
            continue
        value = cells[col].strip()
        if value:
            by_qid[qid] = value
            by_title[_norm_question(cells[1])] = value
    return by_qid, by_title


def _norm_question(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*_`\\]+", "", text or "")).strip().lower()


def build_report(dataset: str, rater: str | None = None) -> str:
    import raters as R
    ddir = EVAL_DIR / dataset
    # Solution ratings now live per evaluator; the report is built from one of
    # them (the primary by default). eval_summary.md holds every evaluator.
    summary_path = R.summary_path(dataset, rater or R.primary_code())
    eval_path = ddir / "eval_summary.md"
    existing_comments = extract_existing_comments(ddir / "report.md")
    diff_by_qid, diff_by_title = extract_difference_categories(ddir / "report.md")

    rs_h, rs_titles, rs_solution = parse_rate_summary(summary_path)
    es_h, es_c, es_x, es_judge, es_best = parse_eval_summary(
        eval_path, rater=rater or R.primary_code())

    # One ratings column per evaluator, this report's own first. Ratings come
    # from the dossiers — the same source eval_summary.md is built from.
    who = rater or R.primary_code()
    codes = [who] + [c for c in R.rating_columns(dataset) if c != who]
    disk = R.collect_ratings(dataset, codes)
    per_code = {
        c: {(qid, agent, n): (cell.get(c) or "")
            for qid, per_trial in disk.items()
            for (agent, n), cell in per_trial.items()}
        for c in codes
    }
    # Fall back to the summary files if this evaluator has no dossier folder.
    human_ratings = per_code.get(who) or {**es_h, **rs_h}

    # Prefer titles from summary.md (richer); fall back to the dossiers.
    titles = {**R.collect_titles(dataset, codes), **rs_titles}

    # Question scope stays driven by the summary files, not by the dossiers: a
    # dossier may carry ratings for questions the workflow deliberately leaves
    # out of the roll-up (rate_blind.py skips "aligned with the neural data" for
    # scalar variables, which no judge asks about). The dossiers supply the
    # ratings for these questions, not the list of them.
    qids = sorted({q for (q, _, _) in {**es_h, **rs_h}} | set(rs_titles),
                  key=_qid_sort_key)

    # Name the evaluator this report is built from — with more than one of them,
    # "Human" no longer identifies whose ratings and notes these are.
    others = codes[1:]
    evaluator_line = (
        f"- Human evaluators: **{who}** (this report's comments and notes), "
        f"{', '.join(others)}" if others else f"- Human evaluator: **{who}**")

    lines = [
        f"# Evaluation Report — {dataset}",
        "",
        "## Summary",
        "",
        f"- Dataset: **{dataset}**",
        f"- Questions covered: {len(qids)}",
        f"- Trials per question: 6 (3 claude-code + 3 codex)",
        evaluator_line,
        f"- Judges: Claude, Codex",
        "",
        f"**Legend:**  {LEGEND_LINE}  ",
        f"A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed "
        f"more accurate than evaluator {who}.",
        "",
        "## Comments",
        "",
        *( [existing_comments, ""] if existing_comments else [] ),
        "## Per-question evaluations",
        "",
        "| Q | Question | " + " | ".join(codes)
        + " | Claude judge | Codex judge | Solution comment "
          "| LLM judge comment | Difference categories |",
        "|---" * (len(codes) + 6) + "|",
    ]

    placeholder_comments = {"_(no overall comment)_", "(no overall comment)",
                            "_(no comment)_", "(no comment)", "n/a", "N/A"}
    for qid in qids:
        title = (titles.get(qid) or "").replace("|", "\\|").replace("\n", " ")
        h_cells = [six_squares(per_code.get(c) or human_ratings, qid) for c in codes]
        c_cell = (six_squares(es_c, qid, highlight=es_best, judge_label="Claude judge")
                  if es_c else (EMPTY_MARK * 3 + " " + EMPTY_MARK * 3))
        x_cell = (six_squares(es_x, qid, highlight=es_best, judge_label="Codex judge")
                  if es_x else (EMPTY_MARK * 3 + " " + EMPTY_MARK * 3))
        sol = (rs_solution.get(qid) or "").strip()
        if sol in placeholder_comments:
            sol = ""
        sol = sol.replace("|", "\\|").replace("\n", " ")
        judge = (es_judge.get(qid) or "").strip()
        if judge in placeholder_comments:
            judge = ""
        judge = judge.replace("|", "\\|").replace("\n", " ")
        # Hand-curated column: match on question text, fall back to the number.
        diff = (diff_by_title.get(_norm_question(titles.get(qid, "")))
                or diff_by_qid.get(qid, ""))
        lines.append(
            f"| {qid} | {title} | " + " | ".join(h_cells)
            + f" | {c_cell} | {x_cell} | {sol} | {judge} | {diff} |"
        )

    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Generate evaluation report markdown.")
    ap.add_argument("dataset")
    ap.add_argument("--rater", help="Evaluator whose solution ratings/notes the "
                                    "report is built from (default: primary)")
    ap.add_argument("--out", help="Output path (default: <dataset>/report.md)")
    args = ap.parse_args()

    report = build_report(args.dataset, rater=args.rater)
    out_path = Path(args.out) if args.out else EVAL_DIR / args.dataset / "report.md"
    out_path.write_text(report)
    print(f"Wrote {out_path} ({len(report)} bytes)")


if __name__ == "__main__":
    main()
