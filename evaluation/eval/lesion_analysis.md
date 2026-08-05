# Lesion analysis: what the scores mean

Companion to `lesion_analysis.ipynb` / `lesion_analysis.py`.

This analysis re-expresses the verifier metrics as nine ordered **categories** for all datasets:

Every category is a number in `[0, 1]`, or NaN if N/A or inaccurate. Higher is always better.

| # | key / label | what it means | how it is scored |
|---|---|---|---|
| 1 | `core_files_exist`<br>*Core files exist* | the agent produced the two files without which nothing else can be judged | 1 when both `converted_data.pkl` and `convert_data.py` are present and non-empty |
| 2 | `other_files_exist`<br>*Other files exist* | the rest of `REQUIRED_FILES` | 1 when `CONVERSION_NOTES.md`, `sample_data.pkl` and `README.md` are all present and non-empty |
| 3 | `full_data_format_valid`<br>*Converted data format* | `converted_data.pkl` satisfies the required structure | the `full_data_format_valid` flag from `test_verify_data_format`, i.e. `decoder.verify_data_format` returned valid |
| 4 | `nneurons_total_matches`<br>*N neurons* | the conversion kept the right number of neurons | `nneurons_total_ratio` (agent / reference) inside `1 ± STATLIMITS['nneurons_total_ratio']` = ±10% |
| 5 | `scale_matches`<br>*N replicates* | the conversion kept the right amount of data | fraction of `nsubjects`, `nsessions`, `ntrials_total` whose ratio is inside its own `STATLIMITS` band. `nsubjects` has tolerance 0, so it must match exactly; the other two allow ±10% |
| 6 | `input_range_matches`<br>*Input ranges* | the input variables span the right values | 1 when `mean_input_range_error` ≤ `STATLIMITS['input_range_error']` = 0.2 — the same test `test_data_stats` asserts. That field is the mean, over matched input variables, of the larger endpoint error expressed as a **fraction of the reference variable's span**. Two variables that are both constant count as a perfect match whatever their constant values, since a constant carries no information for the decoder |
| 7 | `output_nclasses_matches`<br>*Output N classes* | the output variables were discretised into the right number of classes | fraction where `output_nclasses_<v>` equals `output_nclasses_reference_<v>` |
| 8 | `output_fraction_matches`<br>*Output distributions* | the classes are populated in the right proportions | fraction where `output_fraction_error_<v>` ≤ `STATLIMITS['output_fraction_error']` = 0.1, the same test `test_data_stats` asserts. That field is the L1 distance between the sorted class-fraction vectors, so it ignores a relabelling of the classes and ranges 0-2.` |
| 9 | `decoder_accuracy_matches`<br>*Decoder accuracy* | a decoder trained on the conversion recovers the behaviour as well as it does from the reference | fraction of output variables with `validation_balanced_accuracy_ratio` ≥ `MIN_ACCURACY_FRAC` = 0.95, the same test `test_decoder_accuracy` asserts |

### Failure propagation

`propagate_failures` converts NaN to 0 where an earlier failure by the agent makes the later check a certain failure. It keys on **which required file is recorded missing**, never on a metric merely being absent:

| trigger | forces to 0 |
|---|---|
| `converted_data.pkl` missing or empty | categories 3-9 |
| `full_data_format_valid` is 0 | categories 4-9 |

Nothing propagates into categories 1-2, and `undefined_categories` blocks propagation into a category with no meaning for the dataset — allen2p has `dinput == 0`, so forcing its input-range score to 0 would invent a failure the agent could not have committed.

## How averaging is done

Four levels, each built from the one above:

```
trial score        one number per trial per category — no averaging

per category       mean over trials (usually 3), NaN dropped

per trial          mean over the 9 categories, within one trial

