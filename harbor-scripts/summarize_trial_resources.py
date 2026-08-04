#!/usr/bin/env python3
"""Per-trial resource accounting: tokens and wall time for the agent and for each judge.

Writes one wide CSV, one row per trial, answering "what did this benchmark cost to run".
Read-only; the only thing it writes is the CSV.

Not to be confused with timing_results/supervised_summary.csv, which times *re-running*
each agent's convert_data.py under /usr/bin/time -v and says nothing about agent or judge
consumption.

Usage:
    python3 harbor-scripts/summarize_trial_resources.py [--out CSV] [--job-dir DIR]

Which trials: the same selection harbor-scripts/rerun_judges.sh uses, so rows line up with
what was actually judged -- _trial[1234] under harbor-jobs/, minus the debug task and minus
the oracle arms. The two _badtrial3 directories drop out on their own, since they end in
`badtrial3` rather than `_trial3`.

What the numbers mean:

  Agent columns describe the ORIGINAL agent run and are untouched by any rerun.

  Judge columns describe the MOST RECENT judge run, not the judging that happened when a
  trial was first scored. Both arms were re-run on 2026-08-03 against the corrected
  judge_instructions.md and reference_DECISIONS.md.

  result.json also records verifier.{started_at,finished_at}, covering decoder training
  plus the original judges. That is deliberately not a column: it mixes work the judge
  columns now measure separately, and it is stale for every trial re-judged since.

Sources, in preference order:

  agent tokens/time   result.json -> agent_result.*, agent_execution.*
                      falling back to agent/trajectory.json -> final_metrics and the first
                      and last steps[].timestamp. Three trials have no result.json; where
                      both exist they agree to within a second.

  claude judge        last {"type":"result"} line of judge_log.txt, which carries
                      duration_ms, num_turns, total_cost_usd and a usage block.

  codex judge         {"type":"turn.completed"} -> usage. Codex reports no turn count, no
                      cost, and -- see below -- no timing.

Codex judge duration is DERIVED, hence the _est suffix on that column. The codex event
stream carries no timestamp field of any kind. Both judges run sequentially inside one
container (rerun_verifier.sh builds a single JUDGE_SCRIPT that runs claude, then codex), so
codex's window is bounded by the two log files' mtimes. That breaks if only one judge was
re-run, e.g. --claude-judge-only, which leaves the other mtime stale; implausible values
are dropped rather than reported.
"""

import argparse
import collections
import csv
import glob
import json
import os
from datetime import datetime

# Trial selection, mirroring rerun_judges.sh. `_trial[1234]` is what excludes _badtrial3.
TRIAL_GLOB = "*/*/*_trial[1234]/"
EXCLUDED_TASKS = {"debug"}
EXCLUDED_ARMS = {"oracle"}

# A codex duration outside this range means the two judges did not run in one invocation.
MAX_PLAUSIBLE_JUDGE_SECONDS = 2 * 60 * 60

# (column infix, verifier subdirectory) for each of the four judge runs
JUDGE_RUNS = [
    ("claude_sup", "judge", "claude"),
    ("codex_sup", "judge", "codex"),
    ("claude_unsup", "judge_unsupervised", "claude"),
    ("codex_unsup", "judge_unsupervised", "codex"),
]


def parse_iso(text):
    """Seconds since epoch for an ISO-8601 stamp, or None.

    Handles the trailing 'Z' that datetime.fromisoformat rejects before 3.11.
    """
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def phase_seconds(blob, name):
    """Duration in seconds of one result.json phase, e.g. 'agent_execution'."""
    phase = (blob or {}).get(name) or {}
    start, end = parse_iso(phase.get("started_at")), parse_iso(phase.get("finished_at"))
    return round(end - start, 1) if start is not None and end is not None else None


