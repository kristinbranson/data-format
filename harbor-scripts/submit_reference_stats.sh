#!/bin/bash
#
# Submit oracle reference-statistic runs to the Janelia cluster, one bsub job per task.
#
# This is step 1 of 2. It runs the task's reference solution on the real dataset and
# records the dataset statistics plus ONE split's decoder accuracy. Step 2 trains the
# decoder 20 more times, for the mean and standard deviation the verifier's accuracy
# threshold compares against:
#
#   harbor-scripts/submit_rerun_verifier.sh --queue gpu_l4 --decoder-stats <trial dir>
#
# Why the cluster rather than the workstation: the tasks are independent, so on the
# cluster they run side by side instead of one after another.
#
# Why podman for every task, not just zhang2025: the datasets live on /groups and /nrs,
# both NFS with sec=krb5. Docker runs the container as real root with no Kerberos ticket
# and is squashed to nobody, so reads succeed (the trees are world-readable) and the
# first write fails with EACCES. Rootless podman maps container root to the invoking
# user, whose ticket the host already holds.
#
# Why NOT a whole node, unlike submit_harbor_cluster.py: that script takes all 64 slots
# because an AGENT trial is unbounded work and podman does not enforce --cpus/--memory,
# so owning the node is the only real limit. A reference solution is known, bounded work
# -- see TASK_QUEUE below for the measurements -- so it gets one GPU's share of a shared
# node. Eleven 8-slot jobs also start together, where eleven whole-node requests would
# queue behind each other waiting for entire free nodes.
#
# Usage:
#   ./submit_reference_stats.sh [OPTIONS] <task> [<task> ...]
#   ./submit_reference_stats.sh [OPTIONS] --all
#
# Options:
#   --all            Submit all eleven tasks that need regenerating (ALL_TASKS below).
#   --queue NAME     Override the per-task queue. Slots default to the queue's
#                    slots-per-GPU ratio; asking for MORE than the ratio leaves the job
#                    PEND forever, because no host in the queue can satisfy it.
#   --slots N        Override the slot count. Fewer than the queue's ratio is allowed and
#                    is the right choice when the queue is picked for availability rather
#                    than for its RAM: a gpu_l4_16 host carries 16 slots per GPU against
#                    gpu_l4's 8, so taking the ratio there buys twice the CPU and twice
#                    the price for the same L4. These runs need 8.
#   --wall HH:MM     Override the per-task wall clock.
#   --exclude-host H Do not place the job on host H. Repeatable. Nothing is excluded by
#                    default. Use it when a node is broken in a way that kills the job
#                    immediately, since LSF will otherwise place the retry there too --
#                    e.g. a node where /scratch/$USER exists but is owned by root, which
#                    rootless podman cannot write to:
#                      mkdir: cannot create directory '/scratch/<user>/podman-<jobid>'
#                    Check with `ssh <host> ls -ld /scratch/$USER` before assuming a node
#                    is still bad; SCS can reset it.
#   --jobs-root DIR  Where trial output goes (default below). Each task gets its own
#                    subdirectory, so concurrent jobs cannot write into one another.
#   --check          Report what each task actually produced, and submit nothing. Use this
#                    rather than bjobs: `harbor run` exits 0 even when the trial inside it
#                    crashed, so LSF reports "Successfully completed" and bjobs says DONE
#                    for a job that converted nothing. The honest test is whether
#                    verifier/snapshot/stats_full.json exists, which is what this checks.
#                    For each finished task it prints the trial directory to hand to
#                    submit_rerun_verifier.sh --decoder-stats.
#   --dry-run, -n    Print the bsub commands, submit nothing.
#
# Examples:
#   ./submit_reference_stats.sh --dry-run majnik2025    # read the command first
#   ./submit_reference_stats.sh majnik2025              # the quickest task, as a smoke test
#   ./submit_reference_stats.sh --all
#   ./submit_reference_stats.sh --wall 12:00 mouseland  # if 8h turns out to be short

set -euo pipefail

