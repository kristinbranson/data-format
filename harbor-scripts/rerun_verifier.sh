#!/bin/bash
#
# Rerun the verifier (test_outputs.py) against an existing trial's snapshot.
#
# Usage:
#   ./rerun_verifier.sh [OPTIONS] <trial_dir>
#
# Options:
#   --claude-judge-only   Only rerun the Claude judge and update metrics.json
#   --codex-judge-only    Only rerun the Codex judge and update metrics.json
#   --judges-only         Rerun both judges and update metrics.json
#   --verifier-dir DIR    Use DIR as the verifier directory (default: newest
#                         verifier_rerun_* if one exists, otherwise verifier/)
#   --apikeys             Take judge credentials from ANTHROPIC_API_KEY and
#                         OPENAI_API_KEY in <repo>/.env instead of the OAuth
#                         credential files. REQUIRED on a batch node, where $HOME
#                         is not the workstation home holding those files.
#   --env FILE            Env file for --apikeys (implies it; default <repo>/.env).
#   --gpu-device ID       Give the container only this GPU, e.g. --gpu-device 1.
#                         decoder.py trains on cuda:0, so with several cards of
#                         different sizes the default (all of them) can land on the
#                         smallest. Check with
#                           nvidia-smi --query-gpu=index,name,memory.total --format=csv
#   --no-gpu              Do not request a GPU. Use when the host's CDI spec does
#                         not declare the device podman asks for; test_gpu_available
#                         then fails and decoder training runs on CPU.
#   --decoder-stats       Instead of grading, compute the 20-split decoder statistics
#                         for a reference solution: runs compute_decoder_stats.py on the
#                         trial's snapshot (converted_data.pkl + stats_full.json from an
#                         oracle run) inside the task's image, and writes
#                         <trial>/decoder_stats_<time>/reference_stats_full.json.
#   --n-replicates N      Splits for --decoder-stats. Unset, compute_decoder_stats.py
#                         uses its own DEFAULT_N_REPLICATES, which is the n the
#                         verifier's ACCURACY_NSTD is derived from.
#   --reuse-accuracy      Run every test, but take the decoder's per-output accuracy from
#                         the trial's existing metrics.json instead of training a decoder
#                         again. Training is the only expensive part of grading -- minutes
#                         to hours per trial -- and every line of test_decoder_accuracy
#                         after it is arithmetic on that accuracy, which is a property of
#                         the agent's own converted data. Reusing it also keeps this run on
#                         the same decoder version as the reference statistics it grades
#                         against, which a fresh training run would not. Implemented as a
#                         conftest.py generated into the throwaway copy of tests/ that this
#                         script mounts, so no task file changes and a normal harbor run
#                         can never pick it up. Drops the GPU request, as nothing trains.
#   --task NAME           Task name, when it cannot be inferred from the trial path.
#                         Inferred from a harbor trial directory named <task>__<id>,
#                         or from jobs/<task>/<agent>/<timestamp>/. Also --task=NAME.
#   --podman              Use rootless podman instead of docker. REQUIRED for
#                         trials stored on /groups or /nrs: docker runs the
#                         container as real root, and those NFS mounts are
#                         root-squashed, so every write the verifier makes
#                         (/logs/verifier, the /app/data mountpoint, the final
#                         chown) is denied. Rootless podman maps container-root
#                         to the invoking user's UID, which is how the cluster jobs
#                         write there successfully.
#
# The task name is inferred from the trial path: jobs/<task>/<agent>/<timestamp>/
#
# Example:
#   ./rerun_verifier.sh /path/to/jobs/sosa2024/oracle/2026-03-10__00-06-35_trial1/
#   ./rerun_verifier.sh --claude-judge-only /path/to/jobs/lee2025/claude/2026-03-10__11-18-23_trial3/
#   ./rerun_verifier.sh --codex-judge-only /path/to/jobs/sosa2024/claude/2026-03-10__19-44-11_trial1/
#   ./rerun_verifier.sh --decoder-stats ~/harbor-tasks/data-format/jobs/oracle/<time>/lee2025__<id>/
#
# Requirements:
#   - The trial must have verifier/snapshot/ with converted_data.pkl
#   - The task's Docker image must be built (or will be built automatically)

set -euo pipefail

