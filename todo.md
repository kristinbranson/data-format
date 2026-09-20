# What is left to do

State as of 2026-09-19. Everything described in `harbor-tasks/changes_since_preprint.md` is
committed and pushed, through `583fe2a`. The preprint's version is tagged `v2`.

**All eight tasks now have reference statistics on the full data**, mouseland included, and
all 54 graded output variables carry a 20-replicate mean and standard deviation. What is left
is rerunning agents, not computing references.

**A 48-job sweep on the newest agents is running** -- every task's maximal prompt on
claude-code 2.1.278 with `claude-opus-5` and codex 0.155.1 with `gpt-5.6-sol`. See section 2
step 1 for what was submitted and what it does not record.

Uncommitted while that runs, and none of it should be committed piecemeal:

| what | where |
|---|---|
| the version bump | `harbor-scripts/config_20260919.json` and the 46 files `apply_versions.py` generates |
| judge pins recorded per trial | `tests/compute_reward.py` and `tests/test.sh`, template plus 23 task copies |
| the config in the collected path | `harbor-scripts/collect_cluster_results.py`, `evaluation/eval/trial_metrics.py` |
| display names for the new arms | `evaluation/eval/utils.py` |
| this file | |

Unpushed commits: `01ba5d7` here, and `fd10a3a` in `codepacks/harbor-kai` (the reward
aggregation fix, without which every job of this sweep would exit 1).

---

## 1. Rerun the agents on four tasks

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

**Partly covered by the sweep launched 2026-09-19.** That sweep runs the maximal prompt of
all eight tasks, so the maximal variant of these four is already in flight and nothing here
needs resubmitting for it. What remains is their `_minimal` variants, and `_datalimit` for
`map` and `sosa2024`:

    --tasks map_minimal map_datalimit hasnain2024_minimal majnik2025_minimal \
            sosa2024_minimal sosa2024_datalimit

**But decide first what they are compared against.** Those reruns would use the 2026-09-19
pins, so a trial differing from its predecessor differs in two ways at once -- the prompt
and the agent -- and neither can be credited. Reading a prompt fix as a prompt fix needs the
old pins, which `VERSIONS_FILE=harbor-scripts/config_20260728.json` still provides. Running
both is the only way to have it both ways, at twice the cost.

## 2. Run the maximal prompt on the newest agents

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

**Done 2026-09-19:** `harbor-scripts/config_20260919.json` holds these pins and
`apply_versions.py` has written all 48 generated files -- each task's
`environment/Dockerfile` and `tests/versions.json`. Do not edit those by hand; edit the
config and rerun the generator.

Two trials of `majnik2025_minimal`, one per CLI arm, ran on `gpu_l4_large` on 2026-09-19 to
prove the new versions build and judge before the rest follow. **The versions work.** Both
images built with the new CLIs, both agents ran on the new models, both judges graded, and
`result.json` records `exception_info: None` for each.

| arm | reward | outcome_all | process | note |
|---|---|---|---|---|
| codex 0.155.1 / `gpt-5.6-sol` | 0.989 | 1.0 | 0.968 | every outcome category 1.0 |
| claude-code 2.1.278 / `claude-opus-5` | 0.609 | 0.0 | 0.916 | 10 of 11 categories 1.0; failed `outcome_decoder_accuracy_matches` |

The claude arm's failure is an agent result, not an infrastructure one, so it stands as
measured.

**The sweep is running, submitted 2026-09-19.** 48 jobs, 8 tasks x 2 CLI arms x 3 trials,
maximal prompt only, `gpu_l4_large` at 64 slots and one L4 each with a 24h wall:

    python harbor-scripts/submit_harbor_cluster.py --maximal --agents claude codex

`--agents claude codex` is not optional. `submit_harbor_cluster.py` takes its default arms
from the newest config's `tools` keys, and that file names four: the two terminus arms would
be submitted as well and cannot run until step 2's re-port. Better still, give the config a
way to mark an arm as not yet runnable, so the default is right rather than remembered.

Nothing is skipped on a resubmit. The submitter has no check for work already done --
`--start N` counts positions and `--jobs <names>` takes explicit names, and the only
`.exists()` test in it is about data mounts. Re-running the whole command after a partial
failure would rerun every job and leave a second `<timestamp>_trial1` beside the first, so a
partial rerun has to name its jobs. The failure report prints them in exactly the form
`--jobs` accepts.

