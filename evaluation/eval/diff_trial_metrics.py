#!/usr/bin/env python3
"""Compare two trial_metrics JSON files and report what actually changed.

Regenerating trial_metrics after a reference solution changes, a verifier is
re-run, or trials are added produces a file that differs from the old one in
thousands of insignificant ways -- float noise in the last decimal, key ordering --
and a handful of significant ones. `diff` cannot tell them apart. This can:

  * trials present only in the new file          (new runs)
  * trials present only in the old file          (deleted, renamed, or excluded)
  * per-trial field changes, with old and new value side by side:
      - ADDED    a field the old trial did not have. This is what an
                 unsupervised -> supervised conversion looks like: every
                 *_ratio, *_reference and matching field appears at once.
      - REMOVED  a field that is gone.
      - CHANGED  a value that moved by more than --tol.

Numbers within `--tol` (default 1e-4) are treated as unchanged, which suppresses
the noise: matching costs are computed from a sentence-transformer embedding and
are not bit-reproducible across machines, so they wander in the 7th decimal
between any two runs.

The two files may have different shapes. The older format nests
dataset -> agent -> trial; the current one inserts a prompt level,
dataset -> agent -> prompt -> trial. Both are flattened to the same key, with the
old format's trials treated as the "full" prompt -- correct, because that format
predates the minimal-prompt sweep.

Tasks that were renamed (chen2024 -> map, zhong2025 -> mouseland) would otherwise
show up as a whole task removed and another added. Pass --rename to pair them.

Usage:
    conda activate decoder-data-format
    python diff_trial_metrics.py trial_metrics.json trial_metrics_all.json
    python diff_trial_metrics.py OLD NEW --rename chen2024=map zhong2025=mouseland
    python diff_trial_metrics.py OLD NEW --tol 1e-6      # stricter
    python diff_trial_metrics.py OLD NEW --summary       # counts only, no per-field lines
    python diff_trial_metrics.py OLD NEW --dataset map   # restrict to one dataset
"""

import argparse
import json
import math
import sys
from pathlib import Path

# The prompt level is identified by its key names rather than by depth, so the same
# code reads both file shapes without being told which it has.
PROMPT_NAMES = {"full", "minimal", "maximal"}

DEFAULT_TOL = 1e-4


def flatten(data: dict) -> dict:
    """Flatten a trial_metrics tree to {(dataset, agent, prompt, trial): metrics}.

    Args:
        data: parsed trial_metrics JSON, either dataset->agent->trial->metrics or
            dataset->agent->prompt->trial->metrics.

    Returns:
        dict keyed by the 4-tuple; `prompt` is "full" for files that lack the level.
    """
    out = {}
    for dataset, by_agent in data.items():
        if not isinstance(by_agent, dict):
            continue
        for agent, level in by_agent.items():
            if not isinstance(level, dict):
                continue
            # With a prompt level, this dict's keys are prompt names; without one
            # they are trial numbers.
            if set(level) & PROMPT_NAMES:
                for prompt, by_trial in level.items():
                    for trial, metrics in (by_trial or {}).items():
                        out[(dataset, agent, prompt, str(trial))] = metrics
            else:
                for trial, metrics in level.items():
                    out[(dataset, agent, "full", str(trial))] = metrics
    return out


def value_diffs(old, new, tol: float, path: str = "") -> list:
    """Differences between two metric values, recursing into dicts and lists.

    Leaf numbers count as equal when they differ by no more than `tol`; bools are
    compared exactly, since `True == 1` would otherwise hide a type change.

    Args:
        old: value from the old file.
        new: value from the new file.
        tol: absolute tolerance for numeric leaves.
        path: dotted field path accumulated during recursion.

    Returns:
        list of (path, old_value, new_value). Empty when the values agree.
    """
    if isinstance(old, bool) or isinstance(new, bool):
        return [] if old is new else [(path, old, new)]

    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        if old is None or new is None:
            return [(path, old, new)]
        # NaN != NaN, so compare those by name rather than by value.
        if math.isnan(old) or math.isnan(new):
            return [] if math.isnan(old) and math.isnan(new) else [(path, old, new)]
        return [] if math.isclose(old, new, rel_tol=0.0, abs_tol=tol) else [(path, old, new)]

    if isinstance(old, dict) and isinstance(new, dict):
        diffs = []
        for k in sorted(set(old) | set(new)):
            sub = f"{path}.{k}" if path else str(k)
            if k not in old:
                diffs.append((sub, "<absent>", new[k]))
            elif k not in new:
                diffs.append((sub, old[k], "<absent>"))
            else:
                diffs.extend(value_diffs(old[k], new[k], tol, sub))
        return diffs

    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return [(path, f"list[{len(old)}]", f"list[{len(new)}]")]
        diffs = []
        for i, (a, b) in enumerate(zip(old, new)):
            diffs.extend(value_diffs(a, b, tol, f"{path}[{i}]"))
        return diffs

    return [] if old == new else [(path, old, new)]


