---
license: cc-by-4.0
pretty_name: IBL Brain-Wide Map — Neuro-Data Reuse Subset (Subject-Subsampled)
tags:
- neuroscience
- electrophysiology
- neuropixels
- mouse
- decision-making
- neural-decoding
---

# IBL Brain-Wide Map — Neuro-Data Reuse Subset (Subject-Subsampled)
Original data source:
https://www.internationalbrainlab.com/data

IBL Neuropixels Brainwide Map on AWS was accessed on 2026-08-15 from 
https://registry.opendata.aws/ibl-brain-wide-map.

## Overview

This is a size-reduced copy of the processed data from the International Brain Laboratory (IBL) 
brain-wide map: Neuropixels recordings made across twelve laboratories while mice performed a 
visual decision-making task, released under the tag `Brainwidemap` and described in [IBL et al. 
2025, *Nature*](https://www.nature.com/articles/s41586-025-09235-0).

It is packaged for an AI for science benchmark task derived from Zhang et al., *Exploiting
correlations across trials and behavioral sessions to improve neural decoding*, [Neuron 114(3),
536–551 (2026)](https://www.cell.com/neuron/fulltext/S0896-6273(25)00807-4); preprint
[doi:10.1101/2024.09.14.613047](https://doi.org/10.1101/2024.09.14.613047). **The data is IBL's;
Zhang et al. is the analysis the benchmark reproduces, not the source of these recordings.**

The copy is byte-for-byte the released data for the subset it contains. Nothing was resampled,
re-sorted, or recomputed.

## Key Modifications

The reduction is by **subject**. The `Brainwidemap` release index lists 480 sessions; this copy
retains **39 sessions from 18 subjects across 12 labs** — 60 probe insertions, about 47 GB.

Every retained subject keeps *all* of its released sessions, and every session keeps all of its
trials and neurons. Raw data are dropped, but all processed signals are kept. So sessions per 
subject, trials per session, and neurons per session match the full release exactly; only the 
number of subjects is smaller. That is what makes the subset usable for analyses that depend on 
within-subject structure: nothing was thinned inside a session.

`DATALIMIT_SUBSET.csv` lists the exact probe insertions retained (`pid`, `eid`, `probe_name`,
`subject`, `lab`, `date`), making the selection reproducible.

**Dataset revisions are frozen.** IBL publishes corrections as dated revisions, and the ONE client
resolves whichever revision is current at the time you ask — so the same query returns different 
bytes at different times. That is what this copy removes: the revisions here are fixed, and reading 
it gives the same files whenever you run. The data files were downloaded on 2025-12-09 and hold the 
revisions current that day. The cached Alyx metadata under `one_cache/.rest` was captured on 
2026-08-15, and is what tells the client which revision to look for. 

## Data Structure

The layout is a ONE cache, unchanged, so the ONE API can read it in place:

```
one_cache/
  <lab>/Subjects/<subject>/<date>/<number>/alf/...   the ALF datasets (~47 GB)
  Brainwidemap/                                       release index: sessions.pqt, datasets.pqt
  2022_Q4_IBL_et_al_BWM/, 2025_Q3_IBL_et_al_BWM/      other release indices, as shipped
  .rest/                                              cached Alyx metadata responses (see below)
DATALIMIT_SUBSET.csv                                  the probe insertions retained
```

This is the processed data, not the raw recordings.

### `one_cache/.rest`

These are cached Alyx REST responses, and they are part of the data. The release index lists 
*pre-revision* paths, so resolving a dataset from the index alone does not find the files on disk; 
the client normally asks Alyx which revision is current. Shipping those answers, with their expiry 
set far in the future, means the cache resolves to the same revisions offline and forever, with no 
network access. Delete them and reads fall back to live Alyx, which reintroduces the drift this copy 
exists to prevent.

## Usage

The ONE api can be used with this cache directory. An Alyx-backed client is needed for probe-insertion 
lookups (`eid2pid` does not exist on the offline `One` class), but with `.rest` present it needs no 
network:

```python
from one.api import ONE

one = ONE(base_url="https://openalyx.internationalbrainlab.org", silent=True,
          cache_dir="<download>/one_cache",
          tables_dir="<download>/one_cache/Brainwidemap",
          mode="remote")
```

## Attribution

This dataset is redistributed under **CC BY 4.0**, the license of the source data. If you use it,
cite the original release rather than this derivative copy:

- **Brain-wide map**: IBL et al. (2025), *A brain-wide map of neural activity during complex
  behaviour*, https://doi.org/10.1101/2023.07.04.547681. 
- **Technical paper** (experiment and data-processing pipelines):
  https://doi.org/10.6084/m9.figshare.21400815
- **Source access**: "IBL Neuropixels Brainwide Map on AWS was accessed on 2026-08-15 from
  https://registry.opendata.aws/ibl-brain-wide-map."

**Changes made to the original**, as CC BY 4.0 requires be indicated: subject-level subsampling to
39 sessions, processed data only, as described above, and the freezing of dataset revisions and Alyx 
metadata responses. No recorded data was altered.
