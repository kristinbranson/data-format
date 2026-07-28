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
  kept the old numbers. Applied once (4 headings). Bring it back only if a
  rating tool reports summary-vs-dossier title drift; follow it with
  `python3 raters.py merge <dataset> --apply`.

Live tools stay in `evaluation/eval/`:

| script | role |
|---|---|
| `raters.py` | shared library — evaluator registry, rater folders, rating I/O, alignment check, `eval_summary.md` merge. Imported by everything below; not optional. Also a CLI: `list` (default), `check [dataset]`, `merge [dataset] [--apply]`. |
| `rate.py` | Q-by-Q rating against a reference `DECISIONS.md` |
| `rate_blind.py` | rating for datasets with no reference |
| `compare.py` | judge-comparison pass (primary evaluator) |
| `report.py` | render `report.md` |

`rate.py` and `rate_blind.py` run the alignment check themselves at startup and
refuse to run on a misaligned dataset, so there is nothing to remember.
