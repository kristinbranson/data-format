#!/bin/bash
#
# Sync job results from local jobs dir to the repo's harbor-jobs/ directory.
#
# Usage:
#   ./sync_jobs.sh              # dry-run: show new files that would be synced
#   ./sync_jobs.sh --apply      # sync new files only
#   ./sync_jobs.sh --update     # dry-run: show new + updated files
#   ./sync_jobs.sh --update --apply  # sync new + updated files
#   ./sync_jobs.sh --depth N    # limit output to N directory levels (default: 4)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$HOME/harbor-tasks/data-format/jobs/"
DST="$(cd "$SCRIPT_DIR/.." && pwd)/harbor-jobs/"

APPLY=false
UPDATE=false
DEPTH=4

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)  APPLY=true; shift ;;
    --update) UPDATE=true; shift ;;
    --depth)  DEPTH="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--apply] [--update] [--depth N]"
      echo "  --apply   Actually sync (default is dry-run)"
      echo "  --update  Also sync files that are newer in source (default: new files only)"
      echo "  --depth N Limit output to N directory levels (default: 4)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"; exit 1 ;;
  esac
done

EXCLUDES="--exclude=raw/ --exclude=debug/ --exclude=*/oracle/"

if [ "$UPDATE" = true ]; then
  SYNC_FLAG="--update"
  MODE="new + updated"
else
  SYNC_FLAG="--ignore-existing"
  MODE="new only"
fi

if [ "$APPLY" = true ]; then
  echo "Syncing ($MODE)..."
  rsync -av $SYNC_FLAG $EXCLUDES "$SRC" "$DST"
else
  echo "Dry run — $MODE items to sync (depth=$DEPTH):"
  echo ""
  rsync -avn --itemize-changes $SYNC_FLAG $EXCLUDES "$SRC" "$DST" \
    | grep -E '^[>c]' \
    | cut -d'/' -f1-"$DEPTH" \
    | sort -u
  echo ""
  echo "Run with --apply to sync."
fi
