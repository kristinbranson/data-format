# What is left to do

State as of 2026-09-19. Everything described in `harbor-tasks/changes_since_preprint.md` is
committed and pushed, through `583fe2a`. The preprint's version is tagged `v2`.

**All eight tasks now have reference statistics on the full data**, mouseland included, and
all 54 graded output variables carry a 20-replicate mean and standard deviation. What is left
is rerunning agents, not computing references.

---

## 1. Mouseland's reference statistics -- DONE 2026-09-19

The oracle and all 20 replicates finished on the cluster and the merged file is installed in
`harbor-tasks/mouseland/tests/` and `harbor-tasks/mouseland_minimal/tests/`, byte-identical;
`check_task_variants.py` passes for all 8 tasks.

Sources, kept in case the numbers need re-deriving:

| what | where |
|---|---|
| oracle trial | `/groups/branson/home/bransonk/harbor-cluster-jobs/refstats/mouseland/2026-09-18__19-18-13/mouseland__LopUGuA` |
| the 20 replicates and the merged file | `/nrs/branson/bransonk/mouseland-refstats/decoder_replicates/` |
| the conversion the replicates trained on | `/nrs/branson/bransonk/mouseland-refstats/converted_data.pkl` |

The oracle's own `converted_data.pkl` and that copy are the same size to the byte and their
`data_summary` blocks are identical, so the merged file's statistics and accuracies describe
one conversion. 19 subjects, 89 sessions, 37,728 trials, 11-238 frames per trial.

Twelve of the twenty replicates fell back to the CPU when the L4 ran out of memory. Each
replicate records which device trained it, and the spread within each device matches the
spread overall, so the fallback is not what makes mouseland's variability large -- see
`changes_since_preprint.md` section 1.

`check_output_classes.py` passes for all three mouseland variants. `visual_stimulus` reports
UNKNOWN rather than ok in every one: the prompt says "e.g. circle, leaf, etc." and names no
count, so the parser has nothing to compare. That is the intended wording, not a defect.

**When mouseland's trials are re-scored, reuse the recorded accuracy with
`rerun_verifier.sh --reuse-accuracy`, as for every other task.** Reuse does put the two sides
of the `mean - ACCURACY_NSTD * sd` comparison on different decoder versions -- mouseland's
reference statistics come from the current decoder, its agents' accuracies from March and
July -- but that mismatch is not specific to mouseland. The other seven tasks' references come
from `ffb68a5`, which is likewise not the decoder that measured their agents.

The size of the gap has been measured, on
`majnik2025_minimal/codex/2026-07-28__22-20-13_trial1`: 0.39974 as recorded in July against
0.39704 retrained in the current tree, which carries both the threading change and the
short-session fix. That is 0.68%, about 13% of the 4.5 sd band, and it did not move the
verdict. Retraining mouseland's eighteen conversions, which run from 156 MB to 383 GB and
would need a GPU queue and a day or more each, buys a shift of that order.

What could make mouseland the exception is the short-session fix specifically: it holds
sessions with fewer than two trials out of both splits, so it only bites on data that has
them. Verify rather than assume, by listing each trial's
`(reference mean - recorded accuracy) / sd` per output variable. A trial clearing its bar by
much more than 1 sd cannot be flipped by a sub-1% shift; retrain only one that does not.

Three trials need deciding separately, having nothing to reuse.
`mouseland_minimal/claude-code` trial2 (22 GB) and trial3 (383 GB) hold a conversion but no
recorded accuracy -- their original runs never produced one -- and `--reuse-accuracy` raises
on a missing accuracy rather than passing quietly, so each needs either a retrain or an
explicit decision to let the decoder test fail. `mouseland/terminus-gpt` trial3 has no
`converted_data.pkl` at all and fails on its own, which is the intended score under
`changes_since_preprint.md` section 1.6.

## 2. Rerun the agents on four tasks

