<!-- Prompt text for mouseland_datalimit, inserted into the minimal prompt by
     harbor-scripts/generate_datalimit_task.py. The "## Data subset" section below goes
     directly before "## Decoder Task"; the bullet after the CONSISTENCY BULLET marker is
     appended to the list under "### Consistency requirements". Edit here, then rerun
     the script; do not edit the generated instruction.md. -->

## Data subset
- **Dataset subset is described in `/app/data/DATALIMIT_SUBSET.csv`.** It lists every session together with how many of its cells were kept (columns `session`, `n_cells_total`, `n_cells_kept`). Do **not** download any data that is missing locally, even if the metadata, reference code, or paper refers to it.
- This task uses a reduced version of the published dataset with fewer **neurons per session**. All mice, all sessions, and all trials are kept — only the number of simultaneously recorded neurons is smaller, subsampled to a random 9.8% within each session. This is important when matching statistics to the references: the number of subjects, sessions, and trials should still match the reference paper, and only neuron counts should be smaller.
- No *type* of data was removed — every variable, signal, and auxiliary array the full release contains is still present.

<!-- CONSISTENCY BULLET -->
- As described under the *Data subset* section, the number of neurons per session will be smaller, but otherwise data statistics should match.
