"""Backfill pytest-produced metrics from trial snapshots.

When a trial's pytest metrics (ratios, matches, decoder accuracy) were wiped by
the old merge_rerun_verifier.sh (which copied the rerun's empty metrics.json
on top of the original), we can still recover them from the snapshot:

  * verifier/snapshot/converted_data.pkl  -> counts, ranges, fractions
  * verifier/snapshot/train_decoder_full_out.txt  -> per-output accuracy
  * harbor-tasks/<task>/tests/reference_stats_full.json  -> reference

This script reads each trial, recomputes what it can, and MERGES into the
existing metrics.json (leaving judge keys untouched). Run without args for a
dry run; pass --write to actually modify files.

Usage:
    conda activate decoder-data-format
    python backfill_metrics.py            # dry-run, prints summary
    python backfill_metrics.py --write    # actually write metrics.json
    python backfill_metrics.py --write --only sosa2024     # single task
"""

import argparse
import difflib
import json
import os
import pickle
import re
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from summarize_judges import SUPERVISED_TASKS, is_bad_trial

REPO = Path("/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format")
DEFAULT_HARBOR_JOBS = REPO / "harbor-jobs"
HARBOR_TASKS = REPO / "harbor-tasks"


# ---------------------------------------------------------------------------
# Stats from converted_data.pkl (replicates print_data_summary from decoder.py).
# ---------------------------------------------------------------------------

def compute_stats(data: dict) -> dict:
    nsessions = len(data["neural"])
    ntrials_per = [len(data["neural"][s]) for s in range(nsessions)]

    dinput = data["input"][0][0].shape[0]
    doutput = data["output"][0][0].shape[0]

    mean_T, min_T, max_T, nneurons = [], [], [], []
    input_range, output_range = [], []
    unique_outputs = [set() for _ in range(doutput)]

    def _per_trial_lo_hi(trials):
        """Return (min-per-dim, max-per-dim) across trials. Supports 1D (per-trial
        scalar per dim) and 2D (dim x time) trial arrays."""
        los, his = [], []
        for t in trials:
            if np.ndim(t) == 1:
                los.append(t)
                his.append(t)
            else:
                los.append(t.min(axis=1))
                his.append(t.max(axis=1))
        return np.min(los, axis=0), np.max(his, axis=0)

    for s in range(nsessions):
        Ts = [trial.shape[-1] if np.ndim(trial) >= 2 else 1 for trial in data["neural"][s]]
        mean_T.append(float(np.mean(Ts)))
        min_T.append(int(np.min(Ts)))
        max_T.append(int(np.max(Ts)))
        nneurons.append(int(data["neural"][s][0].shape[0]))

        in_lo, in_hi = _per_trial_lo_hi(data["input"][s])
        input_range.append((in_lo, in_hi))
        out_lo, out_hi = _per_trial_lo_hi(data["output"][s])
        output_range.append((out_lo, out_hi))

        for trial in data["output"][s]:
            for i in range(doutput):
                if np.ndim(trial) == 1:
                    unique_outputs[i].add(float(trial[i]))
                else:
                    unique_outputs[i].update(np.unique(trial[i, :]).tolist())

    unique_outputs = [sorted(x) for x in unique_outputs]
    bin_edges = []
    for i in range(doutput):
        centers = np.array(unique_outputs[i], dtype=float)
        edges = np.concatenate([[-np.inf], (centers[:-1] + centers[1:]) / 2, [np.inf]])
        bin_edges.append(edges)

    total_hist = [np.zeros(len(x)) for x in unique_outputs]
    for s in range(nsessions):
        for trial in data["output"][s]:
            for i in range(doutput):
                if np.ndim(trial) == 1:
                    idx = unique_outputs[i].index(float(trial[i]))
                    total_hist[i][idx] += 1
                else:
                    counts, _ = np.histogram(trial[i, :], bins=bin_edges[i])
                    total_hist[i] += counts
    total_frac = [h / max(1, h.sum()) for h in total_hist]

    input_range_all = (
        np.min([r[0] for r in input_range], axis=0),
        np.max([r[1] for r in input_range], axis=0),
    )
    output_range_all = (
        np.min([r[0] for r in output_range], axis=0),
        np.max([r[1] for r in output_range], axis=0),
    )

    return {
        "nsessions": nsessions,
        "ntrials_total": int(sum(ntrials_per)),
        "dinput": dinput,
        "doutput": doutput,
        "T_median": float(np.median(mean_T)),
        "nsubjects": len(data.get("subjects", [])),
        "nneurons_mean": float(np.mean(nneurons)),
        "nneurons_total": int(nsessions * float(np.mean(nneurons))),
        "input_names": list(data["input_names"]),
        "output_names": list(data["output_names"]),
        "input_range": {
            data["input_names"][i]: [float(input_range_all[0][i]), float(input_range_all[1][i])]
            for i in range(dinput)
        },
        "output_range": {
            data["output_names"][i]: [float(output_range_all[0][i]), float(output_range_all[1][i])]
            for i in range(doutput)
        },
        "output_fractions": {
            data["output_names"][i]: {str(v): float(f) for v, f in zip(unique_outputs[i], total_frac[i])}
            for i in range(doutput)
        },
    }


