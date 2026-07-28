#!/usr/bin/env python3
"""Rebuild agent/trajectory.json for trials where harbor's converter failed.

Harbor converts an agent's raw session files into an ATIF trajectory during
post-run processing. That conversion can fail while the trial itself succeeds --
the failure is only printed, never raised -- leaving a complete trial with no
trajectory.json. The judges read that file optionally, so the trial is still
scored; the loss is the agent's reasoning in parseable form.

The known cause is a step-numbering bug in harbor: events it cannot map are
skipped, but the skip still consumed a step_id, leaving a gap that ATIF's
"sequential from 1" validator rejects. That is fixed in the vendored harbor at
codepacks/harbor-kai; this script re-runs the (now fixed) converter over session
files that were preserved in the trial output, so trajectories can be recovered
without re-running the agents.

Usage:
    python rebuild_trajectories.py --jobs-root DIR [DIR ...] [--dry-run]
    python rebuild_trajectories.py --trial TRIAL_DIR
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Map the agent directory name used in trial output to harbor's agent class.
# Trial layout is <task>/<agent>/<timestamp>_trialN/. Older runs in harbor-jobs
# wrote the Claude agent as "claude" while newer ones write "claude-code", so
# both must map to the same class -- the same normalisation check_trial_health.py
# does. "oracle" runs the reference solution rather than an LLM, so it has no
# session to convert and is deliberately absent.
AGENT_CLASSES = {
    "claude": ("harbor.agents.installed.claude_code", "ClaudeCode"),
    "claude-code": ("harbor.agents.installed.claude_code", "ClaudeCode"),
    "codex": ("harbor.agents.installed.codex", "Codex"),
}


def find_session_dir(agent_dir: Path) -> Path | None:
    """Locate the directory holding the agent's raw session files.

    Harbor's converter globs ``*.jsonl`` non-recursively, so it needs the exact
    directory, not an ancestor. Claude Code nests these several levels down
    (agent/sessions/projects/-app/), and the depth differs by agent, so search
    for whichever directory actually contains .jsonl files.

    Args:
        agent_dir: the trial's agent/ directory.

    Returns:
        Path to the directory containing the most .jsonl files, or None if the
        session files did not survive (nothing to recover from).
    """
    candidates: dict[Path, int] = {}
    for f in agent_dir.rglob("*.jsonl"):
        candidates[f.parent] = candidates.get(f.parent, 0) + 1
    if not candidates:
        return None
    return max(candidates.items(), key=lambda kv: kv[1])[0]


def model_name_for(trial_dir: Path) -> str:
    """Read the model this trial's agent ran, from harbor's trial config.

    The converter uses self.model_name as the fallback when a step carries no
    model of its own, so it should match what actually ran rather than a guess.

    Args:
        trial_dir: the trial directory containing config.json.

    Returns:
        The model name, or "unknown" if config.json is missing or unparseable.
    """
    try:
        cfg = json.loads((trial_dir / "config.json").read_text())
        return cfg.get("agent", {}).get("model_name") or "unknown"
    except (OSError, json.JSONDecodeError, AttributeError):
        return "unknown"


def rebuild(trial_dir: Path, dry_run: bool = False) -> str:
    """Rebuild trajectory.json for one trial.

    Args:
        trial_dir: .../<task>/<agent>/<timestamp>_trialN/
        dry_run: report what would happen without writing.

    Returns:
        A one-line status string describing the outcome.
    """
    agent_dir = trial_dir / "agent"
    out_path = agent_dir / "trajectory.json"
    if out_path.exists():
        return "already has trajectory.json"

    agent_name = trial_dir.parent.name
    if agent_name == "oracle":
        # The oracle runs the reference solution, not an LLM, so there is no
        # session and no trajectory is expected. Not a failure.
        return "oracle -- no agent session, nothing to convert"
    if agent_name not in AGENT_CLASSES:
        return f"unknown agent {agent_name!r}"

    session_dir = find_session_dir(agent_dir)
    if session_dir is None:
        return "no session .jsonl files -- not recoverable"

    module_path, class_name = AGENT_CLASSES[agent_name]
    module = __import__(module_path, fromlist=[class_name])
    cls = getattr(module, class_name)

    # Build a bare instance: __init__ wants the full run configuration, but the
    # converter only needs a handful of methods plus these two attributes.
    agent = cls.__new__(cls)
    agent.model_name = model_name_for(trial_dir)
    agent._version = None  # Codex reads this; None means "unpinned", as at run time

    try:
        trajectory = agent._convert_events_to_trajectory(session_dir)
    except Exception as exc:  # noqa: BLE001 - report, don't abort the whole sweep
        return f"conversion failed: {type(exc).__name__}: {exc}"
    if trajectory is None:
        return "converter returned None (no usable events)"

    n_steps = len(getattr(trajectory, "steps", []) or [])
    if dry_run:
        return f"would write {n_steps} steps"

    out_path.write_text(
        json.dumps(trajectory.to_json_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return f"wrote {n_steps} steps -> {out_path.name}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jobs-root", nargs="*", type=Path, default=[],
                        help="scan these roots for trials missing trajectory.json")
    parser.add_argument("--trial", type=Path, default=None,
                        help="rebuild a single trial directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="report without writing")
    args = parser.parse_args()

    if args.trial:
        trials = [args.trial]
    else:
        trials = []
        for root in args.jobs_root:
            # Both layouts: cluster adds a per-job level above <task>/<agent>/.
            for pattern in ("*/*/*/*_trial*", "*/*/*_trial*"):
                trials.extend(p for p in sorted(root.glob(pattern)) if p.is_dir())
    if not trials:
        parser.error("nothing to do: pass --trial or --jobs-root")

    n_written = 0
    for trial in trials:
        if (trial / "agent" / "trajectory.json").exists():
            continue
        status = rebuild(trial, dry_run=args.dry_run)
        label = "/".join(trial.parts[-4:])
        print(f"  {label}\n      {status}")
        if status.startswith(("wrote", "would write")):
            n_written += 1

    print(f"\n{'would rebuild' if args.dry_run else 'rebuilt'}: {n_written}")


if __name__ == "__main__":
    main()
