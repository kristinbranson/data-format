#!/bin/bash
#
# Submit a task's decoder replicates to the Janelia cluster as an array, one job per
# replicate, then merge them into reference_stats_full.json.
#
# Why one job per replicate: the replicates are independent -- replicate N draws its
# split from a seed fixed by N -- so nothing forces them to run in sequence. Serially
# they take (replicate time) x --n-replicates, hours to days for a large task, and a
# crash at any point loses everything not yet written. As an array they take one
# replicate's time, and a lost job costs one replicate that can be resubmitted alone.
#
# This does not go through rerun_verifier.sh. That script grades a trial: it snapshots
# the agent's files, runs pytest, the judges and the reward. A replicate needs none of
# that -- one container, the converted data, and the task's decoder.
#
# Usage:
#   ./submit_decoder_replicates.sh [OPTIONS] --task <task> --data <pkl> --stats <json>
#   ./submit_decoder_replicates.sh --merge [OPTIONS] --task <task> --stats <json>
#
# Options:
#   --task NAME         Task whose decoder and image the replicates use. Required.
#   --data PATH         converted_data.pkl the replicates train on.
#   --stats PATH        The oracle's stats_full.json; carried into the merged output.
#   --out-dir DIR       Where replicate_<N>.json and the merged file go.
#                       Default: <data dir>/decoder_replicates.
#   --n-replicates N    How many, and the array's size. Default: the
#                       DEFAULT_N_REPLICATES compute_decoder_stats.py declares, which
#                       is the n the verifier's ACCURACY_NSTD is derived from.
#   --replicates SPEC   Submit only these, as an LSF index list, e.g. 3 or 5-8 or
#                       "2,7,9". For resubmitting the ones that failed.
#   --merge             Assemble finished replicates instead of submitting. Runs here,
#                       not on a node: it reads N small files and writes one.
#   --queue Q           Default gpu_l4_16: mouseland declares 240 GB, more than the
#                       120 GB that gpu_l4's 8 slots provide.
#   --slots N           Override the queue's slots per GPU.
#   --wall HH:MM        Per job, not for the whole array. Default 4:00.
#   --dry-run, -n       Print the bsub command, submit nothing.
set -euo pipefail

# Slots per GPU for each queue, mirroring submit_rerun_verifier.sh's table.
declare -A QUEUE_SLOTS=(
    [gpu_l4]=8 [gpu_l4_16]=16 [gpu_l4_large]=64
    [gpu_a100]=12 [gpu_h100]=12 [gpu_h200]=12 [gpu_t4]=48 [gpu_short]=8
)

TASK=""; DATA=""; STATS=""; OUT_DIR=""; N_REPLICATES=""; REPLICATES=""
QUEUE="gpu_l4_16"; WALL="4:00"; SLOTS_OVERRIDE=""; DRY_RUN=false; MERGE=false
CONDA_ENV="${CONDA_ENV:-eval-data-format}"

while [ $# -gt 0 ]; do
    case "$1" in
        --task)          TASK="$2"; shift 2 ;;
        --data)          DATA="$2"; shift 2 ;;
        --stats)         STATS="$2"; shift 2 ;;
        --out-dir)       OUT_DIR="$2"; shift 2 ;;
        --n-replicates)  N_REPLICATES="$2"; shift 2 ;;
        --replicates)    REPLICATES="$2"; shift 2 ;;
        --merge)         MERGE=true; shift ;;
        --queue)         QUEUE="$2"; shift 2 ;;
        --slots)         SLOTS_OVERRIDE="$2"; shift 2 ;;
        --wall)          WALL="$2"; shift 2 ;;
        --dry-run|-n)    DRY_RUN=true; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# -P throughout: every path below is baked into a command that runs on a compute node,
# where a symlink through the workstation's view of the filesystem does not resolve.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
LOG_DIR="/groups/branson/home/bransonk/cluster_logs/harbor"

[ -n "$TASK" ]  || { echo "ERROR: --task is required" >&2; exit 1; }
[ -n "$STATS" ] || { echo "ERROR: --stats is required" >&2; exit 1; }
TASK_DIR="$REPO_DIR/harbor-tasks/$TASK"
[ -d "$TASK_DIR" ] || { echo "ERROR: no task at $TASK_DIR" >&2; exit 1; }
STATS="$(cd "$(dirname "$STATS")" && pwd -P)/$(basename "$STATS")"

if [ "$MERGE" = false ]; then
    [ -n "$DATA" ] || { echo "ERROR: --data is required unless --merge" >&2; exit 1; }
    [ -f "$DATA" ] || { echo "ERROR: no data file at $DATA" >&2; exit 1; }
    DATA="$(cd "$(dirname "$DATA")" && pwd -P)/$(basename "$DATA")"
fi
OUT_DIR="${OUT_DIR:-$(dirname "${DATA:-$STATS}")/decoder_replicates}"
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd -P)"

