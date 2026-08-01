#!/usr/bin/env python3
"""
Check the health of harbor trial runs.

For each trial, checks the artifacts a complete trial must have:
  - verifier/snapshot/convert_data.py   the agent's conversion script
  - verifier/snapshot/converted_data.pkl the converted dataset ("agent ran")
  - verifier/metrics.json                valid JSON
  - verifier/judge/{claude,codex}/llm_judge_eval.json, with no error recorded
    in metrics.json

A missing snapshot DIRECTORY is reported separately from a missing file inside it.
The distinction matters: without a snapshot there is no converted_data.pkl, so no
verifier rerun or metrics recompute can ever recover the trial -- it has to be run
again from scratch.

Usage:
    python check_trial_health.py [--job-dirs DIR [DIR ...]] [--no-oracle] [--summary-only]

Defaults to scanning the two analysis trees:
    <repo>/harbor-jobs
    <repo>/harbor-jobs-new

Not scanned: harbor-cluster-jobs, whose raw per-job layout is one level deeper
(hb_<task>_<arm>_t<N>/<task>/<agent>/<trial>). Use
`python collect_cluster_results.py` (dry run) for that tree -- it already reports
what is finished, still running, and failed.

The legacy tree ~/harbor-tasks/data-format/jobs is no longer scanned by default;
pass it via --job-dirs if you need it.
"""

import argparse
import json
import os
import glob
import re
import sys
import textwrap
from collections import defaultdict
from pathlib import Path


def print_wrapped_row(columns, widths, aligns=None, sep="  "):
    """Print a row with optional wrapping in any column.

    columns: list of strings (cell values)
    widths: list of column widths (max chars per cell)
    aligns: list of '<' or '>' (default '<')
    sep: separator between columns
    """
    if aligns is None:
        aligns = ["<"] * len(columns)
    # Wrap each cell to its width
    wrapped = []
    for col, w in zip(columns, widths):
        if not col:
            wrapped.append([""])
        else:
            lines = textwrap.wrap(str(col), width=w, break_long_words=False, break_on_hyphens=False) or [""]
            wrapped.append(lines)
    # Pad each cell to the same number of lines
    n_lines = max(len(c) for c in wrapped)
    for c in wrapped:
        while len(c) < n_lines:
            c.append("")
    # Print row by row
    for row_idx in range(n_lines):
        parts = []
        for cell, w, align in zip(wrapped, widths, aligns):
            parts.append(f"{cell[row_idx]:{align}{w}s}")
        print(sep.join(parts))


def parse_metrics_json(path):
    """Parse a metrics.json that may contain NaN/Infinity."""
    with open(path) as f:
        txt = f.read()
    txt = re.sub(r"\bNaN\b", "null", txt)
    txt = re.sub(r"(?<!\w)-?Infinity\b", "null", txt)
    # trailing commas
    txt = re.sub(r",(\s*[}\]])", r"\1", txt)
    return json.loads(txt)


def judge_issues(verifier_dir, metrics, subdir="judge", suffix="", verbose=False, label=None):
    """Problems with the judge outputs under `verifier_dir/subdir/`.

    A judge is only healthy if it BOTH left no error in metrics.json and actually
    wrote llm_judge_eval.json. The two are independent: a judge that hits an API
    quota records an error and writes nothing, while one that finishes but resolves
    its output path against /app writes nothing and records only the resulting
    "[Errno 2]" — so checking one alone misses half the failures.

    Args:
        verifier_dir: directory holding metrics.json and the judge subdirectory.
        metrics: parsed metrics.json, the source of the recorded error fields.
        subdir: "judge" for the verifier's own pass, "judge_unsupervised" for the
            separate reference-hidden pass run by run_unsupervised_judges.sh.
        suffix: "" or "_unsupervised", matching how the metrics.json keys are named.
        verbose: print each problem as it is found.
        label: what to call this trial in verbose output.

    Returns:
        list[str] of problems, empty when both judges are healthy.
    """
    label = label or verifier_dir
    what = " unsupervised" if suffix else ""
    issues = []
    for model in ("claude", "codex"):
        err = metrics.get(f"llm_judge_{model}{suffix}_error", "")
        if err:
            issues.append(f"{model}{what} judge error")
            if verbose:
                print(f"{label} has {model}{what} judge error: {err}")
        if not os.path.exists(os.path.join(verifier_dir, subdir, model, "llm_judge_eval.json")):
            issues.append(f"{model}{what} no llm_judge_eval.json")
            if verbose:
                print(f"{label} missing {model}{what} llm_judge_eval.json")
    return issues


# pytest -rA ends its run with one "FAILED <nodeid> - <ExceptionType>: <msg>" line
# per failure. That summary is the only place the exception type survives; the
# ctrf.json records status but not why.
_PYTEST_FAILED_RE = re.compile(
    r"^FAILED\s+(\S+)\s+-\s+([A-Za-z_.]*(?:Error|Exception))\b[:\s]*(.*)$", re.M
)

