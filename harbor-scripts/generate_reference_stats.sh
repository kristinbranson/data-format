#!/bin/bash
#
# Run the oracle solution without the verifier to generate reference stats.
# Output goes to jobs/oracle/ and the snapshot will contain stats_full.json,
# converted_data.pkl, etc.
#
# That is step 1 of 2. The reference also needs the decoder's accuracy over 20
# independent train/validation splits, which the verifier's accuracy threshold uses:
#   harbor-scripts/rerun_verifier.sh --decoder-stats --task <task> <oracle trial dir>
# writes <trial>/decoder_stats_<time>/reference_stats_full.json; copy that into the
# task's tests/ (and its _minimal twin).
#
# Usage:
#   ./generate_reference_stats.sh [--podman] [task_name]
#
# Examples:
#   ./generate_reference_stats.sh                      # all tasks
#   ./generate_reference_stats.sh sosa2024             # just sosa2024
#   ./generate_reference_stats.sh --podman zhang2025   # solution writes to /app/data
#
# --podman: use rootless podman instead of docker. Needed when the solution has to
# WRITE inside /app/data. The datasets live on /nrs, which is NFS with sec=krb5, so
# the server authenticates by Kerberos ticket rather than by uid. A docker container
# runs as real root with no ticket and gets squashed to nobody -- reads succeed
# because the tree is world-readable, and the first write fails with EACCES. Rootless
# podman maps container root to the invoking user, whose ticket the host already
# holds, so the write goes through as that user.
#
# zhang2025 needs this: its solution drives the IBL ONE api, which caches REST
# responses and the release index inside its cache directory, i.e. under /app/data.

USE_PODMAN=false
TASK=""
# Which harbor to run, matching run_harbor.sh's --harbor. Taken from the newest versions
# config below unless --harbor overrides it, so this script and run_harbor.sh cannot
# disagree about which harbor a round of work used.
HARBOR_VERSION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --podman) USE_PODMAN=true; shift ;;
        --harbor) HARBOR_VERSION="$2"; shift 2 ;;
        --help|-h) sed -n '2,27p' "$0"; exit 0 ;;
        *)        TASK="$1"; shift ;;
    esac
done

JOBS_DIR="${JOBS_DIR:-$HOME/harbor-tasks/data-format/jobs/oracle}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -z "$HARBOR_VERSION" ]; then
    CFG=$(ls -1 "$SCRIPT_DIR"/config_*.json 2>/dev/null | sort | tail -1)
    [ -n "$CFG" ] && HARBOR_VERSION=$(jq -r '.harbor_version // empty' "$CFG")
    if [ -z "$HARBOR_VERSION" ]; then
        HARBOR_VERSION="0.1.45"
        echo "harbor: no harbor_version in ${CFG:-any config}, reading it as 0.1.45"
    fi
fi

# Kept in step with run_harbor.sh's gate; the comments there say why each flag differs.
case "$HARBOR_VERSION" in
    0.23.0)
        PODMAN_ENV="eval-data-format-podman-023"
        TASK_OPT="-i"
        YES_FLAG="-y"
        PODMAN_OPT="-e podman"
        ;;
    0.1.45)
        PODMAN_ENV="eval-data-format-podman"
        TASK_OPT="-t"
        YES_FLAG=""
        PODMAN_OPT="--ek use_podman=true"
        ;;
    *)
        echo "ERROR: --harbor must be 0.23.0 or 0.1.45, got '$HARBOR_VERSION'"
        exit 1
        ;;
esac
echo "harbor: $HARBOR_VERSION"

TASK_FLAG=""
if [ -n "$TASK" ]; then
    TASK_FLAG="$TASK_OPT $TASK"
fi

source "$HOME/miniforge3/etc/profile.d/conda.sh"
# Same split as run_harbor.sh: the podman-capable harbor lives in its own env. The docker
# env is not versioned: it carries a non-editable harbor and has no podman support, so it
# is only ever the local-docker path.
if [ "$USE_PODMAN" = true ]; then
    conda activate "$PODMAN_ENV"
else
    conda activate eval-data-format
fi

# Per-job runroot, cgroupfs and pause-process cleanup for rootless podman. Reads
# $USE_PODMAN, and only does anything under LSF, so it is a no-op here on a
# workstation -- sourced anyway so this script and run_harbor.sh stay identical.
# shellcheck source=harbor-scripts/podman_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/podman_env.sh"

PODMAN_FLAG=""
if [ "$USE_PODMAN" = true ]; then
    PODMAN_FLAG="$PODMAN_OPT"
fi

# Every task compose builds its /app/data mount as "${DATA_ROOT:?...}/<task>", so
# this must be exported or compose refuses to start. See run_harbor.sh for why the
# mount is absolute rather than relative.
export DATA_ROOT="${DATA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)/data}"

harbor run $YES_FLAG \
    -p /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks \
    -a "oracle" \
    -o "$JOBS_DIR" \
    -k 1 -n 1 \
    --disable-verification \
    $TASK_FLAG $PODMAN_FLAG

echo ""
echo "Next: harbor-scripts/rerun_verifier.sh --decoder-stats --task <task> <trial dir under $JOBS_DIR>"
echo "(add --podman for trials on /groups or /nrs), then copy the reference_stats_full.json it writes."