Expect an uneven drain. `majnik2025_minimal` finished in 21 minutes; the archive's median is
about 1.25h of agent plus verifier with mouseland at 6h, and the two judges add roughly an
hour on top. Each job rebuilds its image from scratch, because `PODMAN_PRIVATE_STORAGE`
gives it an empty store, so a few minutes of every job is the build.

**Finish the `_api` variant on the analysis side.** Two of the three places are done:
`submit_harbor_cluster.py` has an `--api` scope, and `trial_metrics.py` strips the suffix so
`sosa2024_api` reads as dataset `sosa2024`, condition `api`, rather than as a ninth dataset.
Verified on the existing archive: all 146 trials still identify unchanged.

What is left is `evaluation/eval/utils.py`:

- `PROMPT_LABEL` is `{"minimal", "full", "datalimit"}` and has no `api` entry.
  `lesion_analysis.py` indexes it directly at lines 718 and 1235, so an api arm reaching
  either raises `KeyError` rather than being skipped. Nothing reaches them yet, because both
  iterate `ARM_COLUMNS` and no api arm is listed, but that is the only thing preventing it.
- `ARM_COLUMNS` and `AGENT_KEYS` need api arms once there is something to plot, and the
  display name has to say what the condition IS -- "api" means the agent was required to
  read the files through the format's own library rather than parsing them, which no reader
  will infer from the word.
- `DATALIMIT_SAME_AS_MINIMAL` has no api counterpart and probably needs none: an `_api` task
  is a real separate run, not an alias for another arm's trials.

Deliberately deferred rather than guessed: the arms cannot be named before there are results
to name. Six `sosa2024_api` trials were submitted on 2026-09-19 at 21:58, so there will be.

A naming wart to decide at the same time: the field is called `prompt` but now carries
`datalimit` and `api`, neither of which is a property of the prompt. It reads as the
condition. Renaming it touches every consumer, so it is recorded rather than done.

**Rerun the codex judge where the provider refused.** On `hb_map_codex_t1` the codex judge
read the task, both implementations and the reference decisions, then the turn failed with

    {"type":"error","message":"Selected model is at capacity. Please try a different model."}

so no `llm_judge_eval.json` was written. That is gpt-5.6-sol being unavailable for a moment,
not the agent's doing and not reproducible, and it is the case `write_reward_file.py` was
built for: `process` becomes the mean over the judge that did answer rather than counting the
failure as zero. The trial still records which judge was meant to run, because
`compute_reward.py` writes the model and harness before its early return.

It still costs a judge. Those trials' `process` scores rest on one rater where every other
trial has two, so they should be re-judged before the scores are pooled.

Find them by `llm_judge_<name>_error` being non-empty in `metrics.json`;
`harbor-scripts/sweep_status.py` flags them as a problem on the page, in red. Fix them with

    harbor-scripts/submit_rerun_verifier.sh --queue gpu_t4 --judges-only <trial dir>

which re-runs only the judges and takes the pytest outcome from the reward file already in
place, so no decoder is retrained. Do it once when the sweeps finish rather than per trial:
the failure is transient, so more of them are likely, and one pass catches the lot.

**Effort is an unrecorded variable.** Claude Code runs at whatever its default is: the
invocation is `claude --verbose --output-format=stream-json --permission-mode=bypassPermissions
--print`, with no effort flag, and its own init event reports `model` and `fast_mode_state`
but nothing about effort or a thinking budget. Nothing sets one -- harbor's claude-code agent
takes `max_thinking_tokens` but this repository never passes it, `MAX_THINKING_TOKENS` is
unset, and `config_*.json` has no effort field. So no trial records what effort produced it,
which is the gap the judge model had until the pins were recorded in `metrics.json`.
Plumbing it through `config_*.json` is the obvious fix, and it belongs to a NEW dated config
rather than this one: changing effort partway makes trials incomparable, and these 48 are
already running.

#### The cluster's harbor could not aggregate our reward file -- FIXED 2026-09-19

Kept here because it is why `codepacks/harbor-kai` carries an unpushed commit, and because
the same shape returns whenever that harbor is replaced.

Both smoke-test jobs exited 1 after doing all their work. Harbor's cross-trial aggregation
raised

    ValueError: Expected exactly one key in reward dictionary, got 15