# `pwd -P`, not plain `pwd`: this repository is reached through
# /home/<user>@hhmi.org/behavioranalysis/... on the workstation, a symlink that does not
# exist on a compute node. Every path baked into the bsub command has to be the real
# one, or the job dies in a second with "No such file or directory". Same reason as in
# submit_rerun_verifier.sh.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"

# Slots per GPU for each queue, mirroring submit_harbor_cluster.py's QUEUE_SPECS and
# submit_rerun_verifier.sh's table. NOT interchangeable: a gpu_l4 host carries 8 slots
# per GPU and a gpu_l4_large host 64, so a 16-slot request on gpu_l4 exceeds one GPU's
# share and the job sits PEND.
declare -A QUEUE_SLOTS=(
    [gpu_l4]=8 [gpu_l4_16]=16 [gpu_t4]=48 [gpu_l4_large]=64
    [gpu_a100]=12 [gpu_h100]=12 [gpu_h200]=12
    # Newer hardware, absent from the cluster documentation's queue table. The ratio
    # is hosts-times-slots divided by GPUs: rtx6000s is 16 hosts of 128 slots and 8
    # NVIDIA RTX PRO 6000 each, b300s 16 hosts of 96 slots. Confirm with
    #   bhosts -o "max" -noheader <group> ; bhosts -gpu <group>
    # before trusting either, since a wrong ratio leaves the job PEND forever.
    [gpu_rtx6000]=16 [gpu_b300]=12
)

# A queue being empty does not mean it has capacity, and a queue with a backlog is not
# necessarily slower to start in. `bqueues` reports three situations identically:
#   PEND large  -- a real backlog, and the job joins the end of it.
#   PEND 0, RUN at the host group's slot total -- no backlog, but every host is busy,
#                  so nothing starts until a running job ends.
#   PEND 0, RUN 0 -- the host group has no usable hosts; jobs pend forever with
#                  "There are no suitable hosts for the job".
# What predicts a fast start is free GPUs on hosts that are open, which the backlog
# does not show. Check the host group directly:
#   bhosts -gpu <group>   # a GPU with NJOBS 0 is free
#   bhosts -o "host_name status" -noheader <group>   # only status "ok" can take work

# RAM per slot is 15 GB on the L4 and T4 queues, so 8 slots = 120 GB and 16 = 240 GB.
#
# Every task declares memory_mb = 65536 (64 GB) in its task.toml except mouseland, which
# declares 240000 because its solution holds the trial arrays of every session at once.
# Peak RSS of each reference solution on full data is in
# timing_results/supervised_summary.csv, in the `manual` rows.
#
# The _datalimit tasks declare 960000 MB, the size of a whole gpu_l4_large node rather
# than a requirement: their parents declare 64 GB and the subsets are at most 50 GB.
DEFAULT_QUEUE="gpu_l4"
declare -A TASK_QUEUE=(
    [mouseland]=gpu_l4_16       # 240 GB declared; the only task that needs more than 120
)

# Wall clock. The cluster's cost formula is written in terms of REQUESTED minutes, so
# this is per task rather than a blanket 8 hours. Measured reference-solution runtimes
# (same source as above): majnik2025 0.7 min, sosa2024 5.9 min, allen2p 40 min. Add the
# ~7 min podman image build that the first job on a node pays, and 2 hours is generous.
#
# map, mouseland and zhang2025 on full data are unmeasured, and mouseland and zhang2025
# read 412 GB and 567 GB over NFS, so they get 8 hours until one has been seen to finish.
# A job killed at the wall clock loses the whole run.
DEFAULT_WALL="2:00"
declare -A TASK_WALL=(
    [map]="8:00" [mouseland]="8:00" [zhang2025]="8:00"
)

# The tasks whose committed reference statistics are stale: four reference solutions
# changed, the accuracy rule now needs 20 decoder runs rather than 1, and every package
# was re-pinned. hasnain2024 and lee2025 are deliberately absent -- their numbers were
# copied from the terminal-bench-science forks, which computed them on this same data
# with this same solution.
ALL_TASKS=(
    majnik2025 allen2p sosa2024 map zhang2025 mouseland
    allen2p_datalimit map_datalimit sosa2024_datalimit
    mouseland_datalimit zhang2025_datalimit
)

