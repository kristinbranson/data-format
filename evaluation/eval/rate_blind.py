#!/usr/bin/env python3
"""
Rate trials WITHOUT a manual reference solution.

For datasets where we have no human-authored DECISIONS.md to compare against
(hasnain2024, map, mouseland, zhang2025), walk every (qid, trial) pair and
display three panels side-by-side:

  A (yellow)  — the per-trial solution summary (dossier body)
  B (blue)    — the Claude judge's DECISIONS section + rating
  C (magenta) — the Codex  judge's DECISIONS section + rating

Per-trial prompt:
  - Rating: incorrect | concerning | ok | match  (no "better" / "missing"
    since there's no reference to be "better than")
  → written immediately to the dossier file's **Rating:** line
    (evaluation/eval/<dataset>/<agent>_trial<N>.md)

Per-question prompts (asked once after all 6 trials of a qid):
  - Solution note  → written to summary.md      as **Overall comment:**
                     (matches rate.py's output format)
  - Judge note     → written to eval_summary.md as **Overall comment:**
                     (matches compare.py's output format; load_eval.py reads this)

Resume:
  - Trials whose Rating is no longer the placeholder are skipped.
  - A qid whose 6 trials are all rated AND whose summary.md / eval_summary.md
    sections already have an Overall comment is skipped entirely.
  - --overwrite re-prompts everything.

Usage:
    python3 rate_blind.py <dataset>
    python3 rate_blind.py <dataset> --question 1-c
    python3 rate_blind.py <dataset> --overwrite
"""

from __future__ import annotations

import argparse
import os
import random
import re
import sys
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from compare import (
    EVAL_DIR,
    TRIAL_KEYS,
    PLACEHOLDER,
    emoji_rating,
    find_trial_path,
    parse_human,
    parse_llm_decisions,
    load_judge,
    build_qid_map,
    _qid_sort_key,
)

_CONSOLE = Console()

VALID_RATINGS = ["match", "ok", "concerning", "incorrect"]
RATING_SHORTCUTS = {
    "i": "incorrect", "x": "incorrect",
    "c": "concerning",
    "o": "ok",
    "m": "match",
}

NO_NOTE = "_(no note)_"


# ---------- atomic file write ----------

