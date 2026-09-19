#!/bin/bash
#
# Submit verifier reruns to the Janelia cluster, one bsub job per trial.
#
# Why not just run rerun_verifier.sh locally: the verifier loads the agent's whole
# converted dataset into memory, twice over -- test_verify_data_format and
# test_data_stats each take the module-scoped `submitted_data_full` fixture, and
# `submitted_data_sample` stays resident alongside it. mouseland/terminus-gpt
# produced a 348 GB converted_data.pkl, which OOM-killed pytest on a 503 GB
# workstation (kernel `Killed`, no traceback, so no metrics.json was ever written).
# A gpu_l4_large node has 960 GB, where it fits with real headroom.
#
# Podman on a batch node needs a per-job runroot, cgroupfs and a pause process that
# gets reaped, so this sources the same podman_env.sh that run_harbor.sh uses rather
# than keeping a second copy of those workarounds.
#
# Usage:
#   ./submit_rerun_verifier.sh [OPTIONS] <trial_dir> [<trial_dir> ...]
#
# Options:
#   --queue NAME     LSF queue (default: gpu_l4_large). On a GPU queue, slots default to
#                    the queue's slots-per-GPU ratio, and asking for more than the ratio
#                    leaves the job PEND forever.
#
#                    A CPU queue (local, short) is the right choice when nothing in the run
#                    trains: --reuse-accuracy takes the decoder accuracy from the trial's
#                    existing metrics.json, and --judges-only skips the decoder test
#                    entirely, so both leave the GPU idle. Queueing for a GPU then costs
#                    twice over -- the card sits unused, and concurrency is capped by how
#                    many cards are free rather than by the work. gpu_l4_large has 18 GPUs
#                    with a ~50%-per-user cap, where `local` allows 5999 slots per user and
#                    `short` has no slot limit and priority scheduling under an hour.
#                    No -gpu is requested on a CPU queue, and slots are yours to choose.
#   --slots N        Override the slot count. Slots are how memory is requested -- a slot is
#                    15 GB, and LSF TERMINATES a job that exceeds slots x 15 GB -- so the CPU
#                    default of 16 is a memory figure, not a parallelism one: 240 GB, which
#                    covers the largest conversion in the tree (108 GB) with room for the
#                    load using more RAM than the file's size on disk. Nothing in a
#                    --reuse-accuracy run is CPU-parallel.
#                    For --decoder-stats, fewer is right: it trains 20 times on ONE GPU, so
#                    a whole node's slots would idle for hours; take a share instead. Fewer than the ratio is allowed, and is
#                    the right choice for --decoder-stats: that work is one GPU running
#                    20 trainings in a loop, so a whole node's slots idle for hours.
#                    Taking a share also lets several tasks run side by side rather
#                    than each waiting for an entire free node. The job's podman image
#                    store is per job (PODMAN_PRIVATE_STORAGE below), which is what
#                    makes sharing a node with other jobs safe.
#   --wall HH:MM     Wall clock (default: 8:00). A 348 GB load plus two LLM judges
#                    is well under that, but a kill loses the run entirely.
#   --name-suffix S  Append _S to the job name and log file. The name is derived from the
#                    trial path, so two submissions for the SAME trial otherwise collide:
#                    same -J, and same -o, so the second overwrites the first's log. That
#                    matters when submitting one trial twice deliberately, e.g. with and
#                    without --reuse-accuracy to compare them.
#   --dry-run, -n    Print the bsub commands, submit nothing.
#
# Any other flag is forwarded to rerun_verifier.sh (--judges-only, --no-gpu,
# --claude-judge-only, ...). Options and trial dirs may be given in any order.
#
# Example:
#   ./submit_rerun_verifier.sh harbor-jobs-new/mouseland/terminus-gpt/*_trial1
#   ./submit_rerun_verifier.sh --queue gpu_t4 --judges-only <trial_dir>

set -euo pipefail