def fmt(v) -> str:
    """Render a value for one-line display, shortening long containers."""
    if isinstance(v, float):
        return f"{v:.6g}"
    s = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
    return s if len(s) <= 70 else s[:67] + "..."


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", type=Path, help="baseline trial_metrics JSON")
    ap.add_argument("new", type=Path, help="regenerated trial_metrics JSON")
    ap.add_argument("--tol", type=float, default=DEFAULT_TOL,
                    help=f"absolute tolerance for numeric fields (default {DEFAULT_TOL})")
    ap.add_argument("--rename", nargs="*", default=[], metavar="OLD=NEW",
                    help="treat an old dataset name as its new one, e.g. chen2024=map")
    ap.add_argument("--dataset", nargs="*", default=None,
                    help="restrict the report to these datasets (new-file names)")
    ap.add_argument("--summary", action="store_true",
                    help="counts only, without the per-field lines")
    args = ap.parse_args()

    renames = dict(r.split("=", 1) for r in args.rename)

    old = flatten(json.loads(args.old.read_text()))
    new = flatten(json.loads(args.new.read_text()))
    if renames:
        old = {(renames.get(d, d), a, p, t): m for (d, a, p, t), m in old.items()}
    if args.dataset:
        keep = set(args.dataset)
        old = {k: v for k, v in old.items() if k[0] in keep}
        new = {k: v for k, v in new.items() if k[0] in keep}

    print(f"old: {args.old}  ({len(old)} trials)")
    print(f"new: {args.new}  ({len(new)} trials)")
    print(f"tolerance: {args.tol}" + (f"   renames: {renames}" if renames else ""))

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    common = sorted(set(old) & set(new))

    def label(k):
        d, a, p, t = k
        return f"{d}/{a}/{p}/trial{t}"

    print(f"\n=== TRIALS ONLY IN NEW ({len(added)}) ===")
    for k in added:
        print(f"  + {label(k)}   ({len(new[k])} fields)")
    print(f"\n=== TRIALS ONLY IN OLD ({len(removed)}) ===")
    for k in removed:
        print(f"  - {label(k)}   ({len(old[k])} fields)")

    n_changed_trials = 0
    n_added = n_removed = n_changed = 0
    print(f"\n=== FIELD CHANGES IN THE {len(common)} SHARED TRIALS ===")
    for k in common:
        diffs = value_diffs(old[k], new[k], args.tol)
        if not diffs:
            continue
        n_changed_trials += 1
        adds = [d for d in diffs if d[1] == "<absent>"]
        dels = [d for d in diffs if d[2] == "<absent>"]
        mods = [d for d in diffs if d[1] != "<absent>" and d[2] != "<absent>"]
        n_added += len(adds)
        n_removed += len(dels)
        n_changed += len(mods)
        if args.summary:
            print(f"  {label(k)}: +{len(adds)} added, -{len(dels)} removed, "
                  f"~{len(mods)} changed")
            continue
        print(f"\n  {label(k)}")
        for p, _, v in adds:
            print(f"      ADDED    {p:<44} -> {fmt(v)}")
        for p, v, _ in dels:
            print(f"      REMOVED  {p:<44}    {fmt(v)}")
        for p, a, b in mods:
            print(f"      CHANGED  {p:<44} {fmt(a)}  ->  {fmt(b)}")

    print(f"\n=== SUMMARY ===")
    print(f"  trials added:            {len(added)}")
    print(f"  trials removed:          {len(removed)}")
    print(f"  shared trials:           {len(common)}")
    print(f"  shared trials changed:   {n_changed_trials}")
    print(f"  fields added:            {n_added}")
    print(f"  fields removed:          {n_removed}")
    print(f"  fields changed:          {n_changed}")


if __name__ == "__main__":
    sys.exit(main())