`tests/write_reward_file.py` writes `reward` plus the three components and the eleven
outcome categories -- fifteen keys, which is the point of it. The cluster's harbor is 0.1.45
(`eval-data-format-podman`, editable from `codepacks/harbor-kai`), whose
`src/harbor/metrics/{mean,max,min,sum}.py` each raised unless the dict had exactly one key.
Nothing about the version bump caused it; any cluster sweep would have hit it, and the
reason none had is that no full harbor sweep had run since `01da698` made the reward file
multi-key. `rerun_verifier.sh` runs its container directly and never reaches that code,
which is why the 145 re-verifications did not see it.

**The trial output is intact.** The crash happens after the work: `result.json`,
`verifier/reward.json`, `metrics.json`, `ctrf.json`, `verifier/judge/{claude,codex}` and the
snapshot are all written. Only harbor's summary across trials is lost, and the analysis
computes its own.

Harbor 0.21.0 fixed this: `metrics/base.py` gained `aggregate_reward_dicts`, which
aggregates each key separately and falls back to the old behaviour when there is one key or
none. The three metric classes are four lines each on top of it.

**Fixed 2026-09-19 by backporting `aggregate_reward_dicts`** into
`codepacks/harbor-kai/src/harbor/metrics/` -- the checkout the cluster imports, confirmed
through the env's `harbor.pth`. `base.py` gains the function and two type aliases and is
otherwise untouched; `mean.py`, `max.py`, `min.py` and `sum.py` each become a single call to
it. Five files, +70/-68. The env is an editable install, so no reinstall was needed.

`min.py` carried the same restriction and never appeared in the traceback, which named only
`mean`, `max` and `sum`. Fixing the three would have left it.

The function is kept byte-identical to upstream, docstring-less like upstream, so a rebase
onto a newer harbor finds nothing to merge there; the explanation sits in a comment above it.

Verified against the two finished trials, through harbor's own models rather than in
isolation: `update_trial` on both real `TrialResult`s gives `n_trials=2, n_errors=0`;
`reward_stats` already tracked all fifteen reward names, so that half was never broken;
`metric.compute` -- the line that raised -- returns four metrics of fifteen keys with the
right values; and `JobResult.model_dump_json` round-trips. Single-key rewards return exactly
what they did before, for all four metrics, which is why no existing single-reward task
changes.

Confirmed on a live job the same day: `154373750` re-ran `majnik2025_minimal` on codex and
exited 0, with no ValueError after its own start line in the shared log, and
`raw/<stamp>/result.json` written for the first time -- one eval key carrying all fifteen,
mean reward 0.995. The 48-job sweep depends on this; without it every job would exit 1.

The alternative, had the fix been larger, was to accept exit 1 and use the per-trial data,
which is complete either way -- at the cost of every job looking failed in `bjobs`, and of
checking `collect_cluster_results.py` and `check_trial_health.py` against a non-zero exit.

This also bears on step 2: the harbor version gap is not only terminus's problem, it broke
harbor's own reward handling for every arm. Upstream v0.23.0 carries
`aggregate_reward_dicts` itself, so this backport retires when the re-port lands.

**A bare sweep now launches terminus by accident.** `submit_harbor_cluster.py` takes its
default arms from the newest config's `tools` keys, and that file names four:
`claude`, `codex`, `terminus-gpt`, `terminus-opus`. The terminus arms cannot run until the
podman re-port in step 2, so every step 1 submission has to pass `--agents claude codex`
explicitly. Better still, give the config a way to mark an arm as not yet runnable, so the
default is right rather than remembered.

Nothing else blocks this step: both are installed CLIs, pinned per task, and the harbor that
runs them does not have to change.

**Watch for:** a bumped CLI that renamed or dropped a flag `tests/test.sh` passes to a
judge. A judge that fails to start records a missing process score rather than an error, so
it shows up as an absent number rather than a crash. The forks verified
`claude-opus-5` and `gpt-5.6-sol` against these flag sets at claude-code 2.1.226 and codex
0.147.0 (fork commit `fadfa9d`); this config is newer than both.

### Step 2: terminus

**The premise this step rested on is gone, as of 2026-09-19.** It read: upstream has not added
podman, so the fork is still needed rather than retirable. That was measured against harbor
0.21.0. Upstream **v0.23.0 has podman natively**, and implements it better than the fork does, so
this is no longer a rebase of the fork's 43 commits -- it is a re-port of a much smaller
remainder onto upstream.

**The versions, verified rather than remembered.** A fork branch's `pyproject.toml` version is
upstream's version at its base, not a version of the podman work, so "the cluster runs 0.1.45"
means "the cluster runs podman work sitting on a March upstream".

