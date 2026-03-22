#!/bin/bash
#
# Sync job results from local jobs dir to the repo's harbor-jobs/ directory.
#
# Usage:
#   ./sync_jobs.sh              # dry-run: show what would be synced
#   ./sync_jobs.sh --apply      # actually sync
#   ./sync_jobs.sh --depth N    # limit output to N directory levels (default: 4)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$HOME/harbor-tasks/data-format/jobs/"
DST="$(cd "$SCRIPT_DIR/.." && pwd)/harbor-jobs/"

APPLY=false
DEPTH=4

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)  APPLY=true; shift ;;
    --depth)  DEPTH="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--apply] [--depth N]"
      echo "  --apply   Actually sync (default is dry-run)"
      echo "  --depth N Limit output to N directory levels (default: 4)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"; exit 1 ;;
  esac
done

EXCLUDES="--exclude=raw/ --exclude=debug/ --exclude=*/oracle/"

if [ "$APPLY" = true ]; then
  rsync -av --ignore-existing $EXCLUDES "$SRC" "$DST"
else
  echo "Dry run — new items to sync (depth=$DEPTH):"
  echo ""
  rsync -avn --itemize-changes --ignore-existing $EXCLUDES "$SRC" "$DST" \
    | grep -E '^[>c]' \
    | cut -d'/' -f1-"$DEPTH" \
    | sort -u
  echo ""
  echo "Run with --apply to sync."
fi