RUN_CLAUDE_JUDGE=false
RUN_CODEX_JUDGE=false
JUDGE_ONLY=false
NO_GPU=false
USE_APIKEYS=false
ENV_FILE=""
VERIFIER_DIR_OVERRIDE=""
DECODER_STATS=false
REUSE_ACCURACY=false
# Empty unless --n-replicates is given, so the default lives in exactly one place:
# compute_decoder_stats.py's DEFAULT_N_REPLICATES.
N_REPLICATES=""
TASK_OVERRIDE=""
CONTAINER_CMD="docker"
# docker and podman spell GPU passthrough differently: docker uses its own
# --gpus flag, podman uses CDI device names from /etc/cdi/nvidia.yaml.
GPU_FLAG="--gpus all"
# --gpu-device: hand the container ONE card instead of all of them. decoder.py takes
# torch.device('cuda') without an index, i.e. cuda:0, so on a host holding cards of
# different sizes "all" trains on whichever the driver enumerates first, which may be
# far too small. List them with
#   nvidia-smi --query-gpu=index,name,memory.total --format=csv
GPU_DEVICE=""
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --claude-judge-only) RUN_CLAUDE_JUDGE=true; JUDGE_ONLY=true; shift ;;
        --codex-judge-only)  RUN_CODEX_JUDGE=true;  JUDGE_ONLY=true; shift ;;
        --judges-only)       RUN_CLAUDE_JUDGE=true; RUN_CODEX_JUDGE=true; JUDGE_ONLY=true; shift ;;
        --verifier-dir)      VERIFIER_DIR_OVERRIDE="$2"; shift 2 ;;
        --decoder-stats)     DECODER_STATS=true; shift ;;
        --reuse-accuracy)    REUSE_ACCURACY=true; shift ;;
        --n-replicates)      N_REPLICATES="$2"; shift 2 ;;
        --n-replicates=*)    N_REPLICATES="${1#*=}"; shift ;;
        --task)              TASK_OVERRIDE="$2"; shift 2 ;;
        # One-word forms, for wrappers such as submit_rerun_verifier.sh that forward
        # options as single words.
        --task=*)            TASK_OVERRIDE="${1#*=}"; shift ;;
        --gpu-device)        GPU_DEVICE="$2"; shift 2 ;;
        --gpu-device=*)      GPU_DEVICE="${1#*=}"; shift ;;
        --podman)            CONTAINER_CMD="podman"; GPU_FLAG="--device nvidia.com/gpu=all"; shift ;;
        --no-gpu)            NO_GPU=true; shift ;;
        --apikeys)           USE_APIKEYS=true; shift ;;
        --env)               ENV_FILE="$2"; USE_APIKEYS=true; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Resolved after the option loop so --gpu-device and --podman can be given in any
# order: the spelling of the device depends on which runtime was chosen.
if [ -n "$GPU_DEVICE" ]; then
    if [ "$CONTAINER_CMD" = "podman" ]; then
        GPU_FLAG="--device nvidia.com/gpu=$GPU_DEVICE"
    else
        GPU_FLAG="--gpus device=$GPU_DEVICE"
    fi
fi

# A judge-only rerun never touches the GPU: the decoder training that needs one
# lives in test_outputs.py, which this mode skips. The judges only read files and
# call an API. Requesting a GPU anyway makes the run depend on the host's CDI
# spec being parseable by the local podman -- skew between nvidia-container-toolkit
# and podman shows up as "unresolvable CDI devices" and kills the run before the
# container starts, for a device nothing was going to use.
if [ "$JUDGE_ONLY" = true ]; then
    GPU_FLAG=""
fi

# --no-gpu: same suppression, requested explicitly. Needed when the host has GPUs
# but its CDI spec does not declare the name podman is asked for -- the run then
# dies with "unresolvable CDI devices nvidia.com/gpu=all" before the container
# starts, even though nvidia-smi lists the cards. test_gpu_available will fail
# without one (it asserts torch.cuda.is_available()), and the decoder training
# falls back to CPU, so this suits a run whose purpose is the judge scores.
if [ "${NO_GPU:-false}" = true ]; then
    GPU_FLAG=""
fi

# --reuse-accuracy: nothing trains, so don't need GPU
if [ "$REUSE_ACCURACY" = true ]; then
    GPU_FLAG=""
    # Both other modes skip the pytest run this flag modifies, so combining them asks for
    # something that cannot happen; saying so beats silently ignoring the flag.
    if [ "$JUDGE_ONLY" = true ]; then
        echo "Error: --reuse-accuracy has no effect with a judge-only rerun: the judges do" >&2
        echo "       not run test_decoder_accuracy. Drop one of the two flags." >&2
        exit 1
    fi
    if [ "$DECODER_STATS" = true ]; then
        echo "Error: --reuse-accuracy and --decoder-stats are contradictory: one reuses a" >&2
        echo "       trained accuracy, the other exists to train the reference's." >&2
        exit 1
    fi
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

