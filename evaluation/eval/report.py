#!/usr/bin/env python3
"""
Generate a human-readable evaluation report (markdown) for one dataset.

Sources (all already produced by other tools):
  - evaluation/eval/<dataset>/summary.md       (rate.py output: Human ratings + per-Q overall comment about the SOLUTION)
  - evaluation/eval/<dataset>/eval_summary.md  (compare.py output: Human + Claude-judge + Codex-judge ratings + per-Q overall comment about the JUDGES)

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

def parse_eval_summary(path: Path) -> tuple[dict, dict, dict, dict, dict]:
    """
    Returns (human_ratings, claude_ratings, codex_ratings, judge_comments, best_picks).
      *_ratings:    {(qid, agent, n): rating}
      judge_comments: {qid: text}  (from `**Overall comment:**`)
      best_picks:   {(qid, agent, n): "Human" | "Claude judge" | "Codex judge" | "—"}
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
        for line in body.splitlines():
            cells = _split_md_row(line)
            if not cells or len(cells) != 6:
                continue
            trial, hv, cv, xv, bv, _why = cells
            m = re.match(r"^(claude-code|codex)\s*/\s*trial([1-3])$", trial)
            if not m:
                continue
            key = (qid, m.group(1), int(m.group(2)))
            h[key] = hv.strip().lower()
            c[key] = cv.strip().lower()
            x[key] = xv.strip().lower()
            best[key] = bv.strip()
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


def build_report(dataset: str) -> str:
    ddir = EVAL_DIR / dataset
    summary_path = ddir / "summary.md"
    eval_path = ddir / "eval_summary.md"
    existing_comments = extract_existing_comments(ddir / "report.md")

    rs_h, rs_titles, rs_solution = parse_rate_summary(summary_path)
    es_h, es_c, es_x, es_judge, es_best = parse_eval_summary(eval_path)

    # Prefer titles from summary.md (richer); fall back to eval_summary.md if missing.
    titles = dict(rs_titles)

    # Use summary.md ratings as the human source of truth (has notes); fall back to
    # eval_summary.md if a question wasn't in summary.md (shouldn't happen normally).
    human_ratings = {**es_h, **rs_h}

    # Question order — union of all qids seen, sorted canonically
    qids = sorted({q for (q, _, _) in human_ratings} | set(rs_titles), key=_qid_sort_key)

    lines = [
        f"# Evaluation Report — {dataset}",
        "",
        "## Summary",
        "",
        f"- Dataset: **{dataset}**",
        f"- Questions covered: {len(qids)}",
        f"- Trials per question: 6 (3 claude-code + 3 codex)",
        f"- Evaluators: Human, Claude judge, Codex judge",
        "",
        f"**Legend:**  {LEGEND_LINE}  ",
        "A square (e.g. 🟩 instead of 🟢) marks a cell where the LLM judge was deemed more accurate than the human.",
        "",
        "## Comments",
        "",
        *( [existing_comments, ""] if existing_comments else [] ),
        "## Per-question evaluations",
        "",
        "| Q | Question | Human | Claude judge | Codex judge | Solution comment | LLM judge comment |",
        "|---|---|---|---|---|---|---|",
    ]

    placeholder_comments = {"_(no overall comment)_", "(no overall comment)",
                            "_(no comment)_", "(no comment)", "n/a", "N/A"}
    for qid in qids:
        title = (titles.get(qid) or "").replace("|", "\\|").replace("\n", " ")
        h_cell = six_squares(human_ratings, qid)
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
        lines.append(
            f"| {qid} | {title} | {h_cell} | {c_cell} | {x_cell} | {sol} | {judge} |"
        )

    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Generate evaluation report markdown.")
    ap.add_argument("dataset")
    ap.add_argument("--out", help="Output path (default: <dataset>/report.md)")
    args = ap.parse_args()

    report = build_report(args.dataset)
    out_path = Path(args.out) if args.out else EVAL_DIR / args.dataset / "report.md"
    out_path.write_text(report)
    print(f"Wrote {out_path} ({len(report)} bytes)")


if __name__ == "__main__":
    main()
