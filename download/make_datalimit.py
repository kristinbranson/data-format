"""Build `data/<task>_datalimit/` trees from the full datasets and the manifests.

Reads the subset decisions frozen in `download/datalimit/<task>.csv` (written by
`select_datalimit.py`) and materialises each 50 GB-capped dataset.

Materialisation strategy, in order of preference:
  hardlink -> copy.
Symlinks are deliberately NOT used for files *inside* a dataset: harbor bind-mounts
the dataset directory into the container, and a symlink pointing at a host path
outside the mount dangles once inside. A symlink for the whole `<task>_datalimit`
directory is fine (docker resolves the mount source on the host), and is what the
already-under-cap datasets use.

Hardlinks fail for `allen2p`, whose files are owned by another user, so those are
copied; every other dataset hardlinks and costs no extra disk.

Downloaded caches are never edited. AllenSDK's metadata tables and the ONE release
index are copied verbatim, so each `<task>_datalimit` tree is exactly what a real
download of those files would produce -- the indexes still describe the full
release and will refer to recordings that are not present. Keeping the agent
inside the cap is therefore an *instruction*, not a crippled cache: every built
dataset carries a `DATALIMIT_SUBSET.csv` listing precisely what to use, and the
`<task>_datalimit` prompt names the same subset.

One dataset needs real rewriting:
  * mouseland -- cells are subsampled inside each session's arrays.

Usage:
    python download/make_datalimit.py                      # all tasks
    python download/make_datalimit.py sosa2024 map
    python download/make_datalimit.py mouseland            # slow: rewrites ~440 GB
    python download/make_datalimit.py --dry-run
    python download/make_datalimit.py --data-root /path/to/data

mouseland is by far the slowest task: its `spk/*.npy` are pickled object arrays
that cannot be memory-mapped, so each of the 89 sessions costs a full 1.5-7.4 GB
load. Run it on its own and expect hours.
"""

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "download"))

from select_datalimit import MANIFEST_DIR, gb, read_manifest  # noqa: E402

# The ONE release-index directories that sit beside the lab folders in one_cache.
# Each holds sessions.pqt / datasets.pqt describing the whole release.
ONE_INDEX_DIRS = ("Brainwidemap", "2022_Q4_IBL_et_al_BWM", "2025_Q3_IBL_et_al_BWM")


# ---------------- materialisation helpers ----------------


def place(src: Path, dst: Path, mode: str = "auto") -> str:
    """Materialise `src` at `dst` as a hardlink or a copy.

    Args:
        src: existing file.
        dst: destination path; parent directories are created.
        mode: 'auto' tries a hardlink then falls back to copying; 'hardlink' and
            'copy' force one strategy.

    Returns:
        The strategy actually used: 'hardlink', 'copy', or 'skip' if dst existed.

    Side effects:
        Creates `dst` and its parents.
    """
    if dst.exists():
        return "skip"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode in ("auto", "hardlink"):
        try:
            os.link(src, dst)
            return "hardlink"
        except OSError:
            if mode == "hardlink":
                raise
    shutil.copy2(src, dst)
    return "copy"


def place_tree(src_dir: Path, dst_dir: Path, mode: str = "auto") -> int:
    """Materialise every file under `src_dir` at the same relative path in `dst_dir`.

    Args:
        src_dir: directory to replicate.
        dst_dir: destination root.
        mode: passed through to `place`.

    Returns:
        Number of files materialised.
    """
    count = 0
    for root, _, filenames in os.walk(src_dir):
        for name in filenames:
            source = Path(root) / name
            place(source, dst_dir / source.relative_to(src_dir), mode)
            count += 1
    return count


def reset_output(path: Path, dry_run: bool) -> None:
    """Remove a previously built `<task>_datalimit` tree so the build starts clean.

    Args:
        path: the output directory or symlink.
        dry_run: if True, only report what would be removed.

    Side effects:
        Deletes `path` recursively (or unlinks it, if it is a symlink).
    """
    if not (path.exists() or path.is_symlink()):
        return
    print(f"    removing existing {path}")
    if dry_run:
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


