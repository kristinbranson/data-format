# Archived scripts

One-off tools kept for provenance. They are not part of the rating workflow.

- **`migrate_raters.py`** — moved the single-evaluator layout to per-rater
  subfolders: copied each dataset's dossiers and `summary.md` into `LZ/`, then
  reset the root dossiers' `**Rating:**` / `**Note:**` lines to placeholders so
  they serve as masters. Run once on 2026-07-28 across all 8 datasets.
- **`verify_migration.py`** — checked that migration against git: every rating
  preserved in `LZ/`, dossier content byte-identical, masters blank. Reported
  OK for all 48 dossiers.

Live tools stay in `evaluation/eval/`: `rate.py`, `rate_blind.py`, `compare.py`,
`merge_eval.py`, `report.py`, `check_alignment.py`, `renumber_summary.py`,
`raters.py`.