# ---------------------------------------------------------------------------
# Fuzzy name matching. Exact name match first; otherwise use a string similarity
# + (optionally) range/fraction constraints, then Hungarian assignment. This is
# deliberately simpler than the sentence-transformers version in test_outputs.py;
# the intent is to recover "reasonable" reference->submitted mappings for
# rerun-wiped trials.
# ---------------------------------------------------------------------------

def _name_similarity(a: str, b: str) -> float:
    """Similarity in [0, 1]; 1 = identical."""
    a = a.replace("_", " ").replace("-", " ").lower()
    b = b.replace("_", " ").replace("-", " ").lower()
    return difflib.SequenceMatcher(None, a, b).ratio()


def match_names(
    sub_ranges: dict,
    ref_ranges: dict,
    sub_fracs: dict | None = None,
    ref_fracs: dict | None = None,
    exact_range: bool = False,
    weight_semantic: float = 0.95,
):
    sub_names = list(sub_ranges.keys())
    ref_names = list(ref_ranges.keys())
    n = len(ref_names)
    if n != len(sub_names):
        return [(rn, None, float("inf")) for rn in ref_names], [float("inf")] * n

    cost = np.full((n, n), np.inf) if exact_range else np.zeros((n, n))
    for i, rn in enumerate(ref_names):
        for j, sn in enumerate(sub_names):
            if rn == sn:
                cost[i, j] = 0.0
                continue
            sim = _name_similarity(rn, sn)
            cost_sem = 1.0 - sim
            if exact_range:
                rlo, rhi = ref_ranges[rn]
                slo, shi = sub_ranges[sn]
                if rlo != slo or rhi != shi:
                    continue
                rf = sorted((ref_fracs or {}).get(rn, {}).values())
                sf = sorted((sub_fracs or {}).get(sn, {}).values())
                if len(rf) != len(sf) or not rf:
                    continue
                cost_fracs = float(np.sum(np.abs(np.array(rf) - np.array(sf))))
                cost[i, j] = cost_fracs * (1 - weight_semantic) + cost_sem * weight_semantic
            else:
                rlo, rhi = ref_ranges[rn]
                slo, shi = sub_ranges[sn]
                scale = max(abs(rhi - rlo), 1e-6)
                cost_range = max(abs(rlo - slo) / scale, abs(rhi - shi) / scale)
                cost[i, j] = cost_range * (1 - weight_semantic) + cost_sem * weight_semantic

    # Replace inf with a very large finite value so linear_sum_assignment runs.
    cost_finite = np.where(np.isinf(cost), 1e9, cost)
    row_ind, col_ind = linear_sum_assignment(cost_finite)
    matches = []
    match_costs = []
    for r, c in zip(row_ind, col_ind):
        cst = float(cost[r, c]) if np.isfinite(cost[r, c]) else float("inf")
        matches.append((ref_names[r], sub_names[c], cst))
        match_costs.append(cst)
    return matches, match_costs