# Empty unless --n-replicates is given, so the default lives in exactly one place:
# compute_decoder_stats.py's DEFAULT_N_REPLICATES.
N_FLAG="${N_REPLICATES:+--n-replicates $N_REPLICATES}"
N_SHOWN="${N_REPLICATES:-$(python3 -c "
import re; print(re.search(r'^DEFAULT_N_REPLICATES\s*=\s*(\d+)',
open('$SCRIPT_DIR/compute_decoder_stats.py').read(), re.M).group(1))")}"

if [ "$MERGE" = true ]; then
    echo "merging $N_SHOWN replicates from $OUT_DIR"
    python3 "$SCRIPT_DIR/compute_decoder_stats.py" \
        --decoder-dir "$TASK_DIR/tests" --stats-json "$STATS" \
        --out "$OUT_DIR/reference_stats_full.json" $N_FLAG --merge "$OUT_DIR"
    exit 0
fi

SLOTS="${SLOTS_OVERRIDE:-${QUEUE_SLOTS[$QUEUE]:-}}"
[ -n "$SLOTS" ] || { echo "ERROR: unknown queue '$QUEUE'. Known: ${!QUEUE_SLOTS[*]}" >&2; exit 1; }
ARRAY="${REPLICATES:-1-$N_SHOWN}"
JOB_NAME="rep_${TASK}[${ARRAY}]"
IMAGE="hb__${TASK}-replicates"

echo "task $TASK, replicates $ARRAY of $N_SHOWN"
echo "  queue $QUEUE ($SLOTS slots, 1 GPU), wall $WALL per job"
echo "  data  $DATA"
echo "  out   $OUT_DIR"

# \$LSB_JOBINDEX is escaped so the node expands it, not this shell: every array element
# runs the same string and picks its replicate out of the environment.
#
# The image is built inside each job. PODMAN_PRIVATE_STORAGE gives every job its own
# graphroot, which starts empty, so there is nothing to reuse between them. The node's
# shared store would avoid the rebuild, but it outlives the job that filled it: one
# killed partway through leaves it unusable, and podman_env.sh refuses to reset a shared
# store rather than break a sibling, so the damage persists for every later job on that
# host. The build is a few minutes and the jobs run in parallel, so it costs that once in
# wall clock rather than once per replicate.
# LSF assigns the job a GPU and names it in the environment. Several jobs share a node on
# some queues, so the index is not always 0: asking for nvidia.com/gpu=0 from a job
# allocated another card hands it a device it does not own, which under the default
# exclusive-process mode is unusable -- torch then reports no GPU and trains on the CPU,
# holding an idle card for the length of the run.
#
# CDI addresses the card by its physical index, which LSF leaves in
# CUDA_VISIBLE_DEVICES_ORIG; CUDA_VISIBLE_DEVICES itself is renumbered from the job's own
# point of view. Neither is set on every queue, so index 0 is the fallback -- right
# wherever a job has the node's only GPU, and the value the flag carried before it was
# resolved at all. A job that ends up without a usable card is not stranded: the decoder
# catches the out-of-memory and finishes on the CPU.
inner="source \$HOME/miniforge3/etc/profile.d/conda.sh \
&& conda activate ${CONDA_ENV} \
&& export USE_PODMAN=true PODMAN_PRIVATE_STORAGE=true \
&& source ${SCRIPT_DIR}/podman_env.sh \
&& podman build -t ${IMAGE} ${TASK_DIR}/environment \
&& podman run --rm --device nvidia.com/gpu=0 \
-v ${DATA}:/app/converted_data.pkl:ro \
-v ${STATS}:/app/stats_full.json:ro \
-v ${TASK_DIR}/tests:/tests:ro \
-v ${SCRIPT_DIR}/compute_decoder_stats.py:/opt/compute_decoder_stats.py:ro \
-v ${OUT_DIR}:/out \
${IMAGE} python3 /opt/compute_decoder_stats.py \
--decoder-dir /tests --stats-json /app/stats_full.json \
--out /out/replicate_\\\${LSB_JOBINDEX}.json ${N_FLAG} \
--replicate \\\${LSB_JOBINDEX} /app/converted_data.pkl"

bsub_cmd="bsub -n ${SLOTS} -gpu \"num=1\" -q ${QUEUE} -W ${WALL} \
-J \"${JOB_NAME}\" -o ${LOG_DIR}/rep_${TASK}_%I.log \"${inner}\""

if [ "$DRY_RUN" = true ]; then
    echo; echo "  $bsub_cmd"
    exit 0
fi
if command -v bsub >/dev/null 2>&1; then
    eval "$bsub_cmd"
else
    # From the workstation: bsub lives on the submit host. One argument, or ssh joins
    # the flags with spaces and bsub reads a jobspec from stdin instead.
    ssh -o BatchMode=yes login1 "$bsub_cmd" < /dev/null
fi

echo
echo "Track:  ssh login1 'bash -l -c \"bjobs -J rep_${TASK}\"'"
echo "Merge:  $0 --merge --task ${TASK} --stats ${STATS} --out-dir ${OUT_DIR}"
