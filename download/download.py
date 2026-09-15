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
    lee2025      Zenodo record 14867736 (data.zip + results.zip, extracted)
    majnik2025   Zenodo record 17091226 (data.zip, extracted)
    map          DANDI dandiset 000363 (via `dandi` CLI)
    mouseland    Figshare article 28811129
    sosa2024     DANDI dandiset 001361 (via `dandi` CLI)
    zhang2025    IBL reproducible-ephys release (via upstream code_zhang2025 caching script)

All downloaders are resumable: re-running skips files already on disk.

Pass --datalimit to fetch the 50 GB-capped variant of a dataset into
`data/<task>_datalimit/` instead of the full release, using the subset frozen in
`download/datalimit/<task>.csv`. allen2p, map and sosa2024 filter at download
time and never transfer the omitted data; hasnain2024, lee2025 and majnik2025 are
already under the cap and download in full. mouseland and zhang2025 come from
reduced copies published on Hugging Face at a pinned revision (see
DATALIMIT_HF_SOURCE); pass --from-ibl to rebuild zhang2025's copy from IBL instead.
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------- Per-task config ----------------

TASKS = {
    "allen2p":     {"kind": "allensdk"},
    "hasnain2024": {"kind": "zenodo", "record_id": "13941415"},
    # 13993254 publishes the 7 .mat files loose; 14867736 is the same series and
    # is a superset -- data.zip holds those .mat files AND behav_dict and the
    # per-animal files, results.zip holds precomputed_results. Fetching 13993254
    # gets 4.31 GB of the 15.7 GB the task ships.
    "lee2025":     {"kind": "zenodo", "record_id": "14867736", "unzip": True},
    # data.zip (9.86 GB -> 16.19 GB) alongside load_data.ipynb and README.md. No
    # wrapper directory in this one, so extract_zips only unpacks and deletes.
    "majnik2025":  {"kind": "zenodo", "record_id": "17091226", "unzip": True},
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


def extract_zips(out_dir):
    """Unpack every .zip in out_dir, flatten a single wrapper directory, delete the zips.

    Zenodo record 14867736 nests its payload one level down: data.zip holds everything
    under `data/`, while results.zip holds `precomputed_results/` at the top. Left as-is
    the first would put the .mat files at `<out_dir>/data/*.mat`, one level deeper than
    the conversion looks, which is the failure hasnain2024 hit -- a good multi-GB
    download rejected later by a layout check.

    macOS resource forks (`__MACOSX/`, `.DS_Store`) are skipped: they are packaging
    residue, and shipping them into the task image would be noise the agent has to read
    past.

    Args:
        out_dir: str, directory holding the downloaded archives; extracted in place.

    Side effects:
        Creates the extracted trees, removes each .zip and any wrapper directory named
        after its archive.
    """
    for name in sorted(os.listdir(out_dir)):
        if not name.endswith(".zip"):
            continue
        archive = os.path.join(out_dir, name)
        print(f"Extracting {name} ...")
        with zipfile.ZipFile(archive) as zf:
            members = [m for m in zf.namelist()
                       if not m.startswith("__MACOSX/")
                       and not os.path.basename(m) == ".DS_Store"]
            zf.extractall(out_dir, members=members)

        # A single top-level directory named for the archive is a wrapper: lift its
        # contents up. Renaming rather than copying -- same filesystem by construction,
        # so gigabytes move in milliseconds.
        wrapper = os.path.join(out_dir, os.path.splitext(name)[0])
        if os.path.isdir(wrapper):
            for entry in os.listdir(wrapper):
                os.replace(os.path.join(wrapper, entry), os.path.join(out_dir, entry))
            os.rmdir(wrapper)
            print(f"  flattened {os.path.basename(wrapper)}/")
        os.remove(archive)
    # __MACOSX is created by extractall for directory entries even when filtered above.
    junk = os.path.join(out_dir, "__MACOSX")
    if os.path.isdir(junk):
        shutil.rmtree(junk)


def download_figshare(article_id, out_dir):
    url = f"https://api.figshare.com/v2/articles/{article_id}/files"
    r = requests.get(url); r.raise_for_status()
    _download_files(r.json(), out_dir, name_key="name", url_key="download_url")


# ---------------- DANDI (shell out to CLI, then rename) ----------------

def download_dandi_assets(dandiset_id, out_dir, keep_paths):
    """Download only the named assets of a dandiset, via the REST API.

    Used by --datalimit, where fetching the whole dandiset and deleting most of
    it would waste the bandwidth the flag exists to save. Falls back on the same
    resumable writer as the Zenodo/Figshare paths.

    Args:
        dandiset_id: e.g. '001361'.
        out_dir: destination directory; asset paths are recreated beneath it.
        keep_paths: iterable of asset paths relative to the dandiset root, e.g.
            'sub-m11/sub-m11_ses-03_behavior+ophys.nwb'.

    Side effects:
        Writes one file per kept asset under `out_dir`.
    """
    wanted = set(keep_paths)
    base = f"https://api.dandiarchive.org/api/dandisets/{dandiset_id}/versions/draft/assets/"
    url, found = f"{base}?page_size=500", []
    while url:
        page = requests.get(url, timeout=120).json()
        for asset in page["results"]:
            if asset["path"] in wanted:
                found.append(asset)
        url = page.get("next")

    missing = wanted - {asset["path"] for asset in found}
    if missing:
        print(f"Warning: {len(missing)} manifest asset(s) not found on DANDI, "
              f"e.g. {sorted(missing)[0]}", file=sys.stderr)

    print(f"Downloading {len(found)} of {len(wanted)} requested assets from "
          f"dandiset {dandiset_id}")
    for asset in found:
        destination = os.path.join(out_dir, asset["path"])
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        _download_files(
            [{"key": os.path.basename(asset["path"]),
              "links": f"{base}{asset['asset_id']}/download/",
              "size": asset["size"]}],
            os.path.dirname(destination), name_key="key", url_key="links")


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

def download_allen2p(out_dir, keep_experiments=None):
    """Populate an AllenSDK cache with the VisualBehavior ophys experiments.

    Args:
        out_dir: cache directory.
        keep_experiments: optional set of ophys_experiment_id ints. When given
            (i.e. --datalimit), only those experiments are fetched, turning a
            247 GB download into ~48 GB.

    Side effects:
        Writes an AllenSDK S3 cache under `out_dir`.
    """
    import warnings
    warnings.filterwarnings("ignore", message="Ignoring the following cached namespace")
    import allensdk.brain_observatory.behavior.behavior_project_cache as bpc

    os.makedirs(out_dir, exist_ok=True)
    print(f"Initializing AllenSDK cache at {out_dir} ...")
    bc = bpc.VisualBehaviorOphysProjectCache.from_s3_cache(cache_dir=out_dir)

    table = bc.get_ophys_experiment_table()
    vb = table[table.project_code == "VisualBehavior"]
    if keep_experiments is not None:
        vb = vb[vb.index.isin(keep_experiments)]
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


def download_zhang2025_datalimit(out_dir, eids):
    """Cache only the named IBL sessions, via the ONE api.

    The upstream caching script populates its cache one eid at a time --
    `prepare_data(one, eid, ...)` calls `one.eid2pid(eid)` and then
    `load_spiking_data(one, pid, ...)` (`ibl_data_utils.py:727-740`), each of
    which downloads on demand. So the set of eids processed *is* the set of data
    fetched; the only thing the upstream `--n_sessions` flag cannot do is express
    an arbitrary eid list, since it slices a fixed release list.

    This fetches every dataset the release holds for each requested session, so
    the result matches a full-release cache restricted to those sessions.

    Args:
        out_dir: destination; the ONE cache is created at `<out_dir>/one_cache`.
        eids: iterable of session eids from the datalimit manifest.

    Side effects:
        Downloads roughly 1.3 GB per session into the cache.
    """
    from one.api import ONE

    cache_dir = os.path.join(out_dir, "one_cache")
    os.makedirs(cache_dir, exist_ok=True)
    one = ONE(base_url="https://openalyx.internationalbrainlab.org",
              password="international", silent=True, cache_dir=cache_dir)
    one.load_cache(tag="Brainwidemap")

    eids = list(eids)
    print(f"Caching {len(eids)} of the release's sessions into {cache_dir}")
    for index, eid in enumerate(eids, start=1):
        datasets = one.list_datasets(eid, details=False)
        failed = 0
        for dataset in datasets:
            try:
                one.load_dataset(eid, dataset, download_only=True)
            except Exception as error:  # a missing revision shouldn't abort the run
                failed += 1
                if failed == 1:
                    print(f"  [{index}/{len(eids)}] {eid}: {dataset} failed ({error})",
                          file=sys.stderr)
        print(f"  [{index}/{len(eids)}] {eid}: {len(datasets) - failed} datasets"
              + (f", {failed} failed" if failed else ""))


# ---------------- Entry point ----------------

# ---------------- datalimit (50 GB-capped) variants ----------------

# Capped datasets that --datalimit fetches as an already-reduced copy from Hugging
# Face, rather than filtering the original source. The FULL tasks still download
# from their original sources; only the dataset-size-capped variants come from here.
#
#   mouseland  its subset lives *inside* the published files: a per-session cell
#              subsample, and figshare serves whole .npy files, so nothing can be
#              filtered at download time. Publishing the reduced copy spares every
#              user a 412 GB download to keep 47.
#   zhang2025  its subset CAN be fetched from IBL (download_zhang2025_datalimit),
#              but not reproducibly: the ONE client resolves each dataset's current
#              default revision, so the same query returns different files once IBL
#              publishes corrections. The mirror is the copy the reference statistics
#              were computed on, including the one_cache/.rest metadata that pins
#              revisions offline. --from-ibl still rebuilds it from the source.
#
# Pinned to a revision, not a branch: the point of the dataset-size-capped variant is
# that every run sees the same bytes, and a moving `main` would silently change the
# dataset.
#
# This is distribution, not production. mouseland's copy is built by
# `download/make_datalimit.py mouseland`, zhang2025's by `download.py zhang2025
# --datalimit --from-ibl`, and uploaded with download/upload_zhang2025_hf.py for the
# latter. Rebuild, re-upload, and update the revision below if a subset ever changes.
DATALIMIT_HF_SOURCE = {
    "mouseland": {
        "repo_id": "kristinbranson/neurodata-reuse-zhong2025",
        "revision": "82c2c31abe3e22672b40be58f749a03475b70f63",
    },
    "zhang2025": {
        "repo_id": "kristinbranson/neurodata-reuse-zhang2025",
        "revision": "b134ad2d41cc7ad3c2ac5a3f70b02287c47ce210",
    },
}

# huggingface_hub's default transfer backend, Xet, stalls on the zhang2025 mirror:
# every download thread blocks at zero bytes, reproduced three times at ~33 GB of 46
# (terminal-bench-science zhang2025 fork, commit bb0bfd9). Plain HTTP finishes the same
# download in ~5 minutes. huggingface_hub reads this at import time.
HF_DISABLE_XET_ENV = "HF_HUB_DISABLE_XET"


def load_datalimit_manifest(task):
    """Read the frozen subset manifest for a task.

    Args:
        task: benchmark task name.

    Returns:
        DataFrame of the manifest body. Empty when the dataset is already under
        the cap and is kept whole.
    """
    manifest = REPO_ROOT / "download" / "datalimit" / f"{task}.csv"
    if not manifest.exists():
        # RuntimeError, not sys.exit: main() catches Exception per task, so one
        # missing manifest must not abort a multi-task run.
        raise RuntimeError(f"no datalimit manifest at {manifest}; generate it with "
                           f"`python download/select_datalimit.py {task}`")
    import pandas as pd
    return pd.read_csv(manifest, comment="#")


def download_datalimit_from_hf(task, out_dir):
    """Fetch a pre-reduced dataset-size-capped dataset from Hugging Face.

    For tasks whose subset cannot be expressed as a choice of files to download,
    the reduced copy is published rather than rebuilt by every user. See
    DATALIMIT_HF_SOURCE for why it is pinned to a revision.

    Args:
        task: benchmark task name; must be a key of DATALIMIT_HF_SOURCE.
        out_dir: str or Path to populate. Created if absent.

    Returns:
        Path, the populated directory.

    Side effects:
        Downloads into `out_dir`. Re-running is cheap: huggingface_hub verifies
        each file against the revision and skips what already matches.
        Sets HF_HUB_DISABLE_XET=1 in this process's environment unless already set.

    Raises:
        RuntimeError: if huggingface_hub is not installed.
    """
    src = DATALIMIT_HF_SOURCE[task]
    out_dir = Path(out_dir)
    # Must precede the import below; see HF_DISABLE_XET_ENV.
    os.environ.setdefault(HF_DISABLE_XET_ENV, "1")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        raise RuntimeError(
            f"{task} --datalimit needs huggingface_hub:  pip install huggingface_hub")

    print(f"{task}: fetching dataset-size-capped dataset from {src['repo_id']} "
          f"@ {src['revision'][:12]}")
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=src["repo_id"],
        revision=src["revision"],
        repo_type="dataset",
        local_dir=str(out_dir),
    )
    return out_dir