# `pwd -P`, not plain `pwd`: plain pwd is logical and echoes back whatever symlinked
# path the caller happened to be standing in. Invoked from
# /home/<user>@hhmi.org/behavioranalysis/... -- a symlink to /groups/branson/... that
# exists only on the workstation -- every path baked into the bsub command pointed at
# a directory the compute node cannot see, and the job died in 1 s with
# "podman_env.sh: No such file or directory". -P resolves to the real path, which is
# the same on both.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"

# Slots per GPU for each queue, mirroring submit_harbor_cluster.py's QUEUE_SPECS.
# Not interchangeable: gpu_l4_large hosts carry 64 slots and gpu_t4 hosts 48, so a
# 64-slot request on gpu_t4 can never be satisfied and the job sits PEND.
declare -A QUEUE_SLOTS=(
    [gpu_l4_large]=64 [gpu_t4]=48 [gpu_l4]=8 [gpu_l4_16]=16
    [gpu_a100]=12 [gpu_h100]=12 [gpu_h200]=12
)
# CPU queues: no GPU to request, so no slots-per-GPU ratio applies either. `short` caps at
# one hour, which a cold image build plus two judge sessions can approach, so it is not the
# default. Runtime limits are LSF's, not ours: local 14 days, short 1 hour.
CPU_QUEUE_MAX_WALL=" short 1:00 "
declare -A CPU_QUEUE_DEFAULT_SLOTS=( [local]=16 [short]=16 )
QUEUE="gpu_l4_large"
WALL="8:00"
DRY_RUN=false
CONDA_ENV="eval-data-format-podman"
LOG_DIR="/groups/branson/home/bransonk/cluster_logs/harbor"
SLOTS_OVERRIDE=""
NAME_SUFFIX=""
PASSTHROUGH=()

# Options and trial dirs may be interleaved, so scan everything rather than only
# a leading run of flags -- an earlier version consumed only leading options, so a
# flag written after a trial dir was silently treated as another trial directory.
# Flags this script does not know are forwarded to rerun_verifier.sh, which
# rejects its own unknowns; that keeps `--judges-only` and `--no-gpu` working
# without a `--` separator to get wrong.
TRIALS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --queue)      QUEUE="$2"; shift 2 ;;
        --slots)      SLOTS_OVERRIDE="$2"; shift 2 ;;
        --wall)       WALL="$2"; shift 2 ;;
        --name-suffix) NAME_SUFFIX="$2"; shift 2 ;;
        --dry-run|-n) DRY_RUN=true; shift ;;
        -*)           PASSTHROUGH+=("$1"); shift ;;
        *)            TRIALS+=("$1"); shift ;;
    esac
done
[ ${#TRIALS[@]} -gt 0 ] || { echo "ERROR: no trial directories given." >&2; exit 1; }

GPU_BSUB='-gpu "num=1"'
if [ -n "${CPU_QUEUE_DEFAULT_SLOTS[$QUEUE]:-}" ]; then
    # CPU queue: no GPU request at all, and slots are a free choice rather than a ratio.
    GPU_BSUB=""
    SLOTS="${CPU_QUEUE_DEFAULT_SLOTS[$QUEUE]}"
    # The container asks podman for a GPU unless the run is one that does not need one.
    # On a CPU node that request fails, so refuse rather than submit jobs that all die.
    case " ${PASSTHROUGH[*]:-} " in
        *" --reuse-accuracy "*|*" --judges-only "*|*" --claude-judge-only "*|*" --codex-judge-only "*|*" --no-gpu "*) ;;
        *)
            echo "ERROR: queue '$QUEUE' has no GPUs, but this run would ask the container for" >&2
            echo "       one. Add --reuse-accuracy (reuses the recorded accuracy), a judge-only" >&2
            echo "       flag, or --no-gpu; or submit to a GPU queue." >&2
            exit 1 ;;
    esac
    if [ "$QUEUE" = short ] && [ "$WALL" != "${WALL%%:*}:00" -o "${WALL%%:*}" -gt 1 ] 2>/dev/null; then
        echo "WARNING: the short queue caps runtime at 1:00 and --wall is $WALL; LSF will reject it." >&2
    fi
