"""Rerun selected `test_outputs.py` tests against a trial's snapshot and
merge any new metrics into metrics.json.

Consolidates `rerun_file_format_checks.py`, `rerun_data_stats.py`, and
`rerun_decoder_accuracy.py`. The big win is that each trial's snapshot
pickle is loaded **once** even when several tests are requested — so on
slow trials (e.g. mouseland with multi-GB pickles) you don't pay the
load cost three times.

By default the script runs the *cheap* subset:
  * test_required_files_exist
  * test_no_contamination
  * test_expected_files_exist
  * test_verify_data_format
  * test_data_stats          (skipped automatically on unsupervised tasks)
Add `--decoder` to also run `test_decoder_accuracy` (slow — GPU/CPU
decoder training, several minutes per trial).

All tests are invoked by *fresh-importing* the task's `tests/test_outputs.py`
— so any future change to that file flows through here automatically.

`--reference-only` is the mode for "the reference solution changed, refresh
everything that depends on it". It runs test_data_stats and then DERIVES the
decoder's reference fields arithmetically instead of retraining:

    validation_balanced_accuracy_reference  <- straight from the new reference
    validation_balanced_accuracy_ratio      <- stored agent accuracy / new reference

That is legitimate because everything test_decoder_accuracy does after training
depends only on the agent's per-output accuracy (already recorded in metrics.json
as `validation_balanced_accuracy`, and unaffected by a reference change), the
reference's accuracy, and the output matching — which this mode recomputes from
the freshly loaded pickle. Training again would reproduce the same agent numbers
at a cost of minutes to hours per trial.

The pickle is still loaded, because test_data_stats needs the submitted
output_range/output_fractions to redo the Hungarian matching and those are not
recorded in metrics.json. Only the decoder training is skipped.

Merge behaviour:
  * Default: ADD missing keys only (safe; preserves whatever was already
    in metrics.json).
  * `--force`: also OVERWRITE existing keys when the new value differs.
    Use this after a test_outputs.py change that should update existing
    fields (e.g., the matcher fix). `--reference-only` is nearly always
    paired with it, since the fields it refreshes already exist.

Two things this script does NOT do, both of which have bitten before:

1. It writes metrics.json ONLY. reward.txt, ctrf.json and test-stdout.txt keep
   whatever the verifier decided when the trial actually ran. As of the range
   checks added to test_data_stats (input_range_error / output_range_error),
   67 of 128 supervised trials hold a metrics.json that fails a check their
   reward.txt says they passed. lesion_analysis.py is unaffected -- it derives
   every category from metrics plus STATLIMITS -- but check_trial_health.py
   parses test-stdout.txt and therefore reports the pre-range verdict. Use
   rerun_verifier.sh if you need reward and metrics to agree.

2. It cannot make a partial sweep safe. `input_range_error_<var>` changed
   meaning -- it was an absolute endpoint error in the variable's own units and
   is now a FRACTION of the reference variable's span -- and nothing in
   metrics.json records which meaning a given file holds. Sweeping a subset
   leaves the two silently mixed under one key, and trial_metrics._curate maxes
   over that prefix into `input_range_error_max`. Sweep everything or nothing.
   The same applies to any future change that redefines an existing field.

Usage:
    conda activate decoder-data-format
    # Dry-run: list candidate trials (those with a snapshot)
    python rerun_metrics.py
    # Rerun one trial (cheap suite, dry-run)
    python rerun_metrics.py --trial harbor-jobs/sosa2024/.../trial1
    # Rerun one trial and write
    python rerun_metrics.py --trial <trial> --write --force
    # Sweep every trial
    python rerun_metrics.py --all --write --force
    # Sweep + also run decoder accuracy (slow)
    python rerun_metrics.py --all --decoder --write --force
    # Skip a test group
    python rerun_metrics.py --all --no-data-stats --write --force
    # After changing a task's reference solution — no decoder training:
    python rerun_metrics.py --all --task map --reference-only --write --force
"""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import pickle
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")
HARBOR_TASKS = REPO_ROOT / "harbor-tasks"
HARBOR_JOBS = REPO_ROOT / "harbor-jobs"
# One tree: harbor-jobs-new was merged into harbor-jobs. It stays a list because the
# reason for sweeping every root at once still holds -- refreshing half a task's
# trials leaves the rest holding metrics on the old definitions, which is worse than
# not running at all.
JOB_ROOTS = [HARBOR_JOBS]


