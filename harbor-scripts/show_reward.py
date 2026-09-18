#!/usr/bin/env python3
"""Print a trial's reward from its verifier directory, for the status and rerun scripts.

A trial's reward lives in one of two files, and which one depends on when the trial ran:

    reward.json   written by tests/write_reward_file.py (current tasks). Its "reward" is
                  the mean of outcome_all (pytest pass/fail), outcome_mean_per_category
                  and, when the judges ran, process.
    reward.txt    written by older tasks' tests/test.sh: pytest pass/fail alone, 1 or 0.

reward.json wins when both exist, matching harbor's own precedence. One helper rather
than a copy in each caller, so the precedence and the key names are decided in one place.
Used by check_status.sh, run_harbor.sh, rerun_verifier.sh and merge_rerun_verifier.sh.

Usage:
    show_reward.py <verifier_dir>            one-line summary, or "N/A"
    show_reward.py --value <verifier_dir>    the reward number only, or nothing (exit 1)
"""

import argparse
import json
import pathlib
import sys

# Name of the pass/fail key in reward.json, and the name it had in the earliest
# reward.json files written during terminal-bench-science development.
OUTCOME_KEYS = ("outcome_all", "outcome")


def read_reward(verifier_dir):
    """Read the reward for one trial.

    Args:
        verifier_dir: str or Path, a trial's verifier directory (holding reward.json
            and/or reward.txt).

    Returns:
        dict or None. None when neither file exists or neither parses. Otherwise a dict
        with keys:
            'source'        str, 'reward.json' or 'reward.txt'
            'reward'        float, the trial's reward
            'outcome_all'   float or None, pytest pass/fail (1.0 / 0.0)
            'per_category'  float or None, mean of the per-category outcome scores
            'process'       float or None, mean of the LLM judges' scores; None when the
                            judges were switched off or did not finish
    """
    verifier_dir = pathlib.Path(verifier_dir)
    json_path = verifier_dir / "reward.json"
    txt_path = verifier_dir / "reward.txt"
    try:
        if json_path.is_file():
            rewards = json.loads(json_path.read_text())
            outcome = next((rewards[k] for k in OUTCOME_KEYS if k in rewards), None)
            return {
                "source": "reward.json",
                "reward": float(rewards["reward"]),
                "outcome_all": outcome,
                "per_category": rewards.get("outcome_mean_per_category"),
                "process": rewards.get("process"),
            }
        if txt_path.is_file():
            value = float(txt_path.read_text().strip())
            return {"source": "reward.txt", "reward": value, "outcome_all": value,
                    "per_category": None, "process": None}
    except (ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"show_reward.py: could not read reward in {verifier_dir}: {error}",
              file=sys.stderr)
    return None


def format_summary(reward):
    """One-line summary of a read_reward() result.

    Args:
        reward: dict from read_reward, or None.

    Returns:
        str, e.g. "0.5900 (outcome_all=0.0; per_category=0.4170; process=0.7650)", or
        "N/A" when there is no reward.
    """
    if reward is None:
        return "N/A"
    if reward["source"] == "reward.txt":
        return f"{reward['reward']:.4f} (reward.txt: pass/fail only)"
    parts = []
    if reward["outcome_all"] is not None:
        parts.append(f"outcome_all={reward['outcome_all']:.1f}")
    if reward["per_category"] is not None:
        parts.append(f"per_category={reward['per_category']:.4f}")
    parts.append(f"process={reward['process']:.4f}" if reward["process"] is not None
                 else "no process score: judges off or did not finish")
    return f"{reward['reward']:.4f} ({'; '.join(parts)})"


def main():
    """Parse arguments and print. Exit status 1 when --value finds no reward."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("verifier_dir", help="a trial's verifier directory")
    parser.add_argument("--value", action="store_true",
                        help="print only the reward number (nothing, and exit 1, if absent)")
    args = parser.parse_args()

    reward = read_reward(args.verifier_dir)
    if args.value:
        if reward is None:
            sys.exit(1)
        print(f"{reward['reward']:.4f}")
    else:
        print(format_summary(reward))


if __name__ == "__main__":
    main()
