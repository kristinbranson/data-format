#!/bin/bash
#
# Rerun the verifier for all supervised (non-oracle) trials in the jobs directory.
# Supervised tasks are identified by having reference_stats_full.json in their tests/.
#
# Usage:
#   ./rerun_supervised_verifiers_20260406.sh [--dry-run]
#
# Skips trials that already have an unmerged verifier_rerun_* directory.

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

# Skip this trial — already rerun
SKIP="sosa2024/claude/2026-03-10__19-44-11_trial1"

TRIALS=()
for verifier_dir in $(find "$JOBS_DIR" -maxdepth 5 -type d -name 'verifier' | grep -v '/raw/' | grep -v '/oracle/' | sort); do
    trial_dir=$(dirname "$verifier_dir")
    rel=$(echo "$trial_dir" | sed "s|$JOBS_DIR/||")
    task_name=$(echo "$rel" | cut -d/ -f1)

    # Only supervised tasks (have reference_stats_full.json)
    if [ ! -f "$REPO_DIR/harbor-tasks/$task_name/tests/reference_stats_full.json" ]; then
        continue
    fi

    # Skip excluded trial
    if [ "$rel" = "$SKIP" ]; then
        echo "SKIP (already done): $rel"
        continue
    fi

    # Skip if there's already an unmerged rerun
    if ls -d "$trial_dir"/verifier_rerun_*/ 2>/dev/null | grep -qv '_merged/$'; then
        echo "SKIP (has unmerged rerun): $rel"
        continue
    fi

    TRIALS+=("$trial_dir")
done

echo ""
echo "Found ${#TRIALS[@]} supervised trials to rerun"
echo ""

if [ "$DRY_RUN" = true ]; then
    for t in "${TRIALS[@]}"; do
        echo "  $t"
    done
    echo ""
    echo "(dry run — no action taken)"
    exit 0
fi

TOTAL=${#TRIALS[@]}
CURRENT=0
FAILED=()

for trial_dir in "${TRIALS[@]}"; do
    CURRENT=$((CURRENT + 1))
    rel=$(echo "$trial_dir" | sed "s|$JOBS_DIR/||")
    echo ""
    echo "======== [$CURRENT/$TOTAL] $rel ========"
    if "$SCRIPT_DIR/rerun_verifier.sh" "$trial_dir"; then
        echo "OK: $rel"
    else
        echo "FAILED: $rel"
        FAILED+=("$rel")
    fi
done

echo ""
echo "======== DONE ========"
echo "Total: $TOTAL"
echo "Failed: ${#FAILED[@]}"
if [ ${#FAILED[@]} -gt 0 ]; then
    for f in "${FAILED[@]}"; do
        echo "  $f"
    done
fi
