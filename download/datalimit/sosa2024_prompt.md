<!-- Prompt text for sosa2024_datalimit, inserted into the minimal prompt by
     harbor-scripts/generate_datalimit_task.py. The "## Data subset" section below goes
     directly before "## Decoder Task"; the bullet after the CONSISTENCY BULLET marker is
     appended to the list under "### Consistency requirements". Edit here, then rerun
     the script; do not edit the generated instruction.md. -->

## Data subset
- **Dataset subset is described in `/app/data/DATALIMIT_SUBSET.csv`.** It lists every NWB file included, by subject and path (columns `subject`, `nwb_path`). Do **not** download any data that is missing locally, even if the metadata, reference code, or paper refers to it.
- This task uses a reduced version of the published dataset with fewer **mice**: 6 of the 11 released subjects. Every session and every trial of each retained mouse is kept, and no neurons were removed. This is important when matching statistics to the references: the number of subjects and the number of sessions will be smaller than the paper reports, while the number of neurons per session and the structure of each trial should still match.
- No *type* of data was removed — every variable, signal, and auxiliary array the full release contains is still present.

<!-- CONSISTENCY BULLET -->
- As described under the *Data subset* section, the numbers of mice and sessions will be smaller than the paper's, but otherwise data statistics should match.