def read_json(path):
    """Parse a JSON file, or return None if missing or malformed."""
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def agent_row(trial_dir):
    """Agent token counts and wall time for one trial.

    trial_dir: path to the trial directory.
    Returns a dict of the agent_* columns; agent_source records which file supplied them.
    """
    row = {"agent_source": ""}
    result = read_json(os.path.join(trial_dir, "result.json"))
    tokens = (result or {}).get("agent_result") or {}

    if tokens.get("n_input_tokens") is not None:
        row.update(
            agent_input_tokens=tokens.get("n_input_tokens"),
            agent_cached_tokens=tokens.get("n_cache_tokens"),
            agent_output_tokens=tokens.get("n_output_tokens"),
            agent_execution_s=phase_seconds(result, "agent_execution"),
            env_setup_s=phase_seconds(result, "environment_setup"),
            agent_setup_s=phase_seconds(result, "agent_setup"),
            agent_source="result.json",
        )
        start, end = parse_iso(result.get("started_at")), parse_iso(result.get("finished_at"))
        row["trial_total_s"] = round(end - start, 1) if start and end else None

    trajectory = read_json(os.path.join(trial_dir, "agent", "trajectory.json"))
    if trajectory:
        metrics = trajectory.get("final_metrics") or {}
        agent = trajectory.get("agent") or {}
        row.setdefault("agent_name", agent.get("name"))
        row["agent_name"] = agent.get("name")
        row["model_name"] = agent.get("model_name")
        row["agent_steps"] = metrics.get("total_steps") or len(trajectory.get("steps") or [])

        # Fallback only: result.json is authoritative where present, and the two agree to
        # within a second on every trial that has both.
        if not row["agent_source"]:
            stamps = [parse_iso(s.get("timestamp")) for s in trajectory.get("steps") or []]
            stamps = [s for s in stamps if s is not None]
            row.update(
                agent_input_tokens=metrics.get("total_prompt_tokens"),
                agent_cached_tokens=metrics.get("total_cached_tokens"),
                agent_output_tokens=metrics.get("total_completion_tokens"),
                agent_execution_s=round(stamps[-1] - stamps[0], 1) if len(stamps) > 1 else None,
                agent_source="trajectory",
            )
    return row


