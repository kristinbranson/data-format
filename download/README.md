# Downloading the benchmark data

Two versions of every dataset are available:

| | Disk | What it is |
|---|---:|---|
| **Full** | ~1.4 TB | The complete published release for all 8 datasets. What the preprint's results were produced from. |
| **Data-limited** | ~294 GB | Every dataset capped at **50 GB**, for running the benchmark without 1.4 TB free. Feeds the `<task>_datalimit` harbor tasks. |

Both land under `data/`: the full datasets in `data/<task>/`, the capped ones in
`data/<task>_datalimit/`. They can coexist, and the harbor tasks pick them up
automatically — `<task>` mounts the former, `<task>_datalimit` the latter.

## Files here

| File | Purpose |
|---|---|
| `download.py` | Fetches data from the upstream sources. `--datalimit` fetches the capped variant. |
| `select_datalimit.py` | Decides *which samples* each capped dataset keeps, and freezes that into `datalimit/<task>.csv`. Already run; you should not need to re-run it. |
| `make_datalimit.py` | Builds `data/<task>_datalimit/` from an already-downloaded full dataset. |
| `datalimit/<task>.csv` | The frozen subset manifests. Committed, so the subsets are reproducible and citable. |

## Full download

```bash
python download/download.py hasnain2024                  # one task
python download/download.py hasnain2024 lee2025          # several
python download/download.py --all                        # everything (~1.4 TB)
python download/download.py allen2p -o /scratch/allen2p   # custom destination
```

Per-task sizes: `hasnain2024` 16 GB, `lee2025` 15 GB, `majnik2025` 16 GB,
`map` 54 GB, `sosa2024` 92 GB, `allen2p` 254 GB, `mouseland` 442 GB,
`zhang2025` 608 GB.

All downloaders are resumable — re-running skips files already on disk. If one
task fails the rest still run, and the failures are listed at the end.

## Data-limited

Versions of the data that are capped to 50 GB. Data will be downloaded to the directory `<dataset>_limited`. 
Each directory will have a file `DATALIMIT_SUBSET.csv`

### Selecting data subsets

Generates manifest files, which are already committed. Only need to rerun
if something changes. 

```bash
python download/select_datalimit.py --dry-run     # print the selection, write nothing
python download/select_datalimit.py sosa2024      # rewrite one manifest
```

Selection measures the full datasets already on disk under `--data-root`
(default `<repo>/data`), so it needs the full data present. After changing a
manifest, rebuild the data and regenerate both the harbor task and its reference
stats:

```bash
python download/make_datalimit.py sosa2024 --force
python harbor-scripts/generate_datalimit_task.py sosa2024 --force
harbor-scripts/generate_reference_stats.sh sosa2024_datalimit
```

### Downloading data limited 

```bash
python download/download.py sosa2024 --datalimit         # -> data/sosa2024_datalimit/
python download/download.py --all --datalimit
```

Seven of the eight tasks are handled entirely by that one command, and never
transfer the data they leave out:

- `allen2p` fetches only the listed `ophys_experiment_id`s through the AllenSDK.
- `map`, `sosa2024` fetch only the listed assets through the DANDI REST api.
- `zhang2025` caches only the listed `eid`s through the ONE api. This works
  because the upstream caching script populates its cache one eid at a time —
  `prepare_data(one, eid, ...)` calls `one.eid2pid(eid)` then
  `load_spiking_data(one, pid, ...)` (`ibl_data_utils.py:727-740`), each
  downloading on demand — so the eids processed *are* the data fetched. The
  upstream `--n_sessions` flag cannot express an arbitrary eid list (it just
  slices a fixed release list), but the ONE api can.
- `hasnain2024`, `lee2025`, `majnik2025` are under the cap and download in full.

**Only `mouseland` is different.** Its subset is a per-session *cell* subsample
living inside the published `.npy` files, and figshare serves whole files, so
there is nothing to filter at download time. Fetch it in full once, then reduce:

```bash
python download/download.py mouseland
python download/make_datalimit.py mouseland
```

`download.py --datalimit mouseland` refuses with exactly that instruction rather
than silently downloading the wrong thing. `--all --datalimit` still handles the
other seven, then lists `mouseland` as a failure and exits non-zero — expected,
not a broken run.

`make_datalimit.py` works for any task, so if you already have the full data
locally you can build every capped variant without re-downloading anything:

```bash
python download/make_datalimit.py            # all tasks
python download/make_datalimit.py sosa2024 map
python download/make_datalimit.py --dry-run  # report the plan, touch nothing
python download/make_datalimit.py sosa2024 --force   # rebuild in place
```

Where possible it **hardlinks** the retained files, so the capped variant costs
no extra disk. Two exceptions: `allen2p`'s files are owned by another user and
must be copied (~48 GB), and `mouseland`'s files are genuinely rewritten.

`mouseland` is by far the slowest — expect **hours**. Its `spk/*.npy` are pickled
object arrays, which cannot be memory-mapped, so each of the 89 sessions costs a
full 1.5–7.4 GB load. Run it on its own.