| | harbor | source | base |
|---|---|---|---|
| cluster (`eval-data-format-podman`) | 0.1.45 | editable, `codepacks/harbor-kai` on `kristin-podman` @ `fd10a3a` | `6f280307`, 2026-03-05 |
| local docker (`eval-data-format`) | 0.1.44 | site-packages, no repo | |
| `tb-science` | 0.21.0 | editable, `codepacks/harbor` on `main` @ `a27e9c2a` | |
| **re-port target** | **0.23.0** | **tag `v0.23.0` = `1e5c5c6d`, 2026-09-11** | |
| upstream `main` | 0.23.0 | `71c77fdd` | |

Both the tag and `main` report 0.23.0, so the version string cannot tell them apart. **Pin the
tag.** `main` is 80 commits and 8 days past it, touching exactly the files a re-port has to
resolve -- `docker.py` +70, `claude_code.py` +72/-14, `codex.py` +57/-12, `cli/trials.py` +162/-2
-- and moving about ten commits a day. Conflicts are 36 hunks against the tag against 37 for
`main`, and `terminus_2.py` differs between them by one line, so pinning costs nothing this step
is for.

Both conda envs -- the workstation's, and the cluster's own install under
`/groups/branson/home/bransonk/miniforge3` -- point `harbor.pth` at the one shared tree
`codepacks/harbor-kai/src`. A single edit there changes what every compute node runs, with no
reinstall in between. **Do the work in `/groups/branson/home/bransonk/codepacks/harbor-rebase`**, a
clone made for it, with `framework` (harbor-framework/harbor), `kai` and `origin` as remotes.

#### What upstream v0.23.0 provides

`-e podman` selects `PodmanEnvironment(DockerEnvironment)` in `src/harbor/environments/podman.py`,
registered in `environments/factory.py` under `EnvironmentType.PODMAN`. The dialect differences
live on a `ContainerRuntime` dataclass in `environments/docker/runtime.py`, whose module docstring
is explicit: `-e docker` and `-e podman` only swap engine argv, compose argv and a few capability
flags, and `start()`/`stop()` are not to be forked. Every workaround the fork threads through
`docker.py` as `if self._use_podman:` has a counterpart:

| fork's workaround | upstream mechanism |
|---|---|
| `up -d` in place of `up --detach --wait` | `supports_compose_wait=False`, read by `runtime.up_args` |
| `_run_podman_cp_command`, podman-compose having no `cp` | `supports_compose_cp` |
| drop `--project-directory` for podman-compose | `supports_compose_project_directory` |
| skip `--rmi all`, which killed concurrent trials | `stop()` uses `--rmi local` |
| hardcoded `podman-compose` | `resolve_podman_runtime()` picks `podman compose`, else `podman-compose --in-pod=false` |
| absent | SELinux `:z` relabel, on Harbor's own log binds only |
| absent | rootless detection via `{{.Host.Security.Rootless}}` |
| absent | egress-control sidecar image built through the podman engine |
| absent | preflight probes `podman compose ls`, since `podman info` passes without the API socket |

So `docker.py` -- 16 of the 36 conflict hunks, and the reason this looked hard -- is mostly not
ported but deleted. The fork's 568-line `docker.py` becomes upstream's 1403-line one plus
`-e podman`.

#### What is genuinely fork-only and has to be carried

1. **GPU pooling.** A class-level `asyncio.Queue` of `gpu_ids`, one GPU handed to each trial and
   returned on stop. The one substantial piece; upstream has no equivalent.
2. **The device compose override** -- `nvidia.com/gpu=<n>` written to a temporary compose file and
   appended to `_docker_compose_paths`. Paired with (1).
3. **`shm_mb`** in `[environment]` of `task.toml`, reaching the container as `shm_size`. Upstream
   now writes resources through `_write_resources_compose_file`, which is where this belongs.
4. **Codex `--profile` and `--oss` flags, and `CODEX_CONFIGS`**, which uploads named config files
   into `$CODEX_HOME=/logs/agent` at run time because that path is a runtime bind mount. Kai's
   `3446caa0`.
5. **Agent output file permissions, and taking the codex API key from the environment** --
   `44e7d7fc`; and the `trajectory.json` fix `83da9e87`, which needs re-checking first, upstream
   having just added `trial/sync_trajectory.py`.
6. **`hpc/`** -- `harbor-lsf-wrapper.sh`, `check-progress.sh` and their README. Standalone scripts,
   nothing to conflict with.

