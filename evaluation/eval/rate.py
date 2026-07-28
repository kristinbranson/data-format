#!/usr/bin/env python3
"""
Interactive Q-by-Q rating tool for the Data-Format evaluation.

Usage:
    python rate.py <dataset>                 # prompts for the evaluator code
    python rate.py <dataset> --rater LZ      # skip the prompt
    python rate.py <dataset> --overwrite     # re-rate everything

For each question in the reference DECISIONS.md, walks through all 6 trial
samples (3 claude-code + 3 codex) one at a time in random anonymized order,
shows the reference answer alongside, and prompts for rating + note. Writes
each answer back to the per-trial markdown file immediately.

Each evaluator works in their own folder, seeded from the master dossiers at
the dataset root (see raters.py)::

    eval/<dataset>/claude-code_trial1.md   master: content, ratings blank
    eval/<dataset>/<CODE>/claude-code_trial1.md   this evaluator's ratings
    eval/<dataset>/<CODE>/summary.md              this evaluator's summary

so evaluators never see each other's ratings and never write the same file.
Register new evaluator codes in raters.json.
"""

import argparse
import random
import re
import shutil
import sys
import textwrap
from pathlib import Path

import raters as R
from compare import build_qid_map

try:
    from rich.columns import Columns
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.rule import Rule
    _RICH = True
    _CONSOLE = Console()
except ImportError:
    _RICH = False
    _CONSOLE = None

REPO_ROOT = Path("/groups/zhang/home/zhangl5/Data-Format")
EVAL_DIR = R.EVAL_DIR
MANUAL_DIR = REPO_ROOT / "manual"

VALID_RATINGS = ["better", "match", "ok", "concerning", "incorrect", "missing"]
# Explicit shortcut map (dict-comp on first letter would clash on m=match/missing).
RATING_SHORTCUTS = {
    "b": "better",
    "m": "match",
    "o": "ok",
    "c": "concerning",
    "i": "incorrect",
    "x": "incorrect",
    "n": "missing",   # n for "none" / missing
}

PLACEHOLDER_RATING = "_(to be filled by evaluator)_"
PLACEHOLDER_NOTE = "_(to be filled by evaluator)_"

TRIAL_ORDER = [
    ("claude-code", 1), ("claude-code", 2), ("claude-code", 3),
    ("codex", 1), ("codex", 2), ("codex", 3),
]


# ---------- parsing ----------