# Substrings that mark a failure as the machine's fault rather than the data's.
# Matched against both the exception type and its message.
_ENVIRONMENT_MARKERS = ("CUDA", "OutOfMemory", "MemoryError", "Timeout", "Cancelled")

# What each test is responsible for recording. A failed test is only worth
# rerunning if these are still absent: several April trials died on CUDA and were
# repaired later by rerun_metrics.py, leaving a stale ctrf.json beside a complete
# metrics.json. Keyed on metrics, not on test status, for exactly that reason.
TEST_METRICS = {
    "test_required_files_exist": ("required_files_missing",),
    "test_verify_data_format": ("full_data_format_valid",),
    "test_data_stats": ("input_range_mean_cost", "output_fraction_mean_cost"),
    "test_decoder_accuracy": ("validation_balanced_accuracy",),
}


def classify_failure(exception, message):
    """Whose fault a pytest failure was.

    Args:
        exception: exception type name from the pytest FAILED summary line.
        message: the truncated message that followed it.

    Returns:
        "agent" when the verifier ran correctly and the submitted data missed a
        limit -- an AssertionError is the measurement working, not a fault.
        "environment" for a GPU or memory fault, which a rerun can clear.
        "verifier" for anything else: the verifier crashed on input it should
        have handled, so a rerun reproduces it and the code needs the fix. The
        known case is `ValueError: cost matrix is infeasible`, raised by
        linear_sum_assignment when every variable pairing costs inf.
    """
    if exception == "AssertionError":
        return "agent"
    if any(marker in exception or marker in message
           for marker in _ENVIRONMENT_MARKERS):
        return "environment"
    return "verifier"


def pytest_failures(verifier_dir):
    """Failing tests for one trial, with the cause of each.

    Args:
        verifier_dir: directory holding test-stdout.txt.

    Returns:
        list of (test_name, category, "Exception: message") where category is
        from classify_failure(). Empty when the file is absent or nothing failed.
    """
    stdout_path = os.path.join(verifier_dir, "test-stdout.txt")
    if not os.path.exists(stdout_path):
        return []
    try:
        with open(stdout_path, errors="ignore") as f:
            text = f.read()
    except OSError:
        return []
    failures = []
    for nodeid, exception, message in _PYTEST_FAILED_RE.findall(text):
        failures.append((nodeid.split("::")[-1],
                         classify_failure(exception, message),
                         f"{exception}: {message.strip()[:60]}"))
    return failures


def rerun_reasons(verifier_dir, metrics, task_is_supervised):
    """Split this trial's problems into ones a rerun fixes and ones it does not.

    The gate on both is metrics still missing AND a cause worth acting on.
    Either half alone is misleading: a trial can fail a test and be repaired
    afterwards by one of the rerun_*.py backfills, and a trial can be missing
    metrics simply because the task has no reference solution to compare against.

    Args:
        verifier_dir: the trial's verifier directory.
        metrics: parsed metrics.json, or None if absent or unreadable.
        task_is_supervised: whether the task ships reference_stats_full.json.
            test_data_stats legitimately skips without one, recording nothing.

    Returns:
        (rerun, bugs), both list[str] of human-readable reasons.
        `rerun` is recoverable by resubmitting the verifier: a GPU or memory
        fault, or a run that never finished. `bugs` is not -- the verifier
        crashed on input it should have handled, so a rerun reproduces it and
        the fix belongs in the code.
    """
    if not os.path.exists(os.path.join(verifier_dir, "ctrf.json")):
        return ["pytest never finished (no ctrf.json)"], []
    if metrics is None:
        return ["metrics.json missing or unparseable"], []
    if "required_files_missing" not in metrics:
        return ["pytest wrote nothing (judges-only metrics.json)"], []

    rerun, bugs = [], []
    for test, category, detail in pytest_failures(verifier_dir):
        if category == "agent":
            continue          # the verifier worked; this is the result, not a fault
        if not task_is_supervised and test in ("test_data_stats", "test_decoder_accuracy"):
            continue          # nothing to compare against, so nothing to recover
        still_missing = [key for key in TEST_METRICS.get(test, ())
                         if key not in metrics or metrics[key] is None]
        if not still_missing:
            # A later backfill already supplied what this test failed to record,
            # so there is nothing to recover even though ctrf still says failed.
            continue
        target = rerun if category == "environment" else bugs
        target.append(f"{test}: {detail} -> missing {', '.join(still_missing)}")
    return rerun, bugs


def check_verifier_dir(verifier_dir, verbose=False, label=None):
    """Check a verifier directory for valid metrics.json and judge results.
    Returns (ok: bool, issues: list[str])."""
    label = label or verifier_dir
    issues = []

    metrics_path = os.path.join(verifier_dir, "metrics.json")
    if not os.path.exists(metrics_path):
        if verbose:
            print(f"{label} missing metrics.json")
        issues.append("no metrics.json")
        return False, issues

    try:
        metrics = parse_metrics_json(metrics_path)
    except (json.JSONDecodeError, Exception) as e:
        if verbose:
            print(f"{label} has bad metrics.json: {e}")
        issues.append(f"bad metrics.json: {e}")
        return False, issues

    issues.extend(judge_issues(verifier_dir, metrics, verbose=verbose, label=label))
    return len(issues) == 0, issues


