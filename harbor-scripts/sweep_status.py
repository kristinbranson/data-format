#!/usr/bin/env python3
"""Render the live stage of every job in a cluster sweep as a local HTML page.

A sweep is one bsub job per (task, agent, trial), and `bjobs` only distinguishes PEND from
RUN. Most of a job's wall clock is RUN, so that says almost nothing: a job eight hours in
could be building its image, waiting on an agent, training a decoder or running the second
judge, and the difference decides whether it is healthy or stuck.

This reads two sources and joins them:

  * `bjobs -a` on login1, for the LSF state -- including jobs that finished, which drop out
    of a plain `bjobs`, and jobs never submitted, which were never in it.
  * the job's own output tree under CLUSTER_JOBS_DIR, for what the job is actually doing.
    harbor and tests/test.sh leave enough behind to tell the stages apart without parsing
    any log: the trial directory appears when the image is built, `verifier/` when the agent
    is done, `.judge_start` when the judges begin, and one eval JSON per judge as each
    finishes.

`harbor view` is not this. It serves finished trajectory files and knows nothing about LSF,
so it cannot show pending, not-launched, or how far along a running trial is.

Usage:
    python sweep_status.py --maximal --agents claude codex          # write and open
    python sweep_status.py --maximal --agents claude codex --watch 60
    python sweep_status.py --tasks sosa2024 --agents codex --out /tmp/one.html

The page carries a meta refresh, so with --watch running in a terminal the browser tab
updates itself.
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from submit_harbor_cluster import (  # noqa: E402
    CLUSTER_JOBS_DIR,
    CLUSTER_LOG_DIR,
    discover_tasks,
)

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "sweep_status.html"

# Seconds to wait for login1. A sweep of 48 jobs makes one call, not one per job, so this
# only has to cover a single bjobs; the default ssh timeout would hang the whole page.
BJOBS_TIMEOUT_SEC = 60

# Stage order, coarsest first. The index doubles as the progress bar's width, so a stage
# added here must go in the position it actually occurs in.
STAGES = [
    "not launched",
    "pending",
    "starting",
    "building image",
    "agent running",
    "verifying",
    "judging",
    "judged",
    "done",
    "FAILED",
]
STAGE_INDEX = {name: i for i, name in enumerate(STAGES)}

# LSF states that mean the job is over. EXIT covers both a crash and a wall-clock kill.
LSF_FINISHED = {"DONE", "EXIT"}


def bjobs_states() -> tuple[dict[str, str], str | None]:
    """Read every hb_* job's LSF state from login1.

    Uses `bjobs -a` so finished jobs are included; a plain `bjobs` lists only unfinished
    ones, which would make a completed sweep look as though it had never run.

    Returns:
        ({job_name: LSF state}, error message or None). On failure the map is empty and
        the message is shown on the page, so a login1 outage degrades the page to
        filesystem-only stages rather than producing nothing.
    """
    cmd = ["ssh", "login1", "bash -l -c 'bjobs -a -o \"job_name stat\" -noheader'"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=BJOBS_TIMEOUT_SEC)
    except (subprocess.TimeoutExpired, OSError) as error:
        return {}, f"could not reach login1: {error!r}"
    if out.returncode != 0:
        return {}, f"bjobs exited {out.returncode}: {out.stderr.strip()[:200]}"

    states: dict[str, str] = {}
    for line in out.stdout.splitlines():
        # The login shell prints its own banner ("bashrc: initializing conda"), which has
        # no second field; skip anything that is not two tokens starting with hb_.
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("hb_"):
            # A resubmitted job name appears more than once. The last line is the most
            # recent, so a rerun's state wins over the earlier attempt's.
            states[parts[0]] = parts[1]
    return states, None


def newest_run_dir(job_dir: Path) -> Path | None:
    """Return the most recent harbor run directory inside a job's tree.

    A job directory accumulates one `raw/<timestamp>/` per run, because the job name has no
    date in it and a resubmit reuses it. The newest is the run this status is about.

    Args:
        job_dir: CLUSTER_JOBS_DIR/<job name>, which need not exist.

    Returns:
        The newest `raw/<timestamp>` directory, or None if the job has produced none.
    """
    raw = job_dir / "raw"
    if not raw.is_dir():
        return None
    runs = sorted((p for p in raw.iterdir() if p.is_dir() and p.name.startswith("20")),
                  key=lambda p: p.name)
    return runs[-1] if runs else None


def trial_stage(run_dir: Path) -> tuple[str, str]:
    """Work out how far a run has got from the files it has left behind.

    The order below follows tests/test.sh, and each test is for something that exists only
    once that stage has begun, so the first match from the bottom up is the current stage.

    Args:
        run_dir: a `raw/<timestamp>` directory.

    Returns:
        (stage name, one-line detail for the page).
    """
    # harbor names the trial `<task>__<random>`; its absence means the environment is still
    # being set up, which on a cold podman store is the image build.
    trials = [p for p in run_dir.iterdir() if p.is_dir() and "__" in p.name]
    if not trials:
        return "building image", "no trial directory yet"
    trial = trials[0]

    verifier = trial / "verifier"
    reward = verifier / "reward.json"
    if reward.is_file():
        try:
            value = json.loads(reward.read_text()).get("reward")
            return "done", f"reward {value:.3f}" if isinstance(value, float) else "done"
        except (OSError, ValueError):
            return "done", "reward.json unreadable"

    # harbor creates verifier/ EMPTY when it sets the trial up, long before the agent
    # finishes, so its existence says nothing. Only content means the verifier has begun:
    # tests/test.sh writes the snapshot first, then metrics.json, then the judge markers.
    if verifier.is_dir() and any(verifier.iterdir()):
        judges = verifier / "judge"
        if (verifier / ".judge_start").is_file():
            finished = sorted(p.name for p in judges.iterdir()
                              if judges.is_dir() and (p / "llm_judge_eval.json").is_file())
            if len(finished) >= 2:
                return "judged", "both judges finished, computing reward"
            if finished:
                return "judging", f"{finished[0]} done, other still running"
            return "judging", "judges started"
        if (verifier / "metrics.json").is_file():
            return "verifying", "tests finished, judges not started"
        return "verifying", "tests running (decoder training)"

    if (trial / "agent").is_dir():
        return "agent running", "agent working in /app"
    return "starting", "trial created"


def job_rows(tasks: list[str], agents: list[str], trials: int) -> list[dict]:
    """Build one row per expected job, whether or not it was ever submitted.

    Args:
        tasks: task directory names.
        agents: arm names, as passed to submit_harbor_cluster.py.
        trials: how many trials per (task, agent).

    Returns:
        One dict per job with keys name, task, agent, trial, lsf, stage, detail, log.
    """
    states, error = bjobs_states()
    rows = []
    for task in tasks:
        for agent in agents:
            for trial in range(1, trials + 1):
                name = f"hb_{task}_{agent}_t{trial}"
                lsf = states.get(name, "")
                job_dir = CLUSTER_JOBS_DIR / name
                run_dir = newest_run_dir(job_dir)

                if run_dir is not None:
                    stage, detail = trial_stage(run_dir)
                else:
                    stage, detail = "starting", "no run directory yet"

                # LSF outranks the filesystem for the two states the filesystem cannot
                # see: a job that never ran leaves nothing, and a job killed mid-stage
                # leaves its last stage looking current forever.
                if not lsf and run_dir is None:
                    stage, detail = "not launched", "not in bjobs, no output"
                elif lsf == "PEND":
                    stage, detail = "pending", "queued"
                elif lsf in LSF_FINISHED and stage != "done":
                    stage, detail = "FAILED", f"LSF {lsf} before a reward was written"

                rows.append({
                    "name": name, "task": task, "agent": agent, "trial": trial,
                    "lsf": lsf or "-", "stage": stage, "detail": detail,
                    "log": str(CLUSTER_LOG_DIR / f"{name}.log"),
                })
    return rows, error


def render(rows: list[dict], error: str | None, refresh: int) -> str:
    """Render the rows as a standalone HTML page.

    Args:
        rows: as returned by job_rows.
        error: message to show if bjobs could not be read, else None.
        refresh: meta-refresh interval in seconds; 0 disables it.

    Returns:
        The complete HTML document.
    """
    counts = {}
    for row in rows:
        counts[row["stage"]] = counts.get(row["stage"], 0) + 1
    summary = " · ".join(f"{counts[s]} {s}" for s in STAGES if s in counts)

    body = []
    for row in rows:
        pct = 100 * STAGE_INDEX[row["stage"]] / (len(STAGES) - 1)
        body.append(
            f'<tr class="s-{row["stage"].replace(" ", "-")}">'
            f'<td class="mono">{html.escape(row["task"])}</td>'
            f'<td>{html.escape(row["agent"])}</td>'
            f'<td class="num">{row["trial"]}</td>'
            f'<td class="num">{html.escape(row["lsf"])}</td>'
            f'<td class="stage">{html.escape(row["stage"])}'
            f'<div class="bar"><i style="width:{pct:.0f}%"></i></div></td>'
            f'<td class="detail">{html.escape(row["detail"])}</td>'
            f'<td class="mono log" title="{html.escape(row["log"])}">'
            f'{html.escape(row["log"])}</td></tr>')

    meta = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
    warn = f'<p class="error">{html.escape(error)}</p>' if error else ""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">{meta}
<title>Sweep status</title>
<style>
 :root {{ color-scheme: light dark;
   --bg:#fff; --fg:#111; --line:#d8d8d8; --muted:#666; --head:#f4f4f4; }}
 @media (prefers-color-scheme: dark) {{ :root {{
   --bg:#16181c; --fg:#e6e6e6; --line:#2e3238; --muted:#9aa0a6; --head:#1d2025; }} }}
 body {{ background:var(--bg); color:var(--fg); margin:0; padding:24px 16px;
   font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif; }}
 h1 {{ font-size:19px; margin:0 0 2px; }}
 .sub {{ color:var(--muted); margin:0 0 18px; }}
 .error {{ color:#b00; }}
 table {{ border-collapse:collapse; width:100%; max-width:1400px; }}
 th,td {{ text-align:left; padding:5px 10px; border-bottom:1px solid var(--line);
   white-space:nowrap; }}
 th {{ background:var(--head); position:sticky; top:0; font-weight:600; }}
 .num {{ text-align:right; }}
 .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
 .log {{ color:var(--muted); max-width:460px; overflow:hidden; text-overflow:ellipsis; }}
 .detail {{ color:var(--muted); }}
 .stage {{ font-weight:600; }}
 .bar {{ height:3px; background:var(--line); border-radius:2px; margin-top:3px;
   width:130px; }}
 .bar i {{ display:block; height:100%; border-radius:2px; background:currentColor; }}
 .s-not-launched .stage {{ color:var(--muted); }}
 .s-pending      .stage {{ color:#8a6d00; }}
 .s-starting,.s-building-image .stage {{ color:#0b6ea8; }}
 .s-agent-running .stage {{ color:#2b6cb0; }}
 .s-verifying    .stage {{ color:#6b46c1; }}
 .s-judging,.s-judged .stage {{ color:#8a5a00; }}
 .s-done         .stage {{ color:#1a7f37; }}
 .s-FAILED       .stage {{ color:#b00; }}
 @media (max-width:760px) {{ .log {{ display:none; }} th:last-child {{ display:none; }} }}
</style></head><body>
<h1>Sweep status</h1>
<p class="sub">{len(rows)} jobs &middot; {html.escape(summary)}<br>
generated {now}{' &middot; refreshing every %ds' % refresh if refresh else ''}</p>
{warn}
<table><thead><tr><th>task</th><th>agent</th><th>trial</th><th>LSF</th>
<th>stage</th><th>detail</th><th>log</th></tr></thead>
<tbody>{''.join(body)}</tbody></table>
</body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", nargs="*", default=None,
                        help="task names; default is the scope flag below")
    parser.add_argument("--maximal", action="store_const", const="maximal", dest="scope")
    parser.add_argument("--minimal", action="store_const", const="minimal", dest="scope")
    parser.add_argument("--agents", nargs="*", default=["claude", "codex"])
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--watch", type=int, default=0, metavar="SEC",
                        help="regenerate every SEC seconds until interrupted")
    args = parser.parse_args()

    tasks = args.tasks or discover_tasks(args.scope or "all")
    refresh = args.watch or 0

    while True:
        rows, error = job_rows(tasks, args.agents, args.trials)
        args.out.write_text(render(rows, error, refresh))
        stamp = datetime.now().strftime("%H:%M:%S")
        done = sum(1 for r in rows if r["stage"] == "done")
        print(f"{stamp}  wrote {args.out}  ({done}/{len(rows)} done)")
        if not args.watch:
            return
        try:
            time.sleep(args.watch)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
