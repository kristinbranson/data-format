"""Compute the subset manifests that define the `<task>_datalimit` variants.

Each benchmark dataset has a `<task>_datalimit` twin capped at 50 GB. This script
decides *which samples* each twin keeps and freezes that decision into
`download/datalimit/<task>.csv`, so the subset is reproducible without rerunning
any of the selection logic.

Governing rule: never drop a *type* of data (a variable, a trace variant, a
stimulus template, an auxiliary array) -- choosing which fields to use is the
benchmark task itself. Only drop *samples*: mice, subjects, sessions, or cells.
Where mice must be dropped, the draw covers every design stratum rather than
minimising bytes, because cheapest-first selection systematically strips the
high-yield (many-cell) sessions.

Usage:
    python download/select_datalimit.py                 # all tasks
    python download/select_datalimit.py allen2p sosa2024
    python download/select_datalimit.py --data-root /path/to/data
    python download/select_datalimit.py --dry-run       # print, don't write

Sizes are measured from the full datasets already on disk under `--data-root`.
The written manifest is the reproducible artifact; downstream tooling
(`make_datalimit.py`, `download.py --datalimit`) reads it and never re-derives it.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "download" / "datalimit"

# The upstream freeze that defines the zhang2025 release: one row per probe
# insertion, columns pid/eid/probe_name/session_number/date/subject/lab. The
# paper's own caching script reads it (code_zhang2025/src/0_data_caching.py) and
# `prepare_data` takes it as `bwm_df`, so it is both the universe the datalimit
# subset is drawn from and the schema that subset is published in.
BWM_RELEASE_CSV = (REPO_ROOT / "harbor-tasks" / "zhang2025" / "environment" / "code"
                   / "code_zhang2025" / "data" / "bwm_release.csv")

# Hard per-dataset ceiling, in decimal bytes (50 GB, not 50 GiB).
CAP_BYTES = 50_000_000_000

# Fixed a priori so the draw cannot be tuned after seeing which seed scores best.
SEED = 0

# Fraction of cells kept per mouseland session. mouseland is the only dataset
# cut on the cell axis: it averages 46,128 cells/session, ~23x decoder.py's
# svd_max_neurons=2000, where every other dataset is at or below that threshold.
MOUSELAND_CELL_FRACTION = 0.098


@dataclass
class Selection:
    """One dataset's subset decision, ready to be written as a manifest.

    Attributes:
        task: benchmark task name, e.g. 'allen2p'.
        rule: one-sentence human-readable statement of what was kept. Reused
            verbatim in the task's instruction.md "Dataset subset" paragraph, so
            it must be true and self-contained.
        columns: column names for `entries`. The first column is always the
            identifier that task's own api takes.
        entries: one tuple per kept sample, matching `columns`. Semantics are
            per-task (experiment ids, relative NWB paths, session directories);
            documented in each select_* function.
        total_bytes: on-disk size of the kept samples, in decimal bytes.
        stats: extra key -> value counts reported in the manifest header and
            used for eyeballing coverage (mice kept, strata covered, ...).
        params: key -> value settings the builder needs beyond the entry list
            (currently only mouseland's cell fraction and seed).
    """

    task: str
    rule: str
    columns: list[str]
    entries: list[tuple]
    total_bytes: int
    stats: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)


# ---------------- size helpers ----------------


def dir_bytes(path: Path) -> int:
    """Total size of every regular file under `path`, in decimal bytes.

    Args:
        path: directory to measure. Symlinks are not followed into.

    Returns:
        Sum of file sizes in bytes (int). Returns 0 for a missing path.
    """
    if not path.exists():
        return 0
    total = 0
    for root, _, filenames in os.walk(path):
        for name in filenames:
            filepath = os.path.join(root, name)
            if os.path.isfile(filepath):
                total += os.path.getsize(filepath)
    return total


def gb(nbytes: int) -> float:
    """Convert decimal bytes to GB for reporting."""
    return nbytes / 1e9


def _fill_under_cap(candidates, sizes, kept, total):
    """Add candidates in the given order while they still fit under CAP_BYTES.

    Args:
        candidates: ordered sequence of keys to consider.
        sizes: mapping key -> size in bytes.
        kept: list of already-selected keys, appended to in place.
        total: bytes already committed by `kept`.

    Returns:
        Updated total bytes (int). `kept` is mutated in place.
    """
    for key in candidates:
        if total + sizes[key] <= CAP_BYTES:
            kept.append(key)
            total += sizes[key]
    return total


# ---------------- allen2p ----------------


def select_allen2p(datadir: Path) -> Selection:
    """Keep whole mice, drawn round-robin over (Cre line x imaging depth) strata.

    allen2p is the only dataset with a per-file constant large enough to force a
    mouse cut: every NWB carries ~232 MB independent of cell count (165.9 MB of
    stimulus templates plus ~66 MB of eye/running/timestamp series), so all 239
    VisualBehavior experiments would cost 55.4 GB before a single neuron.

    Selection covers all 3 Cre lines and all 4 imaging depths by construction:
    strata are visited in a fixed order and drawn from uniformly at random, so no
    stratum can be crowded out and no size bias is introduced within a stratum.

    Only `project_code == 'VisualBehavior'` experiments are eligible, matching
    what `download.py` fetches and what the reference conversion reads; any
    VisualBehaviorMultiscope files in a local copy are ignored.

    Args:
        datadir: `<data-root>/allen2p`, containing
            `visual-behavior-ophys-1.1.0/{behavior_ophys_experiments,project_metadata}`.

    Returns:
        Selection whose entries are `<ophys_experiment_id>\t<nwb filename>`, one
        per kept experiment. Column 1 is the identifier the AllenSDK api takes.
    """
    import pandas as pd

    release = datadir / "visual-behavior-ophys-1.1.0"
    table = pd.read_csv(release / "project_metadata" / "ophys_experiment_table.csv")

    experiment_bytes = {}  # ophys_experiment_id -> bytes on disk
    for nwb in (release / "behavior_ophys_experiments").glob("*.nwb"):
        match = re.search(r"(\d+)\.nwb$", nwb.name)
        if match:
            experiment_bytes[int(match.group(1))] = nwb.stat().st_size

    table["nbytes"] = table.ophys_experiment_id.map(experiment_bytes)
    eligible = table[table.project_code == "VisualBehavior"].dropna(subset=["nbytes"])

    per_mouse = eligible.groupby("mouse_id").agg(
        nbytes=("nbytes", "sum"),
        cre_line=("cre_line", "first"),
        imaging_depth=("imaging_depth", "first"),
        n_experiments=("nbytes", "size"),
    )
    sizes = per_mouse.nbytes.to_dict()
    strata = {}  # (cre_line, imaging_depth) -> sorted list of mouse_id
    for mouse_id, row in per_mouse.iterrows():
        strata.setdefault((row.cre_line, row.imaging_depth), []).append(mouse_id)

    # Shuffle within each stratum, then take one mouse per stratum per pass.
    # Sorting the stratum keys and the mouse ids first keeps this independent of
    # filesystem and pandas iteration order.
    rng = np.random.default_rng(SEED)
    pools = {key: list(rng.permutation(sorted(strata[key]))) for key in sorted(strata, key=str)}

    kept, total, made_progress = [], 0, True
    while made_progress:
        made_progress = False
        for key in pools:
            while pools[key]:
                mouse_id = pools[key].pop(0)
                if total + sizes[mouse_id] <= CAP_BYTES:
                    kept.append(mouse_id)
                    total += sizes[mouse_id]
                    made_progress = True
                    break

    chosen = eligible[eligible.mouse_id.isin(kept)]
    # Column 1 is the identifier the AllenSDK api takes -- ophys_experiment_id is
    # what indexes the experiment table and what
    # `VisualBehaviorOphysProjectCache.get_behavior_ophys_experiment()` accepts.
    # Column 2 is the file it corresponds to, for the builder and for a human.
    entries = sorted(
        ((int(row.ophys_experiment_id),
          f"behavior_ophys_experiment_{int(row.ophys_experiment_id)}.nwb")
         for row in chosen.itertuples()),
        key=lambda row: row[0])
    rule = (f"{len(kept)} of {len(per_mouse)} mice, drawn to cover every "
            f"(Cre line x imaging depth) stratum; every ophys experiment of each "
            f"retained mouse is included.")
    return Selection(
        task="allen2p",
        rule=rule,
        columns=["ophys_experiment_id", "nwb_filename"],
        entries=entries,
        total_bytes=int(total),
        stats={
            "mice": f"{len(kept)} of {len(per_mouse)}",
            "experiments": f"{len(chosen)} of {len(eligible)}",
            "cre_lines": f"{chosen.cre_line.nunique()} of {eligible.cre_line.nunique()}",
            "imaging_depths": f"{chosen.imaging_depth.nunique()} of {eligible.imaging_depth.nunique()}",
            "session_types": f"{chosen.session_type.nunique()} of {eligible.session_type.nunique()}",
            "experience_levels": f"{chosen.experience_level.nunique()} of {eligible.experience_level.nunique()}",
            "mouse_ids": ",".join(str(int(m)) for m in sorted(kept)),
        },
    )


# ---------------- sosa2024 ----------------


def select_sosa2024(datadir: Path) -> Selection:
    """Keep every session of every other mouse, ranked by data volume.

    Whole mice are required rather than merely convenient: reward-zone location
    is not stored in the NWB, it is reconstructed per mouse by pooling
    reward-zone entries across that mouse's entire session sequence
    (`manual/sosa2024/convert_data.py`, `segment_reward_positions`). Dropping
    sessions within a mouse would change the reward_location and
    distance_to_reward_zone labels; dropping whole mice leaves every retained
    mouse's labels bit-for-bit unchanged.

    Per-mouse volume tracks cell count (1.38-16.55 GB across the 11 mice), so
    taking every other mouse in volume order spans the full cell-count range
    instead of favouring the small end the way a budget-greedy draw would.

    Args:
        datadir: `<data-root>/sosa2024`, containing `sub-m*/`.

    Returns:
        Selection whose entries are `sub-mNN/sub-mNN_ses-NN_behavior+ophys.nwb`
        relative paths, sorted.
    """
    per_mouse = {}  # subject -> (bytes, [relative nwb paths])
    for nwb in sorted(datadir.glob("sub-*/*.nwb")):
        subject = nwb.parent.name
        nbytes, paths = per_mouse.get(subject, (0, []))
        per_mouse[subject] = (nbytes + nwb.stat().st_size,
                              paths + [(subject, f"{subject}/{nwb.name}")])

    by_volume = sorted(per_mouse, key=lambda s: (per_mouse[s][0], s))
    kept = by_volume[::2]  # every other mouse, smallest first
    total = sum(per_mouse[s][0] for s in kept)
    if total > CAP_BYTES:
        raise RuntimeError(f"sosa2024 every-other-mouse selection is {gb(total):.1f} GB, over cap")

    entries = sorted(row for s in kept for row in per_mouse[s][1])
    rule = (f"{len(kept)} of {len(per_mouse)} mice ({', '.join(sorted(kept))}); every "
            f"session and every trial of each retained mouse is included.")
    return Selection(
        task="sosa2024",
        rule=rule,
        columns=["subject", "nwb_path"],
        entries=entries,
        total_bytes=total,
        stats={
            "mice": f"{len(kept)} of {len(per_mouse)}",
            "sessions": f"{len(entries)} of {sum(len(v[1]) for v in per_mouse.values())}",
            "subject_ids": ",".join(sorted(kept)),
        },
    )


# ---------------- map (chen2024) ----------------


def select_map(datadir: Path) -> Selection:
    """Drop the largest sessions until the dataset fits, keeping all 28 subjects.

    map needs the lightest touch of any dataset -- 53.6 GB decimal, already under
    50 GiB -- so no subject has to go. Dropping the few largest sessions reaches
    the cap while every subject keeps most of its recordings.

    Args:
        datadir: `<data-root>/map`, containing `sub-<id>/*.nwb`.

    Returns:
        Selection whose entries are `sub-<id>/<file>.nwb` relative paths, sorted.
    """
    sessions = {f"{nwb.parent.name}/{nwb.name}": nwb.stat().st_size
                for nwb in datadir.glob("sub-*/*.nwb")}

    # Drop largest-first until under cap; ties broken by name for determinism.
    by_size_desc = sorted(sessions, key=lambda p: (-sessions[p], p))
    kept = set(sessions)
    total = sum(sessions.values())
    dropped = []
    for path in by_size_desc:
        if total <= CAP_BYTES:
            break
        kept.discard(path)
        dropped.append(path)
        total -= sessions[path]

    subjects_kept = {p.split("/")[0] for p in kept}
    subjects_all = {p.split("/")[0] for p in sessions}
    rule = (f"{len(kept)} of {len(sessions)} sessions; the {len(dropped)} largest "
            f"recordings were dropped so that all {len(subjects_all)} subjects are kept.")
    return Selection(
        task="map",
        rule=rule,
        columns=["subject", "nwb_path"],
        entries=[(p.split("/")[0], p) for p in sorted(kept)],
        total_bytes=total,
        stats={
            "subjects": f"{len(subjects_kept)} of {len(subjects_all)}",
            "sessions": f"{len(kept)} of {len(sessions)}",
            "dropped_sessions": ",".join(dropped),
        },
    )


# ---------------- zhang2025 ----------------


def select_zhang2025(datadir: Path) -> Selection:
    """Keep whole subjects, anchoring at least one in each of the 12 IBL labs.

    zhang2025 has by far the most subjects (141 across 461 sessions) and they are
    cheap to trade, so dropping subjects buys whole sessions with every trial
    intact -- no cropping and no rewriting.

    The lab anchor is drawn from each lab's *smaller half* by volume rather than
    uniformly. That restriction is load-bearing: mean subject volume is 4.31 GB,
    so twelve uniformly-drawn anchors average 51.7 GB and blow the cap outright.
    Restricting to the smaller half keeps anchors typical rather than minimal
    while still guaranteeing all 12 labs fit. The remaining budget is then filled
    uniformly at random from every unselected subject.

    Args:
        datadir: `<data-root>/zhang2025`, containing
            `one_cache/<lab>/Subjects/<subject>/<date>/<number>/`.

    Returns:
        Selection whose entries are `<eid>\t<session dir relative to one_cache>`,
        i.e. `<eid>\t<lab>/Subjects/<subject>/<date>/<number>`. Column 1 is the
        identifier the ONE api takes.
    """
    import pandas as pd

    cache = datadir / "one_cache"
    # The release universe is the upstream freeze file, which is what the paper's
    # own caching script reads (code_zhang2025/src/0_data_caching.py) and what
    # `prepare_data` takes as `bwm_df`. It lists 699 probe insertions over 459
    # eids and 139 subjects. Anything cached on disk but absent from it is not
    # part of the release and cannot be used, so it must not consume budget.
    release = pd.read_csv(BWM_RELEASE_CSV, index_col=0)
    # eid is the identifier every ONE call takes: `one.search` returns them and
    # `one.load_object(eid, ...)` consumes them.
    eid_by_session = {
        (row.lab, row.subject, str(row.date), int(row.session_number)): row.eid
        for row in release.itertuples()}
    in_release = set(eid_by_session)

    subjects = {}  # (lab, subject) -> (bytes, [relative session dirs])
    skipped_sessions = 0
    for lab_dir in sorted(cache.iterdir()):
        subjects_dir = lab_dir / "Subjects"
        if not subjects_dir.is_dir():
            continue  # release-index dirs (Brainwidemap, 2022_Q4_..., .rest)
        for subject_dir in sorted(subjects_dir.iterdir()):
            if not subject_dir.is_dir():
                continue
            session_dirs = []
            for candidate in sorted(d for d in subject_dir.glob("*/*") if d.is_dir()):
                key = (lab_dir.name, subject_dir.name,
                       candidate.parent.name, int(candidate.name))
                if key in in_release:
                    session_dirs.append(candidate)
                else:
                    skipped_sessions += 1
            if not session_dirs:
                continue
            nbytes = sum(dir_bytes(d) for d in session_dirs)
            # Column 1 is the eid the ONE api takes; column 2 is the cache
            # directory it maps to, for the builder and for a human reader.
            relative = [
                (eid_by_session[(lab_dir.name, subject_dir.name,
                                 d.parent.name, int(d.name))],
                 str(d.relative_to(cache)))
                for d in session_dirs]
            subjects[(lab_dir.name, subject_dir.name)] = (nbytes, relative)
    if skipped_sessions:
        print(f"    (ignored {skipped_sessions} cached session(s) absent from "
              f"{BWM_RELEASE_CSV.name})")

    sizes = {key: value[0] for key, value in subjects.items()}
    labs = sorted({lab for lab, _ in subjects})

    rng = np.random.default_rng(SEED)
    kept, total = [], 0
    for lab in labs:
        in_lab = sorted((sizes[k], k) for k in subjects if k[0] == lab)
        smaller_half = in_lab[: max(1, len(in_lab) // 2)]
        _, anchor = smaller_half[rng.integers(len(smaller_half))]
        kept.append(anchor)
        total += sizes[anchor]

    remaining = sorted(k for k in subjects if k not in kept)
    order = [remaining[i] for i in rng.permutation(len(remaining))]
    total = _fill_under_cap(order, sizes, kept, total)

    entries = sorted(row for key in kept for row in subjects[key][1])
    labs_kept = {lab for lab, _ in kept}
    rule = (f"{len(kept)} of {len(subjects)} subjects, with at least one from each "
            f"of the {len(labs)} labs; every session and every trial of each "
            f"retained subject is included.")
    return Selection(
        task="zhang2025",
        rule=rule,
        columns=["eid", "session_path"],
        entries=entries,
        total_bytes=int(total),
        stats={
            "subjects": f"{len(kept)} of {len(subjects)}",
            "sessions": f"{len(entries)} of {sum(len(v[1]) for v in subjects.values())}",
            "labs": f"{len(labs_kept)} of {len(labs)}",
            "subject_ids": ",".join(f"{lab}/{s}" for lab, s in sorted(kept)),
        },
    )


# ---------------- mouseland (zhong2025) ----------------


def select_mouseland(datadir: Path) -> Selection:
    """Keep every session and mouse; subsample cells within each session.

    mouseland is the only dataset with a huge number of cells per session
    (46,128 mean, 78,815 max) -- roughly 23x decoder.py's svd_max_neurons=2000,
    where every other dataset sits at or below that threshold. Cutting cells
    therefore costs the least: all 89 sessions, 19 mice, and trials survive.

    A uniform *fraction* is kept rather than a flat per-session cap, so the
    between-session variation in population size (20,547-78,815 cells) is
    preserved instead of flattened.

    Cell counts are read from `retinotopy/<session>_trans.npz['xpos']`, which is
    indexed in the same order as the concatenated `spk` imaging planes, so no
    multi-GB pickle has to be loaded here.

    Args:
        datadir: `<data-root>/mouseland`, containing `spk/`, `beh/`, `retinotopy/`.

    Returns:
        Selection whose entries are `<session>\t<n_cells_total>\t<n_cells_kept>`
        rows. The kept cell *indices* are not listed -- they are redrawn from the
        recorded seed in `make_datalimit.py`, which keeps the manifest small.
    """
    spk_files = sorted((datadir / "spk").glob("*_neural_data.npy"))
    entries, kept_cells, all_cells = [], 0, 0
    spk_bytes_kept = 0
    for spk in spk_files:
        session = spk.name[: -len("_neural_data.npy")]
        # retinotopy filenames drop the trailing run number
        date_key = "_".join(session.split("_")[:4])
        trans = datadir / "retinotopy" / f"{date_key}_trans.npz"
        with np.load(trans, allow_pickle=True) as npz:
            n_cells = int(npz["xpos"].shape[0])  # (n_cells,) across all planes
        n_keep = int(round(MOUSELAND_CELL_FRACTION * n_cells))
        entries.append((session, n_cells, n_keep))
        all_cells += n_cells
        kept_cells += n_keep
        # spk bytes scale linearly in cells: (n_cells, n_timebins) float32 planes
        spk_bytes_kept += int(round(spk.stat().st_size * n_keep / n_cells))

    # beh/ and retinotopy/ are behaviour and per-cell coordinates, kept whole
    # except for the cell-indexed retinotopy arrays, which shrink with the cells.
    fixed_bytes = dir_bytes(datadir / "beh")
    retinotopy_bytes = int(round(dir_bytes(datadir / "retinotopy") * kept_cells / all_cells))
    total = spk_bytes_kept + fixed_bytes + retinotopy_bytes

    rule = (f"all {len(spk_files)} sessions and all trials are included, but each "
            f"session's recorded cells are subsampled to a random "
            f"{MOUSELAND_CELL_FRACTION:.1%} (seed {SEED}).")
    return Selection(
        task="mouseland",
        rule=rule,
        columns=["session", "n_cells_total", "n_cells_kept"],
        entries=entries,
        total_bytes=total,
        stats={
            "sessions": f"{len(spk_files)} of {len(spk_files)}",
            "cells": f"{kept_cells:,} of {all_cells:,}",
            "cells_per_session_mean": f"{kept_cells // max(1, len(spk_files)):,}",
        },
        params={"cell_fraction": MOUSELAND_CELL_FRACTION, "seed": SEED},
    )


# ---------------- unchanged datasets ----------------


def select_passthrough(task: str, datadir: Path) -> Selection:
    """Keep a dataset whole because it is already under the cap.

    Args:
        task: benchmark task name.
        datadir: `<data-root>/<task>`.

    Returns:
        Selection with no entries; `make_datalimit.py` symlinks the full dataset.
    """
    total = dir_bytes(datadir)
    return Selection(
        task=task,
        rule="the complete published dataset is included; nothing was subsampled.",
        columns=["path"],
        entries=[],
        total_bytes=total,
        stats={"note": "under the 50 GB cap already; identical to the full task"},
    )


SELECTORS = {
    "allen2p": select_allen2p,
    "hasnain2024": lambda d: select_passthrough("hasnain2024", d),
    "lee2025": lambda d: select_passthrough("lee2025", d),
    "majnik2025": lambda d: select_passthrough("majnik2025", d),
    "map": select_map,
    "mouseland": select_mouseland,
    "sosa2024": select_sosa2024,
    "zhang2025": select_zhang2025,
}


# ---------------- manifest I/O ----------------


def write_manifest(selection: Selection, path: Path) -> None:
    """Write a Selection as a CSV with a commented provenance header.

    The provenance (rule, seed, size, coverage stats) lives in leading `#` lines,
    which `pandas.read_csv(..., comment='#')` skips, so the file is both a plain
    CSV and self-documenting.

    Args:
        selection: the decision to record.
        path: destination `download/datalimit/<task>.csv`; parents are created.

    Side effects:
        Creates or overwrites `path`.
    """
    import csv
    import io

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {selection.task}_datalimit selection manifest",
        f"# rule: {selection.rule}",
        f"# size: {gb(selection.total_bytes):.1f} GB (cap {gb(CAP_BYTES):.0f} GB)",
        f"# seed: {SEED}",
    ]
    lines += [f"# {key}: {value}" for key, value in selection.stats.items()]
    lines += [f"# param {key}: {value}" for key, value in selection.params.items()]
    lines.append("# generated by download/select_datalimit.py -- do not hand-edit")

    body = io.StringIO()
    writer = csv.writer(body, lineterminator="\n")
    writer.writerow(selection.columns)
    writer.writerows(selection.entries)
    path.write_text("\n".join(lines) + "\n" + body.getvalue())


def read_manifest(path: Path):
    """Read a manifest back into its rows and header fields.

    Args:
        path: a `download/datalimit/<task>.csv` written by `write_manifest`.

    Returns:
        (entries, header) where entries is a DataFrame of the CSV body (empty for
        a dataset that was not subsampled) and header maps each `# key: value`
        comment to its value, as a string.
    """
    import pandas as pd

    header = {}
    for line in path.read_text().splitlines():
        if not line.startswith("#"):
            break
        body = line[1:].strip()
        if ":" in body:
            key, value = body.split(":", 1)
            header[key.strip()] = value.strip()
    entries = pd.read_csv(path, comment="#")
    return entries, header


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*", choices=sorted(SELECTORS),
                        help="Tasks to select for. Default: all.")
    parser.add_argument("--data-root", default=str(REPO_ROOT / "data"),
                        help="Directory holding the full datasets. Default: <repo>/data")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the selection summary without writing manifests.")
    args = parser.parse_args()

    tasks = args.tasks or sorted(SELECTORS)
    data_root = Path(args.data_root)

    failures = []
    for task in tasks:
        datadir = data_root / task
        if not datadir.exists():
            print(f"!! {task}: {datadir} not found; skipping", file=sys.stderr)
            failures.append(task)
            continue
        try:
            selection = SELECTORS[task](datadir)
        except Exception as error:
            print(f"!! {task} FAILED: {error}", file=sys.stderr)
            failures.append(task)
            continue

        over = " OVER CAP" if selection.total_bytes > CAP_BYTES else ""
        print(f"\n=== {task}_datalimit: {gb(selection.total_bytes):.1f} GB{over}")
        print(f"    {selection.rule}")
        for key, value in selection.stats.items():
            if not key.endswith("_ids") and key != "dropped_sessions":
                print(f"      {key}: {value}")
        if not args.dry_run:
            manifest = MANIFEST_DIR / f"{task}.csv"
            write_manifest(selection, manifest)
            print(f"    wrote {manifest.relative_to(REPO_ROOT)} "
                  f"({len(selection.entries)} entries)")

    if failures:
        print(f"\nFailed: {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