def find_trajectory_step_numbers(trial_path, patterns):
    """Find step numbers in trajectory.json containing each pattern.
    Returns dict {pattern: [step_numbers]}.
    """
    traj_path = os.path.join(trial_path, "agent", "trajectory.json")
    result = {p: [] for p in patterns}
    if not os.path.exists(traj_path):
        return result
    try:
        with open(traj_path) as f:
            d = json.load(f)
    except Exception:
        return result
    steps = d.get("steps", [])
    for i, s in enumerate(steps):
        msg = s.get("message", "")
        if not isinstance(msg, str):
            continue
        for p in patterns:
            if p in msg:
                result[p].append(i)
    return result


def find_claude_event_step(trial_path, event_type, predicate=None):
    """For events in claude-code.txt that don't appear in trajectory.json
    (e.g. rate_limit_event), find the trajectory step that immediately
    precedes them by looking up the most recent tool_use id.

    predicate: optional callable taking the parsed event dict; only events
    where predicate(event) is True are returned.

    Returns a list of (trajectory_step_number, total_steps, event_dict) for each occurrence.
    """
    claude_path = os.path.join(trial_path, "agent", "claude-code.txt")
    traj_path = os.path.join(trial_path, "agent", "trajectory.json")
    if not os.path.exists(claude_path) or not os.path.exists(traj_path):
        return []
    try:
        traj = json.load(open(traj_path))
    except Exception:
        return []
    total_steps = len(traj.get("steps", []))

    # Build a map from tool_use_id -> trajectory step number
    tool_to_step = {}
    for i, s in enumerate(traj.get("steps", [])):
        tool_calls = s.get("tool_calls")
        if not tool_calls:
            continue
        for m in re.finditer(r"toolu_[A-Za-z0-9]+", str(tool_calls)):
            tool_to_step[m.group()] = i

    # Walk through claude-code.txt; track most recent tool_use id;
    # when we hit the target event, record the step
    results = []
    last_tool_id = None
    try:
        with open(claude_path, errors="ignore") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                t = d.get("type")
                if t == "assistant":
                    msg = d.get("message", {})
                    if isinstance(msg, dict):
                        for c in msg.get("content", []):
                            if isinstance(c, dict) and c.get("type") == "tool_use":
                                last_tool_id = c.get("id")
                elif t == event_type:
                    if predicate and not predicate(d):
                        continue
                    step = tool_to_step.get(last_tool_id) if last_tool_id else None
                    results.append((step, total_steps, d))
    except Exception:
        pass
    return results


def check_agent_usage_limit(trial_path, verbose=False):
    """Check the agent log for API usage/auth limit hits.
    Returns a list of issues found (each a string), empty list if none.
    """
    agent_dir = os.path.join(trial_path, "agent")
    if not os.path.isdir(agent_dir):
        return []

    issues = []

    # codex.txt
    codex_path = os.path.join(agent_dir, "codex.txt")
    if os.path.exists(codex_path):
        try:
            with open(codex_path, errors="ignore") as f:
                content = f.read()
        except Exception:
            content = ""
        if '"type":"turn.failed"' in content and "usage limit" in content:
            issues.append("codex: usage limit (fatal)")
            if verbose:
                steps = find_trajectory_step_numbers(trial_path, ["usage limit"])
                step_str = ""
                if steps["usage limit"]:
                    step_str = f" at step(s) {steps['usage limit']}"
                print(f"Trial {trial_path} codex hit fatal usage limit{step_str}")
        elif "usage limit" in content:
            issues.append("codex: usage limit warning")
            if verbose:
                steps = find_trajectory_step_numbers(trial_path, ["usage limit"])
                step_str = ""
                if steps["usage limit"]:
                    step_str = f" at step(s) {steps['usage limit']}"
                print(f"Trial {trial_path} codex usage limit warning{step_str}")

    # claude-code.txt
    claude_path = os.path.join(agent_dir, "claude-code.txt")
    if os.path.exists(claude_path):
        try:
            with open(claude_path, errors="ignore") as f:
                content = f.read()
        except Exception:
            content = ""
        n_401 = content.count("Failed to authenticate. API Error: 401")
        if n_401 > 0:
            traj_steps = find_trajectory_step_numbers(
                trial_path,
                ["Failed to authenticate. API Error: 401"],
            )
            traj = json.load(open(os.path.join(trial_path, "agent", "trajectory.json"))) \
                if os.path.exists(os.path.join(trial_path, "agent", "trajectory.json")) else {"steps": []}
            total_steps = len(traj.get("steps", []))
            issues.append(f"claude: auth failed 401 ({n_401}x)")
            if verbose:
                s = traj_steps["Failed to authenticate. API Error: 401"]
                step_str = f" at step(s) {s}/{total_steps}" if s else ""
                print(f"Trial {trial_path} claude hit {n_401} auth failures{step_str}")

        # Check for actual rate-limit blocks: status="rejected" means the API
        # refused the request. status="allowed_warning" is suppressed because
        # the agent itself is never told about it (it only goes to the SDK
        # output stream / REPL UI), so it can't affect agent behavior.
        # status="allowed" with overageStatus="rejected" is also suppressed
        # (purely informational about extra-usage funding).
        real_blocks = find_claude_event_step(
            trial_path,
            "rate_limit_event",
            predicate=lambda d: d.get("rate_limit_info", {}).get("status") == "rejected",
        )
        if real_blocks:
            issues.append(f"claude: rate limit rejected ({len(real_blocks)}x)")
            if verbose:
                print(f"Trial {trial_path} claude was rate-limit rejected {len(real_blocks)} times:")
                for step, total, ev in real_blocks:
                    loc = f"~step {step+1}/{total}" if step is not None else f"~start/{total}"
                    print(f"  {loc}:")
                    for line in json.dumps(ev, indent=2).split("\n"):
                        print(f"    {line}")

    return issues


