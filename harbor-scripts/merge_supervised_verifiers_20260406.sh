#!/bin/bash
#
# Merge verifier reruns for all supervised (non-oracle) trials that have
# unmerged verifier_rerun_* directories.
#
# Usage:
#   ./merge_supervised_verifiers_20260406.sh [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
JOBS_DIR="$HOME/harbor-tasks/data-format/jobs"
DRY_RUN=false

while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --dry-run|-n) DRY_RUN=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

TRIALS=()
for verifier_dir in $(find "$JOBS_DIR" -maxdepth 5 -type d -name 'verifier' | grep -v '/raw/' | grep -v '/oracle/' | sort); do
    trial_dir=$(dirname "$verifier_dir")
    rel=$(echo "$trial_dir" | sed "s|$JOBS_DIR/||")
    task_name=$(echo "$rel" | cut -d/ -f1)

    # Only supervised tasks (have reference_stats_full.json)
    if [ ! -f "$REPO_DIR/harbor-tasks/$task_name/tests/reference_stats_full.json" ]; then
        continue
    fi

    # Only trials with unmerged reruns
    if ! ls -d "$trial_dir"/verifier_rerun_*/ 2>/dev/null | grep -qv '_merged/$'; then
        continue
    fi

    TRIALS+=("$trial_dir")
done

echo "Found ${#TRIALS[@]} supervised trials with unmerged reruns"
echo ""

if [ ${#TRIALS[@]} -eq 0 ]; then
    echo "Nothing to merge."
    exit 0
fi

TOTAL=${#TRIALS[@]}
CURRENT=0
FAILED=()

for trial_dir in "${TRIALS[@]}"; do
    CURRENT=$((CURRENT + 1))
    rel=$(echo "$trial_dir" | sed "s|$JOBS_DIR/||")
    echo "======== [$CURRENT/$TOTAL] $rel ========"
    if [ "$DRY_RUN" = true ]; then
        newest=$(ls -dt "$trial_dir"/verifier_rerun_*/ 2>/dev/null | grep -v '_merged/' | head -1)
        echo "  Would merge: $(basename "${newest%/}")"
    else
        if "$SCRIPT_DIR/merge_rerun_verifier.sh" --jobdir "$trial_dir"; then
            echo "OK: $rel"
        else
            echo "FAILED: $rel"
            FAILED+=("$rel")
        fi
    fi
    echo ""
done

echo "======== DONE ========"
echo "Total: $TOTAL"
if [ "$DRY_RUN" = true ]; then
    echo "(dry run — no action taken)"
else
    echo "Failed: ${#FAILED[@]}"
    if [ ${#FAILED[@]} -gt 0 ]; then
        for f in "${FAILED[@]}"; do
            echo "  $f"
        done
    fi
fi