def claude_judge(log_path):
    """Tokens, duration, turns and cost from a claude judge log, summed over invocations.

    Each `claude -p` call ends with a {"type":"result"} line carrying its own totals, and a
    log can hold several: 37 of the 145 unsupervised logs do, where the judging run is
    followed by one or two short follow-up calls. Taking the last one recorded a 2-second,
    24-output-token call in place of a 714-second, 46-turn one, so everything here is
    accumulated across every result event rather than read off one.
    """
    totals = collections.Counter()
    seen = False
    try:
        with open(log_path, errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not (line.startswith("{") and '"duration_ms"' in line):
                    continue
                try:
                    parsed = json.loads(line)
                except ValueError:
                    continue
                if parsed.get("type") != "result":
                    continue
                seen = True
                usage = parsed.get("usage") or {}
                totals["input_tokens"] += usage.get("input_tokens") or 0
                totals["cache_read_tokens"] += usage.get("cache_read_input_tokens") or 0
                totals["cache_creation_tokens"] += usage.get("cache_creation_input_tokens") or 0
                totals["output_tokens"] += usage.get("output_tokens") or 0
                totals["duration_ms"] += parsed.get("duration_ms") or 0
                totals["num_turns"] += parsed.get("num_turns") or 0
                totals["cost_usd"] += parsed.get("total_cost_usd") or 0.0
    except OSError:
        return {}
    if not seen:
        return {}
    return {
        "input_tokens": totals["input_tokens"],
        "cache_read_tokens": totals["cache_read_tokens"],
        "cache_creation_tokens": totals["cache_creation_tokens"],
        "output_tokens": totals["output_tokens"],
        "duration_s": round(totals["duration_ms"] / 1000, 1),
        "num_turns": totals["num_turns"],
        "cost_usd": round(totals["cost_usd"], 4),
    }


def codex_judge(log_path, claude_log_path):
    """Tokens from a codex judge log, plus a duration derived from the two logs' mtimes.

    log_path:        the codex judge_log.txt
    claude_log_path: the claude judge_log.txt from the same invocation, whose mtime marks
                     when codex started, since the two run back to back in one container.
    Codex reports no turn count and no cost, so those keys are left absent.
    """
    usage = None
    try:
        with open(log_path, errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not (line.startswith("{") and '"usage"' in line):
                    continue
                try:
                    parsed = json.loads(line)
                except ValueError:
                    continue
                if parsed.get("usage"):
                    usage = parsed["usage"]
    except OSError:
        return {}
    if usage is None:
        return {}

    duration = None
    if os.path.exists(claude_log_path):
        gap = os.path.getmtime(log_path) - os.path.getmtime(claude_log_path)
        # Negative or huge means the two judges did not run in one invocation.
        if 0 < gap < MAX_PLAUSIBLE_JUDGE_SECONDS:
            duration = round(gap, 1)

    return {
        "input_tokens": usage.get("input_tokens"),
        "cache_read_tokens": usage.get("cached_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "duration_s": duration,
    }


def discover_trials(job_dir):
    """Sorted trial directories in the analysis set, matching rerun_judges.sh."""
    found = []
    for path in sorted(glob.glob(os.path.join(job_dir, TRIAL_GLOB))):
        parts = path.rstrip("/").split(os.sep)
        task, arm = parts[-3], parts[-2]
        if task in EXCLUDED_TASKS or arm in EXCLUDED_ARMS:
            continue
        found.append(path.rstrip("/"))
    return found


def build_row(trial_dir):
    """One CSV row: identity, agent columns, then a column group per judge."""
    parts = trial_dir.split(os.sep)
    task, arm, stamp = parts[-3], parts[-2], parts[-1]
    row = {
        "task": task,
        "arm": arm,
        "trial": stamp.split("_")[-1],
        "trial_dir": trial_dir,
        "agent_name": None,
        "model_name": None,
    }
    row.update(agent_row(trial_dir))

    for infix, subdir, judge in JUDGE_RUNS:
        base = os.path.join(trial_dir, "verifier", subdir)
        log = os.path.join(base, judge, "judge_log.txt")
        if judge == "claude":
            fields = claude_judge(log)
        else:
            fields = codex_judge(log, os.path.join(base, "claude", "judge_log.txt"))
        for key, value in fields.items():
            # Keep the derivation visible in the header for the estimated column.
            suffix = "duration_s_est" if (key == "duration_s" and judge == "codex") else key
            row[f"judge_{infix}_{suffix}"] = value
        # Every token the run touched, cached or not. Not a cost proxy -- a cache read is
        # a tenth the price of an input token and a twentieth of an output token.
        row[f"judge_{infix}_total_tokens"] = sum(
            fields.get(k) or 0 for k in
            ("input_tokens", "cache_read_tokens", "cache_creation_tokens", "output_tokens")
        ) or None

    row["agent_total_tokens"] = (
        (row.get("agent_input_tokens") or 0) + (row.get("agent_output_tokens") or 0)
    ) or None

    # Everything one trial consumed: the agent plus all four judge runs. The time figure is
    # churn only -- agent execution and judge wall time -- and excludes environment and
    # agent setup, which are harness overhead rather than model work. It inherits the
    # estimated codex durations, so treat it as approximate to within a couple of minutes.
    row["total_tokens"] = sum(
        row.get(f"judge_{infix}_total_tokens") or 0 for infix, _, _ in JUDGE_RUNS
    ) + (row.get("agent_total_tokens") or 0) or None
    judge_time = sum(
        (row.get(f"judge_{infix}_duration_s") or row.get(f"judge_{infix}_duration_s_est") or 0)
        for infix, _, _ in JUDGE_RUNS
    )
    total_time = (row.get("agent_execution_s") or 0) + judge_time
    row["total_time_s"] = round(total_time, 1) or None
    return row


def column_order():
    """Full header, so every row has the same columns even when a source was missing."""
    columns = [
        "task", "arm", "trial", "trial_dir", "agent_name", "model_name",
        "agent_total_tokens", "agent_input_tokens", "agent_cached_tokens",
        "agent_output_tokens", "agent_steps",
        "agent_execution_s", "env_setup_s", "agent_setup_s", "trial_total_s", "agent_source",
    ]
    for infix, _, judge in JUDGE_RUNS:
        keys = ["total_tokens", "input_tokens", "cache_read_tokens", "output_tokens"]
        if judge == "claude":
            keys.insert(3, "cache_creation_tokens")
            keys += ["duration_s", "num_turns", "cost_usd"]
        else:
            keys += ["duration_s_est"]
        columns += [f"judge_{infix}_{k}" for k in keys]
    return columns + ["total_tokens", "total_time_s"]


def main():
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--job-dir", default=os.path.join(repo_dir, "harbor-jobs"),
                        help="tree of trials to scan (default: <repo>/harbor-jobs)")
    parser.add_argument("--out", default=os.path.join(repo_dir, "evaluation", "eval",
                                                      "trial_resources.csv"),
                        help="CSV to write (default: evaluation/eval/trial_resources.csv)")
    args = parser.parse_args()

    trials = discover_trials(args.job_dir)
    rows = [build_row(t) for t in trials]
    columns = column_order()

    with open(args.out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c) for c in columns})

    fallback = sum(1 for r in rows if r.get("agent_source") == "trajectory")
    no_agent = sum(1 for r in rows if not r.get("agent_source"))
    est_missing = sum(1 for r in rows for infix, _, judge in JUDGE_RUNS
                      if judge == "codex" and r.get(f"judge_{infix}_duration_s_est") is None)
    print(f"{len(rows)} trials -> {args.out}")
    print(f"  agent columns from result.json: {len(rows) - fallback - no_agent}, "
          f"from trajectory: {fallback}, missing: {no_agent}")
    print(f"  codex duration estimates dropped as implausible: {est_missing} "
          f"of {len(rows) * 2}")


if __name__ == "__main__":
    main()