else
    SLOTS="${QUEUE_SLOTS[$QUEUE]:-}"
    [ -n "$SLOTS" ] || {
        echo "ERROR: unknown queue '$QUEUE'. Known GPU queues: ${!QUEUE_SLOTS[*]};" >&2
        echo "       known CPU queues: ${!CPU_QUEUE_DEFAULT_SLOTS[*]}" >&2
        exit 1
    }
fi
# Fewer slots than the queue's ratio is allowed and is usually right here: the work is
# compute_decoder_stats.py training the decoder 20 times in a plain loop on ONE GPU, so
# a whole node's slots would sit idle for hours. Taking a share also lets several of
# these run side by side instead of each waiting for an entire free node.
SLOTS="${SLOTS_OVERRIDE:-$SLOTS}"

mkdir -p "$LOG_DIR"
echo "queue $QUEUE ($SLOTS slots, $([ -n "$GPU_BSUB" ] && echo '1 GPU' || echo 'no GPU')), wall $WALL"
[ ${#PASSTHROUGH[@]} -gt 0 ] && echo "passthrough: ${PASSTHROUGH[*]}"

for trial in "${TRIALS[@]}"; do
    [ -d "$trial" ] || { echo "  SKIP (not a directory): $trial"; continue; }
    # Absolute: rerun_verifier.sh mounts this path into the container, and podman
    # treats a relative bind source as a NAMED VOLUME rather than a bind mount.
    # -P for the same reason as SCRIPT_DIR above: the node has to be able to see it.
    trial_abs="$(cd "$trial" && pwd -P)"
    # Name from the trial's own path: <task>/<agent>/<timestamp>_trialN
    task="$(basename "$(dirname "$(dirname "$trial_abs")")")"
    agent="$(basename "$(dirname "$trial_abs")")"
    stamp="$(basename "$trial_abs")"
    job_name="rv_${task}_${agent}_${stamp##*_}${NAME_SUFFIX:+_$NAME_SUFFIX}"

    # USE_PODMAN is what podman_env.sh keys on; conda must be active before it runs
    # because it calls podman. The trap podman_env.sh installs reaps the catatonit
    # pause process -- without it LSF keeps the job RUN until the wall clock even
    # after the work is done, holding a whole node.
    # PODMAN_PRIVATE_STORAGE, because --slots lets several of these land on one node:
    # a shared image store is only safe for one job at a time, and podman_env.sh's
    # repair path refuses to reset a shared one rather than break a sibling's run.
    # --apikeys, always: the OAuth route reads $HOME/.claude/.credentials.json, and
    # $HOME on a compute node is /groups/branson/home/<user>, not the workstation
    # home where that file lives. Without it the failure is silent -- empty token,
    # judges run unauthenticated, empty judge/ dirs and "[Errno 2] ...
    # llm_judge_eval.json" beside a reward that looks complete. --env is absolute so
    # the node reads the same file regardless of cwd.
    inner="source \$HOME/miniforge3/etc/profile.d/conda.sh \
&& conda activate ${CONDA_ENV} \
&& export USE_PODMAN=true PODMAN_PRIVATE_STORAGE=true \
&& source ${SCRIPT_DIR}/podman_env.sh \
&& bash ${SCRIPT_DIR}/rerun_verifier.sh --podman --env ${REPO_DIR}/.env ${PASSTHROUGH[*]+${PASSTHROUGH[*]} }${trial_abs}"

    bsub_cmd="bsub -n ${SLOTS} ${GPU_BSUB} -q ${QUEUE} -W ${WALL} \
-J ${job_name} -o ${LOG_DIR}/${job_name}.log \"${inner}\""

    if [ "$DRY_RUN" = true ]; then
        echo "  $bsub_cmd"
        continue
    fi
    if command -v bsub >/dev/null 2>&1; then
        eval "$bsub_cmd"
    else
        # From the workstation: bsub lives on the submit host. One argument, or
        # ssh joins the flags with spaces and bsub reads a jobspec from stdin.
        ssh -o BatchMode=yes login1 "$bsub_cmd" < /dev/null
    fi
done
