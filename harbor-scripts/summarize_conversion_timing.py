#!/usr/bin/env python3
"""
Aggregate timing.txt files from submit_conversion_timing.py into a CSV.

Usage:
    summarize_conversion_timing.py [--results-root DIR] [--out CSV]
"""

import argparse
import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")
DEFAULT_RESULTS_ROOT = REPO_ROOT / "timing_results"

# /usr/bin/time -v fields we care about, plus their parsed type
TIME_FIELDS = {
    "Elapsed (wall clock) time (h:mm:ss or m:ss)": ("elapsed_str", str),
    "User time (seconds)": ("user_seconds", float),
    "System time (seconds)": ("system_seconds", float),
    "Maximum resident set size (kbytes)": ("max_rss_kb", int),
    "Percent of CPU this job got": ("cpu_pct", str),
}


def parse_elapsed(s: str) -> float:
    """Parse h:mm:ss or m:ss(.xx) to seconds."""
    parts = s.split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 3:
        h, m, sec = parts
    elif len(parts) == 2:
        h, m, sec = 0.0, parts[0], parts[1]
    else:
        return float("nan")
    return h * 3600 + m * 60 + sec


def parse_verify(path: Path) -> dict:
    """Pull dataset shape from train_decoder.py --verify-only output."""
    out = {}
    if not path.exists():
        return out
    text = path.read_text(errors="replace")

    patterns = {
        "n_trials":       r"Total number of trials:\s*(\d+)",
        "n_sessions":     r"Number of sessions:\s*(\d+)",
        "n_inputs":       r"Input dimension:\s*(\d+)",
        "n_outputs":      r"Output dimension:\s*(\d+)",
        # Floats may have a stray quote in some scripts (e.g. "912.36'")
        "T_mean":         r"T:\s*mean:\s*([\d.]+)",
        "n_neurons_mean": r"n_neurons:\s*mean:\s*([\d.]+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            v = m.group(1)
            try:
                out[key] = float(v) if "." in v else int(v)
            except ValueError:
                pass

    if {"n_trials", "T_mean"} <= out.keys():
        out["total_timepoints"] = out["n_trials"] * out["T_mean"]
    if {"n_neurons_mean", "n_inputs", "n_outputs",
        "total_timepoints"} <= out.keys():
        # work_units = (n_neurons + n_inputs + n_outputs) * sum(trial_T)
        out["work_units"] = (
            (out["n_neurons_mean"] + out["n_inputs"] + out["n_outputs"])
            * out["total_timepoints"]
        )
    return out


def parse_timing(path: Path) -> dict:
    out = {"timing_file": str(path)}
    text = path.read_text()
    for line in text.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if key in TIME_FIELDS:
            field, typ = TIME_FIELDS[key]
            try:
                out[field] = typ(val)
            except ValueError:
                out[field] = val
        elif key in ("task", "script", "host", "started", "ended",
                     "exit_code", "wall_seconds", "output_pkl_size",
                     "verify_exit_code", "verify_wall_seconds",
                     "accepts_datadir"):
            out[key] = val
    if "elapsed_str" in out:
        out["elapsed_seconds"] = parse_elapsed(out["elapsed_str"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    ap.add_argument("--out", type=Path,
                    default=DEFAULT_RESULTS_ROOT / "summary.csv")
    args = ap.parse_args()

    rows = []
    for timing in sorted(args.results_root.glob("*/*/timing.txt")):
        # path: <root>/<task>/<source_id>/timing.txt
        task = timing.parts[-3]
        source_id = timing.parts[-2]
        row = {"task": task, "source_id": source_id}
        row.update(parse_timing(timing))
        row.update(parse_verify(timing.parent / "verify.txt"))

        # work_units / wall_seconds = throughput in (units / sec)
        try:
            wall = float(row.get("wall_seconds", "nan"))
            if "work_units" in row and wall > 0:
                row["throughput_units_per_sec"] = row["work_units"] / wall
        except (TypeError, ValueError):
            pass

        rows.append(row)

    if not rows:
        print("No timing.txt files found under", args.results_root,
              file=sys.stderr)
        sys.exit(1)

    fieldnames = sorted({k for r in rows for k in r.keys()})
    # Put the most useful columns first
    preferred = ["task", "source_id", "exit_code", "verify_exit_code",
                 "wall_seconds", "verify_wall_seconds",
                 "n_sessions", "n_trials", "n_inputs", "n_outputs",
                 "T_mean", "n_neurons_mean", "total_timepoints",
                 "work_units", "throughput_units_per_sec",
                 "elapsed_str", "elapsed_seconds",
                 "user_seconds", "system_seconds",
                 "cpu_pct", "max_rss_kb", "output_pkl_size",
                 "accepts_datadir",
                 "host", "started", "ended", "script", "timing_file"]
    fieldnames = [f for f in preferred if f in fieldnames] + \
                 [f for f in fieldnames if f not in preferred]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
