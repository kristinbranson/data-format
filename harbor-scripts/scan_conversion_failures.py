#!/usr/bin/env python3
"""
Scan timing_results/ for failed conversions or failed verifications.

Usage:
    scan_conversion_failures.py [--results-root DIR] [--show-tail N]
                                [--only-fail|--only-pass|--only-pending]

Status legend:
    OK         convert exit=0, verify exit=0
    BAD-CONV   convert exit != 0
    BAD-VRFY   convert exit=0, verify exit != 0
    NO-VRFY    convert exit=0, no verify_exit_code line (skipped, no pkl)
    PENDING    timing.txt has no exit_code yet (job still running or never wrote)
    NO-TIMING  no timing.txt at all
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")
DEFAULT_RESULTS_ROOT = REPO_ROOT / "timing_results"


def parse_verify_shape(verify_path: Path):
    """Extract n_neurons_mean, n_inputs, n_outputs, n_trials, T_mean from verify.txt.
       Returns dict (possibly empty)."""
    if not verify_path.exists():
        return {}
    text = verify_path.read_text(errors="replace")
    out = {}
    for key, pat in [
        ("n_trials",       r"Total number of trials:\s*(\d+)"),
        ("n_inputs",       r"Input dimension:\s*(\d+)"),
        ("n_outputs",      r"Output dimension:\s*(\d+)"),
        ("T_mean",         r"T:\s*mean:\s*([\d.]+)"),
        ("n_neurons_mean", r"n_neurons:\s*mean:\s*([\d.]+)"),
    ]:
        m = re.search(pat, text)
        if m:
            v = m.group(1)
            out[key] = float(v) if "." in v else int(v)
    return out

KV = re.compile(r"^(\w[\w_]*):\s*(.+)$")


def parse_kv(text):
    out = {}
    for line in text.splitlines():
        m = KV.match(line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def classify(timing_text):
    if timing_text is None:
        return "NO-TIMING", {}
    kv = parse_kv(timing_text)
    if "exit_code" not in kv:
        return "PENDING", kv
    if kv["exit_code"] != "0":
        return "BAD-CONV", kv
    v = kv.get("verify_exit_code")
    if v is None:
        return "NO-VRFY", kv
    if v.startswith("skipped"):
        return "NO-VRFY", kv
    if v != "0":
        return "BAD-VRFY", kv
    return "OK", kv


def tail(path: Path, n: int) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except FileNotFoundError:
        return f"<{path.name} missing>"
    return "\n".join(lines[-n:])


def error_excerpt(path: Path, n: int) -> str:
    """Return the most relevant traceback/error from a log file.

    Strategy:
      - find the LAST 'Traceback' line; print n lines starting there,
        skipping anything below the first '/usr/bin/time -v' block.
      - if no 'Traceback', return the last n lines (excluding the time block).
    """
    try:
        lines = path.read_text(errors="replace").splitlines()
    except FileNotFoundError:
        return f"<{path.name} missing>"

    # Drop the /usr/bin/time -v section (everything from "--- /usr/bin/time -v ---" on)
    cut = next((i for i, ln in enumerate(lines)
                if ln.startswith("--- /usr/bin/time -v ---")
                or ln.startswith("Command exited with non-zero status")
                or ln.startswith("\tCommand being timed")), None)
    if cut is not None:
        lines = lines[:cut]

    tb_idx = None
    for i, ln in enumerate(lines):
        if "Traceback" in ln:
            tb_idx = i
    if tb_idx is not None:
        return "\n".join(lines[tb_idx:tb_idx + n])
    return "\n".join(lines[-n:])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    ap.add_argument("--show-tail", type=int, default=20,
                    help="Lines of stdout/verify to print on failures (default 20)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--only-fail", action="store_true")
    g.add_argument("--only-pass", action="store_true")
    g.add_argument("--only-pending", action="store_true")
    args = ap.parse_args()

    if not args.results_root.exists():
        sys.exit(f"results dir not found: {args.results_root}")

    job_dirs = []
    for task_dir in sorted(args.results_root.iterdir()):
        if not task_dir.is_dir():
            continue
        for src_dir in sorted(task_dir.iterdir()):
            if src_dir.is_dir():
                job_dirs.append((task_dir.name, src_dir.name, src_dir))

    if not job_dirs:
        sys.exit(f"no result subdirs under {args.results_root}")

    counts = {}
    rows = []
    for task, src, jdir in job_dirs:
        timing = jdir / "timing.txt"
        text = timing.read_text() if timing.exists() else None
        status, kv = classify(text)
        counts[status] = counts.get(status, 0) + 1
        rows.append((status, task, src, jdir, kv))

    fail_statuses = {"BAD-CONV", "BAD-VRFY", "NO-VRFY", "NO-TIMING"}

    width = max(len(s) for s, *_ in rows)
    for status, task, src, jdir, kv in rows:
        if args.only_fail and status not in fail_statuses:
            continue
        if args.only_pass and status != "OK":
            continue
        if args.only_pending and status != "PENDING":
            continue

        wall = kv.get("wall_seconds", "?")
        vwall = kv.get("verify_wall_seconds", "")
        pkl  = kv.get("output_pkl_size", "")
        line = f"{status:<{width}}  {task}/{src}"
        if wall != "?":
            line += f"  conv={wall}s"
        if vwall:
            line += f"  vrfy={vwall}s"
        if pkl:
            # value is e.g. "8658200608 bytes"
            try:
                nbytes = int(pkl.split()[0])
                if nbytes >= 1 << 30:
                    sz = f"{nbytes / (1 << 30):.2f}G"
                elif nbytes >= 1 << 20:
                    sz = f"{nbytes / (1 << 20):.1f}M"
                elif nbytes >= 1 << 10:
                    sz = f"{nbytes / (1 << 10):.1f}K"
                else:
                    sz = f"{nbytes}B"
            except (ValueError, IndexError):
                sz = pkl
            line += f"  pkl={sz}"

        # Throughput: (n_neurons + n_inputs + n_outputs) * (n_trials * T_mean) / wall
        if status == "OK" and wall != "?":
            shape = parse_verify_shape(jdir / "verify.txt")
            if {"n_neurons_mean", "n_inputs", "n_outputs",
                "n_trials", "T_mean"} <= shape.keys():
                work = ((shape["n_neurons_mean"]
                         + shape["n_inputs"] + shape["n_outputs"])
                        * shape["n_trials"] * shape["T_mean"])
                try:
                    tput = work / float(wall)
                    line += f"  tput={tput/1e6:.1f}Mu/s"
                except (ValueError, ZeroDivisionError):
                    pass
        print(line)

        if status in fail_statuses and args.show_tail > 0:
            if status == "BAD-CONV":
                print(f"--- error excerpt from stdout.txt ---")
                print(error_excerpt(jdir / "stdout.txt", args.show_tail))
            elif status == "BAD-VRFY":
                print(f"--- error excerpt from verify.txt ---")
                print(error_excerpt(jdir / "verify.txt", args.show_tail))
            elif status == "NO-VRFY":
                print(f"  (no verify run; check stdout.txt for missing pkl)")
            print()

    print("\nSummary:")
    for k in ("OK", "BAD-CONV", "BAD-VRFY", "NO-VRFY", "PENDING", "NO-TIMING"):
        if k in counts:
            print(f"  {k:<10} {counts[k]}")
    total_fail = sum(counts.get(k, 0) for k in fail_statuses)
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
