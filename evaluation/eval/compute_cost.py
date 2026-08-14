#!/usr/bin/env python3
"""What the benchmark cost to run: agent and judge tokens and wall time.

    python3 eval/compute_cost.py                 # print the table, write the .tex
    python3 eval/compute_cost.py --no-write      # print only

Reads the run tree directly. The per-trial extraction -- result.json, the judge
logs, and the Codex duration that has to be inferred because its event stream
carries no timestamps -- is `harbor-scripts/summarize_trial_resources.py`, whose
`discover_trials` and `build_row` are called here in memory. Nothing is cached
to disk in between, so the table cannot go stale against the tree.

Quartiles rather than means: every one of these distributions is right-skewed,
and a mean would sit above the 60th percentile and describe no actual trial.

This is the cost of *producing and grading* the conversions. It is not the cost
of running one, which is `timing_results/supervised_summary.csv` -- that times
`convert_data.py` under `/usr/bin/time -v` and says nothing about agent or
judge consumption.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parents[1]

sys.path.insert(0, str(ROOT / "harbor-scripts"))
import summarize_trial_resources as trials  # noqa: E402

DEFAULT_JOB_DIR = EVAL_DIR.parent / "harbor-jobs"
DEFAULT_OUT = ROOT / "figures" / "resource_summary.tex"

QUANTILES = (25, 50, 75)

# Column headers. Anything not named here falls back to `P<q>`, so changing
# QUANTILES needs no edit. `Q1 / Median / Q3` reads better but only while these
# stay the quartiles.
QUANTILE_HEADER = {}

# Both judges are pooled into one distribution per row, which is why the judge
# rows report twice the trial count. They do not report the same fields: the
# Claude judge logs its own `duration_s`, while the Codex event stream has no
# timestamps at all, so its duration is inferred from log mtimes and named
# `_est`. Implausible inferences are dropped upstream rather than reported.
JUDGES = (("claude", "duration_s"), ("codex", "duration_s_est"))


def _metrics():
    """(label, unit, columns pooled into one distribution)."""
    out = [
        ("Agent tokens", "tokens", ["agent_total_tokens"]),
        ("Agent steps", "count", ["agent_steps"]),
        # The agent's own execution window, not `trial_total_s`: that also
        # carries container setup, and is missing for the three trials with no
        # result.json. `total_time_s` is this plus the four judge durations,
        # which holds exactly across the corpus.
        ("Agent time (min)", "minutes", ["agent_execution_s"]),
    ]
    for mode in ("sup", "unsup"):
        out += [
            (f"Judge {mode} tokens", "tokens",
             [f"judge_{j}_{mode}_total_tokens" for j, _d in JUDGES]),
            (f"Judge {mode} time (min)", "minutes",
             [f"judge_{j}_{mode}_{dur}" for j, dur in JUDGES]),
        ]
    return out + [
        ("Total tokens", "tokens", ["total_tokens"]),
        ("Total time (min)", "minutes", ["total_time_s"]),
    ]


METRICS = _metrics()

# Emphasized in the table: the per-trial totals the other rows decompose.
TOTAL_ROWS = {"Total tokens", "Total time (min)"}


def collect(job_dir=DEFAULT_JOB_DIR) -> list[dict]:
    """One dict per trial, straight from the run tree."""
    found = trials.discover_trials(str(job_dir))
    if not found:
        sys.exit(f"No trials found under {job_dir}")
    return [trials.build_row(t) for t in found]


def significant(value: float, digits: int = 2) -> float:
    """Round to `digits` significant figures. 13.6 -> 14, 118 -> 120, 2.68 -> 2.7."""
    if value is None or not np.isfinite(value):
        return float("nan")
    return float(f"{value:.{digits}g}")


def _cell(value: float, unit: str) -> str:
    if not np.isfinite(value):
        return "--"
    if unit == "tokens":
        # Sub-million counts read better in K; a bare 1102K does not.
        scale, suffix = (1e6, "M") if value >= 1e6 else (1e3, "K")
        return f"{significant(value / scale):g}{suffix}"
    return f"{significant(value):g}"


def summary(rows: list[dict], *, quantiles=QUANTILES) -> list[dict]:
    """Per metric: how many observations it rests on, and its quartiles.

    `n` counts observations, not trials, so a judge row reads twice an agent
    row. A trial missing a field contributes nothing rather than a zero.
    """
    out = []
    for label, unit, columns in METRICS:
        pooled = [float(r[c]) for c in columns for r in rows
                  if r.get(c) is not None and np.isfinite(float(r[c]))]
        if unit == "minutes":
            pooled = [v / 60 for v in pooled]
        out.append({"metric": label, "unit": unit, "n": len(pooled),
                    **{q: float(np.percentile(pooled, q)) for q in quantiles}})
    return out


def table(stats: list[dict], *, fmt: str = "markdown", quantiles=QUANTILES) -> str:
    """The resource table, at two significant figures throughout."""
    header = ["metric", "n trials"] + [QUANTILE_HEADER.get(q, f"P{q}")
                                       for q in quantiles]
    body = [[s["metric"], str(s["n"]), *[_cell(s[q], s["unit"]) for q in quantiles]]
            for s in stats]

    if fmt == "markdown":
        # Only the label is emphasized; bolding the numbers as well would make
        # the two summary rows read as more precise rather than as summaries.
        rows = [[f"**{c[0]}**" if s["metric"] in TOTAL_ROWS else c[0], *c[1:]]
                for c, s in zip(body, stats)]
        return "\n".join(
            ["| " + " | ".join(header) + " |", "|---|" + "---:|" * (len(header) - 1)]
            + ["| " + " | ".join(r) + " |" for r in rows])

    def esc(text):
        return text.replace("%", r"\%")

    lines = [r"% requires \usepackage{booktabs}",
             r"\begin{table}[htb]", r"\centering",
             r"\begin{tabular}{l " + "r" * (len(header) - 1) + "}", r"\toprule",
             " & ".join(esc(h) for h in header) + r" \\", r"\midrule"]
    ruled = False
    for cells, s in zip(body, stats):
        if s["metric"] in TOTAL_ROWS:
            if not ruled:                    # one rule above the block, not each row
                lines.append(r"\midrule")
                ruled = True
            cells = [rf"\textbf{{{esc(cells[0])}}}", *cells[1:]]
        else:
            cells = [esc(cells[0]), *cells[1:]]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}",
              r"\caption{Cost of producing and grading the conversions, over "
              + f"{stats[0]['n']}" + r" trials. Agent figures describe the "
              r"original run; judge figures describe the most recent judging "
              r"pass, and pool both judges, so their counts are doubled. "
              r"Distributions are right-skewed, so quartiles are reported "
              r"rather than means.}",
             r"\label{tab:resource-summary}", r"\end{table}"]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--job-dir", type=Path, default=DEFAULT_JOB_DIR,
                        help=f"tree of trials to scan (default: {DEFAULT_JOB_DIR})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"LaTeX file to write (default: {DEFAULT_OUT})")
    parser.add_argument("--no-write", action="store_true",
                        help="print the table without writing the .tex")
    args = parser.parse_args(argv)

    rows = collect(args.job_dir)
    stats = summary(rows)
    print(table(stats))

    missing = sum(1 for r in rows if not r.get("agent_source"))
    fallback = sum(1 for r in rows if r.get("agent_source") == "trajectory")
    print(f"\n{len(rows)} trials | agent fields from result.json "
          f"{len(rows) - fallback - missing}, from trajectory {fallback}, "
          f"missing {missing}")

    if not args.no_write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(table(stats, fmt="latex") + "\n")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
