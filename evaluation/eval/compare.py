#!/usr/bin/env python3
"""
Walk through human vs LLM-judge mismatches one at a time.

Sources per trial:
  - Human:       evaluation/eval/<dataset>/<agent>_trial<N>.md  (Rating + Note)
  - LLM judges:  evaluation/harbor-jobs/<dataset>/<agent_folder>/*_trial<N>/
                   verifier/judge/{claude,codex}/{llm_judge_eval.json, DECISIONS.md}

Usage:
    python3 compare.py <dataset>                  # walk all trials, all questions
    python3 compare.py <dataset> --question 1-c   # walk one question across trials
"""

import argparse
import glob
import json
import re
import sys
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

_CONSOLE = Console()

REPO_ROOT = Path("/groups/zhang/home/zhangl5/Data-Format")
EVAL_DIR = REPO_ROOT / "evaluation" / "eval"
HARBOR_DIR = REPO_ROOT / "evaluation" / "harbor-jobs"

# On-disk agent folder name (some datasets use `claude/`, others `claude-code/`)
AGENT_FOLDER = {
    "allen2p":     "claude-code",
    "lee2025":     "claude",
    "majnik2025":  "claude",
    "sosa2024":    "claude",
    "hasnain2024": "claude",
    "map":         "claude",
    "mouseland":   "claude-code",
    "zhang2025":   "claude-code",
}

TRIAL_KEYS = [("claude-code", n) for n in (1, 2, 3)] + [("codex", n) for n in (1, 2, 3)]

PLACEHOLDER = "_(to be filled by evaluator)_"

NORM = lambda s: (s or "").strip().lower()

# Bucketed agreement (positive = agent did fine; negative = agent had issues)
POSITIVE = {"better", "match", "ok"}
NEGATIVE = {"concerning", "incorrect", "missing"}

RATING_EMOJI = {
    "better": "⭐",
    "match": "✅",
    "ok": "🟢",
    "concerning": "⚠️",
    "incorrect": "❌",
    "missing": "❓",
}


def emoji_rating(r: str | None) -> str:
    if not r:
        return "—"
    return f"{RATING_EMOJI.get(r, '·')} {r}"


# ---------- file discovery & parsing ----------

def find_trial_path(dataset: str, agent_label: str, n: int) -> Path | None:
    folder = AGENT_FOLDER.get(dataset, agent_label)
    if agent_label == "codex":
        folder = "codex"
    pattern = str(HARBOR_DIR / dataset / folder / f"*_trial{n}")
    matches = [m for m in glob.glob(pattern) if "_badtrial" not in m]
    return Path(sorted(matches)[-1]) if matches else None


