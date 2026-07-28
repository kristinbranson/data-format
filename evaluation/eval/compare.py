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

import raters as _R

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
    "map":         "claude",         # legacy harbor-jobs folder name (eval/ renamed to chen2024)
    "chen2024":    "claude",
    "mouseland":   "claude-code",    # legacy harbor-jobs folder name (eval/ renamed to zhong2025)
    "zhong2025":   "claude-code",
    "zhang2025":   "claude-code",
}

# Some datasets were renamed under `evaluation/eval/` for naming consistency,
# but their `evaluation/harbor-jobs/<...>/` folders still use the legacy name.
# Map the new (eval) name → the legacy (harbor-jobs) name so trial-path lookups
# keep working from either side.
HARBOR_DATASET_ALIAS = {
    "chen2024":  "map",
    "zhong2025": "mouseland",
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
    harbor_dataset = HARBOR_DATASET_ALIAS.get(dataset, dataset)
    pattern = str(HARBOR_DIR / harbor_dataset / folder / f"*_trial{n}")
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
        # Dossier formats without `output`/`input` prefix:
        # "final `lick_direction` data derived from" / "How is the `lick_direction` data processed"
        r"(?:final\s+)?`([a-z_][a-z0-9_]*)`\s+(?:data\s+)?(?:derived|processed|aligned|filtered|thresholded|is\b)",
        # "How is `lick_direction` derived from" / "How is `lick_direction` processed/discretized?"
        r"How is\s+`([a-z_][a-z0-9_]*)`",
        # Em-dash format: "lick_direction — derivation source"
        r"^([a-z_][a-z0-9_]*)\s+(?:—|--|-)",
    ):
        m = re.search(pat, t)
        if m:
            var_name = m.group(1).strip()
            break
    if not var_name:
        return ("unknown", qid)
    var_name = norm_var(var_name, dataset=dataset)
    io = "input" if "input" in tl[:60] else "output"
    if "derived from" in tl or "derivation" in tl: role = "source"
    elif "processing is involved" in tl or "computing" in tl or "processed" in tl or "processing" in tl: role = "processing"
    elif "aligned" in tl or "alignment" in tl: role = "align"
    elif "threshold" in tl or "discretiz" in tl or "binned" in tl: role = "threshold"
    elif "filtered" in tl or "quality control" in tl: role = "filtered"
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
# eval_summary.md is grouped by question (mirrors rate.py's summary.md) and
# carries one rating column per registered evaluator:
#
#   ## Q <qid>. <title>
#
#   | Agent / trial | LZ | KB | Claude judge | Codex judge | Best | Why |
#   |---|---|---|---|---|---|---|
#   | claude-code / trial1 | ok | concerning | ok | incorrect | LZ | ... |
#   ...
#
# Files written before multiple evaluators existed use a single `Human` column;
# it is read as the primary evaluator's ratings.

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


def _parse_header(line: str, primary: str) -> dict[str, int] | None:
    """Map a table header row → {field: column index}. None if not a header."""
    cells = _split_md_row(line)
    if not cells or not cells[0].lower().startswith("agent"):
        return None
    cols: dict[str, int] = {}
    for i, name in enumerate(cells):
        key = name.strip().lower()
        if key in ("claude judge", "claude"):
            cols["claude"] = i
        elif key in ("codex judge", "codex"):
            cols["codex"] = i
        elif key == "best":
            cols["best"] = i
        elif key == "why":
            cols["why"] = i
        elif key == "human":
            cols[f"rater:{primary}"] = i   # legacy single-evaluator file
        elif re.fullmatch(r"[A-Z]{2,4}", name.strip()):
            cols[f"rater:{name.strip()}"] = i
    return cols


def _try_parse_row(line: str, cols: dict[str, int]) -> tuple[str, int, dict] | None:
    cells = _split_md_row(line)
    if not cells:
        return None
    m = re.match(r"^(claude-code|codex)\s*/\s*trial([1-3])$", cells[0])
    if not m:
        return None
    get = lambda i: cells[i] if i is not None and i < len(cells) else ""
    ratings = {k.split(":", 1)[1]: get(i) for k, i in cols.items()
               if k.startswith("rater:")}
    return m.group(1), int(m.group(2)), {
        "ratings": ratings,
        "claude": get(cols.get("claude")),
        "codex": get(cols.get("codex")),
        "best": get(cols.get("best")),
        "why": get(cols.get("why")),
    }