# ---------------------------------------------------------------------------
# Parse train_decoder_full_out.txt for per-output validation accuracy.
# ---------------------------------------------------------------------------

_ACC_RE = re.compile(r"^\s*\d+\s*\(([^)]+)\):\s*([0-9.]+)")


def parse_validation_accuracy(path: Path) -> dict | None:
    if not path.exists():
        return None
    lines = path.read_text(errors="replace").splitlines()
    in_block = False
    found = {}
    for ln in lines:
        if "Validation Balanced Accuracy Scores" in ln:
            in_block = True
            continue
        if in_block:
            m = _ACC_RE.match(ln)
            if m:
                found[m.group(1)] = float(m.group(2))
            elif ln.strip() == "" and found:
                break
    return found or None


# ---------------------------------------------------------------------------
# Per-trial backfill.
# ---------------------------------------------------------------------------

def backfill_trial(task: str, trial_dir: Path, ref_stats: dict, harbor_jobs: Path, write: bool) -> dict:
    """Returns a report dict describing what was added / what's missing."""
    report = {"trial": str(trial_dir.relative_to(harbor_jobs)), "added": [], "skipped": []}

    snap = trial_dir / "verifier" / "snapshot"
    pkl = snap / "converted_data.pkl"
    if not pkl.exists():
        report["skipped"].append("no converted_data.pkl")
        return report

    with open(pkl, "rb") as f:
        data = pickle.load(f)
    stats = compute_stats(data)

    metrics_path = trial_dir / "verifier" / "metrics.json"
    try:
        with open(metrics_path) as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {}

    ref_ds = ref_stats["data_summary"]
    # inject nneurons_total into ref_ds like the test fixture does
    if "nneurons_total" not in ref_ds:
        ref_ds["nneurons_total"] = ref_ds["nsessions"] * ref_ds["nneurons_mean"]

    patch = {}
    # Count ratios.
    for field in ["nsessions", "ntrials_total", "T_median", "nsubjects", "nneurons_total"]:
        sub_v = stats.get(field)
        ref_v = ref_ds.get(field)
        if sub_v is None or ref_v is None or ref_v == 0:
            continue
        patch[f"{field}_ratio"] = float(sub_v) / float(ref_v)

    # Input / output matching + range errors + fraction errors.
    input_matches, input_costs = match_names(
        stats["input_range"], ref_ds["input_range"], exact_range=False,
    )
    patch["input_range_mean_cost"] = float(np.mean(input_costs)) if input_costs else 0.0
    patch["input_matches"] = [
        {"reference": r, "submitted": s, "cost": c} for r, s, c in input_matches
    ]
    for r, s, _ in input_matches:
        if s is None or r not in ref_ds["input_range"] or s not in stats["input_range"]:
            continue
        rlo, rhi = ref_ds["input_range"][r]
        slo, shi = stats["input_range"][s]
        patch[f"input_range_error_{r}"] = float(max(abs(rlo - slo), abs(rhi - shi)))

    output_matches, output_costs = match_names(
        stats["output_range"], ref_ds["output_range"],
        stats["output_fractions"], ref_ds["output_fractions"],
        exact_range=True,
    )
    patch["output_fraction_mean_cost"] = float(np.mean(output_costs)) if output_costs else 0.0
    patch["output_matches"] = [
        {"reference": r, "submitted": s, "cost": c} for r, s, c in output_matches
    ]
    for r, s, _ in output_matches:
        if s is None or r not in ref_ds["output_range"] or s not in stats["output_range"]:
            continue
        rlo, rhi = ref_ds["output_range"][r]
        slo, shi = stats["output_range"][s]
        patch[f"output_range_error_{r}"] = float(max(abs(rlo - slo), abs(rhi - shi)))
        rf = sorted(ref_ds["output_fractions"][r].values())
        sf = sorted(stats["output_fractions"][s].values())
        if len(rf) == len(sf):
            patch[f"output_fraction_error_{r}"] = float(np.sum(np.abs(np.array(rf) - np.array(sf))))
        else:
            patch[f"output_fraction_error_{r}"] = None

    # Decoder accuracy from train_decoder log (if available).
    val_accs = parse_validation_accuracy(snap / "train_decoder_full_out.txt")
    if val_accs:
        # Remap submitted names -> reference names using output_matches.
        sub_to_ref = {s: r for r, s, _ in output_matches if s is not None}
        ref_acc = ref_stats.get("validation_balanced_accuracy") or {}
        patch["validation_balanced_accuracy"] = dict(val_accs)
        patch["validation_balanced_accuracy_reference"] = dict(ref_acc)
        ratio = {}
        for sub_name, acc in val_accs.items():
            ref_name = sub_to_ref.get(sub_name, sub_name)
            if ref_name in ref_acc and ref_acc[ref_name]:
                ratio[ref_name] = float(acc) / float(ref_acc[ref_name])
        patch["validation_balanced_accuracy_ratio"] = ratio
    else:
        report["skipped"].append("no train_decoder_full_out.txt (decoder accuracy not backfilled)")

    # Note what's actually new (vs already present with non-None value).
    new_keys = [
        k for k, v in patch.items()
        if k not in existing or existing.get(k) in (None, {}, [])
    ]
    report["added"] = new_keys

    if write and patch:
        merged = dict(existing)
        merged.update(patch)
        with open(metrics_path, "w") as f:
            json.dump(merged, f, indent=2)

    return report


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

