"""Summarize supervised-judge ratings across harbor trials.

Produces two CSVs in this directory:
  supervised_judge_summary.csv
      One row per (task, agent, trial, judge, category). "ratings" is the
      semicolon-joined list of decision_correctness values for every question
      matching that category; "n_questions" is len(ratings).

  supervised_decoder_accuracy.csv
      One row per (task, agent, trial, output_variable). balanced_accuracy,
      reference, ratio come from metrics.json validation_balanced_accuracy*.
"""

import csv
import glob
import json
import os
import re
from collections import defaultdict

HARBOR_ROOT = "/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-jobs"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Tasks that have both judge/ and judge_unsupervised/ — confirmed supervised.
SUPERVISED_TASKS = ["allen2p", "lee2025", "majnik2025", "sosa2024"]

# All harbor-jobs tasks (supervised + unsupervised-only) that have judge outputs.
ALL_TASKS = [
    "allen2p", "hasnain2024", "lee2025", "majnik2025",
    "map", "mouseland", "sosa2024", "zhang2025",
]

MODES = {
    # "supervised": the 4 tasks that have a manual solution, use judge/ which is
    # the judge that received the manual reference. Metric rows (data counts,
    # decoder accuracy) are meaningful here because a reference is available.
    "supervised": {
        "tasks": SUPERVISED_TASKS,
        "judge_subdir": {t: "judge" for t in SUPERVISED_TASKS},
        "show_metrics": True,
    },
    # "unsupervised": all 8 tasks. For supervised tasks use judge_unsupervised/
    # (same judge, but given no manual reference); for unsupervised-only tasks
    # the only judge output is judge/ which is already unsupervised. Metric
    # rows are hidden because there is no reference to compare against for the
    # unsupervised-only tasks.
    "unsupervised": {
        "tasks": ALL_TASKS,
        "judge_subdir": {
            **{t: "judge_unsupervised" for t in SUPERVISED_TASKS},
            **{t: "judge" for t in ALL_TASKS if t not in SUPERVISED_TASKS},
        },
        "show_metrics": False,
    },
}

# Some tasks have accidentally-duplicated question blocks. Drop the duplicates
# here so each concept is counted once per trial.
DUPLICATE_QIDS_TO_DROP = {
    "lee2025": {
        "5-a",                    # duplicates 2-e (temporal resolution)
        "8",                      # duplicates 6 (minor-issues / bad-data handling)
        "9-a", "9-b", "9-c", "9-d",  # duplicate 7-a..d (code efficiency block)
    },
}


def is_duplicate(task: str, qid: str) -> bool:
    return qid in DUPLICATE_QIDS_TO_DROP.get(task, set())

# Canonical ordering of the category rows (order of columns in the final table).
CATEGORIES = [
    "Data loading - Overall",
    "Data loading - Split into subjects",
    "Data loading - Split into sessions",
    "Data loading - Split into trials",
    "Data loading - Trial filtering",
    "Neural data - Source variables",
    "Neural data - Processing",
    "Neural data - Filtering",
    "Neural data - Alignment",
    "Neural data - Temporal resolution",
    "Decoder inputs - Source variables",
    "Decoder inputs - Processing",
    "Decoder inputs - Thresholding",
    "Decoder inputs - Alignment",
    "Outputs - Source variables",
    "Outputs - Processing",
    "Outputs - Thresholding",
    "Outputs - Alignment",
    "Bad data handling",
    "Code efficiency",
]


def classify(qid: str, text: str) -> str | None:
    """Return category name for this question, or None if it doesn't fit."""
    t = text.lower()

    # 1-* / 2-* are deterministic by ID.
    fixed = {
        "1-a": "Data loading - Overall",
        "1-b": "Data loading - Split into subjects",
        "1-c": "Data loading - Split into sessions",
        "1-d": "Data loading - Split into trials",
        "1-e": "Data loading - Trial filtering",
        "2-a": "Neural data - Source variables",
        "2-b": "Neural data - Processing",
        "2-c": "Neural data - Filtering",
        "2-d": "Neural data - Alignment",
        "2-e": "Neural data - Temporal resolution",
    }
    if qid in fixed:
        return fixed[qid]

    # Free-floating "missing data / minor issues" questions.
    if "minor mistakes" in t or "minor issues" in t:
        return "Bad data handling"

    # Code efficiency 4-question group.
    if (
        "time-consuming" in t
        or "vectorized" in t
        or "repeat multiple times" in t
        or "repeats multiple times" in t
        or "unnecessary processing" in t
    ):
        return "Code efficiency"

    # Stray temporal-resolution and cross-stream alignment questions.
    if "temporal resolution" in t:
        return "Neural data - Temporal resolution"
    if "neural, input, and output" in t and "temporally aligned" in t:
        return "Neural data - Alignment"

    # Per-variable input/output questions. Parent depends on "input" vs "output"
    # keyword in the question text; sub-category depends on phrasing.
    is_input = "`input`" in text or " input " in t
    is_output = "`output`" in text or " output " in t

    if "derived from" in t:
        sub = "Source variables"
    elif "processing is involved" in t:
        sub = "Processing"
    elif "thresholded into categories" in t:
        sub = "Thresholding"
    elif "aligned with the neural data" in t:
        sub = "Alignment"
    else:
        return None

    if is_input and not is_output:
        return f"Decoder inputs - {sub}"
    if is_output and not is_input:
        return f"Outputs - {sub}"
    return None