`map`, `hasnain2024`, `majnik2025` and `sosa2024`, **every variant** -- maximal, `_minimal`
and, where one exists, `_datalimit`. Their existing trials were run against a prompt that
no longer describes the task, so those trials measure a different question from the one
the benchmark now asks, and re-scoring them cannot fix it: the agent saw different
instructions.

The other four need no rerun. `lee2025`, `zhang2025`, `mouseland` and `allen2p` changed
only in typos and wording -- "positon", an unclosed backtick, "circle1, leaf2" for
"circle, leaf" -- none of which alters what the agent is asked to produce.

Two different reasons, and the difference matters for what the reruns can be compared to:

**The prompt was wrong, the reference solution was not.** `map`'s prompt listed 2 choice
classes and 3 tongue-position classes where the reference produces 3 and 4;
`hasnain2024`'s said "two bins" for four output variables that the reference gives three.
Agents that followed the prompt were marked down for it. A terminal-bench-science agent
on map scored 0.45 and then 1.00 on a rerun after only the class lists were corrected --
the whole gap was the prompt. These reruns are comparable to the old ones: the task is
unchanged and the instructions merely stopped misdescribing it.

**The prompt and the reference solution changed together.** `majnik2025` now states
60-second trials, motion-energy percentiles per session rather than pooled, and time from
session start in seconds (section 3.3); `sosa2024` now lists 5 position bins spanning the
450 cm track (section 3.1). The task itself is different, so the old trials are not a
baseline for the new ones -- they answer a different question, and a rerun measures the
new task rather than a correction to the old.

Sections 4.4 and 3 of `changes_since_preprint.md` have the wording before and after.

## 3. Run the maximal prompt on the newest agents

Every task's maximal prompt, on the newest harnesses and models. The pinned versions date
from 2026-07-28 and are two model generations behind. Two steps, because the CLI arms and
the terminus arms are blocked on different things.

### Step 1: claude-code and codex

| arm | pinned now | to run |
|---|---|---|
| claude-code | 2.1.81 + `claude-opus-4-6` | **2.1.278 + `claude-opus-5`** |
| codex | 0.116.0 + `gpt-5.4` | **0.155.1 + `gpt-5.6-sol`** |

`gpt-5.6-sol` rather than `gpt-6-astra`: Astra is newer (2026-08-27) and more capable, but
at $10/$50 per 1M tokens against Sol's $5/$30, over long agentic sessions across many
trials. Sol is the deepest-reasoning tier of the GPT-5.6 family, itself two releases past
the pinned `gpt-5.4`. The `-codex` model variants stop at `gpt-5.3-codex`, so the codex arm
runs a general model either way, as it already does.

To set the versions: copy `harbor-scripts/config_20260728.json` to `config_<newdate>.json`,
edit it, then `python harbor-scripts/apply_versions.py`, which rewrites each task's
`tests/versions.json` and `environment/Dockerfile`. Do not edit those by hand.

Nothing blocks this step: both are installed CLIs, pinned per task, and the harbor that
runs them does not have to change.

### Step 2: terminus

There is no terminus-3. `terminus-2` is harbor's own code rather than an installed CLI, so
its version is the harbor version, and the cluster runs a fork:

| | harbor | source |
|---|---|---|
| cluster (`eval-data-format-podman`) | **0.1.45** | editable, `codepacks/harbor-kai` on `kristin-podman` |
| local docker (`eval-data-format`) | 0.1.44 | site-packages |
| `tb-science` env | 0.21.0 | editable, `codepacks/harbor` on `main` |
| published | 0.23.0 | |

Between 0.1.44 and 0.21.0 `terminus_2.py` grows from 1831 to 1959 lines with 328 lines
differing, and gains `tmux_session.py` and `asciinema_handler.py`. So "newest terminus" is a
real change, and it arrives only with a newer harbor.