def check_unsupervised_judges(verifier_dir, verbose=False, label=None):
    """Check unsupervised judge results in metrics.json.
    Returns (ok: bool, issues: list[str])."""
    label = label or verifier_dir
    issues = []

    # If judge_unsupervised dir doesn't exist, the unsupervised judges were
    # never run for this trial — return "not run" rather than flagging missing
    # files as errors.
    judge_unsup_dir = os.path.join(verifier_dir, "judge_unsupervised")
    if not os.path.isdir(judge_unsup_dir):
        return False, ["not run"]

    metrics_path = os.path.join(verifier_dir, "metrics.json")
    if not os.path.exists(metrics_path):
        issues.append("no metrics.json")
        return False, issues

    try:
        metrics = parse_metrics_json(metrics_path)
    except (json.JSONDecodeError, Exception) as e:
        issues.append(f"bad metrics.json: {e}")
        return False, issues

    # Check for unsupervised judge keys
    for model in ["claude", "codex"]:
        err = metrics.get(f"llm_judge_{model}_unsupervised_error", "")
        eval_path = os.path.join(verifier_dir, "judge_unsupervised", model, "llm_judge_eval.json")
        if err:
            issues.append(f"{model} unsupervised error")
            if verbose:
                print(f"{label} has {model} unsupervised judge error: {err}")
        if not os.path.exists(eval_path):
            issues.append(f"{model} unsupervised no llm_judge_eval.json")
            if verbose:
                print(f"{label} missing {model} unsupervised llm_judge_eval.json")

    return len(issues) == 0, issues