TRIAL_DIR="${1:?Usage: $0 [--claude-judge-only|--codex-judge-only|--judges-only] <trial_dir>}"
# Absolute, and without a trailing slash. The -v flags below pass $TRIAL_DIR
# straight to podman/docker, which treat a RELATIVE bind source as a NAMED VOLUME
# -- the run dies with `creating named volume "harbor-jobs-new/..."` instead of
# mounting anything. DATA_DIR is resolved for the same reason further down; this
# is that hazard for the trial path, and it also keeps the task-name inference
# (basename of the grandparent) working from any cwd.
TRIAL_DIR="$(cd "$TRIAL_DIR" && pwd)"

# Check that base metrics exist. Checked here so we fail early before image is built
BASE_METRICS="$TRIAL_DIR/verifier/metrics.json"
if [ "$REUSE_ACCURACY" = true ] && [ ! -f "$BASE_METRICS" ]; then
    echo "Error: --reuse-accuracy needs $BASE_METRICS, which does not exist." >&2
    echo "       This trial has no recorded accuracy to reuse; rerun it without the flag" >&2
    echo "       to train the decoder instead." >&2
    exit 1
fi

# The snapshot's large files (converted_data.pkl, sample_data.pkl) are symlinks
# to /nearline: the job tree keeps only the small files on /groups so it can be
# browsed and committed, and the pickles stay on the archive filesystem. The
# snapshot is bind-mounted at /app below, and a symlink pointing outside that
# mount is DANGLING inside the container -- test_outputs' _find_workdir_file
# calls Path.exists(), which follows symlinks, so the verifier would report
# converted_data.pkl missing and score the trial as if the agent produced
# nothing. Mounting the archive read-only at its own absolute path makes those
# links resolve. Empty when the tree has no such symlinks, so this is a no-op
# for anyone whose jobs are all on one filesystem.
NEARLINE_ROOT="/nearline/branson/data-format/harbor-jobs"
NEARLINE_MOUNT=""
if [ -d "$NEARLINE_ROOT" ]; then
    NEARLINE_MOUNT="-v $NEARLINE_ROOT:$NEARLINE_ROOT:ro"
fi

# Infer task name from trial directory path: .../jobs/<task>/<agent>/<timestamp>/
# Task name: --task if given; else harbor's own trial directory name, <task>__<id> (what
# generate_reference_stats.sh and raw harbor runs produce); else the reorganized layout
# jobs/<task>/<agent>/<timestamp>/.
TRIAL_BASENAME="$(basename "$TRIAL_DIR")"
if [ -n "$TASK_OVERRIDE" ]; then
    TASK_NAME="$TASK_OVERRIDE"
elif [[ "$TRIAL_BASENAME" =~ ^([A-Za-z][A-Za-z0-9_-]*)__[A-Za-z0-9]+$ ]]; then
    # A task name starts with a letter; the reorganized layout's <timestamp>_trialN
    # directories also contain "__" but start with a digit.
    TASK_NAME="${BASH_REMATCH[1]}"
else
    TASK_NAME="$(basename "$(dirname "$(dirname "$TRIAL_DIR")")")"
fi
TASK_DIR="$REPO_DIR/harbor-tasks/$TASK_NAME"
IMAGE_NAME="hb__${TASK_NAME}-reverify"

# Keep the task Dockerfile in step with the pinned versions before building, and
# fold those versions into the image tag. Without the tag, a version bump would
# silently reuse the image built from the previous Dockerfile, because the build
# below is skipped whenever the tag already exists.
VERSIONS_FILE="${VERSIONS_FILE:-$(ls -1 "$SCRIPT_DIR"/config_*.json 2>/dev/null | sort | tail -1)}"
if [ -f "$VERSIONS_FILE" ]; then
    python3 "$SCRIPT_DIR/apply_versions.py" --versions "$VERSIONS_FILE" >/dev/null \
        || { echo "Error: could not apply $VERSIONS_FILE"; exit 1; }
    read_harness() {  # $1 = tool key
        python3 -c "
import json, sys
print(json.load(open(sys.argv[1]))['tools'][sys.argv[2]]['harness_version'])" \
            "$VERSIONS_FILE" "$1"
    }
    IMAGE_TAG="claude-$(read_harness claude)_codex-$(read_harness codex)"
    IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
    echo "versions: $VERSIONS_FILE  ->  $IMAGE_NAME"
