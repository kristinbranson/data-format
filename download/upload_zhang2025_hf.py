#!/usr/bin/env python3
"""Mirror the zhang2025 datalimit subset to a HuggingFace dataset repo.

The point of the mirror is that a cold fetch gets the same bytes every time. Fetching from
IBL does not give that: the ONE client resolves each dataset's CURRENT default revision, so
the same query returns different files as IBL publishes corrections. Uploading the copy we
measured the reference statistics on, and pinning the commit SHA, removes that.

What is uploaded, and why:
    one_cache/            the ALF datasets, ~47 GB, plus the release index tables
    one_cache/.rest       cached Alyx metadata. NOT optional -- the release index lists
                          pre-revision paths, so without these the loaders ask Alyx which
                          revision is current and the drift comes straight back
    DATALIMIT_SUBSET.csv  the probe insertions retained
    README.md             the dataset card (CC BY 4.0 attribution, changes indicated)

Deliberately NOT uploaded:
    .fetch_complete   written locally after a download completes; it is how the fetcher
                      knows the directory is populated, so shipping it would make an
                      interrupted download look finished
    one_params.json   an Alyx auth token. Same public account whose password IBL
                      publishes, so it leaks nothing, but tokens do not belong in a
                      public repo and it can be regenerated
    .fetch.lock, .write_probe, __pycache__

Usage:
    python upload_zhang2025_hf.py --dry-run          # report what would go, upload nothing
    python upload_zhang2025_hf.py                    # do it
"""
import argparse
import os
import sys

DEFAULT_SOURCE = ("/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/"
                  "data-format/data/zhang2025_datalimit")
DEFAULT_REPO = "kristinbranson/neurodata-reuse-zhang2025"
DEFAULT_CARD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "zhang2025_dataset_card.md")   # beside this script

# Everything here is local bookkeeping or a credential; see the module docstring.
# .cache/ is the uploader's own resume state, written into the folder being uploaded --
# upload_large_folder skipped it implicitly, upload_folder does not.
IGNORE = [".fetch_complete", "one_params.json", ".fetch.lock", ".write_probe",
          ".cache/**", "**/__pycache__/**", "**/*.pyc"]


def survey(source):
    """Count what would be uploaded, split by the part that is easy to lose.

    source: str, the dataset root.
    Returns (n_files, n_bytes, n_rest_files) -- .rest is counted separately because it is
    hidden, and an upload that silently drops it still looks complete.
    """
    n_files = n_bytes = n_rest = 0
    skip = {".fetch_complete", "one_params.json", ".fetch.lock", ".write_probe"}
    for root, dirs, files in os.walk(source):
        # .cache is the uploader's resume state, not data; it appears after a first run
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".cache")]
        for name in files:
            if name in skip or name.endswith(".pyc"):
                continue
            path = os.path.join(root, name)
            n_files += 1
            n_bytes += os.path.getsize(path)
            if os.sep + ".rest" + os.sep in path + os.sep:
                n_rest += 1
    return n_files, n_bytes, n_rest


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="dataset root (default: %(default)s)")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="HF dataset repo (default: %(default)s)")
    ap.add_argument("--card", default=DEFAULT_CARD, help="dataset card to upload as README.md")
    ap.add_argument("--private", action="store_true", help="create the repo private")
    ap.add_argument("--dry-run", action="store_true", help="report and exit")
    args = ap.parse_args()

    n_files, n_bytes, n_rest = survey(args.source)
    print(f"source        {args.source}")
    print(f"to upload     {n_files} files, {n_bytes / 1024**3:.1f} GiB")
    print(f"  of which    {n_rest} cached Alyx responses under one_cache/.rest")
    print(f"repo          {args.repo} ({'private' if args.private else 'public'})")
    print(f"card          {args.card}")
    if n_rest == 0:
        sys.exit("one_cache/.rest is empty or missing; the mirror would not pin the "
                 "revisions. Populate it by reading the cache once through an "
                 "Alyx-backed ONE client (e.g. terminal-bench-science's "
                 "fetch_data.py --adopt).")
    if not os.path.exists(args.card):
        sys.exit(f"dataset card not found at {args.card}")
    if args.dry_run:
        print("\ndry run; nothing uploaded")
        return

    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(args.repo, repo_type="dataset", private=args.private, exist_ok=True)

    # upload_folder splits a large folder into multiple commits by itself, so it handles
    # a transfer this size; upload_large_folder did the same job and is deprecated.
    api.upload_folder(folder_path=args.source, repo_id=args.repo,
                      repo_type="dataset", ignore_patterns=IGNORE)
    api.upload_file(path_or_fileobj=args.card, path_in_repo="README.md",
                    repo_id=args.repo, repo_type="dataset")

    # Verify rather than assume: uploads honour .gitignore, and .rest is hidden, so a
    # silent drop is exactly the failure this mirror exists to prevent.
    listed = api.list_repo_files(args.repo, repo_type="dataset")
    rest_up = sum(1 for f in listed if f.startswith("one_cache/.rest/"))
    print(f"\nuploaded      {len(listed)} files")
    print(f"  .rest       {rest_up} of {n_rest} present in the repo")
    if rest_up != n_rest:
        sys.exit("MISMATCH: .rest did not upload completely. The mirror would fall back "
                 "to live Alyx. Re-upload it explicitly before pinning a revision.")

    sha = api.repo_info(args.repo, repo_type="dataset").sha
    print(f"\ncommit SHA    {sha}")
    print("Pin this as the zhang2025 revision in download/download.py "
          "(DATALIMIT_HF_SOURCE), and as REVISION in the terminal-bench-science task's "
          "environment/fetch_data.py.")


if __name__ == "__main__":
    main()
