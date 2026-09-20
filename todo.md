# What is left to do

---

## 1. Rerun the old agents on four tasks

`map`, `hasnain2024`, `majnik2025` and `sosa2024`, **every variant** -- maximal, `_minimal`
and, where one exists, `_datalimit`. Their existing trials were run against a prompt that
no longer describes the task, so those trials measure a different question from the one
the benchmark now asks, and re-scoring them cannot fix it: the agent saw different
instructions.

The other four need no rerun. `lee2025`, `zhang2025`, `mouseland` and `allen2p` changed
only in typos and wording -- "positon", an unclosed backtick, "circle1, leaf2" for
"circle, leaf" -- none of which alters what the agent is asked to produce.

## 2. Run the maximal prompt on new terminus agents

terminus-2 is harbor's own code, so its version is the harbor version and there is nothing to
pin per task. Moving from 0.1.45 to 0.23.0 changes it by +633/-287 across four files
(`terminus_2.py` 1939 -> 2101 lines). The fork never touched those files, so what ran before
was plain upstream terminus of 2026-03-05.

**The terminus sweep is running**, submitted 2026-09-19: the eight maximal tasks on
`terminus-gpt` and `terminus-opus`, three trials each.

Open, none blocking:

- **Push `podman-v0.23.0`** to `kristinbranson/harbor`, or leave it local?
- **Offer the detection fix upstream?** `21e76a50` fixes a real harbor bug: `podman compose`
  delegating to podman-compose advertises `--detach` like Compose V2 does, so the resolver
  claimed an `ls` subcommand and a `--project-directory` flag podman-compose lacks, and
  preflight then blamed a missing API socket. If upstream takes it, our copy disappears.
- **`reverify` or `regrade`?** The fork's `harbor trials reverify` was not carried; upstream's
  `trials regrade` differs in that it never modifies the source trial. Nothing here calls
  either -- `rerun_verifier.sh` runs its container directly.
- **Upstream's upload path ignores `supports_compose_cp`** where the download path honours it,
  so every upload under podman-compose makes one doomed `cp` call before falling back to a tar
  stream. Harmless, noisy in logs, a candidate for the same PR.

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

Nothing further is needed to make it happen; `apply_versions.py` rewrites all 48 generated
files.

**What a rerun measures.** Harness, model, judges and -- for the four tasks in section 1 --
the prompt all move at once, so it answers "how do current agents do on the current
benchmark" rather than isolating any one change.

## 3. Podman image builds on the cluster

Every cluster job rebuilds the task image, five to seven minutes on these tasks, because
`PODMAN_PRIVATE_STORAGE=true` gives each job its own graphroot. That is deliberate: a shared
store outlives the job that filled it, and a job killed partway leaves it unusable.
`podman_env.sh` then refuses to reset a shared store -- correctly, since it cannot prove no
sibling is using it -- so a poisoned node fails every job it is handed in under a second,
frees itself, and takes the next. Three such hosts destroyed 63 jobs on 2026-09-19. A few
minutes of build per job is cheap against that.

**The GPU is named, not requested.** Every task's `environment/docker-compose.yaml` reserves
its card as `device_ids: ["${HARBOR_GPU_ID:-0}"]`, which `run_harbor.sh` fills from
`harbor-scripts/gpu_ids.py`. Do not put `count:` back: on a multi-GPU node it yields physical
index 0, a card the job does not own, and the decoder falls back to CPU while holding an idle
one. `gpu_ids.py`'s docstring has the reasoning. This is what makes the dense queues usable --
`gpu_l4` is 8 slots against `gpu_l4_large`'s 64, and 88 GPUs against 32.

Recovering a poisoned host: `podman unshare rm -rf /scratch/$USER/podman-storage` on that
node while nothing of yours is running there. A plain `rm -rf` fails -- rootless podman's
overlay directories are owned by subuid-mapped UIDs -- which `podman_env.sh` already
documents at its own reset path.

**A build that overruns is not cleaned up.** `harbor`'s environment start has a
`build_timeout_sec`, and `compose up -d` builds the image when the store is cold, so the
timeout covers the build. On expiry harbor cancels the await but does not kill the
process, leaving `podman build` running: `cleanup_podman_job` removes containers and the
pause process, and a build is neither, so it survives and LSF holds the job in RUN until
someone kills it. The timeout is now 1800 s, which makes the overrun unlikely rather than impossible. The cleanup could also kill processes whose root or cwd is under
`$PODMAN_JOB_DIR` before removing it -- scoped to the job's own directory, so a sibling
is never touched, and by pid rather than by name.

**Both go away with an additional image store.** Podman can read images from a read-only
store listed in `storage.conf` as `additionalimagestores`, layering a private writable
graphroot on top. Build each task's image once into a shared location, and jobs find it
present, never write to it, and cannot corrupt each other: no per-job build, no
corruption risk, and nothing for a timeout to interrupt.