else
    echo "Warning: no config_*.json found; image tag will not record harness versions"
fi

if [ ! -d "$TASK_DIR" ]; then
    echo "Error: Task directory not found: $TASK_DIR"
    echo "Inferred task name '$TASK_NAME' from trial path. Expected jobs/<task>/<agent>/<timestamp>/"
    exit 1
fi

# Read data directory from docker-compose.yaml (the host path mounted to /app/data)
COMPOSE="$TASK_DIR/environment/docker-compose.yaml"
# The compose volume source is "${DATA_ROOT:?<message>}/<task>", absolute so that
# podman-compose resolves it correctly (see run_harbor.sh). This script bypasses
# compose and builds its own -v, so it must expand DATA_ROOT itself.
#
# The old parse was `sed 's|.*- ||'`, which is GREEDY: it matched the last "- " in
# the line, and the :? message contains one ("must be set - run via ..."), so the
# path came out as ".../environment/run via harbor-scripts/run_harbor.sh}/<task>".
# Anchor the strip to the start of the line instead, and drop the surrounding
# quotes the compose entry now carries.
#
# NOTE: duplicated verbatim in run_unsupervised_judges.sh, which parses the same
# line the same way. Change both together.
DATA_ROOT="${DATA_ROOT:-$REPO_DIR/data}"
# Which container path this task mounts its dataset at. Most mount it straight at
# /app/data; zhang2025 mounts it READ-ONLY at /mnt/dataset and its image entrypoint
# assembles a writable ONE cache under /app/data from there, so the dataset itself is
# never written. The mount has to be reproduced at the same path here, because this
# script bypasses compose and builds its own -v.
#
# `|| true` because grep exits 1 when it matches nothing and this script runs under
# `set -o pipefail`: without it a task whose compose matches neither path dies here
# silently, and the explicit check below never runs.
DATA_TARGET=$(grep -oE ':(/app/data|/mnt/dataset)\b' "$COMPOSE" 2>/dev/null \
    | head -1 | tr -d ':' || true)
if [ -z "$DATA_TARGET" ]; then
    echo "Error: no /app/data or /mnt/dataset volume found in $COMPOSE"
    exit 1
fi
DATA_DIR=$(grep ":$DATA_TARGET" "$COMPOSE" | head -1 \
    | sed "s|^[[:space:]]*-[[:space:]]*||; s|:$DATA_TARGET.*||; s|^\"||; s|\"$||")
# Expand a leading ${DATA_ROOT...} by replacing everything up to its closing brace.
case "$DATA_DIR" in
    '${DATA_ROOT'*) DATA_DIR="$DATA_ROOT${DATA_DIR#*\}}" ;;
