# Archived scripts

One-off tools, kept for provenance. They are not part of the day-to-day rating
workflow, but all three still run from here (each adds the parent directory to
`sys.path` so `import raters` keeps working).

- **`migrate_raters.py`** — moved the single-evaluator layout to per-rater
  subfolders: copied each dataset's dossiers and `summary.md` into `LZ/`, then
  reset the root dossiers' `**Rating:**` / `**Note:**` lines to placeholders so
  they serve as masters. Run once on 2026-07-28 across all 8 datasets.

- **`verify_migration.py`** — checked that migration against git: every rating
  preserved in `LZ/`, dossier content byte-identical, masters blank. Reported OK
  for all 48 dossiers. Must be pointed at the *pre-migration* revision, e.g.
  `python3 archive/verify_migration.py --rev ed2b8bd~1`; run against a later
  commit it compares the copies to the blanked masters and reports everything
  as lost.

- **`renumber_summary.py`** — re-keys `## Q <qid>.` headings in `summary.md` /
  `eval_summary.md` to the numbering the dossiers use, matching sections by
  title. Needed when the reference `DECISIONS.md` is renumbered after rating:
  sosa2024 gained two "thresholded into categories" sub-questions, which pushed
  "aligned with the neural data" from `7-c` to `7-d` while the summary files
  kept the old numbers. Applied once (4 headings). Bring it back only if
  `check_alignment.py` reports summary-vs-dossier title drift again; follow it
  with `merge_eval.py --apply`.

Live tools stay in `evaluation/eval/`:

| script | role |
|---|---|
| `raters.py` | shared library — evaluator registry, rater folders, rating I/O. Imported by everything below; not optional. |
| `rate.py` | Q-by-Q rating against a reference `DECISIONS.md` |
| `rate_blind.py` | rating for datasets with no reference |
| `compare.py` | judge-comparison pass (primary evaluator) |
| `merge_eval.py` | regenerate `eval_summary.md`'s evaluator columns from the dossiers |
| `report.py` | render `report.md` |
| `check_alignment.py` | pre-flight: question-numbering drift between reference, dossiers and summaries |