JOBS_ROOT="/groups/branson/home/bransonk/harbor-cluster-jobs/refstats"
LOG_DIR="/groups/branson/home/bransonk/cluster_logs/harbor"

# Hosts to keep a job off, set only by --exclude-host. Empty by default: a node that is
# broken today is usually fixed tomorrow, and a stale entry here would quietly shrink the
# pool for every future run.
EXCLUDE_HOSTS=()

QUEUE_OVERRIDE=""
WALL_OVERRIDE=""
SLOTS_OVERRIDE=""
DRY_RUN=false
CHECK_ONLY=false
TASKS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --all)        TASKS+=("${ALL_TASKS[@]}"); shift ;;
        --queue)      QUEUE_OVERRIDE="$2"; shift 2 ;;
        --slots)      SLOTS_OVERRIDE="$2"; shift 2 ;;
        --wall)       WALL_OVERRIDE="$2"; shift 2 ;;
        --jobs-root)  JOBS_ROOT="$2"; shift 2 ;;
        --exclude-host) EXCLUDE_HOSTS+=("$2"); shift 2 ;;
        --check)      CHECK_ONLY=true; shift ;;
        --dry-run|-n) DRY_RUN=true; shift ;;
        # The header block, i.e. every line up to the blank one before `set -euo`. A line
        # range would silently truncate the next time an option is documented.
        --help|-h)    sed -n '2,/^$/p' "$0"; exit 0 ;;
        -*)           echo "ERROR: unknown option '$1'." >&2; exit 1 ;;
        *)            TASKS+=("$1"); shift ;;
    esac