esac
# Volume sources in docker-compose.yaml are relative to the compose file's own
# directory (compose defines them that way, and it keeps the task portable across
# the workstation and cluster paths). This script bypasses compose and builds its
# own `docker run -v`, so it has to do that resolution itself -- otherwise the
# check below fails from any cwd but harbor-tasks/<task>/environment/.
# Resolving also makes DATA_DIR absolute, which `docker -v` requires: a relative
# source is treated as a named volume rather than a bind mount, which would
# silently hand the container an empty /app/data instead of erroring.
case "$DATA_DIR" in
    /*) ;;
    *)  DATA_DIR=$(realpath -m "$(dirname "$COMPOSE")/$DATA_DIR") ;;
esac
if [ ! -d "$DATA_DIR" ]; then
    echo "Error: Data directory not found: $DATA_DIR (from $COMPOSE)"
    exit 1
fi

# Snapshot dir is resolved after we know which verifier dir to use (see below).
# Default to verifier/snapshot; overridden for judge-only mode targeting a rerun dir.

# Build Docker image if it doesn't exist
if ! "$CONTAINER_CMD" image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Building Docker image $IMAGE_NAME..."
    # Checked explicitly: the build is the last command of this branch, so a non-zero
    # exit would kill the script through `set -e` with nothing printed after the build
    # log, leaving a job that looks complete and produced nothing.
    if ! "$CONTAINER_CMD" build -t "$IMAGE_NAME" "$TASK_DIR/environment"; then
        echo "Error: image build failed for $IMAGE_NAME (exit $?)" >&2
        exit 1
    fi
    # Tagging can print "Successfully tagged" and still leave nothing usable behind,
    # so confirm the image is really there before anything tries to run it.
    if ! "$CONTAINER_CMD" image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
        echo "Error: $IMAGE_NAME is absent after a build that reported success" >&2
        exit 1
    fi
else
    echo "Using existing Docker image $IMAGE_NAME"
fi

# --- Judge credentials ---
# Two routes, and the container accepts either: tests/test.sh uses
# CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY for the Claude judge, and
# CODEX_AUTH_JSON_B64 or OPENAI_API_KEY for Codex.
#
# --apikeys is REQUIRED on a batch node. The OAuth route reads
# $HOME/.claude/.credentials.json, and $HOME on a compute node is
# /groups/branson/home/<user>, not the workstation home where those files live.
# Worse, it fails silently: `export VAR=$(cmd)` does not trip `set -e`, because
# export itself succeeds, so the token became the empty string and the judges ran
# UNAUTHENTICATED -- producing empty judge/ directories and
# "[Errno 2] ... llm_judge_eval.json" in metrics.json, next to a reward that
# looks fine.
if [ "$DECODER_STATS" = true ]; then
    echo "Judge auth: not needed for --decoder-stats"
elif [ "$USE_APIKEYS" = true ]; then
    ENV_FILE="${ENV_FILE:-$REPO_DIR/.env}"
    [ -f "$ENV_FILE" ] || { echo "Error: env file not found: $ENV_FILE"; exit 1; }
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    for var in ANTHROPIC_API_KEY OPENAI_API_KEY; do
        [ -n "${!var:-}" ] || { echo "Error: $var not set in $ENV_FILE"; exit 1; }
    done
    export ANTHROPIC_API_KEY OPENAI_API_KEY
    echo "Judge auth: API keys from $ENV_FILE"
else
    # Checked, not assumed: an unreadable credentials file otherwise yields an empty
    # token and an unauthenticated judge run rather than an error.
    CRED="$HOME/.claude/.credentials.json"
    if [ -f "$CRED" ]; then
        export CLAUDE_CODE_OAUTH_TOKEN=$(python3 -c "import json; print(json.load(open('$CRED'))['claudeAiOauth']['accessToken'])")
    fi
    if [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
        echo "Error: no Claude credentials. $CRED is missing or has no token;" >&2
        echo "       pass --apikeys to use ANTHROPIC_API_KEY from .env instead." >&2
        exit 1
    fi
    if [ -z "${CODEX_AUTH_JSON_B64:-}" ]; then
        export CODEX_AUTH_JSON_B64=$(base64 -w0 "$HOME/.codex/auth.json" 2>/dev/null || true)
    fi
    if [ -z "${CODEX_AUTH_JSON_B64:-}" ]; then
        echo "Warning: Codex auth not available. Codex judge will be skipped."
    fi
    echo "Judge auth: OAuth credential files from \$HOME"
fi

# Harbor copies test files into the container (upload_dir) rather than bind-mounting.
# NFS-mounted paths lose permissions when accessed by non-host users inside Docker.
# Replicate Harbor's behavior by copying tests to a local tmpdir before mounting.
TESTS_TMPDIR=$(mktemp -d)
cp -r "$TASK_DIR/tests/." "$TESTS_TMPDIR/"

# --reuse-accuracy: hand the tests a previous run's decoder accuracy and a conftest.py that
# swaps out the training. Both go in the temp copy of tests/, which this script created and
# deletes, so the task's own tests/ is untouched and a normal harbor run cannot see either
# file. base_metrics.json rather than a mount of verifier/: /logs/verifier is the new, empty
# rerun directory, and anything written there would be copied into verifier/ by
# merge_rerun_verifier.sh.
REUSE_ACCURACY_ENV=""
if [ "$REUSE_ACCURACY" = true ]; then
    cp "$BASE_METRICS" "$TESTS_TMPDIR/base_metrics.json"
    # Stated rather than hidden. Harmless -- the chain back to a real training run is
    # unbroken, since a reused run copies the accuracy forward unchanged -- but anyone
    # reading the log should be able to see how far from a training run this trial is.
    if python3 -c "import json,sys; sys.exit(0 if json.load(open('$BASE_METRICS')).get('validation_balanced_accuracy_reused') else 1)" 2>/dev/null; then
        echo "          (that file was itself produced by a --reuse-accuracy run)"
    fi
    cp "$SCRIPT_DIR/reuse_accuracy_conftest.py" "$TESTS_TMPDIR/conftest.py"
    REUSE_ACCURACY_ENV="-e REUSE_VALIDATION_ACCURACY=/tests/base_metrics.json"
    echo "Accuracy: reused from $BASE_METRICS (no decoder training)"
fi

chmod -R a+rX "$TESTS_TMPDIR"
trap 'rm -rf "$TESTS_TMPDIR"' EXIT

if [ "$DECODER_STATS" = true ]; then
    # Replicate decoder statistics for a reference solution. Run in the task's image, not
    # on the host, so torch and numpy are the versions the verifier grades with.
    SNAPSHOT_DIR="$TRIAL_DIR/verifier/snapshot"
    for f in converted_data.pkl stats_full.json; do
        if [ ! -e "$SNAPSHOT_DIR/$f" ]; then
            echo "Error: no $f in $SNAPSHOT_DIR (run the oracle first)"
            exit 1
        fi
    done
    STATS_OUT="$TRIAL_DIR/decoder_stats_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$STATS_OUT"
    CPU_FLAG=""
    [ -z "$GPU_FLAG" ] && CPU_FLAG="--cpu"

    echo "Trial:    $TRIAL_DIR"
    echo "Task:     $TASK_NAME"
    echo "Output:   $STATS_OUT"
    echo "Mode:     decoder statistics, ${N_REPLICATES:-default} replicates"
    echo ""

    "$CONTAINER_CMD" run --rm \
        $GPU_FLAG \
        -v "$SNAPSHOT_DIR":/app:ro \
        $NEARLINE_MOUNT \
        -v "$TESTS_TMPDIR":/tests:ro \
        -v "$SCRIPT_DIR/compute_decoder_stats.py":/opt/compute_decoder_stats.py:ro \
        -v "$STATS_OUT":/logs/verifier \
        -w /tmp \
        "$IMAGE_NAME" \
        bash -c "python3 /opt/compute_decoder_stats.py --decoder-dir /tests \
                   --stats-json /app/stats_full.json \
                   --out /logs/verifier/reference_stats_full.json \
                   ${N_REPLICATES:+--n-replicates $N_REPLICATES} $CPU_FLAG \
                   /app/converted_data.pkl \
                   2>&1 | tee /logs/verifier/decoder_stats_log.txt; \
                 chown -R \$(stat -c '%u:%g' /logs/verifier) /logs/verifier 2>/dev/null || true"

    echo ""
    echo "Wrote $STATS_OUT/reference_stats_full.json"
    echo "Copy it to harbor-tasks/$TASK_NAME/tests/ (and the task's _minimal twin) once checked."
    exit 0
elif [ "$JUDGE_ONLY" = true ]; then
    if [ -n "$VERIFIER_DIR_OVERRIDE" ]; then
        VERIFIER_OUT="$VERIFIER_DIR_OVERRIDE"
    else
        # Default: newest unmerged verifier_rerun_* if one exists, otherwise verifier/
        NEWEST_RERUN=$(ls -dt "$TRIAL_DIR"/verifier_rerun_*/ 2>/dev/null | grep -v '_merged/$' | head -1 || true)
        if [ -n "$NEWEST_RERUN" ]; then
            VERIFIER_OUT="${NEWEST_RERUN%/}"
            echo "Found unmerged rerun: $VERIFIER_OUT"
        else
            VERIFIER_OUT="$TRIAL_DIR/verifier"
        fi
    fi
    if [ ! -d "$VERIFIER_OUT" ]; then
        echo "Error: No verifier directory at $VERIFIER_OUT"
        exit 1
    fi

    # Resolve snapshot dir: use the target verifier's snapshot, fall back to verifier/snapshot
    SNAPSHOT_DIR="$VERIFIER_OUT/snapshot"
    if [ ! -d "$SNAPSHOT_DIR" ]; then
        SNAPSHOT_DIR="$TRIAL_DIR/verifier/snapshot"
    fi
    if [ ! -d "$SNAPSHOT_DIR" ]; then
        echo "Error: No snapshot directory found"
        exit 1
    fi

    JUDGES=""
    [ "$RUN_CLAUDE_JUDGE" = true ] && JUDGES="$JUDGES claude"
    [ "$RUN_CODEX_JUDGE" = true ] && JUDGES="$JUDGES codex"

    echo "Trial:    $TRIAL_DIR"
    echo "Snapshot: $SNAPSHOT_DIR"
    echo "Mode:     Judge only ($JUDGES) — updating existing verifier/"
    echo ""

    # Build the inline script for selected judges
    JUDGE_SCRIPT='
