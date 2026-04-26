#!/bin/bash
#
# Sync job results between the local (HOME) jobs dir and the repo's
# harbor-jobs/ directory.
#
# Default direction is HOME -> REPO. Use --reverse for REPO -> HOME.
#
# Usage:
#   ./sync_jobs.sh                   # dry-run: HOME -> REPO, new files only
#   ./sync_jobs.sh --apply           # sync HOME -> REPO, new files only
#   ./sync_jobs.sh --update          # dry-run: HOME -> REPO, new + updated
#   ./sync_jobs.sh --update --apply  # sync HOME -> REPO, new + updated
#   ./sync_jobs.sh --reverse         # dry-run: REPO -> HOME, new files only
#   ./sync_jobs.sh --reverse --update --apply  # sync REPO -> HOME, new + updated
#   ./sync_jobs.sh --depth N         # limit output to N directory levels (default: 4)
#   ./sync_jobs.sh --metrics-only    # only sync metrics.json files (skip everything else)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="$HOME/harbor-tasks/data-format/jobs/"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/harbor-jobs/"

APPLY=false
UPDATE=false
REVERSE=false
METRICS_ONLY=false
DEPTH=4

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)        APPLY=true;        shift ;;
    --update)       UPDATE=true;       shift ;;
    --reverse)      REVERSE=true;      shift ;;
    --metrics-only) METRICS_ONLY=true; shift ;;
    --depth)        DEPTH="$2";        shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--apply] [--update] [--reverse] [--metrics-only] [--depth N]"
      echo "  --apply         Actually sync (default is dry-run)"
      echo "  --update        Also sync files that are newer in source (default: new files only)"
      echo "  --reverse       Sync REPO -> HOME instead of HOME -> REPO"
      echo "  --metrics-only  Only sync metrics.json files; ignore everything else"
      echo "  --depth N       Limit output to N directory levels (default: 4)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ "$REVERSE" = true ]; then
  SRC="$REPO_DIR"
  DST="$HOME_DIR"
  DIRECTION="REPO -> HOME"
else
  SRC="$HOME_DIR"
  DST="$REPO_DIR"
  DIRECTION="HOME -> REPO"
fi

EXCLUDES="--exclude=raw/ --exclude=debug/ --exclude=*/oracle/"
# When --metrics-only is set, restrict rsync's transfer set to metrics.json
# files only. The trailing '*/' include preserves directory traversal so
# rsync can descend into subdirs to find them; the catch-all exclude after
# drops everything that doesn't match.
FILTERS=""
SCOPE="all files"
if [ "$METRICS_ONLY" = true ]; then
  FILTERS="--include=*/ --include=metrics.json --exclude=*"
  SCOPE="metrics.json only"
fi

if [ "$UPDATE" = true ]; then
  SYNC_FLAG="--update"
  MODE="new + updated"
else
  SYNC_FLAG="--ignore-existing"
  MODE="new only"
fi

if [ "$APPLY" = true ]; then
  echo "Syncing ($DIRECTION, $MODE, $SCOPE)..."
  rsync -av $SYNC_FLAG $FILTERS $EXCLUDES "$SRC" "$DST"
else
  echo "Dry run — $DIRECTION, $MODE, $SCOPE items to sync (depth=$DEPTH):"
  echo ""
  rsync -avn --itemize-changes $SYNC_FLAG $FILTERS $EXCLUDES "$SRC" "$DST" \
    | grep -E '^[>c]' \
    | cut -d'/' -f1-"$DEPTH" \
    | sort -u
  echo ""
  echo "Run with --apply to sync."
fi