def check_trial(trial_path, task_has_unsupervised=False, verbose=False,
                task_is_supervised=True):
    """Check a single trial directory. Returns a dict of health info."""
    result = {
        "path": trial_path,
        "agent_ran": False,
        "agent_issue": None,
        "agent_warnings": [],  # non-fatal warnings (rate limits, transient auth errors)
        # Per-artifact state, separate from agent_ran so the summary can show which
        # specific file is missing rather than a single pass/fail.
        "has_convert_py": False,   # verifier/snapshot/convert_data.py
        "has_converted_pkl": False,  # verifier/snapshot/converted_data.pkl
        "no_snapshot": False,      # snapshot dir absent entirely -- unrecoverable
        "verifier_ran": False,
        "verifier_issues": [],
        "unsupervised_ran": None,  # None = not applicable
        "unsupervised_issues": [],
        "failures": [],        # (test, cause, "Exception: msg") for each failing test
        "rerun_reasons": [],   # non-empty when rerunning the verifier would help
        "verifier_bugs": [],   # verifier crashed on input it should have handled
    }

    verifier_dir = os.path.join(trial_path, "verifier")
    if not os.path.isdir(verifier_dir):
        if verbose:
            print(f"Trial {trial_path} missing verifier dir")
        result["agent_issue"] = "no verifier dir"
        result["verifier_issues"].append("no verifier dir")
        return result

    # Agent check: which of the agent's outputs made it into the snapshot?
    # A missing snapshot DIRECTORY is called out separately from a missing file: with
    # no snapshot there is no converted_data.pkl to re-read, so rerun_verifier.sh and
    # rerun_metrics.py can do nothing and the trial has to be run again from scratch.
    snapshot_dir = os.path.join(verifier_dir, "snapshot")
    if not os.path.isdir(snapshot_dir):
        result["no_snapshot"] = True
        result["agent_issue"] = "no snapshot dir"
        if verbose:
            print(f"Trial {trial_path} has no verifier/snapshot/")
    else:
        result["has_convert_py"] = os.path.exists(
            os.path.join(snapshot_dir, "convert_data.py"))
        result["has_converted_pkl"] = os.path.exists(
            os.path.join(snapshot_dir, "converted_data.pkl"))
        # agent_ran keeps its original meaning -- produced converted_data.pkl -- so the
        # existing per-trial rows and counters are unaffected by the new fields.
        result["agent_ran"] = result["has_converted_pkl"]
        missing = [n for n, ok in (("convert_data.py", result["has_convert_py"]),
                                   ("converted_data.pkl", result["has_converted_pkl"]))
                   if not ok]
        if missing:
            result["agent_issue"] = "no " + ", ".join(missing)
            if verbose:
                print(f"Trial {trial_path} missing {', '.join(missing)}")

    # Check for usage/auth limit hits in agent log
    limit_issues = check_agent_usage_limit(trial_path, verbose=verbose)
    if limit_issues:
        if not result["agent_ran"]:
            # Agent failed AND had limit issues — those are likely the cause
            extra = "; ".join(limit_issues)
            if result["agent_issue"]:
                result["agent_issue"] = f"{result['agent_issue']}; {extra}"
            else:
                result["agent_issue"] = extra
        else:
            # Agent ran successfully but had limit warnings — surface as warnings
            result["agent_warnings"] = limit_issues

    ok, issues = check_verifier_dir(verifier_dir, verbose=verbose, label=f"Trial {trial_path}")
    result["verifier_ran"] = ok
    result["verifier_issues"] = issues

    # Split the verifier's two halves so the summary can show them separately: pytest
    # writing a parseable metrics.json, and the two judges producing their verdicts.
    # They fail independently and for unrelated reasons -- an API quota kills the
    # judges while pytest is fine -- so a single combined column hid which half broke.
    metrics_path = os.path.join(verifier_dir, "metrics.json")
    metrics = None
    if os.path.exists(metrics_path):
        try:
            metrics = parse_metrics_json(metrics_path)
        except Exception:
            metrics = None
    result["metrics_ok"] = metrics is not None
    # Unknown, not False, when metrics.json is unreadable: the error fields live in it,
    # so there is no basis to judge the judges.
    result["judges_ok"] = (
        not judge_issues(verifier_dir, metrics) if metrics is not None else None
    )

    # Did pytest run at all? test_required_files_exist is the first test in the file
    # and records required_files_missing before anything expensive happens, so its
    # absence means pytest contributed nothing to this metrics.json -- the file is
    # then purely what compute_reward.py merged in from the judges afterwards.
    result["pytest_ok"] = (
        "required_files_missing" in metrics if metrics is not None else None
    )

    # Did the decoder actually produce a result? metrics.json existing is not enough:
    # pytest writes its metrics incrementally, and compute_reward.py merges the judge
    # scores in afterwards, independently. So a run whose pytest died early still
    # leaves a parseable metrics.json holding nothing but llm_judge_* keys -- which
    # looked healthy here while contributing nothing to any figure.
    #
    # Three states, because they mean different things:
    #   missing  the test never ran (pytest died first, or no converted_data.pkl)
    #   None     it ran and failed -- test_decoder_accuracy sets None up front and
    #            only overwrites it once training and scoring succeed
    #   dict     per-output accuracies, the only healthy case
    if metrics is None:
        result["decoder_ok"] = None
        result["decoder_issue"] = None
    elif "validation_balanced_accuracy" not in metrics:
        result["decoder_ok"] = False
        result["decoder_issue"] = "no validation_balanced_accuracy (test never ran)"
    elif not metrics["validation_balanced_accuracy"]:
        result["decoder_ok"] = False
        result["decoder_issue"] = "validation_balanced_accuracy is null (decoder failed)"
    else:
        result["decoder_ok"] = True
        result["decoder_issue"] = None

    # Why the verifier fell over, and whether rerunning it would help. decoder_ok
    # and pytest_ok say a metric is missing; these say whose fault that was, which
    # is what decides between resubmitting the job and recording the result.
    result["failures"] = pytest_failures(verifier_dir)
    result["rerun_reasons"], result["verifier_bugs"] = rerun_reasons(
        verifier_dir, metrics, task_is_supervised)
    if verbose and result["rerun_reasons"]:
        print(f"Trial {trial_path} needs a rerun:")
        for reason in result["rerun_reasons"]:
            print(f"    {reason}")

    # Check unsupervised judges if applicable
    if task_has_unsupervised:
        ok, issues = check_unsupervised_judges(
            verifier_dir, verbose=verbose, label=f"Trial {trial_path}"
        )
        result["unsupervised_ran"] = ok
        result["unsupervised_issues"] = issues

    return result


def find_reruns(trial_path):
    """Find verifier_rerun_* directories, return list of (path, is_merged) sorted newest first."""
    reruns = []
    for d in sorted(glob.glob(os.path.join(trial_path, "verifier_rerun_*")), reverse=True):
        if not os.path.isdir(d):
            continue
        is_merged = d.endswith("_merged")
        reruns.append((d, is_merged))
    return reruns