**Step 2a: find out how hard the rebase is.** The cluster's podman support lives in
`harbor-kai`: 42 commits against merge-base `6f280307f`, 19 files, +1489/-115, concentrated
in `src/harbor/environments/docker/docker.py` and `docker-compose-base.yaml`, with smaller
changes to `agents/installed/{claude_code,codex}.py`, `cli/`, `models/task/config.py` and
`trial/reverify.py`. The first thing to establish is whether upstream has since added podman
support of its own, which would make the fork unnecessary rather than something to rebase.

Until 2a is answered, the options are: rebase the podman work onto upstream; run the sweep
locally on docker with the `tb-science` env and skip the cluster; or keep terminus on 0.1.45
and accept it lagging the CLI arms.

### The judges move with the agents, deliberately

`claude` and `codex` in that config are the judge pins as well as the agent pins -- the
agent and the judge share `/root/.local/bin` in the trial container, so whichever installs
last wins, and one entry per CLI makes "agent and judge run the same CLI" true by
construction. Each task's `tests/versions.json` is generated from it and carries both the
harness version and the model, which the judge scripts read inside the verifier container.

So editing the config updates the judging as well: the trials are judged by
`claude-opus-5` and `gpt-5.6-sol` rather than `claude-opus-4-6` and `gpt-5.4`. That is
wanted -- the judges should be the current models too -- and it follows that `process`
scores on these trials are not comparable to the existing ones, which were judged by the
older pair.

Nothing further is needed to make it happen; `apply_versions.py` rewrites all 36 generated
files. Worth confirming after the first trial that `metrics.json` records the judge versions
actually used, rather than assuming the container installed what the config asked for.

**What a rerun measures.** Harness, model, judges and -- for the four tasks in section 2 --
the prompt all move at once, so it answers "how do current agents do on the current
benchmark" rather than isolating any one change.

## 4. Podman image builds on the cluster

Every cluster job currently rebuilds the task image, a few minutes to twenty. Two
separate reasons, each with its own fix.

**The private store is set where it is not needed.** `podman_env.sh` puts the graphroot
at `/scratch/$USER/podman-storage`, shared by whatever runs on that node, unless
`PODMAN_PRIVATE_STORAGE=true` moves it under the job's own directory. The private store
exists for queues where several jobs land on one host, since a shared store is only safe
for one job at a time. On `gpu_l4_large` there is one GPU per node and jobs take a GPU
exclusively, so no two can share a host -- measured: eighteen replicates went to eighteen
distinct nodes. There the flag only discards a store that would otherwise be warm for the
next job on that node. `submit_decoder_replicates.sh` hardcodes it true and should not:
set it from the queue, or take a flag, defaulting off where jobs cannot share a host.

**A build that overruns is not cleaned up.** `harbor`'s environment start has a
`build_timeout_sec`, and `compose up -d` builds the image when the store is cold, so the
timeout covers the build. On expiry harbor cancels the await but does not kill the
process, leaving `podman build` running: `cleanup_podman_job` removes containers and the
pause process, and a build is neither, so it survives and LSF holds the job in RUN until
someone kills it. Raising the timeout to 1800 s makes the overrun unlikely rather than
impossible. The cleanup could also kill processes whose root or cwd is under
`$PODMAN_JOB_DIR` before removing it -- scoped to the job's own directory, so a sibling
is never touched, and by pid rather than by name.

**Both go away with an additional image store.** Podman can read images from a read-only
store listed in `storage.conf` as `additionalimagestores`, layering a private writable
graphroot on top. Build each task's image once into a shared location, and jobs find it
present, never write to it, and cannot corrupt each other: no per-job build, no
corruption risk, and nothing for a timeout to interrupt.

## 5. Python embedded in shell scripts

`harbor-scripts/` holds 33 standalone Python helpers and one shell script that embeds
Python in a heredoc instead: `merge_rerun_verifier.sh` (14 lines). It would read better as
a script beside the others, invoked the way `check_data_mounts.py` is.

`rerun_verifier.sh`'s 33-line `--reuse-accuracy` check is now
`harbor-scripts/check_reuse_accuracy.py`, whose five exit paths -- reused, trained anyway,
per-variable disagreement, no accuracy recorded, unreadable file -- can be exercised
without a container.