export PATH="$HOME/.local/bin:$PATH"
JUDGE_DIR=/logs/verifier/judge

# Judge models come from /tests/versions.json, which ships in with the tests.
# Fall back to the literals so a task whose tests predate versions.json still
# runs rather than invoking the judge with an empty model flag.
read_judge_model() {  # $1 = judge key, $2 = fallback
  jq -r --arg k "$1" --arg fallback "$2" \
     '"'"'.tools[$k].model // $fallback'"'"' /tests/versions.json 2>/dev/null || echo "$2"
}
CLAUDE_JUDGE_MODEL=$(read_judge_model claude claude-opus-4-6)
CODEX_JUDGE_MODEL=$(read_judge_model codex gpt-5.4)
echo "judge models: claude=$CLAUDE_JUDGE_MODEL codex=$CODEX_JUDGE_MODEL"
'

    if [ "$RUN_CLAUDE_JUDGE" = true ]; then
        JUDGE_SCRIPT+='
CLAUDE_DIR="$JUDGE_DIR/claude"
rm -rf "$CLAUDE_DIR"
mkdir -p "$CLAUDE_DIR"

echo "=== Running Claude judge ==="
cd "$CLAUDE_DIR"
# IS_SANDBOX=1 allows claude to run --permission-mode bypassPermissions as root,
# matching how Harbor runs the claude agent.
# The model is pinned rather than using the bare `opus` alias, which gets
# repointed as new models ship. An unpinned rerun would silently re-judge with a
# different model than the one recorded in the trial being fixed. Matches test.sh.
IS_SANDBOX=1 \
  CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  claude -p "$(cat /tests/judge_instructions.md)" \
    --model "$CLAUDE_JUDGE_MODEL" \
    --permission-mode bypassPermissions \
    --output-format stream-json \
    --no-session-persistence \
    --verbose \
  2>&1 | tee judge_log.txt || true

