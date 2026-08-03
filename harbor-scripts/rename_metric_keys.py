"""Rename or drop keys in recorded verifier metrics.json files.

Pure surgery on already-recorded data: no pickles are loaded, no test is run,
nothing is recomputed. That is the whole point of keeping this separate from
`rerun_metrics.py`, which cannot do the job at all -- its merge only ADDS and
OVERWRITES keys, never removes them, so re-sweeping after a rename would leave
both the old and the new name in every file.

Dry-run by default; pass --write to modify anything.

Usage:
    conda activate decoder-data-format
    python rename_metric_keys.py                    # dry-run, show every change
    python rename_metric_keys.py --write            # apply
    python rename_metric_keys.py --task lee2025     # restrict to one task
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")
HARBOR_JOBS = REPO_ROOT / "harbor-jobs"

# old key -> new key. Both current names describe the wrong quantity: neither is
# a mean of the corresponding *_error_* fields, both are the mean Hungarian
# matching cost, which for exactly-matching variable names is forced to 0 before
# any range or fraction term is even computed.
RENAMES = {
    "input_range_mean_cost":     "input_match_mean_cost",
    "output_fraction_mean_cost": "output_match_mean_cost",
}

# Keys removed outright. Dropping a field destroys the only copy of it, so each
# entry needs its own justification.
#
#   output_match_cost: a duplicate of what is now output_match_mean_cost. Both
#   were np.mean over the same match_outputs() call, one in test_data_stats and
#   one in test_decoder_accuracy. Of 151 recorded trials, 74 held identical
#   values and 37 differed only by MiniLM embedding noise (< 1e-4). The 6 that
#   differed materially are all sosa2024, where this copy was averaged over the
#   3 outputs the reference had when the decoder last ran rather than today's 6
#   -- so its only distinguishable values are stale. test_outputs.py no longer
#   writes it, so a decoder rerun will not bring it back.
DROPS: set[str] = {"output_match_cost"}

# Task directories left alone. `debug` is a scratch task whose tests/test_outputs.py
# is a deliberate stub -- sync_template.py's TASK_EXCLUDED keeps it off the template,
# so it still writes the old key names. Renaming its recorded metrics would put the
# data out of step with the code that produced it, and re-verifying debug would then
# write the old names back alongside the new ones.
SKIP_TASKS = {"debug"}


def plan_file(metrics: dict) -> tuple[list, list, list]:
    """Work out what would change in one metrics dict, without changing it.

    Args:
        metrics: parsed contents of one verifier/metrics.json.

    Returns:
        (renames, drops, conflicts), where
          renames   is [(old, new, value)] for keys that move cleanly,
          drops     is [(key, value)] for keys in DROPS that are present,
          conflicts is [(old, new, old_value, new_value)] for renames whose
                    destination key already exists. A conflict is never resolved
                    here: silently picking a side would discard a recorded
                    measurement.
    """
    renames, drops, conflicts = [], [], []
    for old, new in RENAMES.items():
        if old not in metrics:
            continue
        if new in metrics:
            conflicts.append((old, new, metrics[old], metrics[new]))
        else:
            renames.append((old, new, metrics[old]))
    for key in DROPS:
        if key in metrics:
            drops.append((key, metrics[key]))
    return renames, drops, conflicts


def apply_renames(metrics: dict, renames: list, drops: list) -> dict:
    """Build a new dict with keys renamed and dropped, preserving key order.

    Order is preserved because the two on-disk formats differ: files written by
    `rerun_metrics.py` are sorted, but the verifier's own metrics fixture writes
    `json.dump(data, f, indent=2)` with no sort_keys, so unswept trials are in
    insertion order. Rebuilding in place keeps the diff to the renamed lines in
    both cases; re-sorting would rewrite every unsorted file end to end.

    Args:
        metrics: parsed metrics.json. Not modified.
        renames: [(old, new, value)] from plan_file.
        drops: [(key, value)] from plan_file.

    Returns:
        A new dict, same order, with old keys replaced in position.
    """
    rename_map = {old: new for old, new, _ in renames}
    drop_keys = {key for key, _ in drops}
    return {rename_map.get(k, k): v for k, v in metrics.items()
            if k not in drop_keys}


def write_preserving_style(path: Path, metrics: dict, was_sorted: bool) -> None:
    """Write metrics.json back in the style the file already used.

    Args:
        path: file to overwrite.
        metrics: the new contents.
        was_sorted: whether the original file was sorted; if so the output is
            re-sorted so the renamed key lands in its correct new position
            rather than leaving the file half-sorted.

    Side effects:
        Overwrites `path`.
    """
    # No trailing newline, matching json.dump() as used by the verifier's metrics
    # fixture and by rerun_metrics.py. Adding one would be stripped again by the
    # next writer, giving every file a spurious one-line diff on every rerun.
    path.write_text(json.dumps(metrics, indent=2, sort_keys=was_sorted))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs-root", type=Path, default=HARBOR_JOBS,
                    help=f"Tree to scan. Default: {HARBOR_JOBS}")
    ap.add_argument("--task", action="append", default=[],
                    help="Restrict to this task directory. Repeatable.")
    ap.add_argument("--write", action="store_true",
                    help="Actually modify files (default: dry-run).")
    args = ap.parse_args()

    files = sorted(args.jobs_root.glob("*/*/*/verifier/metrics.json"))
    files = [f for f in files
             if f.relative_to(args.jobs_root).parts[0] not in SKIP_TASKS]
    if args.task:
        wanted = set(args.task)
        files = [f for f in files
                 if f.relative_to(args.jobs_root).parts[0] in wanted]
    if not files:
        sys.exit(f"No metrics.json found under {args.jobs_root}")

    print(f"Scanning {len(files)} metrics.json under {args.jobs_root}")
    print(f"Renames: {RENAMES}")
    print(f"Drops:   {DROPS or '(none)'}\n")

    n_changed = n_conflict = 0
    per_key: dict[str, int] = {}
    for path in files:
        try:
            raw = path.read_text()
            metrics = json.loads(raw)
        except (OSError, json.JSONDecodeError) as e:
            print(f"  UNREADABLE {path}: {e}")
            continue

        renames, drops, conflicts = plan_file(metrics)
        if not (renames or drops or conflicts):
            continue

        rel = path.relative_to(args.jobs_root)
        print(f"{rel}")
        for old, new, value in renames:
            print(f"    {old} -> {new}   = {value!r}")
            per_key[old] = per_key.get(old, 0) + 1
        for key, value in drops:
            print(f"    DROP {key}   = {value!r}")
            per_key[f"DROP {key}"] = per_key.get(f"DROP {key}", 0) + 1
        for old, new, old_value, new_value in conflicts:
            # Not resolved and not written: both names hold a recorded number,
            # and choosing one here would throw the other away silently.
            print(f"    CONFLICT {old}={old_value!r} but {new} already "
                  f"exists ={new_value!r} -- file left untouched")
            n_conflict += 1

        if conflicts:
            continue
        n_changed += 1
        if args.write:
            was_sorted = raw.rstrip("\n") == json.dumps(metrics, indent=2,
                                                        sort_keys=True)
            write_preserving_style(path, apply_renames(metrics, renames, drops),
                                   was_sorted)

    print(f"\n{'WROTE' if args.write else 'DRY-RUN'}: "
          f"{n_changed} file(s) would change, {n_conflict} conflict(s) skipped")
    for key, count in sorted(per_key.items()):
        print(f"    {count:>4}  {key}")
    if not args.write and n_changed:
        print("\nRe-run with --write to apply.")


if __name__ == "__main__":
    main()