def parse_summary(path: Path, primary: str | None = None
                  ) -> tuple[dict[tuple[str, str, int], dict], dict[str, str]]:
    """Parse eval_summary.md → (rows, overall_comments).

    Each row carries `ratings` ({evaluator code: rating}) plus the judge
    columns. `human` is kept as an alias for the primary evaluator's rating so
    existing callers keep working.
    """
    if not path.exists():
        return {}, {}
    primary = primary or _R.primary_code()
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
        cols: dict[str, int] = {}
        for line in body.splitlines():
            header = _parse_header(line, primary)
            if header:
                cols = header
                continue
            if not cols:
                continue
            parsed = _try_parse_row(line, cols)
            if not parsed:
                continue
            agent, n, fields = parsed
            rows[(qid, agent, n)] = {
                **fields,
                "human": fields["ratings"].get(primary),
                "title": title,
            }
        m = re.search(r"^\*\*Overall comment:\*\*\s*(.+)$", body, re.MULTILINE)
        if m:
            overalls[qid] = m.group(1).strip()
    return rows, overalls


def write_summary(path: Path, entries: dict[tuple[str, str, int], dict],
                  titles: dict[str, str], overalls: dict[str, str] | None = None):
    """Render the full eval_summary.md from `entries` + `overalls` (grouped by qid).

    Writes atomically via a sibling tempfile + os.replace so a crash mid-write
    cannot leave a truncated file.
    """
    import os
    overalls = overalls or {}
    # Safety: never wipe a populated file by writing empty entries+overalls.
    if not entries and not overalls and path.exists() and path.stat().st_size > 0:
        print(f"WARN: refusing to wipe non-empty {path} with empty content.",
              file=sys.stderr)
        return
    # One rating column per evaluator who has a folder for this dataset; their
    # ratings are read straight from their dossier copies at write time.
    dataset = path.parent.name
    codes = _R.rating_columns(dataset)
    disk_ratings = _R.collect_ratings(dataset, codes)
    # A qid is only refreshed from the dossiers if both sides still label it the
    # same question. Question numbering has drifted before (sosa2024 gained two
    # sub-questions after its summary was written), and refreshing across a
    # renumbering would pair one question's rating with another's judges.
    dossier_titles = _R.collect_titles(dataset, codes)
    stale = set()
    for qid, t in titles.items():
        d = dossier_titles.get(qid)
        if d and _R.normalize_title(d) != _R.normalize_title(t):
            stale.add(qid)
    if stale:
        print(f"WARN: {dataset}: question numbering differs from the dossiers for "
              f"Q {', '.join(sorted(stale))} — keeping the ratings already in "
              f"{path.name} for those questions.", file=sys.stderr)
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
            lines.append("| Agent / trial | " + " | ".join(codes)
                         + " | Claude judge | Codex judge | Best | Why |")
            lines.append("|---" * (len(codes) + 5) + "|")
            for (agent, n), v in sorted(by_qid[qid], key=lambda x: TRIAL_KEYS.index(x[0])):
                on_disk = ({} if qid in stale
                           else disk_ratings.get(qid, {}).get((agent, n), {}))
                rated = v.get("ratings") or {}

                def cell(c, qid=qid, on_disk=on_disk, rated=rated):
                    # The dossiers are authoritative: an un-rated question must
                    # clear rather than keep a stale value. The one exception is
                    # a renumbered question, where the dossiers cannot be joined
                    # to this row at all and the file's own value stands.
                    if on_disk.get(c):
                        return on_disk[c]
                    return (rated.get(c) or "—") if qid in stale else "—"

                row_cells = [
                    f"{agent} / trial{n}",
                    *[cell(c) for c in codes],
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

    new_text = "\n".join(lines)

    # Sanity check: never let a write strictly shrink the count of qids
    # represented in the file. parse_summary→write_summary→ours should be
    # monotonic in coverage. If it isn't, something bad happened upstream.
    if path.exists():
        prev_entries, prev_overalls = parse_summary(path)
        prev_qids = {q for (q, _, _) in prev_entries} | set(prev_overalls)
        new_qids = set(by_qid) | set(overalls)
        lost = prev_qids - new_qids
        if lost:
            print(f"WARN: refusing to write {path}: would drop qids {sorted(lost)}.",
                  file=sys.stderr)
            return

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_text)
    os.replace(tmp, path)


