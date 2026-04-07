#!/usr/bin/env python3
"""
Check the health of harbor trial runs.

For each trial, checks:
  - Agent ran: converted_data.pkl exists in verifier/snapshot/
  - Verifier ran: metrics.json is valid JSON, and both claude and codex judges
    produced llm_judge_eval.json without errors

Usage:
    python check_trial_health.py [--job-dirs DIR [DIR ...]] [--no-oracle] [--summary-only]

Defaults to scanning:
    ~/harbor-tasks/data-format/jobs
    <repo>/harbor-jobs
"""

import argparse
import json
import os
import glob
import re
import sys
from collections import defaultdict
from pathlib import Path


def parse_metrics_json(path):
    """Parse a metrics.json that may contain NaN/Infinity."""
    with open(path) as f:
        txt = f.read()
    txt = re.sub(r"\bNaN\b", "null", txt)
    txt = re.sub(r"(?<!\w)-?Infinity\b", "null", txt)
    # trailing commas
    txt = re.sub(r",(\s*[}\]])", r"\1", txt)
    return json.loads(txt)


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

    for model in ["claude", "codex"]:
        err = metrics.get(f"llm_judge_{model}_error", "")
        eval_path = os.path.join(verifier_dir, "judge", model, "llm_judge_eval.json")
        if err:
            issues.append(f"{model} judge error")
            if verbose:
                print(f"{label} has {model} judge error: {err}")
        if not os.path.exists(eval_path):
            issues.append(f"{model} no llm_judge_eval.json")
            if verbose:
                print(f"{label} missing {model} llm_judge_eval.json")

    return len(issues) == 0, issues


def check_unsupervised_judges(verifier_dir, verbose=False, label=None):
    """Check unsupervised judge results in metrics.json.
    Returns (ok: bool, issues: list[str])."""
    label = label or verifier_dir
    issues = []

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
    has_any = False
    for model in ["claude", "codex"]:
        err = metrics.get(f"llm_judge_{model}_unsupervised_error", "")
        reward = metrics.get(f"llm_judge_{model}_unsupervised_reward")
        eval_path = os.path.join(verifier_dir, "judge_unsupervised", model, "llm_judge_eval.json")
        if err:
            has_any = True
            issues.append(f"{model} unsupervised error")
            if verbose:
                print(f"{label} has {model} unsupervised judge error: {err}")
        elif reward is not None:
            has_any = True
        if not os.path.exists(eval_path):
            issues.append(f"{model} unsupervised no llm_judge_eval.json")
            if verbose:
                print(f"{label} missing {model} unsupervised llm_judge_eval.json")
        else:
            has_any = True

    if not has_any:
        issues.append("no unsupervised results")
        return False, issues

    return len(issues) == 0, issues