# ---------------- per-task builders ----------------


def build_passthrough(task: str, full: Path, out: Path, mode: str, dry_run: bool) -> None:
    """Point `<task>_datalimit` at the full dataset, which is already under the cap.

    A directory-level symlink is safe here: harbor resolves the bind-mount source
    on the host, and `data/mouseland` and `data/zhang2025` already work this way.

    Args:
        task: benchmark task name.
        full: `<data-root>/<task>`.
        out: `<data-root>/<task>_datalimit`.
        mode: unused; kept for a uniform builder signature.
        dry_run: if True, report without creating anything.
    """
    print(f"    symlink {out.name} -> {full.name} (already under cap, nothing subsampled)")
    if not dry_run:
        out.symlink_to(full.name)


def build_from_file_list(task: str, full: Path, out: Path, entries: list[str],
                         mode: str, dry_run: bool) -> None:
    """Materialise a list of dataset-relative file paths.

    Used by `sosa2024` (whole mice) and `map` (whole sessions), whose manifests
    name NWB files directly.

    Args:
        task: benchmark task name.
        full: `<data-root>/<task>`.
        out: `<data-root>/<task>_datalimit`.
        entries: dataset-relative file paths to keep.
        mode: passed to `place`.
        dry_run: if True, report without creating anything.
    """
    print(f"    {len(entries)} files")
    if dry_run:
        return
    strategies = set()
    for relative in entries.nwb_path:
        strategies.add(place(full / relative, out / relative, mode))
    # Carry across small top-level metadata (dandiset.yaml, README, ...).
    for extra in sorted(full.iterdir()):
        if extra.is_file():
            place(extra, out / extra.name, mode)
    print(f"    placed via {'/'.join(sorted(strategies - {'skip'})) or 'skip'}")


def build_allen2p(task: str, full: Path, out: Path, entries: list[str],
                  mode: str, dry_run: bool) -> None:
    """Materialise the kept experiments, leaving every AllenSDK index untouched.

    The metadata tables and cache manifests are copied verbatim: they describe
    the released dataset, and rewriting them would leave a cache that no download
    could ever have produced. The subset is instead communicated to the agent --
    as `DATALIMIT_SUBSET.csv` beside the data, and as an explicit instruction in
    the task prompt naming the mice to use.

    Args:
        task: 'allen2p'.
        full: `<data-root>/allen2p`.
        out: `<data-root>/allen2p_datalimit`.
        entries: `<ophys_experiment_id>\t<nwb filename>` rows to keep.
        mode: passed to `place`.
        dry_run: if True, report without creating anything.
    """
    import pandas as pd

    release_name = "visual-behavior-ophys-1.1.0"
    src_release = full / release_name
    dst_release = out / release_name
    kept_ids = entries.ophys_experiment_id.tolist()
    filenames = entries.nwb_filename.tolist()

    experiments = pd.read_csv(src_release / "project_metadata" / "ophys_experiment_table.csv")
    kept_mice = sorted(set(experiments[experiments.ophys_experiment_id.isin(kept_ids)].mouse_id))
    print(f"    {len(entries)} experiments, {len(kept_mice)} mice "
          f"(copied, not hardlinked: files are owned by another user)")
    if dry_run:
        return

    for name in filenames:
        place(src_release / "behavior_ophys_experiments" / name,
              dst_release / "behavior_ophys_experiments" / name, mode)

    # Metadata tables copied unchanged -- they are part of the release.
    for csv_path in sorted((src_release / "project_metadata").glob("*.csv")):
        place(csv_path, dst_release / "project_metadata" / csv_path.name, mode)
    print(f"      project_metadata/*.csv copied unmodified")