cd /
python3 /tests/compute_reward.py \
  --eval-json "$CLAUDE_DIR/llm_judge_eval.json" \
  --model-name claude \
  --metrics-json /logs/verifier/metrics.json 2>&1 || true
'
    fi

    if [ "$RUN_CODEX_JUDGE" = true ]; then
        JUDGE_SCRIPT+='
CODEX_DIR="$JUDGE_DIR/codex"
rm -rf "$CODEX_DIR"
mkdir -p "$CODEX_DIR"

# Codex reads its credentials from /root/.codex/auth.json and nothing else -- it does not
# look at OPENAI_API_KEY in the environment. With no such file it sends no Authorization
# header at all and every call dies with 401 "Missing bearer or basic authentication in
# header", which the `|| true` below swallows: the trial still reports success while
# compute_reward.py records a null codex reward. Under --apikeys, CODEX_AUTH_JSON_B64 is
# deliberately unset, so the OAuth branch alone left codex unauthenticated on every trial.
# The elif mirrors tests/test.sh, which has had it all along.
mkdir -p /root/.codex
if [ -n "${CODEX_AUTH_JSON_B64:-}" ]; then
  echo "$CODEX_AUTH_JSON_B64" | base64 -d > /root/.codex/auth.json
elif [ -n "${OPENAI_API_KEY:-}" ]; then
  cat > /root/.codex/auth.json <<EOF
{
  "OPENAI_API_KEY": "${OPENAI_API_KEY}"
}
EOF
fi

echo "=== Running Codex judge ==="
cd "$CODEX_DIR"
codex exec "$(cat /tests/judge_instructions.md)" \
    -m "$CODEX_JUDGE_MODEL" \
    --dangerously-bypass-approvals-and-sandbox \
    --json \
    --ephemeral \
    --skip-git-repo-check \
  2>&1 | tee judge_log.txt || true

cd /
python3 /tests/compute_reward.py \
  --eval-json "$CODEX_DIR/llm_judge_eval.json" \
  --model-name codex \
  --metrics-json /logs/verifier/metrics.json 2>&1 || true
'
    fi

    JUDGE_SCRIPT+='
# Rewrite reward.json so its process score reflects the judges just rerun. pytest is not
# rerun here, so the pass/fail outcome is read back from the reward file already in place.
# Tasks whose tests predate write_reward_file.py keep reward.txt as their only reward.
if [ -f /tests/write_reward_file.py ]; then
  python3 /tests/write_reward_file.py --reuse-outcome \
    || echo "WARNING: reward.json not rewritten; judge scores are in metrics.json only"
