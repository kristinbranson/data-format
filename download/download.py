"""Download raw data for any of the benchmark's datasets.

Usage:
    python download/download.py <task> [<task> ...] [--output-dir DIR]
    python download/download.py --all

Each task's data goes to `<repo_root>/data/<task>/` by default. The
`--output-dir` flag overrides the destination and is only valid when
exactly one task is requested.

Supported tasks and where each one's data is fetched from:

    allen2p      Allen Brain Observatory: Visual Behavior 2P (via AllenSDK S3 cache)
    hasnain2024  Zenodo record 13941415
    lee2025      Zenodo record 13993254
    majnik2025   Zenodo record 17091226
    map          DANDI dandiset 000363 (via `dandi` CLI)
    mouseland    Figshare article 28811129
    sosa2024     DANDI dandiset 001361 (via `dandi` CLI)
    zhang2025    IBL reproducible-ephys release (via upstream code_zhang2025 caching script)

All downloaders are resumable: re-running skips files already on disk.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------- Per-task config ----------------

TASKS = {
    "allen2p":     {"kind": "allensdk"},
    "hasnain2024": {"kind": "zenodo", "record_id": "13941415"},
    "lee2025":     {"kind": "zenodo", "record_id": "13993254"},
    "majnik2025":  {"kind": "zenodo", "record_id": "17091226"},
    "map":         {"kind": "dandi",  "dandiset": "000363"},
    "mouseland":   {"kind": "figshare", "article_id": "28811129"},
    "sosa2024":    {"kind": "dandi",  "dandiset": "001361"},
    "zhang2025":   {"kind": "zhang2025"},
}


# ---------------- Zenodo / Figshare downloaders (shared loop) ----------------

def _download_files(files, out_dir, *, name_key, url_key):
    os.makedirs(out_dir, exist_ok=True)
    for fileinfo in files:
        filename = fileinfo[name_key]
        download_url = fileinfo[url_key] if isinstance(fileinfo[url_key], str) \
                       else fileinfo[url_key]["self"]
        remote_size = fileinfo.get("size")

        local_path = os.path.join(out_dir, filename)
        existing_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

        if remote_size is not None:
            if existing_size == remote_size:
                print(f"Skipping {filename} (already fully downloaded).")
                continue
            elif existing_size > remote_size:
                print(f"Warning: local {filename} larger than remote "
                      f"({existing_size} > {remote_size}); skipping.")
                continue

        headers, mode = {}, "wb"
        if existing_size > 0:
            print(f"Resuming {filename} from byte {existing_size}...")
            headers["Range"] = f"bytes={existing_size}-"
            mode = "ab"
        else:
            print(f"Downloading {filename} from scratch...")

        with requests.get(download_url, headers=headers, stream=True,
                          allow_redirects=True) as resp:
            if resp.status_code not in (200, 206):
                resp.raise_for_status()
            with open(local_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        final_size = os.path.getsize(local_path)
        if remote_size is not None and final_size != remote_size:
            print(f"Warning: size mismatch for {filename} "
                  f"(local {final_size}, remote {remote_size}).")
        else:
            print(f"Finished {filename} ({final_size} bytes).")


def download_zenodo(record_id, out_dir):
    url = f"https://zenodo.org/api/records/{record_id}"
    r = requests.get(url); r.raise_for_status()
    _download_files(r.json()["files"], out_dir, name_key="key", url_key="links")


def download_figshare(article_id, out_dir):
    url = f"https://api.figshare.com/v2/articles/{article_id}/files"
    r = requests.get(url); r.raise_for_status()
    _download_files(r.json(), out_dir, name_key="name", url_key="download_url")


# ---------------- DANDI (shell out to CLI, then rename) ----------------

def download_dandi(dandiset_id, out_dir):
    if not shutil.which("dandi"):
        sys.exit("dandi CLI not found on PATH. Install with `pip install dandi`.")
    out = Path(out_dir).resolve()
    parent = out.parent
    parent.mkdir(parents=True, exist_ok=True)
    # dandi requires the parent to exist; it will create parent/<dandiset_id>/.
    url = f"https://dandiarchive.org/dandiset/{dandiset_id}"
    subprocess.run(["dandi", "download", "-o", str(parent), url], check=True)
    nested = parent / dandiset_id
    if nested.exists() and nested != out:
        # Move into the requested task-named dir (e.g. data/000363 -> data/map).
        if out.exists():
            # Already populated from a prior run; just merge by replacing.
            print(f"Note: {out} already exists; replacing with newly downloaded data.")
            shutil.rmtree(out)
        nested.rename(out)
    print(f"Done. DANDI dandiset {dandiset_id} downloaded to {out}")


# ---------------- AllenSDK (Visual Behavior 2P) ----------------

def download_allen2p(out_dir):
    import warnings
    warnings.filterwarnings("ignore", message="Ignoring the following cached namespace")
    import allensdk.brain_observatory.behavior.behavior_project_cache as bpc

    os.makedirs(out_dir, exist_ok=True)
    print(f"Initializing AllenSDK cache at {out_dir} ...")
    bc = bpc.VisualBehaviorOphysProjectCache.from_s3_cache(cache_dir=out_dir)

    table = bc.get_ophys_experiment_table()
    vb = table[table.project_code == "VisualBehavior"]
    print(f"VisualBehavior project: {len(vb)} experiments across "
          f"{vb.mouse_id.nunique()} mice")

    for i, exp_id in enumerate(vb.index, start=1):
        try:
            bc.get_behavior_ophys_experiment(exp_id)
        except Exception as e:
            print(f"  [{i}/{len(vb)}] {exp_id}: FAILED — {e}", file=sys.stderr)
            continue
        if i == 1 or i % 25 == 0 or i == len(vb):
            print(f"  [{i}/{len(vb)}] {exp_id}")
    print(f"Done. Cache directory: {out_dir}")


# ---------------- zhang2025 (shell out to upstream caching script) ----------------

def download_zhang2025(out_dir, n_sessions=10, n_workers=1):
    code_dir = REPO_ROOT / "harbor-tasks" / "zhang2025" / "environment" / "code" / "code_zhang2025"
    cache_script = code_dir / "src" / "0_data_caching.py"
    if not cache_script.exists():
        sys.exit(f"Upstream caching script not found at {cache_script}")

    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, str(cache_script),
           "--datasets", "reproducible-ephys",
           "--n_sessions", str(n_sessions),
           "--n_workers", str(n_workers),
           "--base_path", str(out)]
    print("Running:", " ".join(cmd))
    print("From:   ", code_dir)
    # Upstream uses relative paths under code_zhang2025/, so cd there first.
    subprocess.run(cmd, cwd=code_dir, check=True)


# ---------------- Entry point ----------------

def _run_one(task, out_dir, n_sessions, n_workers):
    cfg = TASKS[task]
    kind = cfg["kind"]
    if kind == "zenodo":
        download_zenodo(cfg["record_id"], out_dir)
    elif kind == "figshare":
        download_figshare(cfg["article_id"], out_dir)
    elif kind == "dandi":
        download_dandi(cfg["dandiset"], out_dir)
    elif kind == "allensdk":
        download_allen2p(out_dir)
    elif kind == "zhang2025":
        download_zhang2025(out_dir, n_sessions=n_sessions, n_workers=n_workers)
    else:
        sys.exit(f"Unknown kind: {kind}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks", nargs="*", choices=sorted(TASKS.keys()),
                    help="One or more datasets to download.")
    ap.add_argument("--all", action="store_true",
                    help="Download every supported dataset.")
    ap.add_argument("--output-dir", "-o", default=None,
                    help="Override output directory. Only valid with a single task; "
                         "ignored otherwise. Default: data/<task> in repo root.")
    ap.add_argument("--n-sessions", type=int, default=10,
                    help="(zhang2025 only) sessions to cache. Default: 10.")
    ap.add_argument("--n-workers", type=int, default=1,
                    help="(zhang2025 only) parallel workers. Default: 1.")
    args = ap.parse_args()

    if args.all:
        if args.tasks:
            sys.exit("Pass either --all or explicit task names, not both.")
        tasks = sorted(TASKS.keys())
    else:
        if not args.tasks:
            ap.error("Specify at least one task, or pass --all.")
        tasks = args.tasks

    if args.output_dir and len(tasks) > 1:
        sys.exit("--output-dir is only valid when downloading a single task.")

    failures = []
    for i, task in enumerate(tasks, start=1):
        out_dir = args.output_dir or str(REPO_ROOT / "data" / task)
        print(f"\n========== [{i}/{len(tasks)}] {task}  ->  {out_dir} ==========")
        try:
            _run_one(task, out_dir, args.n_sessions, args.n_workers)
        except Exception as e:
            print(f"!! {task} FAILED: {e}", file=sys.stderr)
            failures.append(task)

    if failures:
        print(f"\nFailed tasks: {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