def _run_one(task, out_dir, n_sessions, n_workers, datalimit=False, from_ibl=False):
    cfg = TASKS[task]
    kind = cfg["kind"]

    # --from-ibl only has an alternative to offer for zhang2025; mouseland's subset
    # is rebuilt with make_datalimit.py, not downloaded.
    use_mirror = task in DATALIMIT_HF_SOURCE and not (from_ibl and task == "zhang2025")
    if datalimit and use_mirror:
        # Already-reduced copy: fetch it whole, no manifest to filter against.
        return download_datalimit_from_hf(task, out_dir)

    entries = load_datalimit_manifest(task) if datalimit else None

    if kind == "zenodo":
        # hasnain2024 / lee2025 / majnik2025 are already under the cap: the
        # datalimit variant is the complete dataset.
        download_zenodo(cfg["record_id"], out_dir)
        if cfg.get("unzip"):
            extract_zips(out_dir)
    elif kind == "figshare":
        download_figshare(cfg["article_id"], out_dir)
    elif kind == "dandi":
        if datalimit:
            download_dandi_assets(cfg["dandiset"], out_dir, entries.nwb_path)
        else:
            download_dandi(cfg["dandiset"], out_dir)
    elif kind == "allensdk":
        keep = None
        if datalimit:
            keep = set(entries.ophys_experiment_id)
        download_allen2p(out_dir, keep_experiments=keep)
    elif kind == "zhang2025":
        if datalimit:
            download_zhang2025_datalimit(out_dir, entries.eid)
        else:
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
    ap.add_argument("--datalimit", action="store_true",
                    help="Download the 50 GB-capped variant into data/<task>_datalimit, "
                         "using the subset frozen in download/datalimit/<task>.csv. "
                         "mouseland and zhang2025 come from pinned Hugging Face copies.")
    ap.add_argument("--from-ibl", action="store_true",
                    help="(zhang2025 --datalimit only) rebuild the dataset-size-capped "
                         "copy from IBL through the ONE api instead of the Hugging Face "
                         "copy. Not reproducible: returns different files once IBL "
                         "publishes new dataset revisions.")
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
        suffix = "_datalimit" if args.datalimit else ""
        out_dir = args.output_dir or str(REPO_ROOT / "data" / f"{task}{suffix}")
        print(f"\n========== [{i}/{len(tasks)}] {task}{suffix}  ->  {out_dir} ==========")
        try:
            _run_one(task, out_dir, args.n_sessions, args.n_workers,
                     datalimit=args.datalimit, from_ibl=args.from_ibl)
        except Exception as e:
            print(f"!! {task} FAILED: {e}", file=sys.stderr)
            failures.append(task)

    if failures:
        print(f"\nFailed tasks: {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