fi

HOST_UID=$(stat -c "%u" /logs/verifier)
HOST_GID=$(stat -c "%g" /logs/verifier)
chown -R "$HOST_UID:$HOST_GID" /logs/verifier/ 2>/dev/null || true
echo "=== Judge rerun complete ==="
'

    "$CONTAINER_CMD" run --rm \
        $GPU_FLAG \
        -e CLAUDE_CODE_OAUTH_TOKEN \
        -e CODEX_AUTH_JSON_B64 \
        -e ANTHROPIC_API_KEY \
        -e OPENAI_API_KEY \
        -v "$SNAPSHOT_DIR":/app \
        $NEARLINE_MOUNT \
        -v "$DATA_DIR":"$DATA_TARGET":ro \
        -v "$TESTS_TMPDIR":/tests:ro \
        -v "$VERIFIER_OUT":/logs/verifier \
        -v "$TRIAL_DIR/agent":/logs/agent \
        -w /app \
        "$IMAGE_NAME" \
        bash -c "$JUDGE_SCRIPT"
else
    # Full verifier rerun
    SNAPSHOT_DIR="$TRIAL_DIR/verifier/snapshot"
    if [ ! -d "$SNAPSHOT_DIR" ]; then
        echo "Error: No snapshot directory at $SNAPSHOT_DIR"
        exit 1
    fi
    if [ ! -f "$SNAPSHOT_DIR/converted_data.pkl" ]; then
        echo "Warning: No converted_data.pkl in snapshot. Tests requiring it will be skipped."
    fi
    VERIFIER_OUT="$TRIAL_DIR/verifier_rerun_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$VERIFIER_OUT"

    echo "Trial:    $TRIAL_DIR"
    echo "Snapshot: $SNAPSHOT_DIR"
    echo "Output:   $VERIFIER_OUT"
    echo ""

    # Run test.sh inside the container
    # Mount layout matches Harbor:
    #   - snapshot -> /app (the agent's working directory)
    #   - data -> /app/data (the source data)
    #   - tests -> /tests
    #   - verifier output -> /logs/verifier
    #   - agent logs -> /logs/agent (for chown)
    # Claude and Codex CLIs are pre-installed in the Docker image.
    "$CONTAINER_CMD" run --rm \
        $GPU_FLAG \
        -e CLAUDE_CODE_OAUTH_TOKEN \
        -e CODEX_AUTH_JSON_B64 \
        -e ANTHROPIC_API_KEY \
        -e OPENAI_API_KEY \
        -v "$SNAPSHOT_DIR":/app \
        $NEARLINE_MOUNT \
        -v "$DATA_DIR":"$DATA_TARGET":ro \
        -v "$TESTS_TMPDIR":/tests:ro \
        -v "$VERIFIER_OUT":/logs/verifier \
        -v "$TRIAL_DIR/agent":/logs/agent \
        $REUSE_ACCURACY_ENV \
        -w /app \
        "$IMAGE_NAME" \
        bash /tests/test.sh

    # The flag's contract, checked from outside the container as well as inside it: a run
    # that trained instead of reusing would otherwise be visible only to someone reading
    # test-stdout.txt, and the number it produced would rest on a different decoder version
    # than the reference statistics it was compared against.
    if [ "$REUSE_ACCURACY" = true ]; then
        python3 "$SCRIPT_DIR/check_reuse_accuracy.py" \
            "$BASE_METRICS" "$VERIFIER_OUT/metrics.json" || exit 1
    fi
fi

echo ""
echo "Verifier output: $VERIFIER_OUT"
echo "Reward: $(python3 "$SCRIPT_DIR/show_reward.py" "$VERIFIER_OUT" 2>/dev/null || echo 'N/A')"
if [ -f "$VERIFIER_OUT/metrics.json" ]; then
    echo "Judge:  $(python3 -c "
import json
d = json.load(open('$VERIFIER_OUT/metrics.json'))
parts = []
for model in ['claude', 'codex']:
    r = d.get(f'llm_judge_{model}_reward')
    if r is not None:
        parts.append(f'{model}={r:.3f}')
    elif f'llm_judge_{model}_error' in d:
        parts.append(f'{model}=ERR')
print(', '.join(parts) if parts else 'N/A')
" 2>/dev/null || echo 'N/A')"
fi
