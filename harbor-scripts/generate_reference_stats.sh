#!/bin/bash
#
# Run the oracle solution without the verifier to generate reference stats.
# Output goes to jobs/oracle/ and the snapshot will contain stats_full.json,
# converted_data.pkl, etc.
#
# Usage:
#   ./generate_reference_stats.sh [task_name]
#
# Examples:
#   ./generate_reference_stats.sh           # all tasks
#   ./generate_reference_stats.sh sosa2024  # just sosa2024

JOBS_DIR="/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs/oracle"

TASK_FLAG=""
if [ -n "$1" ]; then
    TASK_FLAG="-t $1"
fi

source /home/bransonk@hhmi.org/miniforge3/etc/profile.d/conda.sh
conda activate eval-data-format

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
    $TASK_FLAG