**The seam for (1) and (2) is clean.** Upstream's `start()` opens with `_write_mounts_compose_file`,
`_write_resources_compose_file` and `_write_env_compose_file`, and `stop()` closes with the
matching `_cleanup_*` calls inside a `finally:`. A device override is a fourth pair in those two
lists, and the GPU is acquired beside the first and released beside the last -- rather than patched
into the middle of `start()` and `stop()` as the fork does now.

#### What drops entirely

- All the `use_podman` threading through `docker.py`, replaced by `-e podman`.
- `metrics/{base,max,mean,min,sum}.py`. Upstream has `aggregate_reward_dicts`, which is what the
  backport recorded above took from 0.21.0, so that backport retires when this lands.
- `trial/reverify.py`, its `--interactive`, and Kai's `--keep-eval`. Upstream has
  `harbor trials regrade`, which takes `-e podman` and never modifies the source trial. **And
  nothing in this repo calls harbor's reverify** -- the only `reverify` in `harbor-scripts/` is the
  image name `hb__<task>-reverify`, and `rerun_verifier.sh` runs its container directly.
- Kai's podman-aware `preflight()` (`407d5a11`) and his `_run_full_command` env threading
  (`22b8f4ee`), both superseded upstream.

#### Branch topology, so the same ground is not covered twice

`podman_colm` (`7b6b088f`, identical in both forks) is the shared foundation, and **COLM is the
conference** -- the branch is that deadline's snapshot, not a person's. Three authors:
HairlessVillager wrote the original podman port, Goran Ceric wrote `hpc/`, Kai Horstmann wrote the
podman hardening. `kristin-podman` forked from it at `d7ac3b21` (2026-03-10), so it lacks
`podman_colm`'s last three commits and adds five of its own. `kai/podman` is `podman_colm` rebased
onto v0.3.0 plus six commits, and `kristinbranson/podman` is a strict ancestor of `kai/podman`, so
that branch can be ignored. Neither fork has moved since 2026-06-10.

#### This repo's migration surface: two lines

The fork never added a `--podman` CLI flag; it passes harbor's generic environment kwargs. So
`-e podman` replaces exactly:

| file | now | becomes |
|---|---|---|
| `harbor-scripts/run_harbor.sh:92` | `PODMAN_FLAG="--ek use_podman=true"` | `PODMAN_FLAG="-e podman"` |
| `harbor-scripts/generate_reference_stats.sh:65` | the same line | the same change |

`run_harbor.sh:97`'s `--ek gpu_ids=$GPUIDS` is unchanged, provided (1) is ported. Every other
`--podman` in `harbor-scripts/` -- `rerun_verifier.sh`, `rerun_judges.sh`,
`run_unsupervised_judges.sh`, the `submit_*.sh` -- drives `podman` directly without harbor and is
unaffected.

#### What the upgrade buys

terminus-2 is harbor's own code, so its version is the harbor version. Cluster 0.1.45 to v0.23.0 is
**+633/-287** across four files: `terminus_2.py` 1939 to 2101 lines, `tmux_session.py` 697 to 876,
and small changes to the two parsers. (An earlier note here said 0.1.44 to 0.21.0 grew
`terminus_2.py` from 1831 to 1959 lines and *gained* `tmux_session.py` and `asciinema_handler.py`,
citing `agents/installed/terminus_2.py`. That path does not exist -- the package is
`agents/terminus_2/` -- and both files are already present in 0.1.44.)

#### Order of work

1. Build `podman-v0.23.0` in `codepacks/harbor-rebase` from the `v0.23.0` tag, adding the six items
   above. Nothing lands in `codepacks/harbor-kai` while cluster jobs are queued.
2. Check whether `83da9e87`'s `trajectory.json` failure still happens on v0.23.0 before porting it.
3. Switch the two script lines to `-e podman`, then run one `majnik2025_minimal` terminus trial.
4. Only then a sweep, and only then point a conda env at the new tree.

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

**Which judge graded a trial is now recorded, as of 2026-09-19.** `tests/test.sh` reads
`harness_version` from `/tests/versions.json` the way it already read `model`, and passes
both to `compute_reward.py`, which writes `llm_judge_<name>_model` and
`llm_judge_<name>_harness_version` into `metrics.json`. They are written before the
early return on an unreadable eval, so a judge that failed still records what was meant to
run, and they are `null` on a trial graded by a `test.sh` predating the flags.