done
[ ${#TASKS[@]} -gt 0 ] || {
    if [ "$CHECK_ONLY" = true ]; then
        TASKS=("${ALL_TASKS[@]}")     # --check on its own means all of them
    else
        echo "ERROR: no tasks given. Name them, or pass --all." >&2
        exit 1
    fi
}

# --check: report what is on disk, submit nothing. A task's newest run is the one that
# counts, since a failed task gets resubmitted into the same directory.
if [ "$CHECK_ONLY" = true ]; then
    ready=()
    for task in "${TASKS[@]}"; do
        trial=$(ls -dt "$JOBS_ROOT/$task"/*/"${task}__"* 2>/dev/null | head -1)
        if [ -z "$trial" ]; then
            printf '  %-22s not started\n' "$task"
        elif [ -f "$trial/verifier/snapshot/stats_full.json" ]; then
            printf '  %-22s OK        %s\n' "$task" "$trial"
            ready+=("$trial")
        elif [ -f "$trial/exception.txt" ]; then
            # The exception line, not the last line: harbor embeds the container's whole
            # build log in the message, so the file ends in build output ("Stderr: None.")
            # rather than in anything that says what failed.
            reason=$(grep -oE '^[A-Za-z_.]*(Error|Exception):.*' "$trial/exception.txt" \
                     | tail -1 | cut -c1-100)
            printf '  %-22s FAILED    %s\n' "$task" "${reason:-see $trial/exception.txt}"
        else
            printf '  %-22s running   %s\n' "$task" "$trial"
        fi
    done
    if [ ${#ready[@]} -gt 0 ]; then
        echo ""
        echo "Stage 2 for the finished tasks:"
        for trial in "${ready[@]}"; do
            echo "  $SCRIPT_DIR/submit_rerun_verifier.sh --queue gpu_rtx6000 --decoder-stats $trial"
        done
    fi
    exit 0
fi

if [ -n "$QUEUE_OVERRIDE" ] && [ -z "${QUEUE_SLOTS[$QUEUE_OVERRIDE]:-}" ]; then
    echo "ERROR: unknown queue '$QUEUE_OVERRIDE'. Known: ${!QUEUE_SLOTS[*]}" >&2
    exit 1
fi

# Every task directory has to exist before anything is submitted, so a typo costs a
# message here rather than eleven jobs of which one fails on the node.
for task in "${TASKS[@]}"; do
    [ -d "$REPO_DIR/harbor-tasks/$task" ] || {
        echo "ERROR: no such task: $REPO_DIR/harbor-tasks/$task" >&2
        exit 1
    }
done

# Pre-flight the data mounts on the host. The tasks' own test_data_dir_accessible
# asserts the same thing, but it runs in the verifier, i.e. after the work is done. A
# missing bind source is CREATED by the container runtime rather than refused, so
# without this a whole sweep can run to completion against an empty /app/data.
# DATA_ROOT has to be exported for the check to resolve the compose mounts;
# generate_reference_stats.sh
# computes the same default itself inside the job.
export DATA_ROOT="${DATA_ROOT:-$REPO_DIR/data}"
python3 "$SCRIPT_DIR/check_data_mounts.py" "${TASKS[@]}" || {
    echo "ERROR: data mount check failed; nothing submitted." >&2
    exit 1
}

[ "$DRY_RUN" = true ] || mkdir -p "$LOG_DIR"

# --exclude-host as one LSF resource requirement, e.g.
#   -R "select[hname!='hostA' && hname!='hostB']"
# Empty when nothing was excluded, so the bsub line is unchanged in the common case.
RES_REQ=""
if [ ${#EXCLUDE_HOSTS[@]} -gt 0 ]; then
    select_expr=""
    for host in "${EXCLUDE_HOSTS[@]}"; do
        [ -n "$select_expr" ] && select_expr="$select_expr && "
        select_expr="${select_expr}hname!='${host}'"
    done
    RES_REQ="-R \"select[${select_expr}]\" "
    echo "excluding host(s): ${EXCLUDE_HOSTS[*]}"
fi

for task in "${TASKS[@]}"; do
    queue="${QUEUE_OVERRIDE:-${TASK_QUEUE[$task]:-$DEFAULT_QUEUE}}"
    wall="${WALL_OVERRIDE:-${TASK_WALL[$task]:-$DEFAULT_WALL}}"
    slots="${SLOTS_OVERRIDE:-${QUEUE_SLOTS[$queue]}}"
    jobs_dir="$JOBS_ROOT/$task"

    # generate_reference_stats.sh activates the podman-capable conda env, sources
    # podman_env.sh for the batch-node workarounds, and sets DATA_ROOT, so the inner
    # command carries nothing but the output directory. JOBS_DIR is per task because
    # harbor writes a timestamped run directory underneath it and eleven jobs sharing
    # one root would interleave their output.
    # PODMAN_PRIVATE_STORAGE: these jobs take one GPU's share rather than a whole node,
    # so several of them land on the same host and would otherwise build images into one
    # shared podman store at the same time. See podman_env.sh for what that corrupted.
    inner="JOBS_DIR=${jobs_dir} PODMAN_PRIVATE_STORAGE=true \
bash ${SCRIPT_DIR}/generate_reference_stats.sh --podman ${task}"

    # %J is the job id, which LSF substitutes. Unlike submit_rerun_verifier.sh this
    # keeps one log per submission rather than overwriting: a task gets rerun here (map
    # is run twice on purpose, to compare trial matching), and the earlier log is the
    # evidence of what the earlier numbers came from.
    log="${LOG_DIR}/refstat_${task}_%J.log"
    bsub_cmd="bsub -n ${slots} -gpu \"num=1\" -q ${queue} -W ${wall} ${RES_REQ}\
-J refstat_${task} -o ${log} \"${inner}\""

    echo "${task}: ${queue}, ${slots} slots, 1 GPU, wall ${wall} -> ${jobs_dir}"
    if [ "$DRY_RUN" = true ]; then
        echo "  $bsub_cmd"
        continue
    fi
    mkdir -p "$jobs_dir"
    if command -v bsub >/dev/null 2>&1; then
        eval "$bsub_cmd"
    else
        # From the workstation: bsub lives on the submit host. One argument, or ssh
        # joins the flags with spaces and bsub reads a jobspec from stdin instead.
        ssh -o BatchMode=yes login1 "$bsub_cmd" < /dev/null
    fi
done

if [ "$DRY_RUN" = false ]; then
    echo ""
    echo "Track:  ssh login1 'bash -l -c \"bjobs -J refstat_*\"'"
    echo "Then:   harbor-scripts/submit_rerun_verifier.sh --queue gpu_l4 --decoder-stats <trial dir>"
fi
