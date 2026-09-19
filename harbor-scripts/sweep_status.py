#!/usr/bin/env python3
"""Render the live stage of every job in a cluster sweep as a local HTML page.

A sweep is one bsub job per (task, agent, trial), and `bjobs` only distinguishes PEND from
RUN. Most of a job's wall clock is RUN, so that says almost nothing: a job eight hours in
could be building its image, waiting on an agent, training a decoder or running the second
judge, and the difference decides whether it is healthy or stuck.

This reads two sources and joins them:

  * `bjobs -a` on login1, for the LSF state and the submit and start times -- including jobs
    that finished, which drop out of a plain `bjobs`, and jobs never submitted, which were
    never in it.
  * the job's own output tree under CLUSTER_JOBS_DIR, for what the job is actually doing.
    harbor and tests/test.sh leave enough behind to tell the stages apart without parsing
    any log: the trial directory appears when the image is built, `verifier/` fills when the
    agent is done, `.judge_start` is touched when the judges begin, and one eval JSON
    appears per judge as each finishes.

Each stage is announced by a file whose mtime IS the moment that stage began, so how long a
trial has been in its current stage is a subtraction, and the stages it has already passed
are the gaps between those marks. A finished trial is better than that: harbor's own
result.json records environment_setup, agent_setup, agent_execution and verifier with exact
start and finish times, so completed trials are read from there and only running ones are
estimated from mtimes.

`harbor view` is not this. It serves finished trajectory files and knows nothing about LSF,
so it cannot show pending, not-launched, or how far along a running trial is.

Usage:
    python sweep_status.py --maximal --agents claude codex
    python sweep_status.py --maximal --agents claude codex --watch 60
    python sweep_status.py --tasks sosa2024 --agents codex --out /tmp/one.html

The page carries a meta refresh, so with --watch running in a terminal the browser tab
updates itself.
"""

from __future__ import annotations

import argparse
import html
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from submit_harbor_cluster import (  # noqa: E402
    CLUSTER_JOBS_DIR,
    CLUSTER_LOG_DIR,
    discover_tasks,
)

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "sweep_status.html"

# Seconds to wait for login1. A sweep makes one call, not one per job, so this only has to
# cover a single bjobs; the default ssh timeout would hang the whole page.
BJOBS_TIMEOUT_SEC = 60

# LSF prints times as "Sep 19 14:59:12 2026", in the cluster's local zone, which is this
# machine's too. A field can also read "-" for a job that has not started.
LSF_TIME_FORMAT = "%b %d %H:%M:%S %Y"

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

# Colour per phase of the timeline bar, in the order the phases occur. Chosen to hold their
# distinctness on both light and dark backgrounds, which the page supports through
# prefers-color-scheme.
PHASE_COLOR = {
    "build":  "#0f9b8e",   # teal
    "agent":  "#2b6cb0",   # blue
    "tests":  "#7c3aed",   # purple
    "judges": "#d97706",   # amber
}

# LSF states that mean the job is over. EXIT covers both a crash and a wall-clock kill.
LSF_FINISHED = {"DONE", "EXIT"}


def parse_lsf_time(text: str) -> datetime | None:
    """Parse one LSF timestamp into a local-zone datetime.

    Args:
        text: a field from bjobs, e.g. "Sep 19 14:59:12 2026", or "-" for a job that has
            not reached that point.

    Returns:
        An aware datetime in the local zone, or None if the field carries no time.
    """
    text = text.strip()
    if not text or text == "-":
        return None
    try:
        return datetime.strptime(text, LSF_TIME_FORMAT).astimezone()
    except ValueError:
        return None


