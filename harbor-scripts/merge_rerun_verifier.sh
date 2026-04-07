#!/bin/bash
#
# Merge a verifier_rerun_* directory into the base verifier/ directory.
#
# Usage:
#   ./merge_rerun_verifier.sh --jobdir <trial_dir> [--basedir <dir>] [--newdir <dir>] [--dry-run]
#
# If only --jobdir is given, merges the newest verifier_rerun_* into verifier/.
# --basedir overrides the target (default: <jobdir>/verifier)
# --newdir  overrides the source (default: newest verifier_rerun_* in jobdir)
# --dry-run shows what would be done without modifying anything
#
# What gets merged:
#   - Top-level files (ctrf.json, reward.txt, test-stdout.txt, metrics.json):
#     replaced from newdir if present
#   - judge/ subdirectories: each model dir (claude/, codex/) replaced if it
#     contains an llm_judge_eval.json (i.e. the judge actually produced results)
#   - snapshot/: never touched

set -euo pipefail

JOBDIR=""
BASEDIR=""
NEWDIR=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --jobdir)  JOBDIR="$2";  shift 2 ;;
        --basedir) BASEDIR="$2"; shift 2 ;;
        --newdir)  NEWDIR="$2";  shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ -z "$JOBDIR" ]; then
    echo "Error: --jobdir is required"
    echo "Usage: $0 --jobdir <trial_dir> [--basedir <dir>] [--newdir <dir>] [--dry-run]"
    exit 1
fi

JOBDIR="${JOBDIR%/}"

if [ -z "$BASEDIR" ]; then
    BASEDIR="$JOBDIR/verifier"
fi
BASEDIR="${BASEDIR%/}"

if [ -z "$NEWDIR" ]; then
    NEWDIR=$(ls -dt "$JOBDIR"/verifier_rerun_*/ 2>/dev/null | head -1)
    if [ -z "$NEWDIR" ]; then
        echo "Error: No verifier_rerun_* directories found in $JOBDIR"
        exit 1
    fi
fi
NEWDIR="${NEWDIR%/}"

if [ ! -d "$BASEDIR" ]; then
    echo "Error: Base directory not found: $BASEDIR"
    exit 1
fi
if [ ! -d "$NEWDIR" ]; then
    echo "Error: New directory not found: $NEWDIR"
    exit 1
fi

echo "Merging verifier rerun results"
echo "  Base (target): $BASEDIR"
echo "  New  (source): $NEWDIR"
echo "  Dry run:       $DRY_RUN"
echo ""

# 1. Replace top-level files (skip snapshot/ and judge/)
for f in "$NEWDIR"/*; do
    name=$(basename "$f")
    case "$name" in
        snapshot|judge) continue ;;
    esac
    if [ -f "$f" ]; then
        echo "Replace $name"
        if [ "$DRY_RUN" = false ]; then
            cp "$f" "$BASEDIR/$name"
        fi
    fi
done

# 2. Replace judge model dirs that have actual results
if [ -d "$NEWDIR/judge" ]; then
    for model_dir in "$NEWDIR"/judge/*/; do
        [ -d "$model_dir" ] || continue
        model=$(basename "$model_dir")
        if [ ! -f "$model_dir/llm_judge_eval.json" ]; then
            echo "Skip judge/$model/ (no llm_judge_eval.json)"
            continue
        fi
        dest="$BASEDIR/judge/$model"
        echo "Replace judge/$model/"
        if [ "$DRY_RUN" = false ]; then
            mkdir -p "$BASEDIR/judge"
            rm -rf "$dest"
            cp -r "$model_dir" "$dest"
        fi
    done
fi

# 3. Rename rerun dir to mark it as merged
MERGED_NAME="${NEWDIR}_merged"
echo "Rename $NEWDIR -> $MERGED_NAME"
if [ "$DRY_RUN" = false ]; then
    mv "$NEWDIR" "$MERGED_NAME"
fi

echo ""
echo "Done."
if [ -f "$BASEDIR/metrics.json" ] && [ "$DRY_RUN" = false ]; then
    echo "Reward: $(cat "$BASEDIR/reward.txt" 2>/dev/null || echo 'N/A')"
    echo "Judge:  $(python3 -c "
import json
d = json.load(open('$BASEDIR/metrics.json'))
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