def write_subset_table(out: Path, task: str, entries: list[str], full: Path) -> Path:
    """Publish the subset of data the agent is instructed to use, as a CSV.

    Always `DATALIMIT_SUBSET.csv`, so there is exactly one file and one format to
    learn across the benchmark. Where the task already has a canonical table
    naming which recordings to process, the subset is a filtered copy of it with
    identical columns, so existing code can read it unchanged:

      * zhang2025 -- `bwm_release.csv`, the upstream release freeze read by
        `code_zhang2025/src/0_data_caching.py` and passed to `prepare_data` as
        `bwm_df`. One row per probe insertion, so a kept session contributes all
        of its probes.
      * allen2p -- `project_metadata/ophys_experiment_table.csv`, the release
        table the conversion filters on.

    The remaining tasks address their data by file path or session name, so they
    get a minimal table in those terms. No original is ever modified.

    Args:
        out: directory to write into.
        task: benchmark task name.
        entries: manifest DataFrame, api identifier in the first column.
        full: the full dataset directory, for allen2p's release table.

    Returns:
        The path written.
    """
    import pandas as pd

    ids = entries.iloc[:, 0].tolist()
    path = out / "DATALIMIT_SUBSET.csv"

    if task == "zhang2025":
        source = REPO_ROOT / ("harbor-tasks/zhang2025/environment/code/code_zhang2025"
                              "/data/bwm_release.csv")
        table = pd.read_csv(source, index_col=0)
        subset = table[table.eid.isin(ids)]
        # Source has a leading unnamed row-number column and is read back with
        # index_col=0, so keep the index to stay schema-identical.
        subset.to_csv(path)
        summary = (f"{len(subset)} of {len(table)} {source.name} rows -- "
                   f"{subset.eid.nunique()} sessions, {subset.subject.nunique()} subjects")
    elif task == "allen2p":
        source = (full / "visual-behavior-ophys-1.1.0" / "project_metadata"
                  / "ophys_experiment_table.csv")
        table = pd.read_csv(source)
        subset = table[table.ophys_experiment_id.isin({int(i) for i in ids})]
        subset.to_csv(path, index=False)
        summary = (f"{len(subset)} of {len(table)} {source.name} rows -- "
                   f"{len(subset)} experiments, {subset.mouse_id.nunique()} mice")
    elif task == "mouseland":
        subset = entries
        subset.to_csv(path, index=False)
        summary = (f"{len(subset)} sessions, "
                   f"{subset.n_cells_kept.astype(int).sum():,} of "
                   f"{subset.n_cells_total.astype(int).sum():,} cells")
    else:
        # map, sosa2024: addressed by NWB path, e.g. sub-m11/sub-m11_ses-03_....nwb
        subset = entries
        subset.to_csv(path, index=False)
        summary = f"{len(subset)} sessions, {subset.subject.nunique()} subjects"

    print(f"      wrote {path.relative_to(out.parent)}: {summary}")
    return path


def build_zhang2025(task: str, full: Path, out: Path, entries: list[str],
                    mode: str, dry_run: bool) -> None:
    """Materialise the kept ONE session directories, leaving the index untouched.

    The release index (`one_cache/<tag>/{sessions,datasets}.pqt`) is copied
    verbatim. Rewriting it would both misrepresent the release and be futile:
    `OneAlyx.load_cache(tag=...)` re-downloads the remote index whenever the local
    one looks stale or differently tagged (`one/api.py:1740`), so any edit is
    liable to be overwritten mid-run. The subset is communicated to the agent
    instead, via `DATALIMIT_SUBSET.csv` and the task prompt.

    Args:
        task: 'zhang2025'.
        full: `<data-root>/zhang2025`.
        out: `<data-root>/zhang2025_datalimit`.
        entries: `<eid>\t<session dir relative to one_cache>` rows.
        mode: passed to `place`.
        dry_run: if True, report without creating anything.
    """
    src_cache = full / "one_cache"
    dst_cache = out / "one_cache"
    session_dirs = entries.session_path.tolist()
    subjects = {tuple(path.split("/")[:3:2]) for path in session_dirs}
    print(f"    {len(entries)} sessions, {len(subjects)} subjects")
    if dry_run:
        return

    total_files = 0
    for relative in session_dirs:
        total_files += place_tree(src_cache / relative, dst_cache / relative, mode)
    print(f"      {total_files} session files placed")

    for index_name in ONE_INDEX_DIRS:
        src_index = src_cache / index_name
        if src_index.is_dir():
            place_tree(src_index, dst_cache / index_name, mode)
            print(f"      {index_name}/ copied unmodified")


