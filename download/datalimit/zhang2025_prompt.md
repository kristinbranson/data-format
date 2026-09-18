<!-- Prompt text for zhang2025_datalimit, inserted into the minimal prompt by
     harbor-scripts/generate_datalimit_task.py. The "## Data subset" section below goes
     directly before "## Decoder Task"; the bullet after the CONSISTENCY BULLET marker is
     appended to the list under "### Consistency requirements". Edit here, then rerun
     the script; do not edit the generated instruction.md. -->

## Data subset
- **Dataset subset — use only the data listed in `/app/data/DATALIMIT_SUBSET.csv`.** Process exactly the `eid` values it lists. Do **not** download any data that is missing locally, even if the metadata, reference code, or papers refer to it — this overrides the note above about data that may need to be downloaded.
- This task uses a reduced version of the published dataset with fewer **subjects**. Each retained subject keeps *all* of its released sessions, so sessions per subject, trials per session, and neurons per session are unchanged. Only the number of subjects — and therefore the total number of sessions, trials, and neurons — is smaller. This is important when matching statistics to the references.
- No *type* of data was removed — every variable, signal, and auxiliary array the full release contains is still present.

<!-- CONSISTENCY BULLET -->
- As described under the *Data subset* section, the numbers of subjects and sessions will be smaller than the papers', but otherwise data statistics should match.