def parse_iso(text: str | None) -> datetime | None:
    """Parse one of harbor's result.json timestamps.

    Args:
        text: an ISO-8601 string ending in Z, or None.

    Returns:
        An aware datetime, or None if absent or unparseable.
    """
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def mtime(path: Path) -> datetime | None:
    """Return a path's modification time, or None if it does not exist."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    except OSError:
        return None


def human(seconds: float | None) -> str:
    """Format a duration the way a status page should read.

    Args:
        seconds: elapsed seconds, or None.

    Returns:
        "" for None, else a compact form: "48s", "12m", "3h41m".
    """
    if seconds is None or seconds < 0:
        return ""
    seconds = int(seconds)
    if seconds < 90:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 90:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def bjobs_rows() -> tuple[dict[str, dict], str | None]:
    """Read every hb_* job's LSF state and times from login1.

    Uses `bjobs -a` so finished jobs are included; a plain `bjobs` lists only unfinished
    ones, which would make a completed sweep look as though it had never run. The fields are
    pipe-delimited because LSF's own time format contains spaces.

    Returns:
        ({job_name: {"stat", "submit", "start"}}, error message or None). On failure the map
        is empty and the message is shown on the page, so a login1 outage degrades the page
        to filesystem-only stages rather than producing nothing.
    """
    # The remote runs through `bash -l -c`, so the whole bjobs command is one argument to
    # it and has to survive that quoting intact; shlex.quote does it correctly where hand
    # written backslashes did not, which silently produced an empty state for every job.
    # The delimiter is single-quoted inside the double-quoted -o string for the same reason.
    inner = ("bjobs -a -o \"jobid job_name stat submit_time start_time delimiter='|'\" "
             "-noheader")
    cmd = ["ssh", "login1", f"bash -l -c {shlex.quote(inner)}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=BJOBS_TIMEOUT_SEC)
    except (subprocess.TimeoutExpired, OSError) as error:
        return {}, f"could not reach login1: {error!r}"
    if out.returncode != 0:
        return {}, f"bjobs exited {out.returncode}: {out.stderr.strip()[:200]}"

    jobs: dict[str, dict] = {}
    for line in out.stdout.splitlines():
        # The login shell prints its own banner ("bashrc: initializing conda"), which has no
        # pipes; skip anything that is not a delimited row naming an hb_ job.
        parts = line.split("|")
        if len(parts) < 5 or not parts[1].startswith("hb_"):
            continue
        try:
            jobid = int(parts[0])
        except ValueError:
            continue
        name = parts[1]
        # A resubmitted job name appears more than once, and `bjobs -a` lists UNFINISHED
        # jobs before finished ones, so the newest record comes FIRST rather than last.
        # Keeping the highest job id does not depend on that ordering either way; taking
        # the last row showed every resubmitted job with its predecessor's EXIT.
        if name in jobs and jobs[name]["jobid"] > jobid:
            continue
        jobs[name] = {"jobid": jobid,
                      "stat": parts[2].strip(),
                      "submit": parse_lsf_time(parts[3]),
                      "start": parse_lsf_time(parts[4])}
    return jobs, None


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


def newest_trial_dir(job_dir: Path) -> Path | None:
    """Return the trial directory of a job's most recent run, wherever it now lives.

    A trial starts in `raw/<timestamp>/<task>__<random>/` and run_harbor.sh MOVES it, once
    the run finishes, to `<task>/<agent>/<timestamp>_trial<N>/`. Looking only in raw/ finds
    nothing for a job that completed, which reads as a job that never built its image --
    and, with LSF reporting DONE, as a failure. Both places are searched, newest first.

    Args:
        job_dir: CLUSTER_JOBS_DIR/<job name>, which need not exist.

    Returns:
        The newest trial directory, or None if the job has produced none.
    """
    candidates = []
    # Tidied: <job>/<task>/<agent>/<timestamp>_trialN
    candidates.extend(p for p in job_dir.glob("*/*/*_trial*") if p.is_dir())
    run_dir = newest_run_dir(job_dir)
    if run_dir is not None:
        candidates.extend(p for p in run_dir.iterdir() if p.is_dir() and "__" in p.name)
    if not candidates:
        return None
    # The timestamp leads both spellings, so sorting by name puts the newest run last
    # regardless of which form it is in.
    return max(candidates, key=lambda p: (p.name.split("_trial")[0], p.name))


def final_reward(verifier: Path) -> tuple[dict, datetime] | None:
    """Read a trial's reward file, but only once it is the final one.

    tests/test.sh writes reward.json TWICE: `--provisional` straight after pytest, so a run
    that dies during judging still reports an outcome, and again at the end. The provisional
    write carries only `reward` and `outcome_all`; as write_reward_file.py's own docstring
    puts it, the absent `process` key is what marks a write as provisional. Treating the
    first one as the finished article reports a trial as done while its judges are still
    running, which is exactly what this page exists to distinguish.

    `outcome_mean_per_category` is accepted as well as `process`, because a task with
    run_llm_judge false reaches its final write with no judge score at all.

    Args:
        verifier: a trial's verifier directory.

    Returns:
        (parsed reward dict, its mtime), or None if the file is absent, unreadable or still
        provisional.
    """
    path = verifier / "reward.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if "process" not in data and "outcome_mean_per_category" not in data:
        return None
    stamp = mtime(path)
    return (data, stamp) if stamp else None


def trial_problems(trial: Path) -> str:
    """Report anything that went wrong for reasons other than the agent's own work.

    A low reward is a RESULT, not a problem: an agent that converted the data badly is what
    the benchmark is measuring, and flagging it would bury the cases that need a human. What
    belongs here is the trial failing in ways nobody chose -- harbor recording an exception,
    or a judge failing to produce a score, which leaves `process` averaged over one judge or
    missing entirely.

    Args:
        trial: a trial directory.

    Returns:
        A short description, empty when nothing is wrong.
    """
    notes = []
    try:
        if json.loads((trial / "result.json").read_text()).get("exception_info"):
            notes.append("trial exception")
    except (OSError, ValueError):
        pass
    try:
        metrics = json.loads((trial / "verifier" / "metrics.json").read_text())
    except (OSError, ValueError):
        metrics = {}
    for key, value in sorted(metrics.items()):
        # llm_judge_<name>_error, cleared to "" at the start of every scoring run, so a
        # non-empty value is this run's failure rather than a stale one.
        if key.startswith("llm_judge_") and key.endswith("_error") and value:
            notes.append(f"{key.split('_')[2]} judge failed")
    return "; ".join(notes)


def run_started(run_dir: Path) -> datetime | None:
    """When harbor began this run, from its directory's name.

    harbor names the directory after the local time it started, so the name is a better
    clock than any mtime: a directory's mtime moves every time something is written inside
    it. This is also where the image build begins -- measured against a finished trial, the
    name is within a few seconds of result.json's environment_setup start.

    Args:
        run_dir: a `raw/<timestamp>` directory, named like 2026-09-19__14-59-36.

    Returns:
        The parsed start time, or None if the name is not in that form.
    """
    try:
        return datetime.strptime(run_dir.name, "%Y-%m-%d__%H-%M-%S").astimezone()
    except ValueError:
        return None


def agent_started(trial: Path) -> datetime | None:
    """When the agent's container work began, which is when the image build ended.

    The trial's own config.json is written when harbor CREATES the trial, before the
    environment is up, so it dates the start of the build and not its end. The first file
    harbor writes under agent/ lands within a fraction of a second of agent_setup starting
    -- measured at 0.15s against a finished trial -- so the earliest mtime there is the
    boundary.

    Args:
        trial: a trial directory.

    Returns:
        The earliest mtime under agent/, or None if it is absent or empty.
    """
    agent = trial / "agent"
    if not agent.is_dir():
        return None
    # Top level only. Recursing gives the same answer to within 0.15s but descends into
    # sessions/, skills/ and the agent's sqlite files, which on NFS across a whole sweep
    # took the page from seconds to minutes.
    stamps = [t for t in (mtime(p) for p in agent.iterdir()) if t is not None]
    return min(stamps) if stamps else None


def verifier_start(verifier: Path) -> datetime | None:
    """When the verifier first wrote anything.

    tests/test.sh installs dependencies and snapshots the agent's files before running any
    test, so the earliest mtime in the directory is when the verifier took over from the
    agent -- closer than the directory's own mtime, which moves with every later write.

    Args:
        verifier: a trial's verifier directory.

    Returns:
        The earliest mtime inside it, or None if it is absent or empty.
    """
    if not verifier.is_dir():
        return None
    stamps = [t for t in (mtime(p) for p in verifier.iterdir()) if t is not None]
    return min(stamps) if stamps else None


def trial_stage(trial: Path | None, run_dir: Path | None) -> tuple[str, str, datetime | None]:
    """Work out how far a run has got, and when that stage began.

    The order below follows tests/test.sh, and each test is for something that exists only
    once that stage has begun, so the first match from the bottom up is the current stage.

    Args:
        trial: the run's trial directory, in either location, or None if it has none yet.
        run_dir: the run's `raw/<timestamp>` directory, for dating the image build.

    Returns:
        (stage name, one-line detail, when the stage began or None).
    """
    # harbor creates the trial directory once the environment is up, so its absence while
    # the job runs means the image is still building -- on a cold podman store, every job.
    if trial is None:
        return "building image", "no trial directory yet", mtime(run_dir) if run_dir else None

    verifier = trial / "verifier"
    final = final_reward(verifier)
    if final is not None:
        data, stamp = final
        value = data.get("reward")
        detail = f"reward {value:.3f}" if isinstance(value, float) else "finished"
        return "done", detail, stamp

    # harbor creates verifier/ EMPTY when it sets the trial up, long before the agent
    # finishes, so its existence says nothing. Only content means the verifier has begun.
    started = verifier_start(verifier)
    if started is not None:
        judges = verifier / "judge"
        judge_start = verifier / ".judge_start"
        if judge_start.is_file():
            finished = sorted(p.name for p in judges.iterdir()
                              if judges.is_dir() and (p / "llm_judge_eval.json").is_file())
            if len(finished) >= 2:
                last = max(mtime(judges / n / "llm_judge_eval.json") for n in finished)
                return "judged", "both judges finished, computing reward", last
            if finished:
                done_at = mtime(judges / finished[0] / "llm_judge_eval.json")
                return "judging", f"{finished[0]} done, other still running", done_at
            return "judging", "judges started", mtime(judge_start)
        metrics = verifier / "metrics.json"
        if metrics.is_file():
            return "verifying", "tests finished, judges not started", mtime(metrics)
        return "verifying", "tests running (decoder training)", started

    # The trial's own config.json is written once, when harbor creates the trial, so it
    # dates the moment the environment was ready and the agent could start.
    if (trial / "agent").is_dir():
        return "agent running", "agent working in /app", mtime(trial / "config.json")
    return "starting", "trial created", mtime(trial)


def phase_spans(trial: Path | None, run_dir: Path | None, job: dict | None,
                now: datetime) -> list[tuple[str, float, bool]]:
    """Break a trial's elapsed time into the phases it has passed through.

    A completed trial is read from harbor's own result.json, which records
    environment_setup, agent_setup, agent_execution and verifier with exact bounds; the
    verifier span is split at `.judge_start` so the tests and the judges show separately.
    A running trial has no result.json, so its phases are the gaps between the marker files,
    and the phase it is still in runs to `now`.

    Args:
        run_dir: the run's `raw/<timestamp>` directory, or None.
        job: the job's bjobs row, for the queue wait, or None.
        now: the time the page is being generated.

    Returns:
        [(phase name, seconds, still running)] in the order they occurred. The names are the
        keys of PHASE_COLOR. A phase with no measurable bound is left out rather than
        guessed at, so a bar can be shorter than the job's true age.
    """
    spans: list[tuple[str, float, bool]] = []

    def add(name: str, start: datetime | None, end: datetime | None, current: bool = False):
        if start and end and (seconds := (end - start).total_seconds()) > 0:
            spans.append((name, seconds, current))

    # The queue wait is deliberately NOT a span. It is not the trial's work, and it varies
    # by hours with cluster load, so on a shared axis it dwarfs the phases worth comparing.
    # A job's time in the queue is still on the page: the `for` column, while it is pending.
    if trial is None:
        if run_dir is not None:
            # No trial directory yet: everything since harbor started is the image build.
            add("build", run_started(run_dir) or (job.get("start") if job else None),
                now, current=True)
        return spans
    verifier = trial / "verifier"
    judge_start = mtime(verifier / ".judge_start")

    result = trial / "result.json"
    if result.is_file():
        try:
            data = json.loads(result.read_text())
        except (OSError, ValueError):
            data = {}
        env, setup = data.get("environment_setup") or {}, data.get("agent_setup") or {}
        run, verify = data.get("agent_execution") or {}, data.get("verifier") or {}
        add("build", parse_iso(env.get("started_at")), parse_iso(env.get("finished_at")))
        add("agent", parse_iso(setup.get("started_at")), parse_iso(run.get("finished_at")))
        v_start, v_end = parse_iso(verify.get("started_at")), parse_iso(verify.get("finished_at"))
        if v_start and judge_start and v_end:
            add("tests", v_start, judge_start)
            add("judges", judge_start, v_end)
        else:
            add("tests", v_start, v_end)
        return spans

    # No result.json yet: reconstruct from the marks that exist so far. The trial's work can
    # still be over -- tests/test.sh writes reward.json before harbor writes result.json --
    # so the last phase closes at reward.json when there is one, and only runs to `now`, and
    # reads as still running, when there is not.
    final = final_reward(verifier)
    end, open_ended = (final[1], False) if final else (now, True)

    # The build runs from harbor's own start to the moment the agent's first file appears.
    # Measuring it from the LSF start instead would fold in run_harbor.sh's preamble, and
    # ending it at the trial's config.json -- written when the trial is created, before the
    # environment exists -- reported the build as seconds when it was minutes.
    begin = run_started(run_dir) if run_dir else None
    ready = agent_started(trial)
    started = verifier_start(verifier)
    add("build", begin, ready or end, current=open_ended and ready is None)
    if ready is None:
        return spans
    if started is None:
        add("agent", ready, end, current=open_ended)
        return spans
    add("agent", ready, started)
    if judge_start is None:
        add("tests", started, end, current=open_ended)
        return spans
    add("tests", started, judge_start)
    add("judges", judge_start, end, current=open_ended)
    return spans


def job_rows(tasks: list[str], agents: list[str], trials: int) -> tuple[list[dict], str | None]:
    """Build one row per expected job, whether or not it was ever submitted.

    Args:
        tasks: task directory names.
        agents: arm names, as passed to submit_harbor_cluster.py.
        trials: how many trials per (task, agent).

    Returns:
        (rows, bjobs error or None). Each row has name, task, agent, trial, lsf, stage,
        detail, elapsed, phases and log.
    """
    jobs, error = bjobs_rows()
    now = datetime.now().astimezone()
    rows = []
    for task in tasks:
        for agent in agents:
            for trial in range(1, trials + 1):
                name = f"hb_{task}_{agent}_t{trial}"
                job = jobs.get(name)
                lsf = job["stat"] if job else ""
                job_dir = CLUSTER_JOBS_DIR / name
                run_dir = newest_run_dir(job_dir)
                trial_dir = newest_trial_dir(job_dir)

                # Output on disk belongs to the job that WROTE it, not to the one holding
                # the name now. A job name carries no date, so a resubmit reuses the whole
                # tree: without this, a pending job inherits its dead predecessor's run --
                # and since a stale run has no end, its build span ran to `now`, which for
                # a directory left over from July is fifty-three days. One such row set the
                # shared axis and squeezed every real bar to a sliver.
                started = job.get("start") if job else None
                if started is not None and run_dir is not None:
                    begun = run_started(run_dir)
                    if begun is not None and begun < started:
                        run_dir = trial_dir = None
                elif job and job["stat"] == "PEND":
                    run_dir = trial_dir = None

                if run_dir is not None or trial_dir is not None:
                    stage, detail, since = trial_stage(trial_dir, run_dir)
                else:
                    stage, detail, since = "starting", "no run directory yet", None

                # LSF outranks the filesystem for the two states the filesystem cannot see:
                # a job that never ran leaves nothing, and a job killed mid-stage leaves its
                # last stage looking current forever.
                if not job and run_dir is None and trial_dir is None:
                    stage, detail, since = "not launched", "not in bjobs, no output", None
                elif lsf == "PEND":
                    stage, detail = "pending", "queued"
                    since = job["submit"] if job else None
                elif lsf in LSF_FINISHED and stage != "done":
                    stage, detail = "FAILED", f"LSF {lsf} before a reward was written"

                # The three parts the reward is the mean of, kept separate because they
                # answer different questions: whether every check passed, how many passed,
                # and what the judges made of the decisions behind them.
                final = final_reward(trial_dir / "verifier") if trial_dir else None
                scores = final[0] if final else {}
                problems = trial_problems(trial_dir) if trial_dir else ""
                if stage == "FAILED" and not problems:
                    problems = detail

                rows.append({
                    "name": name, "task": task, "agent": agent, "trial": trial,
                    "lsf": lsf or "-", "stage": stage, "detail": detail,
                    # Time in the CURRENT stage, and only while there is one. On a
                    # finished trial this would otherwise count up forever from the moment
                    # it completed, which is time the job was not running.
                    "elapsed": (human((now - since).total_seconds())
                                if since and stage not in ("done", "FAILED") else ""),
                    "spans": phase_spans(trial_dir, run_dir, job, now),
                    "reward": scores.get("reward"),
                    "outcome_all": scores.get("outcome_all"),
                    "categories": scores.get("outcome_mean_per_category"),
                    "process": scores.get("process"),
                    "problems": problems,
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
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["stage"]] = counts.get(row["stage"], 0) + 1
    summary = " · ".join(f"{counts[s]} {s}" for s in STAGES if s in counts)

    # One shared time axis across every bar, so a row's length is comparable to its
    # neighbours' and a slow job is visible without reading a number. Guard the empty
    # sweep, where every total is zero.
    longest = max((sum(s for _, s, _ in row["spans"]) for row in rows), default=0) or 1

    body = []
    for row in rows:
        segments = []
        for phase, seconds, current in row["spans"]:
            label = f"{phase} {human(seconds)}" + (" (running)" if current else "")
            segments.append(
                f'<i class="p-{phase}{" cur" if current else ""}" '
                f'style="width:{100 * seconds / longest:.2f}%" '
                f'title="{html.escape(label)}"></i>')
        total = human(sum(s for _, s, _ in row["spans"])) if row["spans"] else ""

        def score(key: str, klass: str = "") -> str:
            value = row[key]
            if not isinstance(value, (int, float)):
                return '<td class="num sc"></td>'
            # A zero is a real score, not a missing one, so it is shown rather than dimmed.
            return f'<td class="num sc {klass}">{value:.2f}</td>'

        classes = "s-" + row["stage"].replace(" ", "-") + (" err" if row["problems"] else "")
        body.append(
            f'<tr class="{classes}">'
            f'<td class="mono">{html.escape(row["task"])}</td>'
            f'<td>{html.escape(row["agent"])}</td>'
            f'<td class="num">{row["trial"]}</td>'
            f'<td class="num">{html.escape(row["lsf"])}</td>'
            f'<td class="stage">{html.escape(row["stage"])}</td>'
            f'<td class="num for">{html.escape(row["elapsed"])}</td>'
            f'<td class="tl"><div class="bars">{"".join(segments)}</div></td>'
            f'<td class="num total">{html.escape(total)}</td>'
            + score("reward", "rw") + score("outcome_all") + score("categories")
            + score("process")
            + f'<td class="problems">{html.escape(row["problems"])}</td>'
            f'<td class="detail">{html.escape(row["detail"])}</td>'
            f'<td class="mono log">{html.escape(row["log"])}</td></tr>')

    legend = "".join(f'<span class="key"><i class="p-{p}"></i>{p}</span>'
                     for p in PHASE_COLOR)
    # Emitted rather than hardcoded in the stylesheet so PHASE_COLOR stays the one place a
    # phase's colour is set, for both the bars and the legend.
    phase_css = "\n".join(f" .p-{p} {{ background-color:{c}; }}"
                          for p, c in PHASE_COLOR.items())

    meta = f'<meta http-equiv="refresh" content="{refresh}">' if refresh else ""
    warn = f'<p class="error">{html.escape(error)}</p>' if error else ""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    refresh_note = f" &middot; refreshing every {refresh}s" if refresh else ""

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
 table {{ border-collapse:collapse; width:100%; max-width:1500px; }}
 th,td {{ text-align:left; padding:5px 10px; border-bottom:1px solid var(--line);
   white-space:nowrap; }}
 th {{ background:var(--head); position:sticky; top:0; font-weight:600; }}
 .num {{ text-align:right; }}
 .for {{ font-variant-numeric:tabular-nums; font-weight:600; }}
 .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
 .log {{ color:var(--muted); max-width:340px; overflow:hidden; text-overflow:ellipsis; }}
 .detail {{ color:var(--muted); }}
 .stage {{ font-weight:600; }}
 .total {{ font-variant-numeric:tabular-nums; color:var(--muted); }}
 .sc {{ font-variant-numeric:tabular-nums; }}
 .rw {{ font-weight:600; }}
 /* A problem is something nobody chose -- an exception, a judge that did not score. A low
    reward is a result and is deliberately not highlighted. */
 .problems {{ color:#b00; font-weight:600; }}
 tr.err {{ background:rgba(187,0,0,.07); }}
 .tl {{ width:100%; min-width:260px; }}
 /* No track behind the bar. The bar is only the time the job spent working, and a
    background would draw the rest of the shared axis as though it were elapsed time --
    which for a finished job is time after it was done, and for a pending one is queue. */
 .bars {{ display:flex; height:11px; border-radius:3px; overflow:hidden; }}
 .bars i {{ display:block; height:100%; }}
 /* The phase still running is hatched, so an open span reads as "so far" rather than as a
    measured duration. */
 .bars i.cur {{ background-image:repeating-linear-gradient(45deg,
   rgba(255,255,255,.45) 0 3px, rgba(255,255,255,0) 3px 6px); }}
 .key {{ display:inline-flex; align-items:center; gap:5px; margin-right:14px;
   color:var(--muted); font-size:12px; }}
 .key i {{ width:11px; height:11px; border-radius:2px; display:inline-block; }}
{phase_css}
 .s-not-launched .stage {{ color:var(--muted); }}
 .s-pending      .stage {{ color:#8a6d00; }}
 .s-starting,.s-building-image .stage {{ color:#0b6ea8; }}
 .s-agent-running .stage {{ color:#2b6cb0; }}
 .s-verifying    .stage {{ color:#6b46c1; }}
 .s-judging,.s-judged .stage {{ color:#8a5a00; }}
 .s-done         .stage {{ color:#1a7f37; }}
 .s-FAILED       .stage {{ color:#b00; }}
 @media (max-width:900px) {{ .log,th:last-child {{ display:none; }} }}
</style></head><body>
<h1>Sweep status</h1>
<p class="sub">{len(rows)} jobs &middot; {html.escape(summary)}<br>
generated {now}{refresh_note}</p>
<p>{legend}<span class="key"><i style="background-image:repeating-linear-gradient(45deg,
 var(--muted) 0 3px,transparent 3px 6px);background-color:var(--line)"></i>still
 running</span></p>
{warn}
<table><thead><tr><th>task</th><th>agent</th><th>trial</th><th>LSF</th>
<th>stage</th><th>for</th><th>time in each phase</th><th>total</th>
<th class="num" title="mean of the three to its right">reward</th>
<th class="num" title="1 only if every check passed">outcome</th>
<th class="num" title="mean over the outcome categories">categories</th>
<th class="num" title="mean of the judges' scores">process</th>
<th>problem</th><th>detail</th><th>log</th></tr></thead>
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