It had to happen before this sweep, because a trial that did not record its judge cannot be
fixed afterwards: nothing else in a trial carries it. The Claude CLI happens to name its
model in its own transcript; the Codex CLI does not, so for half the judges it was
unrecoverable.

What is recorded is the pinned version rather than a runtime `--version` probe. The
Dockerfile installs exactly that pin -- `apply_versions.py` writes both files from one
config -- so the pin describes what graded the trial, and a probe would add failure modes to
the grading path for no extra truth.

**What a rerun measures.** Harness, model, judges and -- for the four tasks in section 1 --
the prompt all move at once, so it answers "how do current agents do on the current
benchmark" rather than isolating any one change.

## 3. Podman image builds on the cluster

Every cluster job rebuilds the task image, five to seven minutes on these tasks. That is
now deliberate; what follows replaces the argument this section used to make.

**The private store is the right default, and this section previously said the opposite.**
`podman_env.sh` puts the graphroot at `/scratch/$USER/podman-storage`, shared by whatever
runs on that node, unless `PODMAN_PRIVATE_STORAGE=true` moves it under the job's own
directory. This section used to argue the flag was waste on `gpu_l4_large`: one GPU per
node, jobs hold a GPU exclusively, so no two can share a host -- measured, eighteen
replicates went to eighteen distinct nodes -- and the flag therefore only discards a store
that would be warm for the next job.

That reasoning considered only CONCURRENT sharing. Jobs share a node SERIALLY, and that is
enough. On 2026-09-19 three hosts' shared stores went bad; `podman_env.sh` detected it
before any work, attempted repair, and refused to reset the store, correctly, because it
cannot prove no sibling is using a shared one. Each poisoned node then failed every job it
was given in under a second, freed itself immediately, and was handed the next pending job.
Three bad hosts destroyed 63 of the two sweeps' jobs that way -- a failure that accelerates,
because the faster a node fails the sooner it takes another job.

`submit_harbor_cluster.py` now sets `PODMAN_PRIVATE_STORAGE=true` on every job, and
`submit_decoder_replicates.sh` was right to hardcode it. A few minutes of image build per
job is cheap against losing a sweep.

Recovering a poisoned host: `podman unshare rm -rf /scratch/$USER/podman-storage` on that
node while nothing of yours is running there. A plain `rm -rf` fails -- rootless podman's
overlay directories are owned by subuid-mapped UIDs -- which `podman_env.sh` already
documents at its own reset path.

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

## 5. Decisions waiting

- **Push the fork commits?** Each `~/tb-science-*` clone now has three unpushed commits on
  `neurodata-reuse-<name>`, and those branches have open pull requests. The third carries the
  threaded conversion, the CPU fallback and the two session-handling fixes, which brings
  `decoder.py` and `train_decoder.py` back into step with this repository -- each fork keeps
  only its own harbor-canary line in `tests/train_decoder.py`.
- **Untracked files** deliberately left out of the commits: `harbor-tasks/sosa2024_api/`,
  `harbor-scripts/data_roots.sh`, `evaluation/decoder_variability/`, `figures/*` (regenerated
  from the statistics anyway), `evaluation/eval/lesion_analysis.ipynb`.
- **Does a re-collected July trial keep its bare name?** `collect_cluster_results.py` now
  appends the config it was given, so collecting with `--versions config_20260728.json` files
  trials under `claude-code-config_20260728`. The trials already in `harbor-jobs/` are bare
  `claude-code`, which is what `utils.AGENT_KEYS` maps to the 4.6/5.4 display names, and they
  parse unchanged -- all 146 of them. The two spellings only diverge if July trials are ever
  re-collected out of `harbor-cluster-jobs/`. Either add the four `-config_20260728` keys
  pointing at the same display names, or decide that already-collected trials are never
  collected again.
- **What the section 1 reruns are compared against**, recorded there: running them on the new
  pins moves the prompt and the agent at once.
- **Untracked and unclaimed.** `harbor-tasks/sosa2024_api/` and `harbor-scripts/data_roots.sh`
  are in neither session's work and predate both; `data_roots.sh` is referenced by nothing.
  Left out of every commit so far.
- **A loud failure for zhang2025's index loading.** If the session index is not found, the
  search returns nothing without raising. The index is present in both datasets, so it should
  not fire, but a check would fail at the point of the mistake. It would have to go into the
  terminal-bench-science copy too, to keep that one file shared.

## 6. Known gaps, not yet scheduled

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