## 4. Python embedded in shell scripts

`merge_rerun_verifier.sh` embeds 14 lines of Python in a heredoc; every other helper in
`harbor-scripts/` is a script of its own. It is the last one: `rerun_verifier.sh`'s
`--reuse-accuracy` check became `check_reuse_accuracy.py`.

A heredoc cannot be unit tested, is opaque to `ruff` and an editor, survives `bash -n` while
broken, and names `File "<stdin>", line 12` in a traceback, which locates nothing in a
cluster log.

## 5. Finish the `_api` variant

`sosa2024_api` has run: six trials, every one scoring 1.00 on `outcome_all` where plain
`sosa2024` managed 0.67 and 0.00. They are deliberately **not collected**, so that the whole
`_api` set is collected in one pass. `allen2p_api`, `map_api` and `zhang2025_api` exist but
are still being written.

Submitting them is `--api --agents claude codex`. The arms are not optional: the submitter
takes its default arms from the config's `tools` keys, which names four, so omitting them
turns 24 jobs into 48 and sends terminus work that cannot run yet.

Two of the three places that need to know about `_api` are done -- `submit_harbor_cluster.py`
has the scope, and `trial_metrics.py` strips the suffix so a trial reads as dataset
`sosa2024` in condition `api` rather than as a ninth dataset. What is left is
`evaluation/eval/utils.py`:

- **`PROMPT_LABEL` has no `api` entry, and that is a crash rather than a gap.**
  `lesion_analysis.py` indexes it directly at lines 718 and 1235, so the first api arm added
  to `ARM_COLUMNS` raises `KeyError`. Nothing reaches it today only because no api arm is
  listed there yet.
- `ARM_COLUMNS` and `AGENT_KEYS` need api arms once there are results to name them from, and
  the label has to say what the condition IS -- that the agent was required to read the files
  through the format's own library -- which no reader infers from "api".

A naming wart to settle at the same time: the field is called `prompt` but now carries
`datalimit` and `api`, neither of which is a property of the prompt. It reads as the
condition. Renaming touches every consumer.

## 6. Decisions waiting

- **Push the fork commits?** Each `~/tb-science-*` clone now has three unpushed commits on
  `neurodata-reuse-<name>`, and those branches have open pull requests. The third carries the
  threaded conversion, the CPU fallback and the two session-handling fixes, which brings
  `decoder.py` and `train_decoder.py` back into step with this repository -- each fork keeps
  only its own harbor-canary line in `tests/train_decoder.py`.
- **Does a re-collected July trial keep its bare name?** `collect_cluster_results.py` now
  appends the config it was given, so collecting with `--versions config_20260728.json` files
  trials under `claude-code-config_20260728`. The trials already in `harbor-jobs/` are bare
  `claude-code`, which is what `utils.AGENT_KEYS` maps to the 4.6/5.4 display names, and they
  parse unchanged -- all 146 of them. The two spellings only diverge if July trials are ever
  re-collected out of `harbor-cluster-jobs/`. Either add the four `-config_20260728` keys
  pointing at the same display names, or decide that already-collected trials are never
  collected again.
- **`harbor-scripts/data_roots.sh` is unclaimed** -- in neither session's work, referenced by
  nothing, left out of every commit.
- **A loud failure for zhang2025's index loading.** If the session index is not found, the
  search returns nothing without raising. The index is present in both datasets, so it should
  not fire, but a check would fail at the point of the mistake. It would have to go into the
  terminal-bench-science copy too, to keep that one file shared.

## 7. Known gaps, not yet scheduled

- **The forks are behind on grading code.** `check_forks_match.py --worktree` reports
  `tests/test_outputs.py`, `write_reward_file.py` and `train_decoder.py` as differing: the
  forks do not have the per-task `expected_files.json` or the required-files change, and some
  of it cannot be shared anyway, because the forks have no LLM judges.
- **Version pins are patched into each Dockerfile rather than read from a file.**
  `apply_versions.py` rewrites two `RUN` lines in all 24 `environment/Dockerfile` copies by
  regular expression. The forks solved this properly in `fadfa9d`: `tests/Dockerfile` does
  `COPY versions.json` and reads it at build time with `jq -er`, so one file decides what
  grades a run and a malformed pin fails the build rather than installing `null`. It does not
  transfer as written, because that needs the verifier in its own container: data-format
  grades in the agent's container -- there is no `tests/Dockerfile` at all -- and a Dockerfile
  cannot COPY from outside its own build context, which is `environment/`. Doing it here means
  generating `environment/versions.json` too, and the Dockerfile ends `WORKDIR /app` with
  `COPY . .`, so that file would land in `/app` and tell the agent which models judge it.
  Copying it to `/opt` early and deleting `/app/versions.json` as the last line works, and
  `jq` is already installed. Worth doing; not worth doing mid-sweep, and the delete step is
  the kind of thing that stops working quietly.
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