def build_mouseland(task: str, full: Path, out: Path, entries: list[str],
                    params: dict, mode: str, dry_run: bool) -> None:
    """Rewrite each session's arrays with a random subset of its cells.

    The only dataset cut on the cell axis, and the only one whose files are
    genuinely rewritten. Per session:
      * `spk/<session>_neural_data.npy` is a 0-d pickled object array holding
        `{'spks': [plane arrays]}`, each plane `(n_cells_plane, n_timebins)`
        float32. The reference concatenates the planes along axis 0
        (`manual/zhong2025/convert_data.py:126-128`).
      * `retinotopy/<mouse>_<Y>_<M>_<D>_trans.npz` holds per-cell arrays
        (`xpos`, `ypos`, `xy_t`, `iarea`) indexed in that same concatenated order.
    A single index is drawn over the concatenated cells, then split back per
    plane, so the two files stay aligned.

    `beh/` is behaviour, not cells, and is carried across untouched.

    Args:
        task: 'mouseland'.
        full: `<data-root>/mouseland`.
        out: `<data-root>/mouseland_datalimit`.
        entries: `<session>\t<n_cells_total>\t<n_cells_kept>` rows.
        params: manifest params; must contain 'cell_fraction' and 'seed'.
        mode: passed to `place` for the untouched `beh/` tree.
        dry_run: if True, report without creating anything.
    """
    seed = int(params["seed"])
    print(f"    {len(entries)} sessions, cell fraction {params['cell_fraction']}, seed {seed}")
    if dry_run:
        return

    place_tree(full / "beh", out / "beh", mode)
    (out / "spk").mkdir(parents=True, exist_ok=True)
    (out / "retinotopy").mkdir(parents=True, exist_ok=True)

    for index, row in enumerate(entries.itertuples(), start=1):
        session = row.session
        n_cells, n_keep = int(row.n_cells_total), int(row.n_cells_kept)
        date_key = "_".join(session.split("_")[:4])  # retinotopy names drop the run number

        # Derive the index from (seed, session) so each session is reproducible
        # on its own and the draw does not depend on processing order. Uses a
        # stable digest rather than hash(), which is salted per interpreter run.
        session_key = int.from_bytes(hashlib.sha256(session.encode()).digest()[:4], "big")
        rng = np.random.default_rng(np.random.SeedSequence(entropy=[seed, session_key]))
        keep_index = np.sort(rng.choice(n_cells, size=n_keep, replace=False))  # (n_keep,)

        spikes = np.load(full / "spk" / f"{session}_neural_data.npy",
                         allow_pickle=True).item()
        planes = spikes["spks"]  # list of (n_cells_plane, n_timebins) float32
        offsets = np.cumsum([0] + [plane.shape[0] for plane in planes])
        if offsets[-1] != n_cells:
            raise RuntimeError(f"{session}: spk has {offsets[-1]} cells, "
                               f"retinotopy has {n_cells}")
        kept_planes = []
        for plane_number, plane in enumerate(planes):
            lo, hi = offsets[plane_number], offsets[plane_number + 1]
            within = keep_index[(keep_index >= lo) & (keep_index < hi)] - lo
            kept_planes.append(plane[within])  # (n_kept_plane, n_timebins)
        spikes["spks"] = kept_planes
        np.save(out / "spk" / f"{session}_neural_data.npy",
                np.array(spikes, dtype=object), allow_pickle=True)

        with np.load(full / "retinotopy" / f"{date_key}_trans.npz", allow_pickle=True) as npz:
            trans = {key: npz[key] for key in npz.files}
        for key in ("xpos", "ypos", "iarea", "xy_t"):
            if key in trans and trans[key].shape[0] == n_cells:
                trans[key] = trans[key][keep_index]
        np.savez(out / "retinotopy" / f"{date_key}_trans.npz", **trans)

        print(f"      [{index}/{len(entries)}] {session}: {n_keep} of {n_cells} cells")


