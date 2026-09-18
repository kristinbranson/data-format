# Evaluation

Two halves, one notebook each, and a third that puts them side by side.

**Outcome** — what the verifier measured about the converted data.
**Ratings** — how humans and LLM judges rated the agents' conversion code.

## Notebooks

| file | what it holds |
|---|---|
| `ratings_analysis.ipynb` | The paper's ratings results and analysos, rater agreement, binary accuracy against the human reference, and the per-condition comparisons (harness, prompt) |
| `outcome_analysis.ipynb` | The paper's outcome tables, plus the same per-condition comparisons scored on verifier metrics |
| `condition_summary.ipynb` | Both evaluations pooled over datasets: all six conditions as one box apiece, outcome above process |

## Standalone files

| file | what it does |
|---|---|
| `utils.py` | Shared vocabulary and loaders for the outcome half: `trial_metrics_df`, `load_reference_stats`, agent/dataset names and aliases |
| `trial_metrics.py` | Walks the run tree and writes `trial_metrics.json` — one curated record per trial. Run it after new trials land |
| `trial_metrics.json` | That output. Everything on the outcome side reads it |
| `outcome_analysis.py` | The four tables and the comparison figures. Thresholds come from the verifier's own `test_outputs.py` |
| `lesion_analysis.py` | The nine-category scoring across all six conditions, failure propagation, and the threshold sweeps. `lesion_analysis.md` explains the categories |
| `compute_cost.py` | Tokens and wall time per trial, for agents and judges. Prints the table and writes `figures/resource_summary.tex` |
| `diff_trial_metrics.py` | Diffs two `trial_metrics.json` with a tolerance, so a regeneration shows the real changes and not float noise |

## Folders

| folder | what it is |
|---|---|
| `ratings/` | The ratings package — loading, agreement, judge import, figures. One CLI: `python3 -m ratings`; see `ratings/README.md` |
| `case_studies/` | The paper's appendix of worked failures. `python3 -m case_studies` rewrites `examples.tex`; `--check` fails if it is stale |
| `<dataset>/` | Per-trial rating files, judge output and the reference `eval_summary.md`, one folder per dataset |
| `archive/` | One-off migration scripts, already applied. Kept for provenance |
| `trajectory/` | Hand-written notes on specific trial divergences |