def is_bad_trial(trial_name: str) -> bool:
    """Skip trials the user has marked as failed reruns."""
    return "badtrial" in trial_name.lower()


def iter_trials(tasks):
    """Yield (task, agent, trial_name, trial_dir) for every trial in the given tasks."""
    for task in tasks:
        task_dir = os.path.join(HARBOR_ROOT, task)
        if not os.path.isdir(task_dir):
            continue
        for agent in sorted(os.listdir(task_dir)):
            if agent == "oracle":
                continue
            agent_dir = os.path.join(task_dir, agent)
            if not os.path.isdir(agent_dir):
                continue
            for trial_name in sorted(os.listdir(agent_dir)):
                if is_bad_trial(trial_name):
                    continue
                trial_dir = os.path.join(agent_dir, trial_name)
                if not os.path.isdir(trial_dir):
                    continue
                yield task, agent, trial_name, trial_dir


def load_judge(trial_dir: str, judge_subdir: str, judge: str):
    path = os.path.join(trial_dir, "verifier", judge_subdir, judge, "llm_judge_eval.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def build_rating_rows(mode: str):
    cfg = MODES[mode]
    rows = []
    unclassified = []
    for task, agent, trial_name, trial_dir in iter_trials(cfg["tasks"]):
        judge_subdir = cfg["judge_subdir"][task]
        for judge in ("claude", "codex"):
            data = load_judge(trial_dir, judge_subdir, judge)
            if data is None:
                continue
            by_category = defaultdict(list)
            for qid, q in data.items():
                if is_duplicate(task, qid):
                    continue
                cat = classify(qid, q.get("question", ""))
                if cat is None:
                    unclassified.append((task, agent, trial_name, judge, qid, q.get("question", "")[:120]))
                    continue
                rating = q.get("decision_correctness", "")
                by_category[cat].append(rating)
            for cat in CATEGORIES:
                ratings = by_category.get(cat, [])
                rows.append(
                    {
                        "task": task,
                        "agent": agent,
                        "trial": trial_name,
                        "judge": judge,
                        "category": cat,
                        "ratings": ";".join(ratings),
                        "n_questions": len(ratings),
                    }
                )
    return rows, unclassified


def build_decoder_rows(mode: str):
    """Emit per-output rows, joining submitted names to reference names via the
    fuzzy `output_matches` / `input_matches` lists in metrics.json (ratios and
    reference values are keyed on reference names, not submitted names).
    """
    rows = []
    for task, agent, trial_name, trial_dir in iter_trials(MODES[mode]["tasks"]):
        mpath = os.path.join(trial_dir, "verifier", "metrics.json")
        if not os.path.exists(mpath):
            continue
        with open(mpath) as f:
            m = json.load(f)
        acc = m.get("validation_balanced_accuracy")
        ref = m.get("validation_balanced_accuracy_reference") or {}
        ratio = m.get("validation_balanced_accuracy_ratio") or {}
        if not isinstance(acc, dict) or not acc:
            continue

        # submitted_name -> (reference_name, cost) from fuzzy matcher.
        sub_to_ref = {}
        for entry in (m.get("output_matches") or []) + (m.get("input_matches") or []):
            sub = entry.get("submitted")
            if sub:
                sub_to_ref[sub] = (entry.get("reference"), entry.get("cost"))

        for var, val in acc.items():
            ref_name, cost = sub_to_ref.get(var, (None, None))
            # Fall back to exact name match if the fuzzy matcher wasn't run.
            if ref_name is None and var in ref:
                ref_name = var
            rows.append(
                {
                    "task": task,
                    "agent": agent,
                    "trial": trial_name,
                    "output_variable": var,
                    "reference_variable": ref_name or "",
                    "match_cost": "" if cost is None else cost,
                    "balanced_accuracy": val,
                    "reference": ref.get(ref_name, "") if ref_name else "",
                    "ratio": ratio.get(ref_name, "") if ref_name else "",
                }
            )
    return rows


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=list(MODES), default="supervised",
                    help="which judge output to summarize (default: supervised)")
    args = ap.parse_args()
    mode = args.mode

    rating_rows, unclassified = build_rating_rows(mode)
    decoder_rows = build_decoder_rows(mode)

    rating_path = os.path.join(OUT_DIR, f"{mode}_judge_summary.csv")
    with open(rating_path, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["task", "agent", "trial", "judge", "category", "ratings", "n_questions"],
        )
        w.writeheader()
        w.writerows(rating_rows)

    decoder_path = os.path.join(OUT_DIR, f"{mode}_decoder_accuracy.csv")
    with open(decoder_path, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "task",
                "agent",
                "trial",
                "output_variable",
                "reference_variable",
                "match_cost",
                "balanced_accuracy",
                "reference",
                "ratio",
            ],
        )
        w.writeheader()
        w.writerows(decoder_rows)

    print(f"Wrote {len(rating_rows)} rating rows to {rating_path}")
    print(f"Wrote {len(decoder_rows)} decoder rows to {decoder_path}")
    if unclassified:
        print(f"\nWARNING: {len(unclassified)} unclassified questions:")
        for u in unclassified[:20]:
            print(" ", u)


if __name__ == "__main__":
    main()