# ---------------------------------------------------------------- imports / refs

def _import_task_tests(task: str, workdir: Path):
    """Fresh-import the task's decoder.py + test_outputs.py with WORKDIR set."""
    tests_dir = HARBOR_TASKS / task / "tests"
    os.environ["WORKDIR"] = str(workdir)
    os.environ["METRICS_PATH"] = "/dev/null"
    for mod_name in ("decoder", "test_outputs"):
        sys.modules.pop(mod_name, None)
    sys.path.insert(0, str(tests_dir))
    try:
        spec = importlib.util.spec_from_file_location("test_outputs", tests_dir / "test_outputs.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


_REF_CACHE: dict[str, dict | None] = {}
def _reference_data_stats(task: str):
    if task in _REF_CACHE:
        return _REF_CACHE[task]
    ref_path = HARBOR_TASKS / task / "tests" / "reference_stats_full.json"
    if not ref_path.exists():
        _REF_CACHE[task] = None
        return None
    with open(ref_path) as f:
        stats = json.load(f)
    stats["data_summary"]["nneurons_total"] = (
        stats["data_summary"]["nsessions"] * stats["data_summary"]["nneurons_mean"]
    )
    _REF_CACHE[task] = stats
    return stats


def _derive_decoder_reference_fields(test_mod, existing, submitted_data_stats,
                                     reference_data_stats, new_metrics) -> str:
    """Recompute the decoder's reference-dependent metrics without retraining.

    Mirrors the block of `test_outputs.test_decoder_accuracy` that runs *after*
    train_validate_decoder returns. That block reads only three things, none of
    which require the decoder:

      * the agent's per-output accuracy -- fixed by the agent's own data, so the
        value already in metrics.json under `validation_balanced_accuracy` is the
        same one retraining would produce (the decoder is seeded from the
        reference's `rng_state`, so it is reproducible)
      * the reference's per-output accuracy, read from reference_stats_full.json
      * the submitted->reference output matching, recomputed here from the
        freshly loaded pickle via the task's own `match_outputs`

    Args:
        test_mod: the freshly imported task `test_outputs` module, for match_outputs.
        existing: metrics.json as already on disk; source of the agent accuracy.
        submitted_data_stats: stats computed from the agent's converted_data.pkl.
        reference_data_stats: parsed reference_stats_full.json, or None.
        new_metrics: dict this function writes its results into, merged by the caller.

    Returns:
        A one-line status string for the run report.

    Side effects:
        Adds `validation_balanced_accuracy_reference`, `validation_balanced_accuracy_ratio`
        and `output_match_cost` to `new_metrics`.
    """
    if reference_data_stats is None:
        return "derive decoder refs: skipped (unsupervised task, no reference)"

    # Written by test_decoder_accuracy on a real run. Absent means the decoder has
    # never successfully run for this trial, and there is no agent number to divide
    # -- deriving a ratio would be inventing one.
    sub_accuracy = existing.get("validation_balanced_accuracy")
    if not sub_accuracy:
        return ("derive decoder refs: skipped (no stored validation_balanced_accuracy; "
                "run once with --decoder first)")

    ref_accuracy = reference_data_stats["validation_balanced_accuracy"]
    new_metrics["validation_balanced_accuracy_reference"] = ref_accuracy

    output_matches, output_match_costs = test_mod.match_outputs(
        submitted_data_stats, reference_data_stats
    )
    if output_match_costs is not None and len(output_match_costs):
        new_metrics["output_match_cost"] = float(
            sum(output_match_costs) / len(output_match_costs)
        )

    # Same guards as the test: skip any pair the matcher could not resolve, and any
    # reference accuracy of 0, which would divide by zero.
    ratio = {}
    for ref_name, sub_name, _cost in output_matches:
        if sub_name is None or sub_name not in sub_accuracy:
            continue
        if ref_name is None or ref_name not in ref_accuracy or not ref_accuracy[ref_name]:
            continue
        ratio[ref_name] = sub_accuracy[sub_name] / ref_accuracy[ref_name]
    new_metrics["validation_balanced_accuracy_ratio"] = ratio

    return f"derive decoder refs: {len(ratio)} output(s) from stored accuracy (no training)"


# Significant figures for values shown in the run report. Full float repr costs
# 17 digits per number, which pushes structures like output_matches (a list of
# dicts, each with a cost) past any sane line length for no benefit: the size of
# a change is read off the delta in _fmt_change, which stays exact.
_DISPLAY_SIGFIGS = 6


def _round_floats(v, sigfigs: int = _DISPLAY_SIGFIGS):
    """Recursively round floats inside a metric value, for display only.

    Ints are left alone (they are exact counts, and bool is an int subclass that
    must not be turned into a float). nan/inf survive the %g round-trip
    unchanged, so they need no special case.

    Args:
        v: any metric value -- scalar, list, or dict, nested arbitrarily.
        sigfigs: significant figures to keep on each float.

    Returns:
        The same structure with floats rounded. Never mutates the input.
    """
    if isinstance(v, float):
        return float(f"%.{sigfigs}g" % v)
    if isinstance(v, dict):
        return {k: _round_floats(x, sigfigs) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_round_floats(x, sigfigs) for x in v]
    return v


def _fmt_value(v, maxlen: int = 220) -> str:
    """Render one metric value as a single line for the run report.

    Floats are rounded to _DISPLAY_SIGFIGS so more of a structure fits on the
    line. Long values (the *_warnings lists reach megabytes) are cut, but the cut
    is always stated: a silently truncated log is worse than a verbose one when
    the log is what you are reading to make a decision.

    Args:
        v: any metric value; JSON-representable types render exactly, anything
           else falls back to repr().
        maxlen: characters to keep before truncating.

    Returns:
        Single-line string, with " ...[+N chars]" appended if it was cut.
    """
    try:
        s = json.dumps(_round_floats(v), sort_keys=True)
    except (TypeError, ValueError):
        s = repr(v)
    if len(s) <= maxlen:
        return s
    return f"{s[:maxlen]} ...[+{len(s) - maxlen} chars]"


def _fmt_change(old, new) -> str:
    """Render an overwrite as 'old -> new', with a delta for plain numbers.

    The delta is what makes float noise self-evident: +5.7e-08 next to a value
    of 0.13 reads as noise at a glance, where the two full-precision numbers on
    their own do not. bool is excluded because it is an int subclass and
    "True -> False (delta -1)" is nonsense.

    Args:
        old: value currently in metrics.json.
        new: value the freshly-run test produced.

    Returns:
        Single-line string.
    """
    shown_old, shown_new = _fmt_value(old), _fmt_value(new)
    line = f"{shown_old} -> {shown_new}"
    numeric = (int, float)
    if (isinstance(old, numeric) and isinstance(new, numeric)
            and not isinstance(old, bool) and not isinstance(new, bool)):
        try:
            line += f"   (delta {new - old:+.6g})"
        except (TypeError, OverflowError, ValueError):
            pass
    elif shown_old == shown_new:
        # Rounding for display can make a real change look like none at all.
        # There is no scalar delta to fall back on for a list or dict, so say it.
        line += f"   (differs only below {_DISPLAY_SIGFIGS} s.f.)"
    return line


# Overwrites whose every numeric leaf moves by less than this are collapsed to a
# single summary line in the report. The matcher's semantic embeddings are not
# bit-reproducible across runs, so costs wobble by ~1e-7 on most trials; listing
# those individually buries the changes that matter.
_NOISE_EPSILON = 1e-4


def _max_abs_delta(old, new):
    """Largest absolute difference between corresponding numeric leaves.

    Recurses into lists and dicts so a nested value like output_matches (a list
    of {reference, submitted, cost} dicts) is judged on its costs rather than
    treated as opaque.

    Args:
        old: value currently in metrics.json.
        new: value the freshly-run test produced.

    Returns:
        float -- the largest absolute leaf difference; nan if any leaf pair mixes
        nan with a number (allen2p's input_range_mean_cost goes nan -> 0.0, which
        is a real fix and must not be squashed); or None when the two values are
        not comparable leaf-for-leaf -- different types, dict keys, or lengths.
        None means a structural change, which is always worth reporting whatever
        its magnitude. Callers must treat both None and nan as significant.
    """
    # bool before int: bool is an int subclass and True/False has no useful delta.
    if isinstance(old, bool) or isinstance(new, bool):
        return 0.0 if old == new else None
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        return abs(new - old)
    if isinstance(old, dict) and isinstance(new, dict):
        if set(old) != set(new):
            return None
        deltas = [_max_abs_delta(old[k], new[k]) for k in old]
    elif isinstance(old, (list, tuple)) and isinstance(new, (list, tuple)):
        if len(old) != len(new):
            return None
        deltas = [_max_abs_delta(a, b) for a, b in zip(old, new)]
    else:
        return 0.0 if old == new else None
    if any(d is None for d in deltas):
        return None
    if any(d != d for d in deltas):          # nan anywhere -> nan, not max()
        return float("nan")
    return max(deltas) if deltas else 0.0


def _invoke(fn, *args, label: str):
    """Call a test fn, returning (raised?, msg)."""
    try:
        fn(*args)
        return False, "passed"
    except BaseException as e:
        msg = f"{type(e).__name__}: {e}".strip()
        if type(e).__name__ == "Skipped":
            msg = f"skipped: {e}"
        return True, msg


# ---------------------------------------------------------------- per-trial

def rerun_trial(trial_dir: Path, task: str, *,
                run_checks: bool, run_data_stats: bool, run_decoder: bool,
                derive_decoder_refs: bool = False,
                write: bool, force: bool) -> dict:
    report = {"trial": str(trial_dir), "ok": False, "events": [],
              "keys_added": [], "keys_overwritten": []}

    snap = trial_dir / "verifier" / "snapshot"
    if not snap.is_dir():
        report["events"].append("no verifier/snapshot/")
        return report

    metrics_path = trial_dir / "verifier" / "metrics.json"
    try:
        with open(metrics_path) as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing = {}

    # Fresh-import once per trial so test_outputs.py picks up the right WORKDIR.
    test_mod = _import_task_tests(task, workdir=snap)
    finder = getattr(test_mod, "_find_workdir_file", None)
    def _find(name):
        if finder is not None:
            return finder(name)
        p = snap / name
        return p if p.exists() else None

    # Decide which pickles we need (load lazily, once each).
    need_sample = run_checks                  # test_verify_data_format
    # derive_decoder_refs needs submitted_data_stats for the output matching, which
    # comes from the full pickle -- the same load test_data_stats already pays for.
    need_full   = run_checks or run_data_stats or run_decoder or derive_decoder_refs

    submitted_sample = submitted_full = None
    if need_sample:
        p = _find("sample_data.pkl")
        if p is not None:
            t0 = time.time()
            with open(p, "rb") as f:
                submitted_sample = pickle.load(f)
            if time.time() - t0 > 2:
                report["events"].append(f"loaded sample_data.pkl ({time.time()-t0:.1f}s)")
    if need_full:
        p = _find("converted_data.pkl")
        if p is not None:
            t0 = time.time()
            with open(p, "rb") as f:
                submitted_full = pickle.load(f)
            if time.time() - t0 > 2:
                report["events"].append(f"loaded converted_data.pkl ({time.time()-t0:.1f}s)")

    # Compute data-stats fixtures lazily (only if needed AND we have the pkl).
    # print_data_summary prints ~50 lines of stats to stdout per call — silence
    # it here since the per-test pass/fail lines below are what we care about.
    need_stats = run_data_stats or run_decoder or derive_decoder_refs
    submitted_data_stats = None
    if need_stats and submitted_full is not None:
        with contextlib.redirect_stdout(io.StringIO()):
            submitted_data_stats = test_mod.print_data_summary(submitted_full)
        submitted_data_stats["nneurons_total"] = (
            submitted_data_stats["nsessions"] * submitted_data_stats["nneurons_mean"]
        )
    reference_data_stats = _reference_data_stats(task) if need_stats else None

    new_metrics: dict = {}

    # ---- cheap checks ----
    if run_checks:
        for label, fn, args in [
            ("test_required_files_exist", test_mod.test_required_files_exist, (new_metrics,)),
            ("test_no_contamination",     test_mod.test_no_contamination,     (new_metrics,)),
            ("test_expected_files_exist", test_mod.test_expected_files_exist, (new_metrics,)),
        ]:
            _, msg = _invoke(fn, *args, label=label)
            report["events"].append(f"{label}: {msg}")
        if submitted_sample is not None and submitted_full is not None:
            _, msg = _invoke(test_mod.test_verify_data_format,
                             new_metrics, submitted_sample, submitted_full,
                             label="test_verify_data_format")
            report["events"].append(f"test_verify_data_format: {msg}")
        else:
            report["events"].append("test_verify_data_format: skipped (missing pickle)")

    # ---- data stats (supervised: full check; unsupervised: pytest.skip — fine) ----
    if run_data_stats and submitted_data_stats is not None:
        _, msg = _invoke(test_mod.test_data_stats,
                         new_metrics, submitted_data_stats, reference_data_stats,
                         label="test_data_stats")
        report["events"].append(f"test_data_stats: {msg}")
    elif run_data_stats:
        report["events"].append("test_data_stats: skipped (no converted_data.pkl)")

    # ---- decoder accuracy (slow) ----
    if run_decoder and submitted_full is not None:
        _, msg = _invoke(test_mod.test_decoder_accuracy,
                         new_metrics, submitted_full, submitted_data_stats, reference_data_stats,
                         label="test_decoder_accuracy")
        report["events"].append(f"test_decoder_accuracy: {msg}")
    elif run_decoder:
        report["events"].append("test_decoder_accuracy: skipped (no converted_data.pkl)")

    # ---- decoder reference fields, derived rather than retrained ----
    # Deliberately after the decoder block: if both are somehow requested, the real
    # training run is authoritative and this must not overwrite it.
    if derive_decoder_refs and not run_decoder:
        if submitted_data_stats is not None:
            report["events"].append(_derive_decoder_reference_fields(
                test_mod, existing, submitted_data_stats, reference_data_stats, new_metrics))
        else:
            report["events"].append("derive decoder refs: skipped (no converted_data.pkl)")

    # ---- merge ----
    # Carries the values, not just the key names. A bare list of changed keys
    # cannot distinguish 1e-7 of float wobble in a matcher cost from a genuine
    # redefinition of the field, and both happen in the same run. The old value
    # has to be read before the assignment clobbers it.
    #   keys_added:       [(key, new_value)]
    #   keys_overwritten: [(key, old_value, new_value)]
    keys_added, keys_overwritten = [], []
    for k, v in new_metrics.items():
        if k not in existing:
            keys_added.append((k, v))
            existing[k] = v
        elif force and existing[k] != v:
            keys_overwritten.append((k, existing[k], v))
            existing[k] = v
    report["keys_added"] = sorted(keys_added, key=lambda t: t[0])
    report["keys_overwritten"] = sorted(keys_overwritten, key=lambda t: t[0])
    report["ok"] = True

    changed = bool(keys_added or keys_overwritten)
    if write and changed:
        with open(metrics_path, "w") as f:
            json.dump(existing, f, indent=2, sort_keys=True)
        report["events"].append(f"wrote {metrics_path}")
    elif write:
        report["events"].append("no changes; metrics.json untouched")
    return report


# ---------------------------------------------------------------- main

def find_candidates(only_tasks: set | None = None,
                    skip_tasks: set | None = None) -> list[tuple[Path, str]]:
    """Every trial with a snapshot dir, across both job trees, excluding oracle
    and badtrial.

    `only_tasks` and `skip_tasks` filter by top-level task directory name.

    Returns:
        [(trial_dir, task)], sorted within each root, harbor-jobs before
        harbor-jobs-new.
    """
    out = []
    for root in JOB_ROOTS:
        if not root.is_dir():
            continue
        for trial_dir in sorted(root.glob("*/*/*/")):
            if "oracle" in trial_dir.parts or "badtrial" in str(trial_dir):
                continue
            if not (trial_dir / "verifier" / "snapshot").is_dir():
                continue
            task = trial_dir.relative_to(root).parts[0]
            if only_tasks is not None and task not in only_tasks:
                continue
            if skip_tasks is not None and task in skip_tasks:
                continue
            out.append((trial_dir, task))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--trial", help="Path to one trial dir (relative to repo root or absolute).")
    g.add_argument("--all", action="store_true",
                   help="Process every trial that has a verifier/snapshot/.")
    ap.add_argument("--write", action="store_true",
                    help="Actually write metrics.json (default: dry-run).")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing keys in metrics.json when values "
                         "differ (default: only ADD missing keys).")
    ap.add_argument("--epsilon", type=float, default=_NOISE_EPSILON,
                    help="Collapse overwrites whose every numeric leaf moves by "
                         f"less than this into one summary line (default "
                         f"{_NOISE_EPSILON:g}). Display only -- they are still "
                         "written. Pass 0 to list every change individually.")
    ap.add_argument("--task", action="append", default=[],
                    help="Restrict to this task (top-level dir under harbor-jobs/). "
                         "Can be repeated, e.g. `--task hasnain2024 --task map`.")
    ap.add_argument("--skip-task", action="append", default=[],
                    help="Skip this task. Can be repeated.")
    # Test-group selection. --decoder is off by default because it's slow.
    ap.add_argument("--no-checks",     action="store_true",
                    help="Skip the cheap file/format/contamination tests.")
    ap.add_argument("--no-data-stats", action="store_true",
                    help="Skip test_data_stats.")
    ap.add_argument("--decoder",       action="store_true",
                    help="Also run test_decoder_accuracy (slow).")
    ap.add_argument("--reference-only", action="store_true",
                    help="Refresh only what a changed reference solution affects: "
                         "run test_data_stats, then derive "
                         "validation_balanced_accuracy_{reference,ratio} from the "
                         "accuracy already in metrics.json instead of retraining. "
                         "Implies --no-checks; incompatible with --decoder.")
    args = ap.parse_args()

    if args.reference_only and args.decoder:
        sys.exit("--reference-only and --decoder are contradictory: one derives the "
                 "decoder's reference fields, the other recomputes them by training.")

    run_checks     = not args.no_checks and not args.reference_only
    run_data_stats = not args.no_data_stats
    run_decoder    = args.decoder

    if args.reference_only and not run_data_stats:
        sys.exit("--reference-only needs test_data_stats; drop --no-data-stats.")
    if not (run_checks or run_data_stats or run_decoder):
        sys.exit("Nothing to do — at least one of checks / data-stats / decoder must be enabled.")

    # Every field --reference-only touches already exists in metrics.json, so without
    # --force the merge is a guaranteed no-op. Warn rather than imply it: silently
    # overwriting on a dry-run-looking command is the worse failure.
    if args.reference_only and args.write and not args.force:
        print("WARNING: --reference-only without --force will not update anything — "
              "the fields it refreshes are already present. Add --force.\n")

    if args.trial:
        trial = Path(args.trial)
        if not trial.is_absolute():
            trial = (REPO_ROOT / trial).resolve()
        # Match against each root both as written and as resolved: harbor-jobs is a
        # symlink to /nearline/branson/data-format/harbor-jobs, and `trial` has been
        # through .resolve() above, so a `harbor-jobs/...` argument arrives as a
        # /nearline path and relative_to(HARBOR_JOBS) alone never matches.
        task = None
        for root in JOB_ROOTS:
            for base in (root, root.resolve()):
                try:
                    task = trial.relative_to(base).parts[0]
                    break
                except ValueError:
                    continue
            if task is not None:
                break
        if task is None:
            sys.exit("Trial path must be under one of: "
                     + ", ".join(str(r) for r in JOB_ROOTS))
        candidates = [(trial, task)]
    else:
        only_tasks = set(args.task) if args.task else None
        skip_tasks = set(args.skip_task) if args.skip_task else None
        cands = find_candidates(only_tasks=only_tasks, skip_tasks=skip_tasks)
        if args.all:
            candidates = cands
            filt = []
            if only_tasks:
                filt.append(f"--task {' --task '.join(sorted(only_tasks))}")
            if skip_tasks:
                filt.append(f"--skip-task {' --skip-task '.join(sorted(skip_tasks))}")
            extra = f" ({' '.join(filt)})" if filt else ""
            print(f"Found {len(candidates)} trial(s) with snapshots{extra}.")
        else:
            for trial, task in cands:
                print(f"  {task:<15}  {trial.relative_to(REPO_ROOT)}")
            return

    suite_str = ", ".join([s for s, on in (
        ("checks", run_checks),
        ("data-stats", run_data_stats),
        ("decoder", run_decoder),
        ("decoder-refs (derived, no training)", args.reference_only)) if on])
    print(f"Tests selected: {suite_str}\n")

    for trial, task in candidates:
        print(f"=== {task} / {trial.name} ===")
        try:
            rep = rerun_trial(trial, task,
                              run_checks=run_checks,
                              run_data_stats=run_data_stats,
                              run_decoder=run_decoder,
                              derive_decoder_refs=args.reference_only,
                              write=args.write, force=args.force)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            traceback.print_exc()
            continue
        for ev in rep["events"]:
            print(f"  {ev}")
        if rep["keys_added"]:
            print(f"  + added ({len(rep['keys_added'])}):")
            for k, v in rep["keys_added"]:
                print(f"      {k} = {_fmt_value(v)}")
        if rep["keys_overwritten"]:
            # Split real changes from float noise. None (structural) and nan
            # (nan <-> number) both count as real -- see _max_abs_delta.
            real, noise = [], []
            for k, old, new in rep["keys_overwritten"]:
                delta = _max_abs_delta(old, new)
                significant = delta is None or delta != delta or delta >= args.epsilon
                (real if significant else noise).append((k, old, new, delta))
            print(f"  * overwritten ({len(rep['keys_overwritten'])}):")
            for k, old, new, _ in real:
                print(f"      {k}: {_fmt_change(old, new)}")
            if noise:
                worst = max(d for *_, d in noise)
                print(f"      [{len(noise)} changed by < {args.epsilon:g} "
                      f"(max |delta| {worst:.3g}), still written]: "
                      f"{', '.join(k for k, *_ in noise)}")
        if not rep["keys_added"] and not rep["keys_overwritten"]:
            print("  (no changes)")
        print()


if __name__ == "__main__":
    main()