per arm            mean over trials of the per-trial number, std over trials
```

Two rules applied throughout:

- **NaN is dropped, never treated as zero.** A category that could not be measured shrinks the denominator rather than dragging the mean down.
- **`ddof=1` for every standard deviation.** The trials are a sample of what an arm does, not the population. Undefined for a single observation, so NaN rather than a misleading 0.

### Per output

| output | shows | averaging |
|---|---|---|
| `minimal_vs_full_prompt_{claude,codex}_table.pdf`<br>`agent_vs_model_{gpt,opus}_table.pdf` | one square per (arm, trial) × category, per dataset | **none** — raw per-trial category scores |
| `agent_vs_model_table.md` | the same, as text | **none** — same values, `lesion_score_table` and `render_lesion_table` share `category_matrix` |
| `lesion_scores_table.{md,tex}` | one cell per (arm, dataset) | mean over categories within a trial, then **mean ± std over the 3 trials** |
| `minimal_vs_full_prompt_difference.pdf` | bars per (category, agent) | per-category minimal−maximal per dataset, then **mean ± std over the datasets**; the scattered points are the per-dataset values |
| `LLM_vs_harness_difference_{gpt,opus}.pdf` | the same, for arm pairs | as above |
| `LLM_vs_harness_difference_{gpt,opus}.{md,tex}`<br>`minimal_vs_maximal_difference.{md,tex}`<br>`minimal_vs_full_prompt_{claude,codex}.md` | table form of those figures | as above — verified equal to the drawn bar heights |
| `threshold_sensitivity.pdf`<br>`threshold_sensitivity.txt` | pass rate against threshold, one panel per verifier limit | **none** — a sweep over candidate thresholds, not over trials. See *Threshold sweeps* below |

Every table above also carries a final **Mean** row: for the category-row tables it is the mean of the nine categories, for `lesion_scores_table` the mean over arms. NaN is dropped there too, so a mean can rest on fewer entries than the column appears to show, and in the difference tables its `±` is the spread **across categories** rather than across datasets like the cells above it.

### Why differences average over datasets

A difference is taken **within a dataset**, between the two arms' trial-averaged scores — `compute_diff_per_category` reads `mean_scores_per_category`, which is keyed `(dataset, agent, prompt)` and has already collapsed the trials. Trials are not paired across arms, and could not be: trial 1 under one arm is an independent run from trial 1 under another, and the index is only a repeat counter. Pairing is by dataset, which is what makes the dataset's own difficulty cancel.

The spread is then taken **between datasets**, n = 8. Three trials of one agent on one dataset are not independent evidence that a prompt or model matters: they share the dataset's quirks, its reference statistics and the agent's characteristic approach to it. Pooling all ~100 (dataset, trial, category) differences would give a much smaller error bar by treating correlated observations as independent.

`compute_diff_per_category(arm1, arm2)` is the general form and works for any two arms — a prompt comparison is just an arm pair that shares an agent.

## Threshold sweeps

`threshold_sensitivity.pdf` and `.txt` ask a different question from everything above: not "how did the agents do" but "would a different limit change the answer". One panel per verifier limit, pass rate against candidate threshold, with a marker at the limit actually in force. A flat curve through that marker means the limit is not separating anything.

Every limit comes from `STATLIMITS` rather than being restated, so a panel cannot drift from what `test_outputs.py` asserts.

Three of the tests are asserted **once per output variable**, so they carry two readings and both are drawn:

- **all outputs** (solid) — the fraction of trials where *every* variable passed, which is what the verifier's pass/fail actually is
- **mean over outputs** (dashed, "per output" in the text file) — the mean, over trials, of the fraction of that trial's variables that passed

Note the second reading is a mean of per-trial fractions, **not** the fraction of all variables pooled: every trial counts equally regardless of how many outputs it has, consistent with the averaging rules above. The counts vary from 1 to 6, so the two differ by a couple of points.

## Known caveats

- **The overall arm score weights all nine categories equally.** "Core files exist" counts as much as "Decoder accuracy", and a boolean counts as much as a fraction. It is a summary of breadth, not of quality.
- **Four of the nine are binary, five are fractions.** Categories 1-4 and 6 are 0-or-1; categories 5 and 7-9 are fractions over variables or fields.
- **allen2p scores 1 on input ranges by construction.** It has `dinput == 0`, so there are no input variables to get wrong and `mean_input_range_error` is 0. This is what the verifier does — its assert is guarded on there being matched inputs, so `test_data_stats` never fails allen2p on input ranges — but the category contributes a free point to allen2p rather than measuring anything. It previously scored NaN here, which made a per-category mean average over 5 datasets while every other category used 6; that raggedness is gone, and the mean of the per-category means now agrees with the mean of the per-dataset means.
- **Row means and column means can disagree in sign.** Averaging the same difference matrix across datasets or across categories gives different
  marginals; one strong dataset can make every per-category mean positive while several per-dataset means stay negative. Prefer the per-dataset view for claims about whether one arm beats another.
