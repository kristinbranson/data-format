<!-- Prompt text for map_datalimit, inserted into the minimal prompt by
     harbor-scripts/generate_datalimit_task.py. The "## Data subset" section below goes
     directly before "## Decoder Task"; the bullet after the CONSISTENCY BULLET marker is
     appended to the list under "### Consistency requirements". Edit here, then rerun
     the script; do not edit the generated instruction.md. -->

## Data subset
- **Dataset subset is described in `/app/data/DATALIMIT_SUBSET.csv`.** It lists every NWB file included, by subject and path (columns `subject`, `nwb_path`). Do **not** download any data that is missing locally, even if the metadata, reference code, or paper refers to it.
- This task uses a reduced version of the published dataset with fewer **sessions**: 168 of the 174 released sessions, the 6 largest recordings having been dropped to fit a data cap. All 28 released subjects are kept, and no neurons or trials were removed from a retained session. This is important when matching statistics to the references: the number of sessions will be smaller than the papers report, while the number of subjects, the number of neurons per session and the structure of each trial should still match.
- No *type* of data was removed -- every variable, signal, and auxiliary array the full release contains is still present.

<!-- CONSISTENCY BULLET -->
- As described under the *Data subset* section, the number of sessions will be smaller than the papers', but otherwise data statistics should match.