def parse_human(path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """
    Returns (per_qid_meta, per_qid_full_body).
    per_qid_meta: {qid: {rating, note, title}}
    per_qid_full_body: {qid: markdown body}
    """
    if not path.exists():
        return {}, {}
    text = path.read_text()
    pat = re.compile(
        r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+\d+(?:-[a-z])?\.|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    meta, body = {}, {}
    for m in pat.finditer(text):
        qid = m.group(1)
        title = m.group(2).strip()
        block = m.group(0)
        full = re.sub(r"\n---\s*$", "", m.group(3).strip()).strip()
        rm = re.search(r"^\*\*Rating:\*\*\s*(.+?)\s*$", block, re.MULTILINE)
        nm = re.search(r"^\*\*Note:\*\*\s*(.+?)\s*$", block, re.MULTILINE)
        rating = rm.group(1).strip() if rm else None
        if rating in (None, "", PLACEHOLDER):
            rating = None
        note = nm.group(1).strip() if nm else None
        if note in (None, "", "_(no note)_", PLACEHOLDER):
            note = None
        meta[qid] = {"rating": rating, "note": note, "title": title}
        body[qid] = full
    return meta, body


def parse_llm_decisions(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text()
    pat = re.compile(
        r"^##\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+\d+(?:-[a-z])?\.|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    return {m.group(1): m.group(3).strip() for m in pat.finditer(text)}


def load_judge(trial_path: Path | None, judge: str) -> dict[str, dict]:
    if not trial_path:
        return {}
    p = trial_path / "verifier" / "judge" / judge / "llm_judge_eval.json"
    if not p.exists():
        return {}
    try:
        with p.open() as f:
            d = json.load(f)
    except Exception as e:
        print(f"WARN: failed to load {p}: {e}", file=sys.stderr)
        return {}
    out = {}
    for qid, v in d.items():
        if isinstance(v, dict):
            out[qid] = {
                "decision": NORM(v.get("decision_correctness")),
                "code": NORM(v.get("code_correctness")),
                "decision_just": v.get("decision_correctness_justification", ""),
                "code_just": v.get("code_correctness_justification", ""),
                "title": v.get("question", ""),
            }
    return out


# ---------- qid mapping (human ↔ LLM-judge fingerprints) ----------

_BUILTIN_ALIASES = {
    "image_name": "image_identity", "image_identity": "image_identity",
    "trial_outcome": "outcome", "outcome": "outcome",
    "behavioral_context": "context", "context": "context",
    "prior_probability": "prior", "prior_probability_left": "prior",
    "prior_probability_of_left": "prior", "prior": "prior",
    "tongue_y_position": "tongue_y", "tongue_y_bin": "tongue_y", "tongue_y": "tongue_y",
    "visual_stimulus_category": "visual_stimulus", "visual_stimulus": "visual_stimulus",
    "wheel_speed_bin": "wheel_speed",
    "whisker_motion_energy_bin": "whisker_motion_energy",
}

_dataset_alias_cache: dict[str, dict] = {}


def load_dataset_aliases(dataset: str) -> dict[str, str]:
    if dataset in _dataset_alias_cache:
        return _dataset_alias_cache[dataset]
    p = EVAL_DIR / dataset / "qid_aliases.json"
    aliases: dict[str, str] = {}
    if p.exists():
        try:
            aliases = {k.lower(): v.lower() for k, v in json.loads(p.read_text()).items()}
        except Exception as e:
            print(f"WARN: bad qid_aliases.json for {dataset}: {e}", file=sys.stderr)
    _dataset_alias_cache[dataset] = aliases
    return aliases


def norm_var(name: str, dataset: str | None = None) -> str:
    s = name.lower()
    for suf in ("_bin", " bin", "_binned", " binned", "_category", "_categories",
                "_velocity_bin", " of left"):
        if s.endswith(suf):
            s = s[: -len(suf)]
    s = re.sub(r"[\s_\-]+", "_", s).strip("_")
    if dataset:
        s = load_dataset_aliases(dataset).get(s, s)
    return _BUILTIN_ALIASES.get(s, s)


def fingerprint(qid: str, title: str, dataset: str | None = None) -> tuple:
    t = title.strip()
    tl = t.lower()
    head = qid.split("-")[0]
    sub = qid.split("-")[1] if "-" in qid else ""

    if head == "1":
        return ("data", sub)

    if head == "2":
        if "derived from" in tl or "variables in the raw data" in tl:
            return ("neural", "source")
        if "filtered" in tl or "quality control" in tl:
            return ("neural", "qc")
        if "aligned" in tl or "alignment" in tl:
            return ("neural", "align")
        if "binned" in tl or "resampled" in tl or "temporal resolution" in tl or "time bin" in tl:
            return ("neural", "temporal")
        if "processed" in tl or "processing" in tl:
            return ("neural", "processing")
        return ("neural", sub or "?")

    if "minor mistakes" in tl or "missing data" in tl:
        return ("missing",)
    if any(k in tl for k in ("time-consuming", "vectorized", "repeat multiple",
                             "unnecessary processing", "memory usage")):
        if "time-consuming" in tl or "most time" in tl: role = "time"
        elif "vectorized" in tl: role = "vectorize"
        elif "repeat" in tl: role = "repeat"
        elif "unnecessary" in tl: role = "unnecessary"
        elif "memory" in tl: role = "memory"
        else: role = sub or "?"
        return ("perf", role)

    var_name = None
    for pat in (
        r"\*([^*]+?)\*",
        r"`(?:output|input)`\s+([A-Z][A-Za-z _\-]+?)\s+(?:derived from|thresholded|aligned|is involved|with the neural)",
        r"`(?:output|input)`\s+([A-Z][A-Za-z _\-]+?)\?",
        r"(?:output|input)\s+([A-Z][A-Za-z _\-]+?)\s+(?:derived from|thresholded|aligned|is involved|with the neural)",
    ):
        m = re.search(pat, t)
        if m:
            var_name = m.group(1).strip()
            break
    if not var_name:
        return ("unknown", qid)
    var_name = norm_var(var_name, dataset=dataset)
    io = "input" if "input" in tl[:60] else "output"
    if "derived from" in tl: role = "source"
    elif "processing is involved" in tl or "computing" in tl: role = "processing"
    elif "threshold" in tl or "discretiz" in tl or "binned" in tl: role = "threshold"
    elif "aligned" in tl or "alignment" in tl: role = "align"
    else: role = sub or "?"
    return ("var", io, var_name, role)


def build_qid_map(human: dict, llm: dict, dataset: str | None = None) -> dict[str, str | None]:
    llm_by_fp = {}
    for qid, v in llm.items():
        fp = fingerprint(qid, v.get("title", ""), dataset=dataset)
        llm_by_fp.setdefault(fp, qid)
    return {qid: llm_by_fp.get(fingerprint(qid, v.get("title", ""), dataset=dataset))
            for qid, v in human.items()}


# ---------- summary file I/O ----------
#
# eval_summary.md is grouped by question (mirrors rate.py's summary.md):
#
#   ## Q <qid>. <title>
#
#   | Agent / trial | Human | Claude judge | Codex judge | Best | Why |
#   |---|---|---|---|---|---|
#   | claude-code / trial1 | ok | ok | incorrect | Human | human was right |
#   ...

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
    # Strip only the leading empty cell (from the line's leading `|`).
    # The closing `|` does not produce a phantom trailing cell — but a real
    # empty cell (e.g. blank "Why" column) does, and we must keep it.
    if cells and cells[0] == "":
        cells = cells[1:]
    return cells


def _try_parse_row(line: str) -> tuple[str, int, dict] | None:
    cells = _split_md_row(line)
    if not cells or len(cells) != 6:
        return None
    trial_label, h, c, x, best, why = cells
    m = re.match(r"^(claude-code|codex)\s*/\s*trial([1-3])$", trial_label)
    if not m:
        return None
    return m.group(1), int(m.group(2)), {
        "human": h, "claude": c, "codex": x, "best": best, "why": why,
    }


def parse_summary(path: Path) -> tuple[dict[tuple[str, str, int], dict], dict[str, str]]:
    """Parse eval_summary.md → (rows, overall_comments)."""
    if not path.exists():
        return {}, {}
    text = path.read_text()
    sec_re = re.compile(
        r"^##\s+Q\s+(\d+(?:-[a-z])?)\.\s+(.+?)$(.*?)(?=^##\s+Q\s+|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    rows = {}
    overalls = {}
    for sec in sec_re.finditer(text):
        qid = sec.group(1)
        title = sec.group(2).strip()
        body = sec.group(3)
        for line in body.splitlines():
            parsed = _try_parse_row(line)
            if not parsed:
                continue
            agent, n, fields = parsed
            rows[(qid, agent, n)] = {**fields, "title": title}
        m = re.search(r"^\*\*Overall comment:\*\*\s*(.+)$", body, re.MULTILINE)
        if m:
            overalls[qid] = m.group(1).strip()
    return rows, overalls


def write_summary(path: Path, entries: dict[tuple[str, str, int], dict],
                  titles: dict[str, str], overalls: dict[str, str] | None = None):
    """Render the full eval_summary.md from `entries` + `overalls` (grouped by qid)."""
    overalls = overalls or {}
    # Safety: never wipe a populated file by writing empty entries+overalls.
    if not entries and not overalls and path.exists() and path.stat().st_size > 0:
        print(f"WARN: refusing to wipe non-empty {path} with empty content.",
              file=sys.stderr)
        return
    by_qid: dict[str, list[tuple[tuple[str, int], dict]]] = {}
    for (qid, agent, n), v in entries.items():
        by_qid.setdefault(qid, []).append(((agent, n), v))

    qids_sorted = sorted(set(by_qid) | set(overalls), key=_qid_sort_key)
    lines = [f"# Eval comparison — {path.parent.name}", ""]
    for qid in qids_sorted:
        title = (titles.get(qid)
                 or (by_qid[qid][0][1].get("title") if qid in by_qid else "")
                 or "")
        lines.append("---")
        lines.append("")
        lines.append(f"## Q {qid}. {title}")
        lines.append("")
        if qid in by_qid:
            lines.append("| Agent / trial | Human | Claude judge | Codex judge | Best | Why |")
            lines.append("|---|---|---|---|---|---|")
            for (agent, n), v in sorted(by_qid[qid], key=lambda x: TRIAL_KEYS.index(x[0])):
                row_cells = [
                    f"{agent} / trial{n}",
                    v.get("human") or "—",
                    v.get("claude") or "—",
                    v.get("codex") or "—",
                    v.get("best") or "—",
                    v.get("why") or "",
                ]
                row = "| " + " | ".join(c.replace("|", "\\|") for c in row_cells) + " |"
                lines.append(row)
            lines.append("")
        if qid in overalls and overalls[qid]:
            lines.append(f"**Overall comment:** {overalls[qid]}")
            lines.append("")
    path.write_text("\n".join(lines))


def prompt_best() -> str | None:
    raw = input("  Best [1=Human / 2=Claude / 3=Codex] (Enter to skip): ").strip().lower()
    if not raw:
        return None
    mapping = {"1": "Human", "h": "Human",
               "2": "Claude judge", "c": "Claude judge",
               "3": "Codex judge", "x": "Codex judge"}
    return mapping.get(raw, raw)


def prompt_best_justification() -> str | None:
    raw = input("  Justification (optional, Enter to skip): ").strip()
    return raw or None


def prompt_overall(qid: str) -> str | None:
    raw = input(f"  Overall comment for Q {qid} (optional, Enter to skip): ").strip()
    return raw or None


def render_qid_recap(qid: str, title: str,
                     entries: dict[tuple[str, str, int], dict]):
    """Display a small recap table for one qid across all trials present."""
    from rich.table import Table
    rows = [(k, v) for k, v in entries.items() if k[0] == qid]
    if not rows:
        return
    tbl = Table(title=f"Q {qid}. {title}", title_style="bold cyan", border_style="cyan")
    tbl.add_column("Agent / trial", style="bold")
    tbl.add_column("Human")
    tbl.add_column("Claude")
    tbl.add_column("Codex")
    tbl.add_column("Best")
    tbl.add_column("Why")

    color_map = {"better": "green", "match": "cyan", "ok": "white",
                 "concerning": "yellow", "incorrect": "red", "missing": "red"}
    def colorize(r):
        c = color_map.get(r, "white")
        return f"[{c}]{r or '—'}[/{c}]"

    rows.sort(key=lambda kv: TRIAL_KEYS.index((kv[0][1], kv[0][2])))
    for (q, agent, n), v in rows:
        tbl.add_row(f"{agent}/trial{n}",
                    colorize(v.get("human")),
                    colorize(v.get("claude")),
                    colorize(v.get("codex")),
                    v.get("best") or "—",
                    v.get("why") or "")
    _CONSOLE.print()
    _CONSOLE.print(tbl)


# ---------- walkthrough ----------

def _qid_sort_key(q: str):
    m = re.match(r"(\d+)", q)
    return (int(m.group(1)) if m else 999, q.split("-")[1] if "-" in q else "")


def _is_consistent(h: str | None, jc: str | None, jx: str | None) -> bool:
    """Consistent if every present LLM rating is in the same bucket as human."""
    if not h:
        return False
    for r in (jc, jx):
        if not r:
            continue
        if r == h:
            continue
        if (h in POSITIVE) and (r in POSITIVE):
            continue
        if (h in NEGATIVE) and (r in NEGATIVE):
            continue
        return False
    return True


def walkthrough(dataset: str, only_qid: str | None = None, overwrite: bool = False):
    bundles = []
    for agent, n in TRIAL_KEYS:
        human_path = EVAL_DIR / dataset / f"{agent}_trial{n}.md"
        trial_path = find_trial_path(dataset, agent, n)
        meta, body = parse_human(human_path)
        jc = load_judge(trial_path, "claude")
        jx = load_judge(trial_path, "codex")
        mc = build_qid_map(meta, jc, dataset=dataset)
        mx = build_qid_map(meta, jx, dataset=dataset)
        jc_dec = parse_llm_decisions(trial_path / "verifier/judge/claude/DECISIONS.md") if trial_path else {}
        jx_dec = parse_llm_decisions(trial_path / "verifier/judge/codex/DECISIONS.md") if trial_path else {}
        bundles.append((agent, n, meta, body, jc, jx, mc, mx, jc_dec, jx_dec))

    qids_seen = []
    for _, _, meta, *_ in bundles:
        for q in sorted(meta.keys(), key=_qid_sort_key):
            if q not in qids_seen:
                qids_seen.append(q)

    if only_qid:
        if only_qid not in qids_seen:
            sys.exit(f"Q {only_qid} not found across human files for {dataset}")
        qids_seen = [only_qid]

    summary_path = EVAL_DIR / dataset / "eval_summary.md"
    if overwrite:
        entries, overalls = {}, {}
    else:
        entries, overalls = parse_summary(summary_path)
        if summary_path.exists():
            _CONSOLE.print(
                f"[dim]Loaded {len(entries)} entries and {len(overalls)} overall comments "
                f"from {summary_path.name}[/dim]"
            )
    already = set(entries.keys())
    titles = {qid: entries[(qid, a, n)]["title"]
              for (qid, a, n) in entries
              if entries[(qid, a, n)].get("title")}

    seen_inconsistent = 0
    seen_consistent = 0
    aborted = False
    for qid in qids_seen:
        if aborted:
            break
        title = next((b[2][qid]["title"] for b in bundles if b[2].get(qid)), qid)
        for agent, n, meta, body, jc, jx, mc, mx, jc_dec, jx_dec in bundles:
            sec = meta.get(qid)
            if not sec or not sec.get("rating"):
                continue  # skip unrated entries entirely
            h_rating = sec["rating"]
            h_note = sec.get("note")

            jc_qid = mc.get(qid)
            jx_qid = mx.get(qid)
            jc_rating = jc.get(jc_qid, {}).get("decision") if jc_qid else None
            jx_rating = jx.get(jx_qid, {}).get("decision") if jx_qid else None
            jc_just = jc.get(jc_qid, {}).get("decision_just", "") if jc_qid else ""
            jx_just = jx.get(jx_qid, {}).get("decision_just", "") if jx_qid else ""
            jc_dec_md = jc_dec.get(jc_qid, "") if jc_qid else ""
            jx_dec_md = jx_dec.get(jx_qid, "") if jx_qid else ""
            jc_code = jc.get(jc_qid, {}).get("code") if jc_qid else None
            jx_code = jx.get(jx_qid, {}).get("code") if jx_qid else None

            consistent = _is_consistent(h_rating, jc_rating, jx_rating)
            key = (qid, agent, n)
            titles[qid] = title

            # CONSISTENT: silently record and move on
            if consistent:
                if key not in already:
                    entries[key] = {
                        "human": h_rating or "—",
                        "claude": jc_rating or "—",
                        "codex": jx_rating or "—",
                        "best": "—",
                        "why": "",
                        "title": title,
                    }
                    write_summary(summary_path, entries, titles)
                seen_consistent += 1
                continue

            # INCONSISTENT: skip if already recorded (resume), unless overwrite
            if key in already:
                seen_inconsistent += 1
                continue

            seen_inconsistent += 1

            # Display all three panels
            _CONSOLE.print()
            _CONSOLE.print(Rule(
                f"[bold cyan]{dataset} • {agent}/trial{n} • Q {qid} — {title}[/bold cyan]"
            ))

            human_panel = Panel(
                Markdown(body.get(qid, "_(no body found)_")),
                title=f"[bold yellow]HUMAN[/bold yellow]  ({emoji_rating(h_rating)})",
                border_style="yellow",
            )

            def judge_panel(label, color, dec_md, rating, code, dj, cj, jq):
                code_line = f"  · code: **`{code}`**" if code else ""
                body_md = (
                    (dec_md or "_(no DECISIONS section found)_")
                    + f"\n\n---\n\n**LLM rating:** **`{rating or '—'}`**" + code_line
                    + (f"\n\n**Justification:** {dj}" if dj else "")
                    + (f"\n\n**Code-correctness justification:** {cj}" if cj else "")
                )
                # Same-bucket as human → green; cross-bucket → red; missing → dim
                if rating is None:
                    border = "dim"
                elif rating == h_rating or (
                    (h_rating in POSITIVE) == (rating in POSITIVE)
                ):
                    border = "green"
                else:
                    border = "red"
                title_q = f" ↔ qid {jq}" if jq else ""
                return Panel(
                    Markdown(body_md),
                    title=f"[bold {color}]{label}[/bold {color}]  ({emoji_rating(rating)}){title_q}",
                    border_style=border,
                )

            claude_p = judge_panel("Claude judge", "blue",
                                   jc_dec_md, jc_rating, jc_code, jc_just,
                                   jc.get(jc_qid, {}).get("code_just", "") if jc_qid else "",
                                   jc_qid)
            codex_p = judge_panel("Codex judge", "magenta",
                                  jx_dec_md, jx_rating, jx_code, jx_just,
                                  jx.get(jx_qid, {}).get("code_just", "") if jx_qid else "",
                                  jx_qid)

            cols = [human_panel, claude_p, codex_p]
            term_w = _CONSOLE.size.width
            if len(cols) * 70 <= term_w:
                cw = (term_w - 2 * (len(cols) - 1)) // len(cols)
                for c in cols:
                    c.width = cw
                _CONSOLE.print(Columns(cols, padding=(0, 1), expand=False))
            else:
                for c in cols:
                    _CONSOLE.print(c)

            # Prompt user for best evaluation + justification
            try:
                best = prompt_best()
            except (EOFError, KeyboardInterrupt):
                aborted = True
                break
            if best is None:
                # User pressed Enter to skip — don't persist; will re-prompt next run.
                _CONSOLE.print("[dim]→ skipped (not written)[/dim]")
                continue
            try:
                best_just = prompt_best_justification()
            except (EOFError, KeyboardInterrupt):
                best_just = None

            entries[key] = {
                "human": h_rating or "—",
                "claude": jc_rating or "—",
                "codex": jx_rating or "—",
                "best": best,
                "why": best_just or "",
                "title": title,
            }
            write_summary(summary_path, entries, titles, overalls)
            _CONSOLE.print(f"[dim]→ written to {summary_path}[/dim]")

        # End of trial loop for this qid — show recap + prompt for overall comment
        if aborted:
            break
        # Only prompt if there's actually some data for this qid AND
        # either no overall comment exists yet OR --overwrite was requested
        has_data = any(k[0] == qid for k in entries)
        if has_data and (qid not in overalls or overwrite):
            render_qid_recap(qid, title, entries)
            try:
                overall = prompt_overall(qid)
            except (EOFError, KeyboardInterrupt):
                aborted = True
                break
            if overall is not None:
                overalls[qid] = overall
                write_summary(summary_path, entries, titles, overalls)
                _CONSOLE.print(f"[dim]→ overall comment saved[/dim]")

    if aborted:
        _CONSOLE.print(f"\n[dim]Stopped. consistent={seen_consistent}  "
                       f"inconsistent reviewed={seen_inconsistent}[/dim]")
    else:
        _CONSOLE.print(f"\n[dim]Done. consistent={seen_consistent}  "
                       f"inconsistent={seen_inconsistent}  "
                       f"summary: {summary_path}[/dim]")


def main():
    ap = argparse.ArgumentParser(description="Walk through human vs LLM-judge mismatches.")
    ap.add_argument("dataset")
    ap.add_argument("--question", help="Limit walkthrough to one question (e.g. 1-a)")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-prompt for entries already present in eval_summary.md")
    args = ap.parse_args()
    walkthrough(args.dataset, only_qid=args.question, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