def _atomic_write(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


# ---------- dossier writeback (per-trial Rating) ----------

def write_trial_rating(path: Path, qid: str, rating: str):
    """Replace the **Rating:** line for one qid in a dossier file. Also clears
    the Note placeholder to `_(no note)_` so the section reads cleanly."""
    text = path.read_text()
    sec_re = re.compile(
        rf"(##\s+Q\s+{re.escape(qid)}\.\s.*?)(?=^---\s*$|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = sec_re.search(text)
    if not m:
        raise RuntimeError(f"Could not find Q {qid} section in {path}")
    section = m.group(1)
    section, n_r = re.subn(
        r"^\*\*Rating:\*\*.*$", f"**Rating:** {rating}",
        section, count=1, flags=re.MULTILINE,
    )
    if n_r == 0:
        raise RuntimeError(f"No **Rating:** field in Q {qid} section of {path}")
    # Clear the Note placeholder; leave any non-placeholder Note alone.
    section = re.sub(
        rf"^\*\*Note:\*\*\s*{re.escape(PLACEHOLDER)}\s*$",
        f"**Note:** {NO_NOTE}",
        section, count=1, flags=re.MULTILINE,
    )
    new_text = text[:m.start(1)] + section + text[m.end(1):]
    _atomic_write(path, new_text)


# ---------- per-qid summary files ----------
#
# Two output files (matching the formats produced by rate.py / compare.py):
#
#   summary.md (Solution-side):
#     ## Q <qid>. <title>
#     | Agent / trial | Rating | Note |
#     | claude-code / trial1 | ok | _(no note)_ |
#     ...
#     **Overall comment:** <solution note>
#
#   eval_summary.md (Judge-side):
#     ## Q <qid>. <title>
#     | Agent / trial | Human | Claude judge | Codex judge | Best | Why |
#     | claude-code / trial1 | ok | match | match | — |  |
#     ...
#     **Overall comment:** <judge note>

_QID_HEADER_RE = re.compile(
    r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+|\Z)",
    re.DOTALL | re.MULTILINE,
)


def parse_overall_comments(path: Path) -> dict[str, str]:
    """Return {qid: overall_comment} from a summary-style file."""
    if not path.exists():
        return {}
    text = path.read_text()
    out = {}
    for m in _QID_HEADER_RE.finditer(text):
        qid = m.group(1)
        body = m.group(3)
        oc = re.search(r"^\*\*Overall comment:\*\*\s*(.+)$", body, re.MULTILINE)
        if oc:
            out[qid] = oc.group(1).strip()
    return out


def _insert_or_replace(path: Path, qid: str, header: str, block: str):
    """Insert/replace a qid block. `header` is the file header used for new files."""
    if not path.exists():
        _atomic_write(path, header + block)
        return
    text = path.read_text()
    existing = re.search(
        rf"(?ms)^##\s+Q\s+{re.escape(qid)}\..*?^---\s*$\n?",
        text,
    )
    if existing:
        new_text = text[: existing.start()] + block + text[existing.end():]
        _atomic_write(path, new_text)
        return
    # Append in qid-sorted order
    sections = list(_QID_HEADER_RE.finditer(text))
    insert_at = len(text)
    for sec in sections:
        if _qid_sort_key(sec.group(1)) > _qid_sort_key(qid):
            pre = text.rfind("---", 0, sec.start())
            insert_at = pre if pre != -1 else sec.start()
            break
    new_text = text[:insert_at] + block + text[insert_at:]
    _atomic_write(path, new_text)


def write_summary_qid(path: Path, qid: str, title: str,
                      rows: list[tuple[str, int, str | None, str | None, str | None]],
                      solution_note: str | None):
    """summary.md: per-trial Rating + Note table + Solution note as Overall comment."""
    lines = [f"## Q {qid}. {title}", ""]
    lines.append("| Agent / trial | Rating | Note |")
    lines.append("|---|---|---|")
    for agent, n, h, _jc, _jx in rows:
        lines.append(f"| {agent} / trial{n} | {h or '—'} | {NO_NOTE} |")
    lines.append("")
    lines.append(f"**Overall comment:** {solution_note or '_(no overall comment)_'}")
    lines.append("")
    lines.append("---")
    block = "\n".join(lines) + "\n"
    header = f"# Evaluation summary — {path.parent.name}\n\n---\n\n"
    _insert_or_replace(path, qid, header, block)


def write_eval_summary_qid(path: Path, qid: str, title: str,
                           rows: list[tuple[str, int, str | None, str | None, str | None]],
                           judge_note: str | None):
    """eval_summary.md: Human + Claude judge + Codex judge comparison + Judge note."""
    lines = [f"## Q {qid}. {title}", ""]
    lines.append("| Agent / trial | Human | Claude judge | Codex judge | Best | Why |")
    lines.append("|---|---|---|---|---|---|")
    for agent, n, h, jc, jx in rows:
        cells = [
            f"{agent} / trial{n}",
            h or "—", jc or "—", jx or "—",
            "—", "",
        ]
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    lines.append("")
    lines.append(f"**Overall comment:** {judge_note or '_(no overall comment)_'}")
    lines.append("")
    lines.append("---")
    block = "\n".join(lines) + "\n"
    header = f"# Eval comparison — {path.parent.name}\n\n---\n\n"
    _insert_or_replace(path, qid, header, block)


# ---------- prompts ----------

def prompt_rating() -> str | None:
    choices = " | ".join(VALID_RATINGS)
    while True:
        try:
            raw = input(f"  Rating [{choices}] (m/o/c/i, Enter to skip): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            raise
        if raw == "":
            return None
        if raw in VALID_RATINGS:
            return raw
        if raw in RATING_SHORTCUTS:
            return RATING_SHORTCUTS[raw]
        print(f"  Invalid: '{raw}'. Try again.")


def prompt_note(label: str, existing: str | None = None) -> str | None:
    suffix = f" [keep: {existing}]" if existing and existing != NO_NOTE else ""
    raw = input(f"  {label}{suffix} (Enter for blank/keep): ").strip()
    if raw == "":
        return existing  # keep existing (or None)
    return raw


# ---------- rendering ----------

def _strip_eval_lines(body: str) -> str:
    out = []
    for line in body.splitlines():
        if re.match(r"^\*\*(Rating|Note|Judge note):\*\*", line):
            continue
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out)


def _judge_panel(label, color, dec_md, rating, code, dj, cj, jq):
    body_md = (
        (dec_md or "_(no DECISIONS section found)_")
        + f"\n\n---\n\n**LLM rating:** **`{rating or '—'}`**"
        + (f"  ·  code: **`{code}`**" if code else "")
        + (f"\n\n**Justification:** {dj}" if dj else "")
        + (f"\n\n**Code-correctness justification:** {cj}" if cj else "")
    )
    title_q = f" ↔ qid {jq}" if jq else ""
    return Panel(
        Markdown(body_md),
        title=f"[bold {color}]{label}[/bold {color}]  ({emoji_rating(rating)}){title_q}",
        border_style=color,
    )


def _solution_panel(body: str):
    return Panel(
        Markdown(_strip_eval_lines(body) or "_(empty body)_"),
        title="[bold yellow]SOLUTION[/bold yellow]",
        border_style="yellow",
    )


def render_qid_recap(qid: str, title: str,
                     rows: list[tuple[str, int, str | None, str | None, str | None]]):
    tbl = Table(title=f"Q {qid}. {title}", title_style="bold cyan", border_style="cyan")
    tbl.add_column("Agent / trial", style="bold")
    tbl.add_column("Human")
    tbl.add_column("Claude")
    tbl.add_column("Codex")
    color_map = {"better": "green", "match": "cyan", "ok": "white",
                 "concerning": "yellow", "incorrect": "red", "missing": "red"}
    def colorize(r):
        c = color_map.get(r, "white")
        return f"[{c}]{r or '—'}[/{c}]"
    for agent, n, h, jc, jx in rows:
        tbl.add_row(f"{agent}/trial{n}", colorize(h), colorize(jc), colorize(jx))
    _CONSOLE.print()
    _CONSOLE.print(tbl)


# ---------- walkthrough ----------

def walkthrough(dataset: str, only_qid: str | None = None, overwrite: bool = False):
    bundles = []
    for agent, n in TRIAL_KEYS:
        human_path = EVAL_DIR / dataset / f"{agent}_trial{n}.md"
        if not human_path.exists():
            print(f"WARN: dossier missing: {human_path}", file=sys.stderr)
            continue
        trial_path = find_trial_path(dataset, agent, n)
        meta, body = parse_human(human_path)
        jc = load_judge(trial_path, "claude")
        jx = load_judge(trial_path, "codex")
        mc = build_qid_map(meta, jc, dataset=dataset)
        mx = build_qid_map(meta, jx, dataset=dataset)
        jc_dec = parse_llm_decisions(trial_path / "verifier/judge/claude/DECISIONS.md") if trial_path else {}
        jx_dec = parse_llm_decisions(trial_path / "verifier/judge/codex/DECISIONS.md") if trial_path else {}
        bundles.append((agent, n, human_path, meta, body, jc, jx, mc, mx, jc_dec, jx_dec))

    if not bundles:
        sys.exit(f"No dossier files found under {EVAL_DIR / dataset}")

    qids_seen = []
    for _, _, _, meta, *_ in bundles:
        for q in sorted(meta.keys(), key=_qid_sort_key):
            if q not in qids_seen:
                qids_seen.append(q)

    if only_qid:
        if only_qid not in qids_seen:
            sys.exit(f"Q {only_qid} not found across dossiers for {dataset}")
        qids_seen = [only_qid]

    summary_path = EVAL_DIR / dataset / "summary.md"          # solution-side
    eval_summary_path = EVAL_DIR / dataset / "eval_summary.md"  # judge-side
    sol_notes = parse_overall_comments(summary_path)
    judge_notes = parse_overall_comments(eval_summary_path)
    if summary_path.exists() or eval_summary_path.exists():
        _CONSOLE.print(
            f"[dim]Loaded {len(sol_notes)} solution notes from {summary_path.name}, "
            f"{len(judge_notes)} judge notes from {eval_summary_path.name}[/dim]"
        )

    rated_trials = 0
    rated_qids = 0
    skipped_qids = 0
    aborted = False

    for qid in qids_seen:
        if aborted:
            break
        title = next((b[3][qid]["title"] for b in bundles if b[3].get(qid)), qid)

        # Skip alignment qids for per-trial scalars: if fewer than half of the
        # 12 judge cells (6 trials × 2 judges) ask the alignment question for
        # this variable, treat it as a scalar (choice/outcome/prior/etc.) and
        # skip the qid entirely. True time-series vars consistently get 12/12.
        if "aligned" in title.lower() or "alignment" in title.lower():
            mapped = sum(
                int(b[7].get(qid) is not None) + int(b[8].get(qid) is not None)
                for b in bundles
            )
            if mapped < 6:
                _CONSOLE.print(
                    f"[dim]Q {qid}: only {mapped}/12 judges ask the alignment "
                    f"question for this variable — skipping[/dim]"
                )
                skipped_qids += 1
                continue

        # Quick fast-path: fully rated and notes already in summary → skip qid
        all_rated = all(
            (b[3].get(qid, {}).get("rating") not in (None, ""))
            for b in bundles
            if b[3].get(qid)
        )
        notes_done = qid in sol_notes and qid in judge_notes
        if all_rated and notes_done and not overwrite:
            skipped_qids += 1
            continue

        # ---- per-trial loop: rating only ----
        rows: list[tuple[str, int, str | None, str | None, str | None]] = []
        any_new = False
        # Shuffle the 6 trials per qid so the agent/order doesn't bias ratings.
        # Seeded by qid so a re-run sees the same order — useful when resuming.
        ordered = list(bundles)
        random.Random(qid).shuffle(ordered)
        for sample_idx, (agent, n, human_path, meta, body, jc, jx, mc, mx, jc_dec, jx_dec) in enumerate(ordered):
            sample_label = f"{agent} trial{n}"
            if aborted:
                break
            sec = meta.get(qid)
            if not sec:
                continue

            jc_qid = mc.get(qid)
            jx_qid = mx.get(qid)
            jc_rating = jc.get(jc_qid, {}).get("decision") if jc_qid else None
            jx_rating = jx.get(jx_qid, {}).get("decision") if jx_qid else None

            existing = sec.get("rating")
            if existing and not overwrite:
                rows.append((agent, n, existing, jc_rating, jx_rating))
                continue

            jc_just = jc.get(jc_qid, {}).get("decision_just", "") if jc_qid else ""
            jx_just = jx.get(jx_qid, {}).get("decision_just", "") if jx_qid else ""
            jc_code_just = jc.get(jc_qid, {}).get("code_just", "") if jc_qid else ""
            jx_code_just = jx.get(jx_qid, {}).get("code_just", "") if jx_qid else ""
            jc_dec_md = jc_dec.get(jc_qid, "") if jc_qid else ""
            jx_dec_md = jx_dec.get(jx_qid, "") if jx_qid else ""
            jc_code = jc.get(jc_qid, {}).get("code") if jc_qid else None
            jx_code = jx.get(jx_qid, {}).get("code") if jx_qid else None

            _CONSOLE.print()
            _CONSOLE.print(Rule(
                f"[bold cyan]{dataset} • {sample_label} ({sample_idx + 1}/6) • Q {qid} — {title}[/bold cyan]"
            ))

            cols = [
                _solution_panel(body.get(qid, "")),
                _judge_panel("Claude judge", "blue",
                             jc_dec_md, jc_rating, jc_code,
                             jc_just, jc_code_just, jc_qid),
                _judge_panel("Codex judge", "magenta",
                             jx_dec_md, jx_rating, jx_code,
                             jx_just, jx_code_just, jx_qid),
            ]
            term_w = _CONSOLE.size.width
            if len(cols) * 70 <= term_w:
                cw = (term_w - 2 * (len(cols) - 1)) // len(cols)
                for c in cols:
                    c.width = cw
                _CONSOLE.print(Columns(cols, padding=(0, 1), expand=False))
            else:
                for c in cols:
                    _CONSOLE.print(c)

            try:
                rating = prompt_rating()
            except (EOFError, KeyboardInterrupt):
                _CONSOLE.print("\n[dim]aborted[/dim]")
                aborted = True
                break

            if rating is None:
                _CONSOLE.print("[dim]→ skipped (no rating written)[/dim]")
                rows.append((agent, n, existing, jc_rating, jx_rating))
                continue

            try:
                write_trial_rating(human_path, qid, rating)
            except Exception as e:
                _CONSOLE.print(f"[red]ERROR writing {human_path}: {e}[/red]")
                aborted = True
                break

            rated_trials += 1
            any_new = True
            rows.append((agent, n, rating, jc_rating, jx_rating))
            _CONSOLE.print(f"[dim]→ saved {rating} ({sample_label})[/dim]")

        if aborted:
            break

        # If nothing was rated this round AND notes are already saved, no need
        # to re-prompt for notes.
        if not any_new and notes_done and not overwrite:
            continue
        # If no trial has a rating at all (all skipped, none pre-existing), don't
        # write a notes section yet — the qid stays untouched.
        if not any(r[2] for r in rows):
            _CONSOLE.print(f"[yellow]Q {qid}: no ratings — skipping notes prompt.[/yellow]")
            continue

        # Sort rows back to canonical order before rendering / writing.
        rows.sort(key=lambda r: TRIAL_KEYS.index((r[0], r[1])))

        # ---- per-qid notes ----
        render_qid_recap(qid, title, rows)
        try:
            sn = prompt_note("Solution note", sol_notes.get(qid))
            jn = prompt_note("Judge note", judge_notes.get(qid))
        except (EOFError, KeyboardInterrupt):
            _CONSOLE.print("\n[dim]aborted before saving notes[/dim]")
            aborted = True
            break

        try:
            write_summary_qid(summary_path, qid, title, rows, sn)
            write_eval_summary_qid(eval_summary_path, qid, title, rows, jn)
            if sn is not None:
                sol_notes[qid] = sn
            if jn is not None:
                judge_notes[qid] = jn
            rated_qids += 1
            _CONSOLE.print(
                f"[dim]→ Q {qid} flushed to {summary_path.name} + {eval_summary_path.name}[/dim]"
            )
        except Exception as e:
            _CONSOLE.print(f"[red]ERROR writing summary files: {e}[/red]")
            aborted = True
            break

    _CONSOLE.print(
        f"\n[dim]{'Stopped' if aborted else 'Done'}. "
        f"trials_rated={rated_trials}  qids_completed={rated_qids}  qids_skipped={skipped_qids}[/dim]"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("dataset")
    ap.add_argument("--question", help="Limit to one qid (e.g. 1-c)")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-prompt trials/qids that are already filled")
    args = ap.parse_args()
    walkthrough(args.dataset, only_qid=args.question, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