# Where DATALIMIT_SUBSET.csv has to go so the container can read it. Every task
# mounts its dataset root at /app/data except allen2p, which mounts only the
# release subdirectory -- a file at that dataset's root would be invisible.
SUBSET_LIST_SUBDIR = {"allen2p": "visual-behavior-ophys-1.1.0"}

# Task-specific sentence appended to the list's preamble, explaining what the
# entries are and how they map onto what the client's own api will report.
# Already under the 50 GB cap: the datalimit variant is the full dataset.
PASSTHROUGH_TASKS = ("hasnain2024", "lee2025", "majnik2025")
ALL_TASKS = sorted(PASSTHROUGH_TASKS
                   + ("allen2p", "map", "mouseland", "sosa2024", "zhang2025"))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    all_tasks = ALL_TASKS
    parser.add_argument("tasks", nargs="*", choices=all_tasks,
                        help="Tasks to build. Default: all.")
    parser.add_argument("--data-root", default=str(REPO_ROOT / "data"),
                        help="Directory holding the full datasets. Default: <repo>/data")
    parser.add_argument("--link-mode", choices=("auto", "hardlink", "copy"), default="auto",
                        help="How to materialise files. Default: auto (hardlink, else copy).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be built without touching disk.")
    parser.add_argument("--force", action="store_true",
                        help="Remove an existing <task>_datalimit tree first.")
    args = parser.parse_args()

    tasks = args.tasks or all_tasks
    data_root = Path(args.data_root)

    failures = []
    for task in tasks:
        full = data_root / task
        out = data_root / f"{task}_datalimit"
        print(f"\n=== {task}_datalimit  ->  {out}")
        if not full.exists():
            print(f"!! {full} not found; skipping", file=sys.stderr)
            failures.append(task)
            continue

        manifest_path = MANIFEST_DIR / f"{task}.csv"
        if not manifest_path.exists():
            print(f"!! {manifest_path} not found; run select_datalimit.py first",
                  file=sys.stderr)
            failures.append(task)
            continue
        entries, header = read_manifest(manifest_path)
        print(f"    rule: {header.get('rule', '?')}")

        if args.force:
            reset_output(out, args.dry_run)
        elif out.exists() or out.is_symlink():
            print(f"!! {out} already exists; pass --force to rebuild", file=sys.stderr)
            failures.append(task)
            continue

        try:
            if task in PASSTHROUGH_TASKS:
                build_passthrough(task, full, out, args.link_mode, args.dry_run)
            elif task == "mouseland":
                params = {"cell_fraction": float(header["param cell_fraction"]),
                          "seed": int(header["param seed"])}
                build_mouseland(task, full, out, entries, params,
                                args.link_mode, args.dry_run)
            elif task == "allen2p":
                build_allen2p(task, full, out, entries, args.link_mode, args.dry_run)
            elif task == "zhang2025":
                build_zhang2025(task, full, out, entries, args.link_mode, args.dry_run)
            else:
                build_from_file_list(task, full, out, entries, args.link_mode, args.dry_run)

            # Drop the "use exactly this" list beside the data. It must land where
            # the container can see it: allen2p mounts the release subdirectory,
            # every other task mounts the dataset root. Passthrough tasks are
            # symlinks to the full dataset and get no list -- nothing was dropped.
            # One subset file per dataset, always DATALIMIT_SUBSET.csv.
            if not args.dry_run and task not in PASSTHROUGH_TASKS:
                write_subset_table(out / SUBSET_LIST_SUBDIR.get(task, ""),
                                   task, entries, full)
        except Exception as error:
            print(f"!! {task} FAILED: {error}", file=sys.stderr)
            failures.append(task)
            continue

        if not args.dry_run and out.exists():
            built = sum(os.path.getsize(os.path.join(root, name))
                        for root, _, names in os.walk(out) for name in names)
            print(f"    built: {gb(built):.1f} GB")

    if failures:
        print(f"\nFailed: {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