What the heredoc form costs:

- A traceback names `File "<stdin>", line 12`, which does not locate anything in a
  cluster log.
- It cannot be unit tested. `test_write_reward_file.py` is the precedent for testing a
  helper directly.
- Editors and linters see an opaque string: no highlighting, no `ruff`.
- `bash -n` passes a file whose embedded Python is broken, since it only checks the
  shell around it.

## 6. Decisions waiting

- **Push the fork commits?** Each `~/tb-science-*` clone now has three unpushed commits on
  `neurodata-reuse-<name>`, and those branches have open pull requests. The third carries the
  threaded conversion, the CPU fallback and the two session-handling fixes, which brings
  `decoder.py` and `train_decoder.py` back into step with this repository -- each fork keeps
  only its own harbor-canary line in `tests/train_decoder.py`.
- **Untracked files** deliberately left out of the commits: `harbor-tasks/sosa2024_api/`,
  `harbor-scripts/data_roots.sh`, `evaluation/decoder_variability/`, `figures/*` (regenerated
  from the statistics anyway), `evaluation/eval/lesion_analysis.ipynb`.
- **A loud failure for zhang2025's index loading.** If the session index is not found, the
  search returns nothing without raising. The index is present in both datasets, so it should
  not fire, but a check would fail at the point of the mistake. It would have to go into the
  terminal-bench-science copy too, to keep that one file shared.

## 7. Known gaps, not yet scheduled

- **The forks are behind on grading code.** `check_forks_match.py --worktree` reports
  `tests/test_outputs.py`, `write_reward_file.py` and `train_decoder.py` as differing: the
  forks do not have the per-task `expected_files.json` or the required-files change, and some
  of it cannot be shared anyway, because the forks have no LLM judges.
- **The same knowledge lives in two places.** `evaluation/eval/ratings/experiments.py` and
  `evaluation/eval/{utils.py,trial_metrics.py}` each hold the dataset aliases and parse task
  folder names into a dataset and a prompt variant. They agree today only because `3d91595`
  made them agree. One of them should own it.
- **The analysis code is not described** in `changes_since_preprint.md`. `lesion_analysis.py`
  changed substantially: the accuracy criterion and the threshold-sensitivity figure now work
  in standard deviations rather than the old 0.95 fraction, which changes a figure in the
  paper.
- **The decoder's SVD initialisation does not recover the subspace it claims to.** It projects
  onto `svd_max_neurons` random directions, takes the SVD there and maps back through the
  projection. Against the exact top-`npcs` subspace of a power-law spectrum, that reaches a
  mean principal-angle cosine of 0.46, where the standard formulation -- orthonormalise the
  projected range, then project the data onto it -- reaches 0.998 at the same cost, and
  0.9999 with two power iterations at half the cost. Changing it moves every reference
  number, so it is a decision for after this round of statistics, not part of it.
- **One conversion per epoch, not per run.** `SessionData` converts a session's per-trial
  arrays into the contiguous layout training reads, and the training loop reads every session
  on each of the `num_epochs` passes. Threads hide most of the cost, but the work is still
  repeated. Holding the converted sessions removes it entirely and was measured and rejected:
  the converted copy is the size of the source, and the two together do not fit the memory a
  task is given. Converting once and releasing the source as it goes would fit, but the
  release has to happen on the caller's dict, and both callers keep it -- the verifier for a
  CPU retry after a CUDA out-of-memory, `compute_decoder_stats.py` for its other replicates.

## Running the checks

```bash
source /home/bransonk@hhmi.org/miniforge3/etc/profile.d/conda.sh
conda activate test-decoder-data-format
cd /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format

python harbor-scripts/check_task_variants.py           # a task's variants, and manual/
python harbor-scripts/check_forks_match.py --worktree  # this repo vs the tb-science clones
python harbor-scripts/sync_template.py                 # files shared by every task
```

Add a task name to either checker to run just that one. Without `--worktree` the fork checker
reads the committed branches rather than the working files.
