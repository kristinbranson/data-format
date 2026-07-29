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
#   --queue NAME     LSF GPU queue (default: gpu_l4_large). Slots come from the
#                    queue's slots-per-GPU ratio; asking for more than the ratio
#                    leaves the job PEND forever.
#   --wall HH:MM     Wall clock (default: 8:00). A 348 GB load plus two LLM judges
#                    is well under that, but a kill loses the run entirely.
#   --dry-run, -n    Print the bsub commands, submit nothing.
#
# Any other flag is forwarded to rerun_verifier.sh (--judges-only, --no-gpu,
# --claude-judge-only, ...). Options and trial dirs may be given in any order.
#
# Example:
#   ./submit_rerun_verifier.sh harbor-jobs-new/mouseland/terminus-gpt/*_trial1
#   ./submit_rerun_verifier.sh --queue gpu_t4 --judges-only <trial_dir>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Slots per GPU for each queue, mirroring submit_harbor_cluster.py's QUEUE_SPECS.
# Not interchangeable: gpu_l4_large hosts carry 64 slots and gpu_t4 hosts 48, so a
# 64-slot request on gpu_t4 can never be satisfied and the job sits PEND.
declare -A QUEUE_SLOTS=(
    [gpu_l4_large]=64 [gpu_t4]=48 [gpu_l4]=8 [gpu_l4_16]=16
    [gpu_a100]=12 [gpu_h100]=12 [gpu_h200]=12
)
QUEUE="gpu_l4_large"
WALL="8:00"
DRY_RUN=false
CONDA_ENV="eval-data-format-podman"
LOG_DIR="/groups/branson/home/bransonk/cluster_logs/harbor"
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
        --wall)       WALL="$2"; shift 2 ;;
        --dry-run|-n) DRY_RUN=true; shift ;;
        -*)           PASSTHROUGH+=("$1"); shift ;;
        *)            TRIALS+=("$1"); shift ;;
    esac
done
[ ${#TRIALS[@]} -gt 0 ] || { echo "ERROR: no trial directories given." >&2; exit 1; }

SLOTS="${QUEUE_SLOTS[$QUEUE]:-}"
[ -n "$SLOTS" ] || {
    echo "ERROR: unknown queue '$QUEUE'. Known: ${!QUEUE_SLOTS[*]}" >&2
    exit 1
}

mkdir -p "$LOG_DIR"
echo "queue $QUEUE ($SLOTS slots, 1 GPU), wall $WALL"
[ ${#PASSTHROUGH[@]} -gt 0 ] && echo "passthrough: ${PASSTHROUGH[*]}"

for trial in "${TRIALS[@]}"; do
    [ -d "$trial" ] || { echo "  SKIP (not a directory): $trial"; continue; }
    # Absolute: rerun_verifier.sh mounts this path into the container, and podman
    # treats a relative bind source as a NAMED VOLUME rather than a bind mount.
    trial_abs="$(cd "$trial" && pwd)"
    # Name from the trial's own path: <task>/<agent>/<timestamp>_trialN
    task="$(basename "$(dirname "$(dirname "$trial_abs")")")"
    agent="$(basename "$(dirname "$trial_abs")")"
    stamp="$(basename "$trial_abs")"
    job_name="rv_${task}_${agent}_${stamp##*_}"

    # USE_PODMAN is what podman_env.sh keys on; conda must be active before it runs
    # because it calls podman. The trap podman_env.sh installs reaps the catatonit
    # pause process -- without it LSF keeps the job RUN until the wall clock even
    # after the work is done, holding a whole node.
    inner="source \$HOME/miniforge3/etc/profile.d/conda.sh \
&& conda activate ${CONDA_ENV} \
&& export USE_PODMAN=true \
&& source ${SCRIPT_DIR}/podman_env.sh \
&& bash ${SCRIPT_DIR}/rerun_verifier.sh --podman ${PASSTHROUGH[*]+${PASSTHROUGH[*]} }${trial_abs}"

    bsub_cmd="bsub -n ${SLOTS} -gpu \"num=1\" -q ${QUEUE} -W ${WALL} \
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
