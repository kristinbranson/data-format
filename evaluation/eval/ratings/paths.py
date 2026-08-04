"""Every filesystem location the rating tools use, derived once.

Before this package existed each module worked out its own: three of them ran
`Path(__file__).resolve().parent` and two hardcoded an absolute path to the
repo. That is a trap for exactly this kind of move — a module one directory
deeper still computes a path, just the wrong one, and the failure is silent
(empty dataset lists, not an ImportError). Anchoring everything here means a
future move is one edit.

    PACKAGE_DIR   eval/ratings          this package
    EVAL_DIR      eval                  per-dataset rating folders live here
    REPO_ROOT     Data-Format           top of the repo
    MANUAL_DIR    Data-Format/manual    reference solutions (DECISIONS.md)
    EXPERIMENTS_DIR                     judge runs, mirrored in by judge_import
    REGISTRY_PATH eval/ratings/raters.json
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
EVAL_DIR = PACKAGE_DIR.parent
REPO_ROOT = EVAL_DIR.parents[1]

MANUAL_DIR = REPO_ROOT / "manual"
EXPERIMENTS_DIR = REPO_ROOT / "data-format-experiments"

# Moved into the package with the code that reads it, so a checkout carries its
# evaluator registry rather than depending on a file beside it.
REGISTRY_PATH = PACKAGE_DIR / "raters.json"
