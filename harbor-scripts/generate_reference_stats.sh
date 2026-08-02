#!/bin/bash
#
# Run the oracle solution without the verifier to generate reference stats.
# Output goes to jobs/oracle/ and the snapshot will contain stats_full.json,
# converted_data.pkl, etc.
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
while [[ $# -gt 0 ]]; do
    case "$1" in
        --podman) USE_PODMAN=true; shift ;;
        --help|-h) sed -n '2,20p' "$0"; exit 0 ;;
        *)        TASK="$1"; shift ;;
    esac
done

JOBS_DIR="/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs/oracle"

TASK_FLAG=""
if [ -n "$TASK" ]; then
    TASK_FLAG="-t $TASK"
fi

source /home/bransonk@hhmi.org/miniforge3/etc/profile.d/conda.sh
# Same split as run_harbor.sh: the podman-capable harbor lives in its own env.
if [ "$USE_PODMAN" = true ]; then
    conda activate eval-data-format-podman
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
    PODMAN_FLAG="--ek use_podman=true"
fi

# Every task compose builds its /app/data mount as "${DATA_ROOT:?...}/<task>", so
# this must be exported or compose refuses to start. See run_harbor.sh for why the
# mount is absolute rather than relative.
export DATA_ROOT="${DATA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)/data}"

harbor run \
    -p /groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks \
    -a "oracle" \
    -o "$JOBS_DIR" \
    -k 1 -n 1 \
    --disable-verification \
    $TASK_FLAG $PODMAN_FLAG
