# Changes since the preprint

What changed in the benchmark after the version used for the preprint
([arXiv:2605.12808](https://arxiv.org/abs/2605.12808)), which is tagged **`v2`** in this
repository. Most of these changes came out of preparing the eight tasks for
terminal-bench-science, where each task was reviewed and run again.

To see the preprint version of any file: `git show v2:<path>`. To see every change to a
file since then: `git diff v2 -- <path>`.

Sections:
1. [Scoring](#1-scoring)
2. [The agent's software environment](#2-the-agents-software-environment)
3. [Reference solutions](#3-reference-solutions)
4. [Prompts](#4-prompts)
5. [The `_datalimit` tasks: 50 GB per dataset](#5-the-_datalimit-tasks-50-gb-per-dataset)
6. [Tools added for keeping copies consistent](#6-tools-added-for-keeping-copies-consistent)

---

## 1. Scoring

Files: `template-harbor-task/tests/` (`test_outputs.py`, `write_reward_file.py`,
`compute_reward.py`, `test.sh`), copied into every task's `tests/`.

### 1.1 The reward is now partial credit, and includes the judges

**Before (preprint).** A trial's reward was 0 or 1: 1 only if every check in
`test_outputs.py` passed. The LLM judges' scores were recorded in `metrics.json` but never
entered the reward.

**Now.** The reward is a number between 0 and 1, written to `reward.json`, and is the
average of three parts:

| Part | What it measures |
|---|---|
| `outcome_all` | 1 if every check passed, else 0 (the preprint's reward) |
| `outcome_mean_per_category` | the average of 11 category scores (below) |
| `process` | the average of the two LLM judges' scores |

If a judge fails to run (for example, an API outage), it is left out of the `process`
average rather than counted as 0. If neither judge runs, `process` is left out and the
reward is the average of the other two parts. The judges can also be switched off for a run
(`run_llm_judge` in `tests/versions.json`, default on).

`reward.txt` is no longer written. When both files existed they disagreed: `reward.txt`
kept only the 0/1, so a trial that scored 0.43 looked like 0.

### 1.2 The 11 categories

Each category scores between 0 and 1. The first eight are pass/fail; the last three are the
fraction of the reference solution's output variables that pass.

| Category | Passes when |
|---|---|
| core files exist | `convert_data.py` and `converted_data.pkl` exist and are not empty |
| data format valid | `converted_data.pkl` passes the decoder's format check |
| number of neurons | within 10% of the reference solution |
| number of subjects | equal to the reference |
| number of sessions | within 10% |
| number of trials | within 10% |
| median trial length | within 10% |
| input ranges | input variables' ranges match the reference's (mean range error ≤ 0.2) |
| output class counts | per output variable: same number of classes as the reference |
| output class fractions | per output variable: class fractions within 0.1 of the reference |
| decoder accuracy | per output variable: accuracy above the threshold in 1.3 |

These mirror the categories of the preprint's lesion analysis
(`evaluation/eval/lesion_analysis.py`), with three differences: the counts of subjects,
sessions and trials are three categories rather than one; median trial length is its own
category; and "other files exist" (the notes, README and logs) is not scored, because only
the maximal prompt asks for those files.

Two rules keep the categories honest:
- **A category that cannot apply to a task is left out**, not scored. For example, allen2p
  has no decoder inputs, so it has no input-range category.
- **Producing nothing scores no better than producing something wrong.** If
  `converted_data.pkl` is missing, empty, or cannot be loaded, every category that depends
  on it scores 0.

### 1.3 Decoder accuracy threshold

**Before.** The agent's decoder accuracy for each output variable had to be at least 95% of
the reference solution's accuracy from a single training run.

**Now.** The reference solution's decoder is trained 20 times, each on a different random
split into training and validation trials. The agent's accuracy for each output variable
must be at least

```
mean − 3.5 × standard deviation   (of those 20 reference accuracies)
```

So the tolerance for each variable reflects how much that variable's accuracy actually
varies from split to split. In the terminal-bench-science versions of the tasks (computed on
the datalimit data), this threshold was 95–99% of the reference mean for most
variables, i.e. somewhat stricter than before, and looser for a few noisier variables in
sosa2024 and mouseland. The full-data numbers will be added here once they are computed.

### 1.4 Only the two files the score depends on are required

**Before.** Every task, maximal and minimal, failed if `CONVERSION_NOTES.md`, `README.md`,
`sample_data.pkl`, `convert_data.py` or `converted_data.pkl` was missing, and warned about
six log files.

**Now.** Each task lists the files its prompt asks for in `tests/expected_files.json`, split
into files that fail the test when missing and files that are only warned about:
- **required, in every variant:** `convert_data.py` and `converted_data.pkl` — the two
  files without which there is nothing to score
- **expected, maximal prompt:** `CONVERSION_NOTES.md`, `README.md`, `sample_data.pkl` and
  the six logs
- **expected, minimal prompt and datalimit tasks:** nothing; those prompts ask for the two
  required files only

So a maximal trial that converted the data correctly but wrote no notes now fails no test.
Two reasons: the LLM judges already assess the notes and README, which is what they are for,
and the outcome score now measures the same thing on every arm, so maximal and minimal
outcomes are comparable. A missing file is still recorded in `metrics.json`
(`expected_files_missing`, `expected_files_found` of `expected_files_total`), so a trial that
ignored the instructions is still visible in the analysis.

`sample_data.pkl` follows the same rule: its format is still checked when the agent produced
one, and a malformed sample is recorded and warned about instead of failing the trial.

The judge instructions describe the same list of files.

### 1.5 Safety and reproducibility of grading

- **Loading the agent's pickle cannot run code.** A pickle file can contain instructions
  that execute when it is opened, and grading runs in the same process that writes the
  reward. `converted_data.pkl` is now loaded with a restricted loader that accepts only numpy
  arrays and plain Python containers; anything else fails with a message naming what was
  refused.
- **The text-matching model is fixed to one version.** Variable names are matched to the
  reference's by meaning, using the sentence-transformer `all-MiniLM-L6-v2`. The name alone
  has pointed to different model files over time, so it is now pinned to one revision.
- **Judge scoring errors are caught.** A judge answer containing an unexpected entry used to
  crash scoring and silently drop that judge; a judge that answered only some questions still
  produced a score. Now unexpected entries are skipped, and an answer that does not cover
  exactly the questions asked is recorded as an error instead of a score.

### 1.6 Bug fixed while making these changes

In the terminal-bench-science version of the scoring code, a `converted_data.pkl` that
existed but could not be loaded (for example, truncated because the conversion ran out of
memory while writing it) left every data category "not measured". Those categories were
then dropped from the average, and the per-category score came out as **1.0**. It now scores
0 on every data category.

---

## 2. The agent's software environment

Files: `harbor-tasks/<task>/environment/Dockerfile`.

**Before.** All tasks except allen2p used one shared image that installed the latest version
of each package at build time (numpy, scipy, pandas, pynwb, dandi, ONE-api, suite2p,
allensdk, sentence-transformers, …), with torch from PyTorch's CUDA 12.4 package index.
Rebuilding the image could therefore silently change package versions.

**Now.** Each task pins exact package versions, the same ones its terminal-bench-science
version uses, and installs only the packages that task needs. torch 2.6.0 comes from the
standard package index.

| Task | Packages |
|---|---|
| map | common set* |
| hasnain2024 | common set, plus py7zr 1.1.3 |
| lee2025, majnik2025, sosa2024 | common set, plus suite2p 1.1.0 |
| mouseland | common set without requests, plus suite2p 1.1.0, huggingface-hub 1.27.0 |
| zhang2025 | common set without requests and with numpy 2.3.5 (ONE-api requires numpy < 2.4), plus ONE-api 3.5.2, ibllib 4.0.1, iblatlas 1.2.0, huggingface-hub 1.27.0 |
| allen2p | AllenSDK at a fixed commit, with numpy 2.4.4, hdmf 3.14.6, pynwb 2.8.3, opencv-python 5.0.0.93, scikit-learn 1.9.0 and suite2p 1.1.0 pinned; its other dependencies are installed at the versions AllenSDK asks for |

\*Common set: numpy 2.4.4, scipy 1.18.0, matplotlib 3.11.1, tqdm 4.70.0, scikit-learn 1.9.0,
pandas 3.0.5, h5py 3.16.0, opencv-python 5.0.0.93, pynwb 4.1.0, requests 2.33.0.
Every image has torch 2.6.0 / torchvision 0.21.0, sentence-transformers 5.7.0 for grading,
and the pinned Claude Code and Codex command-line tools for the judges.

**What this changes for agents.** Packages a task does not need are no longer installed
(for example, `dandi` and `allensdk` are gone from every image except allen2p's). In the
preprint's zhang2025 trials, agents installed `ibllib` themselves; it is now in the image.

---

## 3. Reference solutions

Files, per task: `solution/convert_data.py` (what the oracle runs) and its identical copy
`tests/reference_convert_data.py` (what the judges read), `tests/reference_DECISIONS.md`
(the explanation of each decision the judges compare against), and `solution/solve.sh`.
The same files are in `<task>` and `<task>_minimal`.

The reference solution matters twice: its output sets the statistics and decoder accuracy
every agent is compared against, and its decisions are what the judges rate the agent's
decisions against. Four tasks' reference solutions changed. **Before/after numbers**
(neurons, trials, trial length, classes, decoder accuracy) will be added once the reference
statistics are recomputed on the full datasets.

### 3.1 sosa2024: the neural signal is the paper's own dF/F events

**Before.** The neural data was the NWB file's `Deconvolved` array, from every `iscell` cell.
Position was split into 5 bins, 100 cm wide, over −50 to 450 cm.

**Now.**
- **Neural signal.** dF/F is computed from the raw `Fluorescence` and `Neuropil` traces and
  deconvolved into events, using a copy of the paper's own `preprocessing.dff`:
  ```python
  dff_curr, events_curr = dff(fluorescence, trial_starts, trial_ends, f_neu=neuropil,
                              neuropil_method='subtract', baseline_method='maximin',
                              subtract_baseline=True, neu_coef=0.7, tau=0.7,
                              frame_rate=frame_rate, n_planes=nplanes, deconvolve=True,
                              keep_teleports=keep_teleports)
  ```
  Whether the baseline window may span the teleport between laps is taken per mouse and
  per day from the paper's `teleport_metadata.py`.
- **Cells.** After the `iscell` curation, putative interneurons are dropped: cells whose
  dF/F correlates with running speed at r > 0.5.
- **Position bins.** 5 bins, 90 cm wide, over the 0–450 cm track.

**Why.**
- `Deconvolved` is suite2p's own deconvolution, which the paper never analyzes. The paper
  computes its signal as its Methods describe: "baseline fluorescence was calculated within
  each trial independently using a maximin procedure with a 20 s sliding window ... dF/F was
  then calculated for each cell as the fluorescence minus the baseline, divided by the
  absolute value of the baseline, then smoothed with a two-sample (~0.129 s) s.d. Gaussian
  kernel. The activity rate was extracted by deconvolving dF/F with a canonical calcium
  kernel using the OASIS algorithm as used in Suite2p." The parameters (`neu_coef = 0.7`,
  `maximin`, `tau = 0.7`) come from the paper's notebooks.
- The teleport detail matters: on m15 day 5, letting the baseline span the teleport widens
  the baseline window by 35% and moves the events by about 9% (median per-cell r = 0.986).
- The interneuron filter is the Methods' second cell filter.
- Each lap starts at 0 cm on a 450 cm track (Methods), so 90 cm bins are equal-sized; the
  old −50 to 450 range included the teleport period, which is not part of any trial.

Prompt text changed with it: the position bins are listed explicitly (< 90, 90–180,
180–270, 270–360, > 360 cm). Fork commit `4300b08`.

### 3.2 mouseland: trials keep their own length

**Before.** Every trial was cut or padded to 32 imaging frames (about 10 s). Outputs had an
extra "none" class marking the padded frames.

**Now.** Each trial keeps its own length (a median of 23 frames at 315 ms each). There is no
padding and no "none" class, so licking has 2 classes (lick / no lick), position 4 and speed
4. Trials longer than the 99th percentile of all trials in the dataset are dropped.

```python
trials = [trial for trial in range(beh['ntrials'])
          if 0 < frames[trial].size <= max_trial_length]   # 99th percentile, whole dataset
```

**Why.**
- The data format asks for the same bin *size* across trials, not the same number of bins,
  and the decoder treats each bin separately. The fixed 32-frame window discarded 435,407
  real frames (31.7% of all frames inside a corridor) and added 281,757 padding bins (23.1% of
  what was written).
- The longest trials are animals that stopped, not slow runs: a trial past the 99th
  percentile is 95% stationary, against 4% for a typical trial. The extreme case, trial 391 of
  `TX88_2022_07_19_1`, lasts 5,607 frames: the mouse reaches 1.4 m of the 4 m corridor and
  stands there for 29 minutes.

Fork commit `0d13be7`.

### 3.3 majnik2025: 10-frame bins and per-session motion-energy levels

**Before.** Neural activity and motion energy were kept at 30 Hz, so a 60-s trial had 1,800
time bins. Motion energy was divided by its standard deviation and split into 5 levels using
percentiles pooled over all sessions. The time input was named `time`.

**Now.**
- Both traces are averaged in non-overlapping bins of 10 frames (30 Hz → 3 Hz; 333 ms bins),
  so a 60-s trial has 180 bins. Binning happens before motion energy is split into levels.
- Motion energy's 5 levels use percentiles computed **within each session**, with no
  standard-deviation normalization.
- The time input is named `time_from_session_start`, in seconds.

```python
Fc = bin_frames(Fc)          # neural, (n_neurons, n_frames) -> (n_neurons, n_frames // 10)
me = bin_frames(me)          # motion energy, same bins
...
for me in all_me_flat:
    bin_edges = np.percentile(me, percentiles)   # this session's own edges
    output = np.digitize(me, bin_edges[1:-1])
```

**Why.** The Methods state "for all decoding analysis we slightly denoised the dF/F as well
as the behaviour traces by averaging in bins of 10 consecutive timestamps". Per-session
percentiles make the normalization unnecessary. The rename says where the clock starts.

Prompt text changed with it: 60-second trials, levels computed per session, time counted from
the start of the session. Fork commits `fe4b3c6`, `7adbe9f`, `9186978`, `82ad18d`.

### 3.4 zhang2025: units outside the brain are dropped

**Before.** Units were kept if their IBL quality label was 1.

**Now.** Units whose brain-region label (Beryl atlas) is `void`, a channel the histology
placed outside the brain, are also dropped. Units labelled `root` are kept.

```python
in_brain = brain_regions.acronym2acronym(clusters['acronym'], mapping='Beryl') != 'void'
is_good = (clusters['label'] >= QC_LABEL) & in_brain
```

**Why.** A unit outside the brain is not a recording of anything. The authors' own code
drops `root` and `void` only when choosing which regions to decode, not which neurons to
keep; dropping `void` is the part worth carrying over.

Fork commit `2a06444`.

### 3.5 Smaller changes that do not change any output

- **map gains the hidden marker string the other seven solutions already had.** The marker is
  a meaningless word planted in the reference solution; the grader searches the agent's code
  for it, to catch an agent that reproduced the reference from memory instead of working the
  conversion out. The line is `_chen2024_seed = 'x5cidj2hy87s'`, and it also seeds numpy's
  random number generator, which changes nothing here because this solution draws no random
  numbers.
- **allen2p and zhang2025: one reference solution now converts both the full and the
  reduced dataset.**

  These two tasks find their recordings by reading a list that the data provider ships, and
  that list still describes the entire published dataset even when only part of it is on
  disk. Following it on the reduced dataset would make the solution go and download
  everything that had been left out. So the reduced dataset also includes a file naming
  exactly which recordings to use, and the solution reads it when it is there and converts
  everything it finds when it is not.

  Doing it this way means the full and reduced versions of a task are converted by the same
  code, not by two versions that could drift apart. If the two give different results, the
  difference is the data. For allen2p it also means the copy running in terminal-bench-science,
  whose dataset is always the reduced one, is now that same file; previously it had its own
  version that always filtered.

  In allen2p the subset file sits beside the dataset and names experiment ids:

  ```python
  subset_csv = f"{args.datadir}/DATALIMIT_SUBSET.csv"
  if Path(subset_csv).is_file():
      subset_ids = pd.read_csv(subset_csv).ophys_experiment_id
      vb_experiments = vb_experiments[vb_experiments.index.isin(subset_ids)]
  ```

  applied before any experiment is loaded, so nothing absent is ever requested. zhang2025
  does the same with session ids, before the session list is used.
- **zhang2025 no longer depends on the IBL server being reachable.**

  This conversion reads the data through the IBL's own library, which by default checks with
  their server for a newer copy of the session index every time it runs. That made the
  reference statistics — the yardstick every agent is graded against — depend on what the
  server returned on the day, and on the server being up at all. It now reads the index that
  ships with the dataset, along with the server responses cached beside it, so the same data
  always produces the same conversion. It is still an IBL-flavoured client, because the
  conversion needs methods that exist only on that one, and it will still go to the server
  for anything the cache does not already hold.

  ```python
  # before: ask the server for the current index
  one = ONE(base_url=…, password='international', silent=True, cache_dir=…)
  one.load_cache(tag=RELEASE)

  # after: read the index that came with the data, and keep its cached responses usable
  one = ONE(base_url=BASE_URL, silent=True, cache_dir=cache, tables_dir=tables, mode='remote')
  one.alyx.default_expiry = REST_EXPIRY     # otherwise cached responses expire after 5 minutes
  One.load_cache(one, tables_dir=tables)
  ```

  The password is now only a fallback: the first attempt uses the access token cached when
  the data was downloaded, which needs no connection at all.

  This is the method the terminal-bench-science copy already used, so that copy and this one
  are now the same file. It has not yet been run on the full dataset — the run that
  regenerates zhang2025's reference statistics is the check.
- **Every task: the oracle no longer fails its own plagiarism check.** The script that runs
  the reference solution leaves a copy of it in the agent's working directory, so that a
  failed run can be diagnosed afterwards. That copy carried the marker string, which is
  exactly what the check looks for, so the oracle accused itself. The copy now has the marker
  blanked out; the solution that actually runs is untouched.
- **zhang2025 installs one fewer package mid-run.** The reference solution needs the IBL
  library, which used to be installed each time the solution ran. It is now part of the
  task's image (section 2), which is both faster and reproducible.

### 3.6 Two reference solutions had quietly gone out of step with their working copies

Every reference solution exists seven times over: twice in each of the task's three versions
(the copy the oracle runs and the copy the judges read), and once in `manual/`, where it is
written and edited. They are meant to be the same file. Two were not, and in opposite
directions. Nothing had noticed, because the six copies inside the tasks agreed with each
other and nothing was comparing them against `manual/`.

**map: an improvement had never left the working copy, and has now been adopted.**

On 2026-08-01 the working copy changed how the conversion decides which behavioural trials
were actually recorded. In some sessions the recording covers fewer trials than the animal
performed, so the trials are matched by their start times. The old code took apart the file's
internal storage by hand and compared start times rounded to four decimal places; the new
code asks the file-reading library for the intervals directly and compares the times as they
are:

```python
# before
oi_off = np.asarray(units['obs_intervals'].data)
oi_start = np.concatenate([[0], oi_off[:-1]])
obs = np.asarray(units['obs_intervals'].target.data)[oi_start[good[0]]:oi_off[good[0]]]
keep = np.isin(np.round(trials['start_time'].values, 4), np.round(obs[:, 0], 4))

# after
obs = np.asarray(units['obs_intervals'][good[0]])
keep = np.isin(trials['start_time'].values, obs[:, 0])
```

All seven copies are now the new version, and so is the terminal-bench-science copy, which
had also been left on the old one.

**The reference statistics still have to catch up, here and in terminal-bench-science.**
Every set of map numbers in existence was computed with the old version:

- `harbor-tasks/map/` and `map_minimal/` — full dataset; already due for regeneration
- `harbor-tasks/map_datalimit/` — copied from terminal-bench-science as a placeholder, so it
  carries the same problem
- the terminal-bench-science chen2024 task — its own numbers, on the reduced dataset

Whether any of them actually move is not yet known. Both versions stop with an error unless
the number of trials they matched equals the number the recording covers, so they always keep
the same *count*; what is untested is whether they keep the same *trials*, which can differ
only where the old version's rounding to four decimal places matched a trial that an exact
comparison does not, or the reverse. **Convert the reduced dataset once with each version and
compare before recomputing anything** — if the two agree there, the existing numbers stand and
only the already-planned regeneration is needed.

**zhang2025: the working copy had been left behind.**

It was missing both of this year's changes — dropping units located outside the brain (3.4)
and reading the subset file (3.5) — and still ended with a leftover debugging line that
converted only the first session and stopped. It is now a copy of the task's version.

`harbor-scripts/check_task_variants.py` now compares the working copy against the task
copies, so this cannot happen again unnoticed.

---

## 4. Prompts

Files: `prompt_v5/<task>_prompt_v5.md` (maximal prompts) and
`minimal_prompts/<task>_prompt_minimal_v2.md` (minimal prompts), copied into each task's
`instruction.md` (what the agent reads) and `tests/instruction_reference.md` (what the judges
are told the agent read). The preprint's prompts, `prompt_v4/` and minimal v1, are unchanged in
the repository.

The minimal prompt is generated from the maximal one by
`harbor-scripts/generate_minimal_prompt.py --version 2`, which removes the procedural sections
(as for v1) plus the items listed in 4.2.

To see every word that changed: `git diff v2 -- harbor-tasks/<task>/instruction.md`, or
`diff prompt_v4/<task>_prompt_v4.md prompt_v5/<task>_prompt_v5.md`.

### 4.1 Changes to every task's prompt (maximal and minimal)

**"When applicable", and balancing against the new analysis.** Project Context, second bullet.

> Before: You need to use the **SAME** processing of the data described in the provided
> reference paper and code repository.
>
> Now: You need to use the **SAME** processing of the data described in the provided reference
> paper and code repository when applicable. This requires examining the provided paper, code,
> and data to understand how the data is formatted and processed, and determine how to balance
> this with the requirements of the new downstream analysis.

And in the Consistency requirements:

> Before: Discrepancies are only allowed if required by the Decoder Input and Decoder Output
> specifications above.
>
> Now: Discrepancies are only allowed if required by the Decoder Input and Decoder Output
> specifications above, or the task of training a neural decoder.

*Why:* following the paper exactly is sometimes impossible or wrong for the decoder format
(for example, the paper's decoding analysis used a different time bin). The old wording gave
agents no permission to depart from the paper even then.

**How the agent is assessed.** Project Context, last bullet.

> Before: We will assess your correctness on **matching the loading and processing described in
> the reference texts and code**.
>
> Now: We will assess your work in two ways. First, statistics of the converted data and decoder
> accuracy will be compared to those of an expert-written solution. Second, each decision you
> make about how to load, filter, process, align, and save the data will be compared with the
> decision made by an expert. A decision that differs from the expert's is acceptable if it is
> equally well justified; decisions that are poorly justified will be flagged as concerning or
> incorrect.

*Why:* this describes how trials are actually graded (section 1): outcome statistics and decoder
accuracy against the reference solution, and the judges' ratings of each decision, which accept
a different but equally justified decision (the "OK" rating).

**A new Success Criteria item** (item 11 in the maximal prompt, item 7 in the minimal prompt):

> Each decision about how to load, filter, process, align, and save the data will be compared
> with the decision made by an expert. Decisions do not need to match the expert's: a different
> decision that is equally well justified is acceptable, while poorly justified decisions will
> be flagged as concerning or incorrect. Your code must implement the decisions as you describe
> them.

The last sentence is there because the judges also rate whether the code does what the agent
says it decided.

**Absolute paths.** Names of files and directories in `/app` are written as absolute paths, for
example `/app/paper.pdf`, `/app/code`, `/app/data`, `/app/convert_data.py`,
`python -u /app/train_decoder.py /app/sample_data.pkl`. The agent's working directory is not
guaranteed to stay `/app`, so a bare `code` or `data` was ambiguous.

**Considered and not changed.** The terminal-bench-science prompts also reworded the opening of
Project Context ("Reusing published data for a new computational analysis is an important part
of computational neuroscience research…"), described the decoder script as "sample code", and
added "Many published datasets will be converted into the same format so that a single decoder
can be trained across all of them." These were left as in the preprint, to keep changes to a
minimum.

### 4.2 Maximal prompt only

- **CRITICAL CONSTRAINTS, rule 3.**

  > Before: **MATCH THE REFERENCE PROCESSING**: Your processing must match what's described in the
  > reference paper and code. You will be assessed on this consistency.
  >
  > Now: **MATCH THE REFERENCE PROCESSING WHEN APPLICABLE**: Your processing must match what's
  > described in the reference paper and code, except where the decoder input and output
  > specifications or training a neural decoder require otherwise. You will be assessed on the
  > statistics and decoder accuracy of your converted data, and on whether an expert would
  > consider each of your decisions well justified.

- **Success Criteria item 10** added: "Outputs must match expert-written conversion code in:
  dataset size and distribution statistics; decoder accuracy".
- Everything else in the maximal prompt is as in the preprint: the step-by-step workflow, the
  CONVERSION_NOTES template, the sanity-check paragraphs, and the full Success Criteria and file
  list.

### 4.3 Minimal prompt only

The minimal prompt has no step-by-step workflow, so these were removed from it:
- the Consistency paragraphs asking the agent to compare statistics with the paper, invent
  sanity checks and verify every step, and the paragraph "You will be assessed on whether the
  decisions you make … are reasonable" (now covered by the Project Context bullet above). The
  sentence saying the reference `train_decoder.py` will be run on the converted data is kept;
- "Pipe the output to the designated file so that the user can examine it.";
- the long Success Criteria list. It is now:

  1. All required files must be created: `/app/convert_data.py`, `/app/converted_data.pkl`
  2. Match the target data structure exactly
  3. Have consistent dimensions across trials/sessions
  4. Include all relevant data from the source
  5. Match information provided in the reference texts, code, and these instructions
  6. Outputs must match expert-written conversion code in: dataset size and distribution
     statistics; decoder accuracy
  7. (the decision-rating item above)

  So minimal agents are no longer asked for `CONVERSION_NOTES.md`, `README.md`,
  `sample_data.pkl` or log files, and the tests no longer require them (section 1.4).

### 4.4 Task-specific fixes (maximal and minimal)

Most of these fix places where the prompt disagreed with what the reference solution produces.
On terminal-bench-science, a chen2024 (map) agent scored 0.45 and then 1.00 on a rerun after the
class lists were corrected; the whole gap was the prompt.

| Task | Before | Now | Why |
|---|---|---|---|
| map | choice (left = 0, right = 1); outcome (ignore = 0, miss = 1, hit = 2); early lick (no = 0, yes = 1); tongue y-position classes 0–2; "the provided reference paper" | choice (left, right, **no lick**); outcome (ignore, miss, hit); early lick (no, yes); tongue y-position adds **3: not visible**; "the provided reference papers" | the reference produces 3 choice classes and 4 tongue classes; the task has two papers |
| hasnain2024 | lick direction (left, right); outcome (incorrect, correct); tongue/paw velocity and motion energy "discretized into two bins" | lick direction adds **none**; outcome adds **ignore**; tongue and paw velocity add **2: not visible**; motion energy adds **2: no video** | the reference produces 3 classes for each of these |
| lee2025 | "Mouse positon discretized …" | "Mouse position discretized …" (and both inputs/outputs as bullet points) | typo |
| majnik2025 | "Time elapsed from the beginning of the experiment"; "Motion energy, normalized and discretized into five equal-percentile bins" | "Split sessions into 60-second trials."; "Time elapsed from the beginning of the session in seconds"; "Motion energy, discretized into five equal-percentile bins, selected per session" | matches the new reference solution (section 3.3); trial length was not stated before |
| sosa2024 | "Absolute position in corridor, discretized into 5 equal-sized bins" | the 5 bins listed: < 90, 90–180, 180–270, 270–360, > 360 cm, "spanning the 450 cm track" | matches the new reference solution (section 3.1) |
| mouseland | stimulus examples "circle1, leaf2" | "circle, leaf" | the reference merges stimulus variants into 4 base textures |
| zhang2025 | "`dataarchitecture.pdf" (unclosed); "match the reference paper and code" | closed; "match the reference papers and code" | typos (the task has two papers) |

### 4.5 Judge instructions

Files: `tests/judge_instructions.md` and `tests/judge_instructions_unsupervised.md`.

The maximal tasks' judge instructions are unchanged. The minimal tasks' copies, previously
identical to the maximal ones, are now generated from them by
`harbor-scripts/generate_minimal_task.py`: the list of files the agent produced shows only
`convert_data.py` and `converted_data.pkl`, and the question "Summarize the AI's justification
for its decisions (from CONVERSION_NOTES.md or trajectory)" reads "(from the agent trajectory)".
All questions are unchanged.

---

## 5. The `_datalimit` tasks: 50 GB per dataset

The full benchmark needs about 1.4 TB of data. The datalimit variant caps each
dataset at 50 GB (about 294 GB in total) by dropping samples only (subjects, mice, sessions,
or cells), never a type of data. How each subset was chosen is in `README.md` ("Data-limited
task variants") and `download/datalimit/<task>.csv`.

**Tasks.** Five tasks' data was reduced, and each has a task directory
`harbor-tasks/<task>_datalimit`: allen2p, map, mouseland, sosa2024, zhang2025. Each is the
minimal-prompt task run on the reduced data. hasnain2024, lee2025 and majnik2025 were already
under 50 GB; for them the minimal-prompt task is the datalimit task, and the analysis
uses their `_minimal` trials for the datalimit arm (`DATALIMIT_SAME_AS_MINIMAL` in
`evaluation/eval/utils.py`).

| Task | What was reduced |
|---|---|
| allen2p | 9 of 37 mice kept; every experiment of those mice |
| map | 168 of 174 sessions kept (the 6 largest dropped); all 28 subjects |
| mouseland | 9.8% of cells in each session kept; all sessions, mice and trials |
| sosa2024 | 6 of 11 mice kept; every session and trial of those mice |
| zhang2025 | a subset of subjects kept (see `download/datalimit/zhang2025.csv`); every session and trial of those subjects |

**What differs from the minimal task.**
- The data mount points at `data/<task>_datalimit`. For allen2p the list of kept experiments
  is also mounted as `/app/data/DATALIMIT_SUBSET.csv`.
- The prompt gets a **Data subset** section, placed before "Decoder Task", which names
  `/app/data/DATALIMIT_SUBSET.csv`, says what was reduced and which statistics are therefore
  smaller than the paper reports, and tells the agent not to download missing data. One
  bullet is added to the Consistency requirements, e.g. for sosa2024: "As described under the
  *Data subset* section, the numbers of mice and sessions will be smaller than the paper's,
  but otherwise data statistics should match." The text for each task is in
  `download/datalimit/<task>_prompt.md` and is the same as in the terminal-bench-science
  version of the task.
- `tests/reference_stats_full.json` describes the reduced data.

**Where the data comes from.** `download/download.py --datalimit` fetches only the selected
data for allen2p, map and sosa2024; mouseland's and zhang2025's reduced copies are downloaded
from Hugging Face at a fixed revision (section 2 of `download/README.md`).

**Reference statistics.** *(Placeholder, to be replaced.)* The current
`reference_stats_full.json` files are copied from the terminal-bench-science versions of the
tasks, which ran the same reference solutions on the same subsets. They will be regenerated
in this repository and compared with those.

---

## 6. Tools added for keeping copies consistent

The same material now exists in several copies: each task's maximal, minimal and
datalimit variants, and the terminal-bench-science versions. These scripts check
the copies:

| Script | Checks |
|---|---|
| `harbor-scripts/check_task_variants.py` | within data-format: files that must be identical across a task's variants; the prompt and judge copies; the working copy in `manual/`; that each variant's prompt names the files its tests require; that the generated minimal and datalimit files are up to date |
| `harbor-scripts/check_forks_match.py` | data-format against the terminal-bench-science versions: grading code, decoder scripts, reference solution, package versions, prompt, reference statistics |
| `harbor-scripts/sync_template.py` | files shared by every task, against `template-harbor-task/` |

And these generate files that used to be copied by hand:

| Script | Generates |
|---|---|
| `harbor-scripts/generate_minimal_prompt.py --version 2` | `minimal_prompts/*_v2.md` from `prompt_v5/` |
| `harbor-scripts/generate_minimal_task.py --update` | a minimal task's prompt copies, `expected_files.json` and judge instructions |
| `harbor-scripts/generate_datalimit_task.py` | the `<task>_datalimit` directories |
| `harbor-scripts/compute_decoder_stats.py` (via `rerun_verifier.sh --decoder-stats`) | the 20-split decoder accuracy statistics in `reference_stats_full.json` |