def iter_trials(harbor_jobs: Path, only: list[str] | None):
    tasks = only or SUPERVISED_TASKS
    for task in tasks:
        ref_path = HARBOR_TASKS / task / "tests" / "reference_stats_full.json"
        if not ref_path.exists():
            print(f"[skip] {task}: no reference_stats_full.json at {ref_path}")
            continue
        with open(ref_path) as f:
            ref_stats = json.load(f)
        task_dir = harbor_jobs / task
        if not task_dir.is_dir():
            continue
        for agent_dir in sorted(task_dir.iterdir()):
            if not agent_dir.is_dir() or agent_dir.name == "oracle":
                continue
            for trial_dir in sorted(agent_dir.iterdir()):
                if not trial_dir.is_dir() or is_bad_trial(trial_dir.name):
                    continue
                yield task, trial_dir, ref_stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="actually modify metrics.json files")
    ap.add_argument("--only", action="append", help="restrict to tasks (repeatable)")
    ap.add_argument(
        "--harbor-jobs",
        type=Path,
        default=DEFAULT_HARBOR_JOBS,
        help=f"root of job trees to backfill (default: {DEFAULT_HARBOR_JOBS})",
    )
    args = ap.parse_args()

    harbor_jobs = args.harbor_jobs.expanduser().resolve()
    print(f"Backfilling trials under {harbor_jobs}\n")
    n_trials = 0
    n_changed = 0
    for task, trial_dir, ref_stats in iter_trials(harbor_jobs, args.only):
        n_trials += 1
        report = backfill_trial(task, trial_dir, ref_stats, harbor_jobs, write=args.write)
        added = report["added"]
        skipped = report["skipped"]
        tag = "WRITE" if args.write and added else "DRY  " if added else "NOOP "
        print(f"[{tag}] {report['trial']}")
        if added:
            print(f"    +{len(added)} keys: {', '.join(sorted(added)[:6])}" +
                  (" ..." if len(added) > 6 else ""))
            n_changed += 1
        for s in skipped:
            print(f"    - {s}")

    verb = "wrote" if args.write else "would write"
    print(f"\nProcessed {n_trials} trials; {verb} {n_changed} files.")


if __name__ == "__main__":
    main()
