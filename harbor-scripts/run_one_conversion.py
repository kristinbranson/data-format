#!/usr/bin/env python3
"""
Run a single convert_data.py with timing.

Usage:
    run_one_conversion.py <task> <convert_data_py> <result_dir>

task             one of: allen2p, lee2025, majnik2025, sosa2024
convert_data_py  path to the convert_data.py to time
result_dir       permanent directory for timing.txt + stdout.txt
                 (created if missing)

Working files (data link, output pkls) go under /scratch/$USER/.
Run inside the `decoder-data-format` conda env.
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/groups/branson/home/bransonk/behavioranalysis/code/"
                 "ScienceBenchmark/data-format")

# data dir per task — mirrors the docker-compose volume mount that places
# the dataset at /app/data inside the container.
TASK_DATA_DIR = {
    "allen2p":    REPO_ROOT / "allen2p"   / "data",
    "lee2025":    REPO_ROOT / "lee2025"   / "data",
    "majnik2025": REPO_ROOT / "track2p"   / "data",
    "sosa2024":   REPO_ROOT / "sosa2024"  / "data",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("task", choices=["allen2p", "lee2025", "majnik2025", "sosa2024"])
    ap.add_argument("convert_data_py", type=Path)
    ap.add_argument("result_dir", type=Path)
    args = ap.parse_args()

    task = args.task
    script = args.convert_data_py.resolve()
    result_dir = args.result_dir
    result_dir.mkdir(parents=True, exist_ok=True)

    data_dir = TASK_DATA_DIR[task]
    env_dir = REPO_ROOT / "harbor-tasks" / task / "environment"
    train_decoder = env_dir / "train_decoder.py"
    decoder_py   = env_dir / "decoder.py"

    for p, label in [(script, "convert_data.py"),
                     (data_dir, "data dir"),
                     (train_decoder, "train_decoder.py"),
                     (decoder_py, "decoder.py")]:
        if not p.exists():
            sys.exit(f"{label} not found: {p}")

    scratch_root = Path(f"/scratch/{os.environ['USER']}")
    scratch_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"conv_timing_{task}_", dir=scratch_root))

    timing_file = result_dir / "timing.txt"
    stdout_file = result_dir / "stdout.txt"
    verify_file = result_dir / "verify.txt"
    time_report = work / "time_v.txt"
    verify_time_report = work / "verify_time_v.txt"

    out_pkl = work / "converted_data.pkl"

    try:
        os.symlink(data_dir, work / "data")
        shutil.copy2(train_decoder, work / "train_decoder.py")
        shutil.copy2(decoder_py,    work / "decoder.py")

        # Copy the script, then rewrite hard-coded "/app/data" -> work/data
        # so scripts that bypass --datadir still find the data outside docker.
        script_text = script.read_text()
        local_data = str(work / "data")
        patched = script_text.replace("/app/data", local_data)
        (work / "convert_data.py").write_text(patched)

        # Some scripts accept --datadir; others use only positional args.
        accepts_datadir = "--datadir" in script_text or "'datadir'" in script_text \
                          or '"datadir"' in script_text

        with timing_file.open("w") as fh:
            fh.write(f"task: {task}\n")
            fh.write(f"script: {script}\n")
            fh.write(f"host: {socket.gethostname()}\n")
            fh.write(f"started: {datetime.now(timezone.utc).isoformat()}\n")
            fh.write(f"slots(LSB_DJOB_NUMPROC): "
                     f"{os.environ.get('LSB_DJOB_NUMPROC', '?')}\n")
            fh.write(f"accepts_datadir: {accepts_datadir}\n")

        cmd = ["/usr/bin/time", "-v", "-o", str(time_report),
               "python3", "-u", "convert_data.py", "--full"]
        if accepts_datadir:
            cmd += ["--datadir", local_data]
        cmd += [str(out_pkl)]

        wall_start = time.monotonic()
        with stdout_file.open("w") as out:
            proc = subprocess.run(cmd, cwd=work, stdout=out,
                                  stderr=subprocess.STDOUT)
        wall_elapsed = time.monotonic() - wall_start

        with timing_file.open("a") as fh:
            if time_report.exists():
                fh.write(time_report.read_text())
            fh.write(f"\nexit_code: {proc.returncode}\n")
            fh.write(f"wall_seconds: {wall_elapsed:.2f}\n")
            fh.write(f"ended: {datetime.now(timezone.utc).isoformat()}\n")
            if out_pkl.exists():
                fh.write(f"output_pkl_size: {out_pkl.stat().st_size} bytes\n")

        # Verification step: run train_decoder.py --verify-only on the
        # produced pkl. Only attempted if conversion produced an output file.
        if out_pkl.exists():
            verify_cmd = [
                "/usr/bin/time", "-v", "-o", str(verify_time_report),
                "python3", "-u", "train_decoder.py",
                "--verify-only", str(out_pkl),
            ]
            v_start = time.monotonic()
            with verify_file.open("w") as out:
                out.write(f"verify command: {' '.join(verify_cmd)}\n\n")
                out.flush()
                v_proc = subprocess.run(verify_cmd, cwd=work,
                                        stdout=out, stderr=subprocess.STDOUT)
            v_elapsed = time.monotonic() - v_start
            with verify_file.open("a") as out:
                out.write(f"\nverify_exit_code: {v_proc.returncode}\n")
                out.write(f"verify_wall_seconds: {v_elapsed:.2f}\n")
                if verify_time_report.exists():
                    out.write("\n--- /usr/bin/time -v ---\n")
                    out.write(verify_time_report.read_text())
            with timing_file.open("a") as fh:
                fh.write(f"verify_exit_code: {v_proc.returncode}\n")
                fh.write(f"verify_wall_seconds: {v_elapsed:.2f}\n")
        else:
            with timing_file.open("a") as fh:
                fh.write("verify_exit_code: skipped (no output pkl)\n")

        sys.exit(proc.returncode)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