### What the data limit actually does

The guiding rule: **no *type* of data is ever removed.** Every variable, signal,
trace variant, stimulus template and auxiliary array the full release contains is
still present, because working out which fields to use is the benchmark task
itself. Only **samples** are dropped — mice, subjects, sessions, or cells.

Which axis each dataset gives up is dictated by what it has a lot of. Where mice
had to go, they were drawn to **cover every design stratum** (Cre line × imaging
depth, recording lab) rather than to minimise bytes: picking the cheapest mice
would systematically strip the sessions with the most cells. All draws use a
fixed seed, chosen in advance rather than after comparing outcomes.

| Task | Full → capped | Axis | What is kept |
|---|---|---|---|
| `hasnain2024` | 16 → 16 GB | — | everything; already under the cap |
| `lee2025` | 15 → 15 GB | — | everything; already under the cap |
| `majnik2025` | 16 → 16 GB | — | everything; already under the cap |
| `map` | 54 → 49.6 GB | sessions | 168 of 174 sessions (the 6 largest dropped); **all 28 subjects** |
| `sosa2024` | 92 → 49.6 GB | mice | 6 of 11 mice, 82 of 152 sessions; every session and trial of each retained mouse |
| `allen2p` | 254 → 48.5 GB | mice | 9 of 37 mice, 61 of 239 experiments; **all 3 Cre lines, all 4 imaging depths, all 6 session types, all 3 experience levels** |
| `mouseland` | 442 → 49.6 GB | cells | **all 89 sessions, all 19 mice, all trials**; 9.8% of cells per session (459,723 of 4,691,034; ~5,165 per session) |
| `zhang2025` | 608 → 49.4 GB | subjects | 18 of 139 subjects, 39 of 459 sessions, **all 12 labs**; every session and trial of each retained subject |

`mouseland` is the only dataset cut on the cell axis, because it is the only one
with a huge number of cells per session — 46,128 on averageA uniform *fraction* 
is kept. It is also the only variant whose files are rewritten. For the other
seven, every retained file is **byte-for-byte identical** to the published
release — the subset is purely a choice of which files to keep.

Each manifest records the rule, the resulting size, the seed and the selected
IDs in its header:

```bash
head -8 download/datalimit/sosa2024.csv
```

### APIs that download missing data

AllenSDK and ONE api will download data that is not cached. It is an instruction to the agent to 
only use the subset of the data selected. Every built dataset ships a **subset list** naming precisely 
what to use, and the `<task>_datalimit` prompt tells the agent to read it, process exactly what it
names, and not download anything missing.

It is always a CSV named **`DATALIMIT_SUBSET.csv`**, one per dataset, at
`data/DATALIMIT_SUBSET.csv` — except `allen2p`, which mounts only the release
subdirectory, so its file lives at
`data/visual-behavior-ophys-1.1.0/DATALIMIT_SUBSET.csv`. Where the task already has
a canonical table upstream, the subset is a filtered copy of it with identical
columns, so existing code reads it unchanged:

| Task | Columns | Identifier to use |
|---|---|---|
| `allen2p` | same as `project_metadata/ophys_experiment_table.csv` | `ophys_experiment_id` — what `cache.get_behavior_ophys_experiment()` takes |
| `zhang2025` | same as the release freeze `code/code_zhang2025/data/bwm_release.csv`, one row per probe insertion | `eid` — what `one.search()` returns and `one.load_object()` takes |
| `map`, `sosa2024` | `subject`, `nwb_path` | `nwb_path`, relative to `data`, as the task globs it |
| `mouseland` | `session`, `n_cells_total`, `n_cells_kept` | `session`; every session is present, its cells subsampled |

The three under-cap tasks have no subset file: nothing was dropped.

`bwm_release.csv` is also the *universe* the zhang2025 subset is drawn from — it
defines the release (699 probe insertions, 459 sessions, 139 subjects), so only
sessions it lists are eligible. Two sessions cached on disk are absent from it and
are excluded; they are not part of the release and `one.search` could never return
them.

**Why this matters for any code you write against a capped dataset.** 

- *AllenSDK* re-downloads only files that are **absent**. `S3CloudCache._download_file`
  loops `while not self._file_exists(...)`, and `_file_exists` (`cloud_cache.py:733`)
  tests only `local_path.exists()` — a pre-existing file is never re-fetched or
  even hash-checked. But `get_ophys_experiment_table()` returns all 1936 released
  experiments, so iterating it will pull the ones that are missing.
- *ONE* re-reads the release index, which lists every released session, so
  `one.search(query_type='local', ...)` returns far more than is on disk. It also
  refreshes that index from Alyx whenever the local copy looks stale or differently
  tagged (`one/api.py:1740`), so there is no point editing it.

In both cases, filter by the subset file rather than by what the client's metadata
advertises. If you need a hard guarantee that a run cannot exceed the cap, run the
task without internet.