def check_trial(trial_path, task_has_unsupervised=False, verbose=False):
    """Check a single trial directory. Returns a dict of health info."""
    result = {
        "path": trial_path,
        "agent_ran": False,
        "agent_issue": None,
        "verifier_ran": False,
        "verifier_issues": [],
        "unsupervised_ran": None,  # None = not applicable
        "unsupervised_issues": [],
    }

    verifier_dir = os.path.join(trial_path, "verifier")
    if not os.path.isdir(verifier_dir):
        if verbose:
            print(f"Trial {trial_path} missing verifier dir")
        result["agent_issue"] = "no verifier dir"
        result["verifier_issues"].append("no verifier dir")
        return result

    # Agent check: did it produce converted_data.pkl?
    pkl_path = os.path.join(verifier_dir, "snapshot", "converted_data.pkl")
    if os.path.exists(pkl_path):
        result["agent_ran"] = True
    else:
        if verbose:
            print(f"Trial {trial_path} missing converted_data.pkl")
        result["agent_issue"] = "no converted_data.pkl"

    ok, issues = check_verifier_dir(verifier_dir, verbose=verbose, label=f"Trial {trial_path}")
    result["verifier_ran"] = ok
    result["verifier_issues"] = issues

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
    (task, agent_normalized, trial_num) -> (trial_path, source_label).
    Prefers earlier directories in the list (first one wins)."""
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
            # Extract trial number
            m = re.search(r"trial(\d+)", ts)
            trial_num = m.group(1) if m else "?"
            key = (task, agent_norm, trial_num)
            if key not in trials:
                source_label = os.path.basename(jobdir)
                trials[key] = (trial_path, source_label)
    return trials


def main():
    parser = argparse.ArgumentParser(description="Check harbor trial health")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)
    default_dirs = [
        os.path.expanduser("~/harbor-tasks/data-format/jobs"),
        os.path.join(repo_dir, "harbor-jobs"),
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

    # Per-trial output
    if not args.summary_only:
        print("=" * 140)
        print(f"{'Trial':<45s}  {'Agent':>7s}  {'Verifier':<25s}  {'Unsupervised':<25s}  {'Source'}")
        print("-" * 140)
        for key in sorted(results.keys()):
            task, agent, trial_num = key
            h = results[key]
            label = f"{task}/{agent}/trial{trial_num}"
            agent_str = "OK" if h["agent_ran"] else h["agent_issue"]
            verifier_str = "OK" if h["verifier_ran"] else "; ".join(h["verifier_issues"])
            if h["unsupervised_ran"] is None:
                unsup_str = "—"
            elif h["unsupervised_ran"]:
                unsup_str = "OK"
            else:
                unsup_str = "; ".join(h["unsupervised_issues"])
            print(f"{label:<45s}  {agent_str:>7s}  {verifier_str:<25s}  {unsup_str:<25s}  {h['source']}")
            # Show unmerged reruns only
            if key in rerun_results:
                for rerun_path, rh in rerun_results[key]:
                    if rh["is_merged"]:
                        continue
                    rerun_name = os.path.basename(rerun_path)
                    rv_str = "OK" if rh["verifier_ran"] else "; ".join(rh["verifier_issues"])
                    print(f"  └ {rerun_name:<52s}  {rv_str}")
        print()

    # Summary table: by task, show claude and codex columns
    tasks = sorted(set(k[0] for k in results))
    agents = ["claude", "codex"]

    # Gather counts
    counts = {}  # (task, agent) -> {n, agent_ok, verifier_ok, ...}
    for key, h in results.items():
        task, agent, trial_num = key
        ta = (task, agent)
        if ta not in counts:
            counts[ta] = {
                "n": 0,
                "agent_ok": 0,
                "verifier_ok": 0,
                "unsupervised_ok": 0,
                "unsupervised_applicable": 0,
                "reruns_unmerged": 0,
                "reruns_ok": 0,
                "agent_issues": [],
                "verifier_issues": [],
            }
        c = counts[ta]
        c["n"] += 1
        if h["agent_ran"]:
            c["agent_ok"] += 1
        else:
            c["agent_issues"].append(f"trial{trial_num}: {h['agent_issue']}")
        if h["verifier_ran"]:
            c["verifier_ok"] += 1
        else:
            c["verifier_issues"].append(f"trial{trial_num} verifier: {'; '.join(h['verifier_issues'])}")
        # Unsupervised
        if h["unsupervised_ran"] is not None:
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

    print("=" * 140)
    print("Summary")
    print("=" * 140)
    print(
        f"{'Task':<15s}  {'Agent':<10s}  {'Agent ran':>12s}  {'Verifier ran':>14s}  {'Unsupervised':>14s}  {'Reruns':>10s}  Notes"
    )
    print("-" * 140)
    for task in tasks:
        first = True
        for agent in agents:
            ta = (task, agent)
            if ta not in counts:
                task_col = task if first else ""
                print(f"{task_col:<15s}  {agent:<10s}  {'—':>12s}  {'—':>14s}  {'—':>14s}  {'—':>10s}")
            else:
                c = counts[ta]
                task_col = task if first else ""
                agent_str = f"{c['agent_ok']}/{c['n']}"
                verifier_str = f"{c['verifier_ok']}/{c['n']}"
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
                print(
                    f"{task_col:<15s}  {agent:<10s}  {agent_str:>12s}  {verifier_str:>14s}  {unsup_str:>14s}  {rerun_str:>10s}  {notes_str}"
                )
            first = False
    print()


if __name__ == "__main__":
    main()