def check_rerun(rerun_path, verbose=False):
    """Check a verifier_rerun_* directory."""
    ok, issues = check_verifier_dir(rerun_path, verbose=verbose, label=f"Rerun {rerun_path}")
    return {
        "path": rerun_path,
        "verifier_ran": ok,
        "verifier_issues": issues,
    }


def discover_trials(job_dirs, skip_oracle=False):
    """Find all trial directories across job_dirs. Returns dict keyed by
    (task, agent_normalized, timestamp, trial_num) -> (trial_path, source_label).
    Prefers earlier directories in the list (first one wins for duplicate keys)."""
    trials = {}
    for jobdir in job_dirs:
        jobdir = os.path.expanduser(jobdir)
        if not os.path.isdir(jobdir):
            continue
        for trial_path in sorted(glob.glob(os.path.join(jobdir, "*", "*", "20*_trial*/"))):
            trial_path = trial_path.rstrip("/")
            rel = os.path.relpath(trial_path, jobdir)
            parts = rel.split(os.sep)
            if len(parts) < 3:
                continue
            task, agent, ts = parts[0], parts[1], parts[2]
            if skip_oracle and agent == "oracle":
                continue
            # Normalize agent name
            agent_norm = "claude" if agent in ("claude", "claude-code") else agent
            # Extract trial number and timestamp
            m = re.search(r"trial(\d+)", ts)
            trial_num = m.group(1) if m else "?"
            timestamp = ts.split("_trial")[0] if "_trial" in ts else ts
            key = (task, agent_norm, timestamp, trial_num)
            if key not in trials:
                source_label = os.path.basename(jobdir)
                trials[key] = (trial_path, source_label)
    return trials