def prompt_best(rater: str = "Human") -> str | None:
    raw = input(f"  Best [1={rater} / 2=Claude / 3=Codex] (Enter to skip): ").strip().lower()
    if not raw:
        return None
    mapping = {"1": rater, "h": rater,
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
    """Consistent if Claude judge is in the same bucket as human, OR Claude has
    no rating. Also flagged as inconsistent if Claude specifically rated "better"
    while human did not. Codex judge is ignored (deemed unreliable)."""
    if not h:
        return False
    if not jc:
        return True
    if jc == h:
        return True
    # Cross-bucket disagreement → inconsistent
    if (h in POSITIVE) != (jc in POSITIVE):
        return False
    # Claude said "better" while human did not → flag for review
    if jc == "better" and h != "better":
        return False
    return True


def walkthrough(dataset: str, only_qid: str | None = None, overwrite: bool = False,
                rater: "_R.Rater | None" = None):
    rater = rater or _R.resolve_rater()
    _CONSOLE.print(f"[bold]Evaluator:[/bold] {rater.label}")
    rater_files = _R.sync_rater_dir(dataset, rater.code)
    bundles = []
    for agent, n in TRIAL_KEYS:
        human_path = rater_files[(agent, n)]
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
    # Always load existing file as a starting point — we never wipe untouched qids.
    entries, overalls = parse_summary(summary_path)
    if summary_path.exists():
        _CONSOLE.print(
            f"[dim]Loaded {len(entries)} entries and {len(overalls)} overall comments "
            f"from {summary_path.name}[/dim]"
        )
    # qid-level resume: any qid already present in eval_summary.md is "done"
    # and is skipped, unless --overwrite was passed (then re-walk it; old data
    # for that qid stays in `entries` until the new walk completes successfully,
    # at which point it is replaced atomically).
    done_qids = {q for (q, _, _) in entries.keys()}
    titles = {qid: entries[(qid, a, n)]["title"]
              for (qid, a, n) in entries
              if entries[(qid, a, n)].get("title")}

    seen_inconsistent = 0
    seen_consistent = 0
    aborted = False
    for qid in qids_seen:
        if aborted:
            break
        if qid in done_qids and not overwrite:
            continue
        title = next((b[2][qid]["title"] for b in bundles if b[2].get(qid)), qid)
        # Buffer per-qid: only flush to disk after the whole qid completes.
        qid_entries: dict[tuple[str, str, int], dict] = {}
        qid_incomplete = False  # any rated trial the user explicitly skipped
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

            # CONSISTENT: buffer and move on
            if consistent:
                qid_entries[key] = {
                    "human": h_rating or "—",
                    "ratings": {rater.code: h_rating or "—"},
                    "claude": jc_rating or "—",
                    "codex": jx_rating or "—",
                    "best": "—",
                    "why": "",
                    "title": title,
                }
                seen_consistent += 1
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
                best = prompt_best(rater.code)
            except (EOFError, KeyboardInterrupt):
                aborted = True
                break
            if best is None:
                # User pressed Enter to skip — mark the qid incomplete so the
                # whole qid is NOT flushed; the user will be re-prompted on the
                # next run from the start of this qid.
                qid_incomplete = True
                _CONSOLE.print("[dim]→ skipped (qid will not be flushed)[/dim]")
                continue
            try:
                best_just = prompt_best_justification()
            except (EOFError, KeyboardInterrupt):
                best_just = None

            qid_entries[key] = {
                "human": h_rating or "—",
                "ratings": {rater.code: h_rating or "—"},
                "claude": jc_rating or "—",
                "codex": jx_rating or "—",
                "best": best,
                "why": best_just or "",
                "title": title,
            }
            _CONSOLE.print(f"[dim]→ buffered (will flush when Q {qid} completes)[/dim]")

        # End of trial loop for this qid — show recap + prompt for overall comment
        if aborted:
            # Don't flush a partial qid; user can re-run to redo it cleanly.
            break
        if qid_incomplete:
            _CONSOLE.print(
                f"[yellow]Q {qid} has skipped trials — NOT flushing. "
                f"Re-run to retry this qid from the start.[/yellow]"
            )
            continue
        if not qid_entries:
            continue
        # In --overwrite mode, prior entries for this qid are present in
        # `entries`; merge with new for the recap so all 6 trials show up
        # using the freshly-rated rows.
        render_qid_recap(qid, title, {**entries, **qid_entries})
        try:
            overall = prompt_overall(qid)
        except (EOFError, KeyboardInterrupt):
            aborted = True
            break
        # Atomic flush: replace any prior entries for this qid, then write.
        entries = {k: v for k, v in entries.items() if k[0] != qid}
        entries.update(qid_entries)
        if overall:
            overalls[qid] = overall
        # In --overwrite, blank input keeps the prior overall; user can edit
        # the .md file directly to clear it.
        write_summary(summary_path, entries, titles, overalls)
        _CONSOLE.print(f"[dim]→ Q {qid} flushed to {summary_path.name}[/dim]")

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
    ap.add_argument("--rater", help="Evaluator code whose ratings are compared against "
                                    "the judges (default: the primary evaluator)")
    ap.add_argument("--question", help="Limit walkthrough to one question (e.g. 1-a)")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-prompt for entries already present in eval_summary.md")
    args = ap.parse_args()
    walkthrough(args.dataset, only_qid=args.question, overwrite=args.overwrite,
                rater=_R.resolve_rater(args.rater or _R.primary_code()))


if __name__ == "__main__":
    main()
