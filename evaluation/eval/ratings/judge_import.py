#!/usr/bin/env python3
"""
Copy LLM-judge results from a `data-format-experiments/` run into eval/.

The experiment tree is organized for running trials, not for analyzing them:

    data-format-experiments/<task>/<agent>/<timestamp>_trial<N>/verifier/
        judge/<judge>/llm_judge_eval.json          supervised (reference given)
        judge_unsupervised/<judge>/llm_judge_eval.json

and it uses the task names (`map`, `mouseland`) and agent names (`claude`) that
predate ours. This mirrors it into a flat, analysis-friendly layout:

    eval/<dataset>/judge_supervised/<agent>_trial<N>_<judge>-judge.json
    eval/<dataset>/judge_unsupervised/<agent>_trial<N>_<judge>-judge.json

e.g. `chen2024/judge_supervised/claude-code_trial1_codex-judge.json`. Our
dataset and agent names are used, so nothing downstream has to know about the
aliases, and each file's name carries everything that identifies it. Only the
two agents the evaluation covers are copied — claude-code and codex — and only
trials 1-3.

Only `llm_judge_eval.json` is copied — it holds the judge's per-question
decision and both justifications. `--decisions` additionally copies the judge's
`DECISIONS.md`, which is its prose answer to each question rather than its
rating.

Usage::

    python3 -m ratings import-judges                          # dry run, both modes
    python3 -m ratings import-judges --mode supervised --apply
    python3 -m ratings import-judges --mode unsupervised --apply
    python3 -m ratings import-judges --dataset chen2024 --apply
    python3 -m ratings import-judges --verify                 # re-check a finished copy
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

from . import raters as R
from .experiments import (AGENT_ALIAS, DATASET_ALIAS, EVAL_AGENTS, MAX_TRIAL,
                          MODES, SKIP_DIRS, TRIAL_RE, discover_runs, skip_notes)
from .paths import EXPERIMENTS_DIR

SOURCE_ROOT = EXPERIMENTS_DIR

# The tree's own vocabulary — task and agent aliases, which runs count, where a
# judge writes — lives in `experiments.py`, because the condition analysis walks
# same tree for a wider slice of it. Re-exported here under the name this
# module has always used.
KEEP_AGENTS = EVAL_AGENTS

__all__ = ["discover", "dest_paths", "copy_one", "run", "verify", "main",
           "DATASET_ALIAS", "AGENT_ALIAS", "KEEP_AGENTS", "MODES", "SKIP_DIRS",
           "TRIAL_RE", "MAX_TRIAL", "SOURCE_ROOT"]


def discover(dataset_filter: str | None = None) -> dict:
    """
    Walk the experiment tree for the runs this evaluation copies.

    Returns {dataset: {mode: {(agent, trial): {judge: source_dir}}}}, with our
    dataset/agent names. Only the two evaluated agents, only the full prompt,
    only trials 1-`MAX_TRIAL`: the minimal-prompt tasks and the other harnesses
    are real runs, but they have no human ratings and are read straight from
    the tree by `analysis.conditions` rather than mirrored here.
    """
    runs, skipped = discover_runs(
        datasets=[dataset_filter] if dataset_filter else None,
        agents=KEEP_AGENTS, prompts=("full",), modes=tuple(MODES),
        max_trial=MAX_TRIAL, root=SOURCE_ROOT)

    notes = skip_notes(skipped, MAX_TRIAL)
    for n in notes:
        print(f"  (skipping {n})")
    if notes:
        print()

    found: dict = {}
    for r in runs:
        (found.setdefault(r.dataset, {}).setdefault(r.mode, {})
              .setdefault((r.agent, r.trial), {})[r.judge]) = r.path
    return found


def dest_paths(dataset: str, mode: str, agent: str, trial: int, judge: str,
               decisions: bool) -> dict[str, Path]:
    """Source filename -> destination path, flat inside judge_<mode>/."""
    stem = f"{agent}_trial{trial}_{judge}-judge"
    out = {"llm_judge_eval.json":
           R.dataset_dir(dataset) / f"judge_{mode}" / f"{stem}.json"}
    if decisions:
        out["DECISIONS.md"] = (R.dataset_dir(dataset) / f"judge_{mode}"
                               / f"{stem}_DECISIONS.md")
    return out


def copy_one(src: Path, targets: dict[str, Path]) -> list[str]:
    copied = []
    for name, dst in targets.items():
        s = src / name
        if s.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, dst)
            copied.append(dst.name)
    return copied


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def run(mode: str, found: dict, apply: bool, decisions: bool) -> None:
    """Copy (or dry-run) one mode."""
    for dataset in sorted(found):
        per_mode = found[dataset].get(mode, {})
        if not per_mode:
            print(f"  {dataset:<12} no {mode} judge output yet")
            continue
        agents = sorted({a for a, _ in per_mode})
        files = 0
        for (agent, trial), judges in sorted(per_mode.items()):
            for judge, src in sorted(judges.items()):
                targets = dest_paths(dataset, mode, agent, trial, judge, decisions)
                names = (copy_one(src, targets) if apply
                         else [d.name for n, d in targets.items() if (src / n).exists()])
                files += len(names)
        print(f"  {dataset:<12} {len(per_mode):>3} agent-trials, {files:>3} files, "
              f"agents: {', '.join(agents)}")


def verify(mode: str, found: dict, decisions: bool) -> int:
    """Compare every copied file against its source. Returns problem count."""
    bad = 0
    for dataset in sorted(found):
        for (agent, trial), judges in sorted(found[dataset].get(mode, {}).items()):
            for judge, src in sorted(judges.items()):
                for name, dst in dest_paths(dataset, mode, agent, trial,
                                            judge, decisions).items():
                    s = src / name
                    if not s.exists():
                        continue
                    if not dst.exists():
                        print(f"   MISSING {dst.relative_to(R.EVAL_DIR)}")
                        bad += 1
                    elif _sha(s) != _sha(dst):
                        print(f"   DIFFERS {dst.relative_to(R.EVAL_DIR)}")
                        bad += 1
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--mode", choices=["supervised", "unsupervised", "both"],
                    default="both")
    ap.add_argument("--dataset", help="Our dataset name (e.g. chen2024)")
    ap.add_argument("--apply", action="store_true", help="Actually copy")
    ap.add_argument("--decisions", action="store_true",
                    help="Also copy each judge's DECISIONS.md (its prose answers)")
    ap.add_argument("--verify", action="store_true",
                    help="Checksum an existing copy against the source")
    args = ap.parse_args(argv)

    found = discover(args.dataset)
    if not found:
        sys.exit("Nothing found — check --dataset, or the experiment tree path.")

    modes = list(MODES) if args.mode == "both" else [args.mode]

    if args.verify:
        total = 0
        for mode in modes:
            print(f"── verifying {mode}")
            total += verify(mode, found, args.decisions)
        print(f"\n{total} problem(s).")
        sys.exit(1 if total else 0)

    print(f"{'COPYING' if args.apply else 'DRY RUN'} from {SOURCE_ROOT}\n")
    for mode in modes:
        print(f"── {mode}  →  eval/<dataset>/judge_{mode}/"
              f"<agent>_trial<N>_<judge>-judge.json")
        run(mode, found, args.apply, args.decisions)
        print()

    if not args.apply:
        print("Nothing written. Re-run with --apply.")


if __name__ == "__main__":
    main()