def main():
    parser = argparse.ArgumentParser(description="Check harbor trial health")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)
    # The two analysis trees. Results are split across them -- harbor-jobs holds the
    # archive (on /nearline), harbor-jobs-new everything collected from the cluster --
    # so scanning only one hides whole arms: every terminus trial lives in the latter.
    default_dirs = [
        os.path.join(repo_dir, "harbor-jobs"),
        os.path.join(repo_dir, "harbor-jobs-new"),
    ]
    parser.add_argument(
        "--job-dirs",
        nargs="+",
        default=default_dirs,
        help="Directories to scan for trials",
    )
    parser.add_argument(
        "--no-oracle",
        action="store_true",
        default=True,
        help="Skip oracle trials (default: True)",
    )
    parser.add_argument(
        "--include-oracle",
        action="store_true",
        help="Include oracle trials",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only show the summary table, not per-trial details",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show more detailed output (currently no-op)",
    )
    parser.add_argument(
        "--needs-rerun",
        action="store_true",
        help="Print only the trials whose verifier should be rerun, one path per "
             "line, for piping into submit_rerun_verifier.sh",
    )
    args = parser.parse_args()
    skip_oracle = not args.include_oracle

    trials = discover_trials(args.job_dirs, skip_oracle=skip_oracle)
    if not trials:
        print("No trials found.")
        sys.exit(1)

    # Determine which tasks have unsupervised judge instructions
    tasks_with_unsupervised = set()
    harbor_tasks_dir = os.path.join(repo_dir, "harbor-tasks")
    for key in trials:
        task = key[0]
        unsup_path = os.path.join(harbor_tasks_dir, task, "tests", "judge_instructions_unsupervised.md")
        if os.path.exists(unsup_path):
            tasks_with_unsupervised.add(task)

    # Tasks with a reference solution. Without reference_stats_full.json,
    # test_data_stats skips and test_decoder_accuracy records no ratio, so their
    # metrics are absent by design and must not be read as something to recover.
    supervised_tasks = {
        task for task in {key[0] for key in trials}
        if os.path.exists(os.path.join(harbor_tasks_dir, task, "tests",
                                       "reference_stats_full.json"))
    }

    # Check each trial
    results = {}
    rerun_results = {}  # key -> list of (rerun_path, is_merged, health)
    for key in sorted(trials.keys()):
        trial_path, source = trials[key]
        task = key[0]
        health = check_trial(
            trial_path,
            task_has_unsupervised=task in tasks_with_unsupervised,
            verbose=args.verbose,
            task_is_supervised=task in supervised_tasks,
        )
        health["source"] = source
        results[key] = health

        # Check reruns
        reruns = find_reruns(trial_path)
        if reruns:
            rerun_results[key] = []
            for rerun_path, is_merged in reruns:
                rh = check_rerun(rerun_path, verbose=args.verbose)
                rh["is_merged"] = is_merged
                rerun_results[key].append((rerun_path, rh))

    # --needs-rerun is meant to be piped, so it prints paths and nothing else.
    if args.needs_rerun:
        for key in sorted(results):
            if results[key]["rerun_reasons"]:
                print(results[key]["path"])
        return

    # Trials worth resubmitting, and why. Printed before the tables because it is
    # the actionable part: an AssertionError is a result to keep, while a CUDA
    # fault or a killed run is a measurement that never happened.
    needs_rerun = {k: v for k, v in results.items() if v["rerun_reasons"]}
    if needs_rerun:
        print("=" * 78)
        print(f"NEEDS RERUN ({len(needs_rerun)} of {len(results)} trials)")
        print("=" * 78)
        for key in sorted(needs_rerun):
            print(f"  {needs_rerun[key]['path']}")
            for reason in needs_rerun[key]["rerun_reasons"]:
                print(f"      {reason}")
        print()

    # Failures the verifier measured correctly. Counted rather than listed: these
    # are the benchmark's results, not its problems.
    # Crashes a rerun cannot fix: the verifier itself needs the repair.
    has_bugs = {k: v for k, v in results.items() if v["verifier_bugs"]}
    if has_bugs:
        print("=" * 78)
        print(f"VERIFIER BUGS ({len(has_bugs)} trials) -- rerunning reproduces these")
        print("=" * 78)
        for key in sorted(has_bugs):
            print(f"  {has_bugs[key]['path']}")
            for reason in has_bugs[key]["verifier_bugs"]:
                print(f"      {reason}")
        print()

    n_agent_failures = sum(
        1 for health in results.values()
        for _test, cause, _detail in health["failures"] if cause == "agent"
    )
    print(f"{n_agent_failures} assertion failures across {len(results)} trials "
          f"(agent results, not faults)\n")

    # Detect duplicate (task, agent, trial_num) combinations across timestamps,
    # so we can disambiguate them in the per-trial label.
    label_counts = {}
    for k in results:
        task, agent, _ts, trial_num = k
        label_counts[(task, agent, trial_num)] = label_counts.get((task, agent, trial_num), 0) + 1

    # Per-trial output
    if not args.summary_only:
        col_widths = [42, 25, 30, 30, 12]
        col_aligns = ["<", "<", "<", "<", "<"]
        total_width = sum(col_widths) + 2 * (len(col_widths) - 1)
        print("=" * total_width)
        print_wrapped_row(
            ["Trial", "Agent", "Verifier", "Unsupervised", "Source"],
            col_widths, col_aligns,
        )
        print("-" * total_width)
        for key in sorted(results.keys()):
            task, agent, ts, trial_num = key
            h = results[key]
            if label_counts.get((task, agent, trial_num), 0) > 1:
                # Disambiguate with timestamp
                label = f"{task}/{agent}/{ts}_trial{trial_num}"
            else:
                label = f"{task}/{agent}/trial{trial_num}"
            if h["agent_ran"]:
                if h["agent_warnings"]:
                    agent_str = "OK* — " + "; ".join(h["agent_warnings"])
                else:
                    agent_str = "OK"
            else:
                agent_str = h["agent_issue"]
            verifier_str = "OK" if h["verifier_ran"] else "; ".join(h["verifier_issues"])
            if h["unsupervised_ran"] is None:
                unsup_str = "—"
            elif h["unsupervised_ran"]:
                unsup_str = "OK"
            elif h["unsupervised_issues"] == ["not run"]:
                unsup_str = "not run"
            else:
                unsup_str = "; ".join(h["unsupervised_issues"])
            print_wrapped_row(
                [label, agent_str, verifier_str, unsup_str, h["source"]],
                col_widths, col_aligns,
            )
            # Show unmerged reruns only
            if key in rerun_results:
                for rerun_path, rh in rerun_results[key]:
                    if rh["is_merged"]:
                        continue
                    rerun_name = os.path.basename(rerun_path)
                    rv_str = "OK" if rh["verifier_ran"] else "; ".join(rh["verifier_issues"])
                    print_wrapped_row(
                        [f"  └ {rerun_name}", "", rv_str, "", ""],
                        col_widths, col_aligns,
                    )
        print()

    # Summary table: by task, show claude and codex columns
    tasks = sorted(set(k[0] for k in results))
    # Derived, not hardcoded: a fixed ["claude", "codex"] silently omitted the whole
    # terminus-opus and terminus-gpt arms once those runs started.
    agents = sorted(set(k[1] for k in results))

    # Gather counts
    counts = {}  # (task, agent) -> {n, agent_ok, verifier_ok, ...}
    for key, h in results.items():
        task, agent, ts, trial_num = key
        ta = (task, agent)
        if ta not in counts:
            counts[ta] = {
                "n": 0,
                "agent_ok": 0,
                "convert_py_ok": 0,
                "no_snapshot": 0,
                "verifier_ok": 0,
                "metrics_ok": 0,
                "judges_ok": 0,
                "pytest_ok": 0,
                "decoder_ok": 0,
                "unsupervised_ok": 0,
                "unsupervised_applicable": 0,
                "reruns_unmerged": 0,
                "reruns_ok": 0,
                "agent_issues": [],
                "verifier_issues": [],
            }
        c = counts[ta]
        c["n"] += 1
        if h["has_convert_py"]:
            c["convert_py_ok"] += 1
        if h["no_snapshot"]:
            c["no_snapshot"] += 1
            # Unrecoverable, so name the trial rather than only counting it.
            c["agent_issues"].append(f"trial{trial_num}: NO SNAPSHOT (unrecoverable)")
        if h["agent_ran"]:
            c["agent_ok"] += 1
            # agent_ran only tracks the pickle, so a missing script would otherwise be
            # invisible on a trial that is otherwise fine.
            if not h["has_convert_py"]:
                c["agent_issues"].append(f"trial{trial_num}: no convert_data.py")
        elif not h["no_snapshot"]:
            c["agent_issues"].append(f"trial{trial_num}: {h['agent_issue']}")
        if h["agent_warnings"]:
            c["agent_issues"].append(
                f"trial{trial_num} warning: {'; '.join(h['agent_warnings'])}"
            )
        if h["verifier_ran"]:
            c["verifier_ok"] += 1
        else:
            c["verifier_issues"].append(f"trial{trial_num} verifier: {'; '.join(h['verifier_issues'])}")
        if h.get("metrics_ok"):
            c["metrics_ok"] += 1
        if h.get("judges_ok"):
            c["judges_ok"] += 1
        if h.get("pytest_ok"):
            c["pytest_ok"] += 1
        elif h.get("pytest_ok") is False:
            c["verifier_issues"].append(
                f"trial{trial_num}: pytest wrote nothing (judges only)")
        if h.get("decoder_ok"):
            c["decoder_ok"] += 1
        elif h.get("decoder_issue"):
            c["verifier_issues"].append(f"trial{trial_num}: {h['decoder_issue']}")
        # Unsupervised
        if h["unsupervised_ran"] is not None:
            # Skip "not run" — task supports unsupervised but this trial hasn't been processed
            if h["unsupervised_issues"] == ["not run"]:
                pass
            else:
                c["unsupervised_applicable"] += 1
                if h["unsupervised_ran"]:
                    c["unsupervised_ok"] += 1
                else:
                    c["verifier_issues"].append(
                        f"trial{trial_num} unsupervised: {'; '.join(h['unsupervised_issues'])}"
                    )
        # Count unmerged reruns
        if key in rerun_results:
            for rerun_path, rh in rerun_results[key]:
                if not rh["is_merged"]:
                    c["reruns_unmerged"] += 1
                    if rh["verifier_ran"]:
                        c["reruns_ok"] += 1
                    else:
                        rerun_name = os.path.basename(rerun_path)
                        c["verifier_issues"].append(
                            f"trial{trial_num} rerun({rerun_name}): {'; '.join(rh['verifier_issues'])}"
                        )

    # Agent names are now derived, and terminus-opus / terminus-gpt are 13 chars, so the
    # agent column is sized for them rather than for "codex".
    # Task column fits the longest name (hasnain2024_minimal, 19); agent fits
    # terminus-opus (13). Both used to be sized for the shortest names and wrapped.
    sum_widths = [20, 14, 9, 9, 8, 9, 8, 8, 12, 7, 26]
    sum_aligns = ["<", "<", ">", ">", ">", ">", ">", ">", ">", ">", "<"]
    sum_total = sum(sum_widths) + 2 * (len(sum_widths) - 1)
    print("=" * sum_total)
    print("Summary")
    print("=" * sum_total)
    print_wrapped_row(
        ["Task", "Agent", "convert.py", "data.pkl", "metrics", "req_files", "judges",
         "val_acc", "Unsupervised", "Reruns", "Notes"],
        sum_widths, sum_aligns,
    )
    print("-" * sum_total)
    for task in tasks:
        first = True
        for agent in agents:
            ta = (task, agent)
            task_col = task if first else ""
            if ta not in counts:
                print_wrapped_row(
                    [task_col, agent, "—", "—", "—", "—", "—", "—", "—", "—", ""],
                    sum_widths, sum_aligns,
                )
            else:
                c = counts[ta]
                convert_str = f"{c['convert_py_ok']}/{c['n']}"
                agent_str = f"{c['agent_ok']}/{c['n']}"
                metrics_str = f"{c['metrics_ok']}/{c['n']}"
                judges_str = f"{c['judges_ok']}/{c['n']}"
                pytest_str = f"{c['pytest_ok']}/{c['n']}"
                decoder_str = f"{c['decoder_ok']}/{c['n']}"
                if c["unsupervised_applicable"] > 0:
                    unsup_str = f"{c['unsupervised_ok']}/{c['unsupervised_applicable']}"
                else:
                    unsup_str = "—"
                if c["reruns_unmerged"] > 0:
                    rerun_str = f"{c['reruns_ok']}/{c['reruns_unmerged']}"
                else:
                    rerun_str = "—"
                notes = []
                notes.extend(c["agent_issues"])
                notes.extend(c["verifier_issues"])
                notes_str = "; ".join(notes) if notes else ""
                print_wrapped_row(
                    [task_col, agent, convert_str, agent_str, metrics_str, pytest_str,
                     judges_str, decoder_str, unsup_str, rerun_str, notes_str],
                    sum_widths, sum_aligns,
                )
            first = False
    print()


if __name__ == "__main__":
    main()
