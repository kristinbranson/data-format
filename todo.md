# What is left to do

State as of 2026-09-18. Everything described in `harbor-tasks/changes_since_preprint.md` is
committed; `ffb68a5` is pushed, `e16347c` is not. The preprint's version is tagged `v2`.

**Only mouseland's reference statistics are still missing.** Seven of the eight tasks are
done and committed. Until mouseland's land, its committed numbers describe the old reference
solution, which padded every trial to 32 bins.

---

## 1. Finish mouseland's reference statistics

Running on the cluster, both against the same conversion.

| job | what it produces |
|---|---|
| `refstat_mouseland` | the oracle: `converted_data.pkl` and a complete `stats_full.json`, including the single-split fields `validation_balanced_accuracy`, `rng_state`, `chance_majority`, `chance_uniform` and `train_balanced_accuracy` |
| `rep_mouseland[1-20]` | one replicate each, as `replicate_<N>.json` in `/nrs/branson/bransonk/mouseland-refstats/decoder_replicates/` |

The replicates train on a copy of an earlier conversion at
`/nrs/branson/bransonk/mouseland-refstats/converted_data.pkl`, so they could start before the
oracle finished. `convert_data.py` has not changed since that conversion was made, so the
oracle's own output should match it byte for byte; check that before merging, since the
merge takes the oracle's `stats_full.json` and the replicates' accuracies and they have to
describe the same data.

One job per replicate rather than one job for all of them: the replicates are independent,
replicate N drawing its split from a seed fixed by N, so serialising them multiplies the
wall clock by twenty and makes any crash cost the whole run.

When both finish:

1. Compare the oracle's `converted_data.pkl` with the copied one.
2. `submit_decoder_replicates.sh --merge --task mouseland --stats <oracle>/verifier/snapshot/stats_full.json --out-dir /nrs/branson/bransonk/mouseland-refstats/decoder_replicates`
3. Copy the result into `harbor-tasks/mouseland/tests/` **and** `mouseland_minimal/tests/` --
   `check_task_variants.py` requires those two to be identical.
4. Fill in the before/after numbers in `changes_since_preprint.md` at the two places that say
   they are pending.
5. `python harbor-scripts/check_output_classes.py`, which confirms each prompt's list of
   output classes still matches what the reference produces.

**mouseland's trials must be re-scored with the decoder retrained, not with
`rerun_verifier.sh --reuse-accuracy`.** Reuse takes an agent's accuracy from the run
that recorded it, which is right where the reference statistics predate the current
decoder. mouseland's will be produced by the current one, so reusing would put the two
sides of the `mean - ACCURACY_NSTD * sd` comparison on different decoder versions.

## 2. Fixed, awaiting a commit

- **`decoder.py` crashed on a session with no trials**, and on a one-trial session, which
  `train_validate_decoder` turned into an empty training session by giving it
  `n_train = min(max(1, int(1 * frac_train)), 0) = 0`. A session now needs two trials to be
  split at all, and the places that read a session's projection tolerate its absence.
- **`run_unsupervised_judges.sh` could not see zhang2025's dataset.** Its `grep ':/app/data'`
  found nothing for a task mounting at `/mnt/dataset`, and under `set -o pipefail` that ended
  the script before its error message could run. It now detects either target, as
  `rerun_verifier.sh` does.
- **sosa2024's teleport comment** named the animals outside the paper's table as m3 and m7.
  On the full dataset m4 is outside it as well.

## 3. Podman image builds on the cluster

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

## 4. Python embedded in shell scripts

`harbor-scripts/` holds 32 standalone Python helpers and two shell scripts that embed
Python in a heredoc instead: `rerun_verifier.sh` (33 lines, the `--reuse-accuracy`
check that the run really did reuse the recorded accuracy) and
`merge_rerun_verifier.sh` (14 lines). Both would read better as scripts beside the
others, invoked the way `check_data_mounts.py` is.

What the heredoc form costs:

- A traceback names `File "<stdin>", line 12`, which does not locate anything in a
  cluster log -- and this particular code exists to fail loudly.
- It cannot be unit tested. Its interesting cases are a missing accuracy, an absent
  `validation_balanced_accuracy_reused`, and a per-variable disagreement, all of which
  need the whole verifier to reach. `test_write_reward_file.py` is the precedent for
  testing a helper directly.
- Editors and linters see an opaque string: no highlighting, no `ruff`.
- `bash -n` passes a file whose embedded Python is broken, since it only checks the
  shell around it.

Not done yet because a sweep is running: every `bsub` job reads `rerun_verifier.sh`
from `/groups` when it starts, so editing it mid-flight changes what later jobs
execute. Committing the file does not affect them; editing it does. The same applies to
the item below.

### `CPU_QUEUE_MAX_WALL` is never read

`submit_rerun_verifier.sh` defines

```sh
CPU_QUEUE_MAX_WALL=" short 1:00 "
```

and nothing reads it: the name appears once in the file, on that line.
`CPU_QUEUE_DEFAULT_SLOTS` beside it is read four times, so the omission is this one
variable rather than a section that was never wired up.

The check it was meant to serve does exist, written inline with a different expression:
`--queue short --wall 8:00` warns that LSF caps that queue at an hour. So this is dead
code rather than a missing guard, and the fix is to delete the constant or make the
check read it -- not to add a check.

Either implement the check or delete the variable. The comment above it is worth keeping
either way: it records that `short` is not the default because a cold image build plus
two judge sessions can approach an hour, and that the limits are LSF's (local 14 days,
short 1 hour).

## 5. Redundant checkpointing in compute_decoder_stats.py

`replicate_accuracies` writes every finished replicate to a checkpoint beside its output
and resumes from it, so a run killed by a wall clock or a node failure does not repeat
hours of training. `--replicate N` then made each replicate its own job, which solves the
same problem better: a crash costs one replicate and the rest are already written, with
no file to keep consistent. The checkpoint now only earns its keep for someone running
all the replicates serially in one process. Worth deleting with that path, or keeping
deliberately if serial runs are expected.

## 6. Decisions waiting

- **Propagate the threaded conversion to the forks?** Deferred until mouseland shows it
  working at scale. `check_forks_match.py` reports `decoder.py` differing on all eight until
  then.
- **Push the fork commits?** Each `~/tb-science-*` clone has two unpushed commits on
  `neurodata-reuse-<name>`, and those branches have open pull requests.
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