def parse_reference(dataset: str) -> dict:
    """Parse manual/<dataset>/DECISIONS.md into {qid: full_section_text}."""
    path = MANUAL_DIR / dataset / "DECISIONS.md"
    if not path.exists():
        sys.exit(f"Reference not found: {path}")
    text = path.read_text()
    sections = {}
    # Headings look like: ## 1-a. How are ...
    pattern = re.compile(r"^##\s+(\d+(?:-[a-z])?)\.\s+(.+?)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        qid = m.group(1)
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[qid] = {"title": title, "body": body}
    return sections


def parse_trial_file(path: Path) -> dict:
    """Parse a per-trial md into {qid: {raw_section, rating, note, span}}."""
    text = path.read_text()
    sections = {}
    # Per-trial headings look like: ## Q 1-a. How are ...
    pattern = re.compile(r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        qid = m.group(1)
        start = m.start()
        # End at the next `---\n` line at column 0 after the section
        # Find the trailing `---` that closes this section.
        section_start = m.end()
        next_heading = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # Look for the last `---` before next heading
        block = text[section_start:next_heading]
        # The section ends at a standalone "---" line
        end_match = re.search(r"\n---\s*\n", block)
        if end_match:
            body = block[:end_match.start()]
            full_end = section_start + end_match.start()
        else:
            body = block.rstrip()
            full_end = next_heading

        rating_match = re.search(r"^\*\*Rating:\*\*\s*(.+?)\s*$", body, re.MULTILINE)
        note_match = re.search(r"^\*\*Note:\*\*\s*(.+?)\s*$", body, re.MULTILINE)
        sections[qid] = {
            "title": m.group(2).strip(),
            "body": body,
            "rating": rating_match.group(1).strip() if rating_match else None,
            "note": note_match.group(1).strip() if note_match else None,
        }
    return sections


def write_rating(path: Path, qid: str, rating: str, note: str):
    """Replace Rating + Note lines for a specific qid in a per-trial file."""
    text = path.read_text()
    # Find the section for this qid
    pattern = re.compile(
        rf"(##\s+Q\s+{re.escape(qid)}\..*?)(\n---\s*\n|\Z)",
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        raise RuntimeError(f"Could not find Q {qid} section in {path}")
    section = m.group(1)
    # Replace Rating line
    section = re.sub(
        r"^\*\*Rating:\*\*.*$",
        f"**Rating:** {rating}",
        section,
        count=1,
        flags=re.MULTILINE,
    )
    # Replace Note line
    section = re.sub(
        r"^\*\*Note:\*\*.*$",
        f"**Note:** {note}",
        section,
        count=1,
        flags=re.MULTILINE,
    )
    new_text = text[:m.start(1)] + section + text[m.end(1):]
    path.write_text(new_text)


# ---------- display ----------

def hr(char: str = "─", color: str = "") -> str:
    width = shutil.get_terminal_size((80, 20)).columns
    return color + (char * width) + ("\033[0m" if color else "")


def header(label: str, color: str = "\033[1;36m") -> str:
    width = shutil.get_terminal_size((80, 20)).columns
    pad = max(0, (width - len(label) - 4) // 2)
    return f"{color}{'═' * pad}  {label}  {'═' * pad}\033[0m"


def strip_eval_lines(body: str) -> str:
    """Drop the Rating/Note lines so the displayed sample is content only."""
    out = [ln for ln in body.splitlines()
           if not re.match(r"^\*\*(Rating|Note):\*\*", ln)]
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out)


def show_pair(qid: str, qtitle: str, ref_section: str, sample_label: str,
              sample_section: str, sample_idx: int, sample_total: int):
    sample_section = strip_eval_lines(sample_section)
    if _RICH:
        term_width = shutil.get_terminal_size((120, 40)).columns
        col_width = (term_width - 4) // 2  # 4 = inter-panel padding margin
        ref_panel = Panel(
            Markdown(ref_section.strip()),
            title="[bold yellow]REFERENCE (manual)[/bold yellow]",
            border_style="yellow",
            width=col_width,
        )
        sample_panel = Panel(
            Markdown(sample_section.strip()),
            title=f"[bold green]SAMPLE {sample_label}  ({sample_idx}/{sample_total})[/bold green]",
            border_style="green",
            width=col_width,
        )
        _CONSOLE.print()
        _CONSOLE.print(Rule(f"[bold cyan]Q {qid}.  {qtitle}[/bold cyan]"))
        _CONSOLE.print(Columns([ref_panel, sample_panel], expand=False, padding=(0, 1)))
    else:
        print()
        print(header(f"Q {qid}.  {qtitle}"))
        print()
        print(header("REFERENCE (manual)", "\033[1;33m"))
        print(ref_section.strip())
        print()
        print(header(f"SAMPLE {sample_label}  ({sample_idx}/{sample_total})", "\033[1;32m"))
        print(sample_section.strip())
        print()
        print(hr())


def prompt_rating() -> str:
    while True:
        choices = " | ".join(VALID_RATINGS)
        try:
            raw = input(f"  Rating [{choices}] (shortcut b/m/o/c/i/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            sys.exit("\nStopped — everything rated so far is already saved.")
        if raw in VALID_RATINGS:
            return raw
        if raw in RATING_SHORTCUTS:
            return RATING_SHORTCUTS[raw]
        if raw == "":
            print("  (please enter a rating)")
            continue
        print(f"  Invalid: '{raw}'. Try again.")


def prompt_note() -> str:
    try:
        note = input("  Note (free text, blank ok): ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nStopped before the note was saved — the rating above was not written.")
    return note if note else "_(no note)_"


def prompt_overall_comment() -> str:
    if _RICH:
        _CONSOLE.print("[bold magenta]Overall comment for this question[/bold magenta] (free text, blank ok):")
    else:
        print("Overall comment for this question (free text, blank ok):")
    try:
        raw = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nStopped — per-trial ratings are saved; this question's summary is not.")
    return raw if raw else "_(no overall comment)_"


def write_summary(summary_path: Path, qid: str, qtitle: str,
                  results: list, overall: str, dataset: str = "", rater: str = ""):
    """
    results: list of dicts {agent, trial, rating, note}, in canonical order.
    Writes/replaces a section for this qid in <dataset>/<CODE>/summary.md.
    """
    block_lines = [f"## Q {qid}. {qtitle}", ""]
    block_lines.append("| Agent / trial | Rating | Note |")
    block_lines.append("|---|---|---|")
    for r in results:
        note_cell = (r["note"] or "").replace("|", "\\|").replace("\n", " ")
        block_lines.append(f"| {r['agent']} / trial{r['trial']} | {r['rating']} | {note_cell} |")
    block_lines.append("")
    overall_cell = overall.replace("\n", " ")
    block_lines.append(f"**Overall comment:** {overall_cell}")
    block_lines.append("")
    block_lines.append("---")
    block = "\n".join(block_lines) + "\n"

    if not summary_path.exists():
        dataset = dataset or summary_path.parent.parent.name
        who = f" · evaluator {rater}" if rater else ""
        header = f"# Evaluation summary — {dataset}{who}\n\n---\n\n"
        summary_path.write_text(header + block)
        return

    text = summary_path.read_text()
    # Replace existing section with same qid if present
    pattern = re.compile(
        rf"^##\s+Q\s+{re.escape(qid)}\..*?(?=^##\s+Q\s+\d+(?:-[a-z])?\.|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    if pattern.search(text):
        new_text = pattern.sub(block + "\n", text, count=1)
    else:
        # Append at end (after a blank line)
        if not text.endswith("\n"):
            text += "\n"
        new_text = text + block
    summary_path.write_text(new_text)


# ---------- reference ↔ dossier question mapping ----------

def _report_mapping(dataset: str, ref: dict, trial_sections: dict, qmaps: dict):
    """Print how reference questions line up with the dossier sections, and
    refuse to continue if any reference question cannot be located."""
    renumbered, unmapped = [], []
    for qid in ref:
        targets = {qmaps[key].get(qid) for key in trial_sections}
        if None in targets:
            unmapped.append(qid)
            targets.discard(None)
        for t in targets:
            if t != qid:
                renumbered.append((qid, t))
                break

    if renumbered:
        print(f"  Note: {len(renumbered)} question(s) are numbered differently in "
              f"the dossiers; pairing them by content:")
        for qid, t in renumbered:
            print(f"    reference {qid} → dossier {t}   ({ref[qid]['title'][:60]})")
    if unmapped:
        print(f"\n  ERROR: {len(unmapped)} reference question(s) have no matching "
              f"dossier section: {', '.join(unmapped)}")
        print("  Rating them would compare unrelated questions. Fix the titles, or "
              f"add variable aliases in {EVAL_DIR / dataset / 'qid_aliases.json'}.")
        sys.exit(1)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Interactive Q-by-Q rating tool.")
    ap.add_argument("dataset", help="Dataset name (e.g. allen2p)")
    ap.add_argument("--rater", help="Evaluator code (e.g. LZ). Prompted for if omitted; "
                                    "$DATAFORMAT_RATER is used as a fallback.")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-rate all entries even if already filled.")
    ap.add_argument("--question", help="Only rate a specific question (e.g. 1-a)")
    args = ap.parse_args()

    dataset_dir = EVAL_DIR / args.dataset
    if not dataset_dir.exists():
        sys.exit(f"Eval folder not found: {dataset_dir}")

    # Who is rating? Seeds/updates <dataset>/<CODE>/ from the master dossiers.
    rater = R.resolve_rater(args.rater)
    print(f"Evaluator: {rater.label}")
    trial_files = R.sync_rater_dir(args.dataset, rater.code)
    rater_workdir = R.rater_dir(args.dataset, rater.code)
    print(f"Working in: {rater_workdir}")
    for key in TRIAL_ORDER:
        if key not in trial_files:
            sys.exit(f"Missing trial file: {rater_workdir / f'{key[0]}_trial{key[1]}.md'}")

    # Parse reference + per-trial content
    print(f"Loading reference for {args.dataset}...")
    ref = parse_reference(args.dataset)
    print(f"  Found {len(ref)} reference questions.")

    trial_sections = {key: parse_trial_file(path) for key, path in trial_files.items()}

    # Reference and dossier question numbers do NOT always agree: the reference
    # has been renumbered/renamed since some dossiers were generated (allen2p
    # reorders its output variables; sosa2024 gained two sub-questions). Pair
    # them by what the question is *about* — the same fingerprint compare.py
    # uses to line human ratings up with the judges — never by bare qid.
    qmaps = {key: build_qid_map(ref, sections, dataset=args.dataset)
             for key, sections in trial_sections.items()}
    _report_mapping(args.dataset, ref, trial_sections, qmaps)

    # Determine ordered question list (from reference)
    qids = list(ref.keys())
    if args.question:
        if args.question not in qids:
            sys.exit(f"Question {args.question} not in reference.")
        qids = [args.question]

    rng = random.Random()  # fresh shuffle each session
    summary_path = R.summary_path(args.dataset, rater.code)

    for qid in qids:
        ref_section = f"## {qid}. {ref[qid]['title']}\n\n{ref[qid]['body']}"

        # summary.md is keyed by the *dossier* numbering, not the reference's:
        # every evaluator's folder is a copy of the same masters, so keying by
        # the dossier keeps all evaluators' summaries directly comparable even
        # when the reference has been renumbered since (see _report_mapping).
        sqid = next((qmaps[key][qid] for key in TRIAL_ORDER
                     if qmaps[key].get(qid)), qid)
        stitle = next((trial_sections[key][sqid]["title"] for key in TRIAL_ORDER
                       if sqid in trial_sections[key]), ref[qid]["title"])

        # Determine which trials still need rating
        unrated = []
        for key in TRIAL_ORDER:
            sec = trial_sections[key].get(qmaps[key].get(qid))
            if sec is None:
                print(f"WARNING: trial {key} is missing question {qid}; skipping.")
                continue
            already = (
                sec["rating"] not in (None, "", PLACEHOLDER_RATING)
                and not args.overwrite
            )
            if not already:
                unrated.append(key)

        if not unrated:
            continue  # fully rated, skip silently

        # Shuffle to anonymous labels
        shuffled = unrated[:]
        rng.shuffle(shuffled)
        labels = [chr(ord("A") + i) for i in range(len(shuffled))]
        mapping = dict(zip(labels, shuffled))

        # Walk one sample at a time
        ratings_collected = {}
        for i, label in enumerate(labels):
            key = mapping[label]
            dqid = qmaps[key][qid]
            sec = trial_sections[key][dqid]
            sample_section = f"## Q {dqid}. {sec['title']}\n\n{sec['body']}"
            show_pair(qid, ref[qid]['title'], ref_section, label,
                      sample_section, i + 1, len(labels))
            rating = prompt_rating()
            note = prompt_note()
            ratings_collected[label] = (rating, note)
            # Write back immediately so we can resume
            write_rating(trial_files[key], dqid, rating, note)
            # Refresh in-memory copy for this trial
            trial_sections[key] = parse_trial_file(trial_files[key])

        # Reveal mapping + collect summary rows in canonical order
        summary_rows = []
        for key in TRIAL_ORDER:
            sec = trial_sections[key].get(qmaps[key].get(qid))
            if sec is None:
                continue
            summary_rows.append({
                "agent": key[0], "trial": key[1],
                "rating": sec["rating"], "note": sec["note"],
            })

        if _RICH:
            from rich.table import Table
            tbl = Table(title=f"Q {qid} mapping", title_style="bold magenta",
                        border_style="magenta")
            tbl.add_column("Sample", style="bold")
            tbl.add_column("Agent / trial")
            tbl.add_column("Rating")
            tbl.add_column("Note")
            for label in labels:
                agent, n = mapping[label]
                rating, note = ratings_collected[label]
                color = {
                    "better": "green", "match": "cyan", "ok": "white",
                    "concerning": "yellow", "incorrect": "red", "missing": "red",
                }.get(rating, "white")
                tbl.add_row(label, f"{agent} / trial{n}",
                            f"[{color}]{rating}[/{color}]", note)
            _CONSOLE.print()
            _CONSOLE.print(tbl)
            _CONSOLE.print()
        else:
            print()
            print(header(f"Q {qid} mapping", "\033[1;35m"))
            for label in labels:
                agent, n = mapping[label]
                rating, note = ratings_collected[label]
                print(f"  {label}  →  {agent} / trial{n}    [{rating}]  {note}")
            print(hr())
            print()

        # Prompt for overall comment and write summary block
        overall = prompt_overall_comment()
        write_summary(summary_path, sqid, stitle, summary_rows, overall,
                      dataset=args.dataset, rater=rater.code)
        if _RICH:
            _CONSOLE.print(f"[dim]→ summary updated: {summary_path}[/dim]\n")
        else:
            print(f"  → summary updated: {summary_path}\n")

    print(f"Done with {args.dataset}.")


if __name__ == "__main__":
    main()
