#!/bin/bash
#
# Re-run both LLM judges over every scored trial, in an order that builds each task's
# image only once.
#
# Needed after any change to a task's tests/judge_instructions.md or
# tests/reference_DECISIONS.md: rerun_verifier.sh bind-mounts tests/ from the working
# tree, so the judges read the current files, but the verdicts already recorded in each
# trial were produced against the old ones.
#
# Usage:
#   ./rerun_judges.sh [OPTIONS]
#
# Options:
#   --parallel N    Trials in flight at once (default: 5). Each trial runs its two judges
#                   sequentially, so this is also the peak number of concurrent LLM
#                   sessions -- shared between Anthropic and OpenAI, not N of each.
#   --unsupervised  Run the unsupervised judges instead, via run_unsupervised_judges.sh.
#                   Those read judge_instructions_unsupervised.md, never see the reference
#                   solution, and write llm_judge_<model>_unsupervised_* keys plus a
#                   judge_unsupervised/ directory, so they do not disturb the supervised
#                   verdicts. Logs go to their own directory and summary file.
#   --dry-run, -n   Print the ordered trial list and exit without running anything.
#
# Which trials run:
#   Those named _trial1 through _trial4. The `_trial[1234]` anchor also drops the two
#   `_badtrial3` directories, since those end in `badtrial3` rather than `_trial3`. The
#   debug task and the oracle arms are excluded: debug's reference_DECISIONS.md is a
#   stale sosa2024 copy, and the oracle trials are the reference solution being judged
#   against itself.
#
# Why the ordering:
#   rerun_verifier.sh builds hb__<task>-reverify when it is missing. Plain alphabetical
#   order groups a task's trials together, so with --parallel 5 the first five trials of
#   a task all race to build the same tag -- five full pip layers where one would do.
#   Interleaving round-robin by task puts 16 distinct tasks in the first 16 slots, so
#   every image is built exactly once and everything after it hits cache.
#
# Why --apikeys:
#   The default credential path uses the OAuth files under $HOME, which draw on the same
#   subscription window as an interactive Claude Code or Codex session. Roughly 290
#   agentic judge runs would compete with your own usage and can exhaust it mid-run.
#   --apikeys uses ANTHROPIC_API_KEY and OPENAI_API_KEY from <repo>/.env instead.
#
# Why --podman:
#   The trials live under /groups, which is root-squashed over NFS. Docker runs the
#   container as real root and every write the judge makes is denied; rootless podman
#   maps container-root to the invoking user.
#
# Failures are quiet by design: rerun_verifier.sh ends both the judge call and
# compute_reward.py with `|| true`, so a rate-limited judge leaves an empty judge
# directory and a null reward while the trial still reports ok. Check afterwards with
#   python3 harbor-scripts/check_trial_health.py
# and re-judge just the affected half with --claude-judge-only / --codex-judge-only.
#
# Everything written lives in the harbor-jobs git repo, so `git -C harbor-jobs checkout .`
# undoes a bad run completely.

set -euo pipefail

PARALLEL=5
DRY_RUN=false
UNSUPERVISED=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --parallel)     PARALLEL="$2"; shift 2 ;;
        --dry-run|-n)   DRY_RUN=true; shift ;;
        --unsupervised) UNSUPERVISED=true; shift ;;
        --help|-h)      sed -n '2,58p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# -P, not plain pwd: this repo is reached through a symlinked $HOME path on the
# workstation, and rerun_verifier.sh bakes the path it is given into a container mount.
# The harbor-jobs glob and the rerun_verifier.sh call below are both repo-relative, so
# this has to be the repo root, one level up from harbor-scripts/.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)"
cd "$REPO_DIR"

# The two arms write to different keys in metrics.json and different judge directories,
# so they never collide -- but their logs would, hence the separate names.
if [ "$UNSUPERVISED" = true ]; then
    JUDGE_CMD="./harbor-scripts/run_unsupervised_judges.sh --podman --apikeys"
    LOG_DIR="$HOME/rerun_judge_logs_unsupervised"
    SUMMARY_PREFIX="rerun_judges_unsupervised_summary"
else
    JUDGE_CMD="./harbor-scripts/rerun_verifier.sh --judges-only --podman --apikeys"
    LOG_DIR="$HOME/rerun_judge_logs"
    SUMMARY_PREFIX="rerun_judges_summary"
fi
# Timestamped: tee truncates, and a rerun should not erase the record of the previous one.
SUMMARY_LOG="$HOME/${SUMMARY_PREFIX}_$(date +%Y%m%d_%H%M%S).log"

# Round-robin by task: number each trial within its own task, sort by that number first
# and task name second, then drop the two bookkeeping columns. Field 2 of the path is the
# task, e.g. harbor-jobs/sosa2024/claude/2026-03-10__19-44-11_trial1/.
trials=$(ls -d harbor-jobs/*/*/*_trial[1234]/ \
    | grep -v '^harbor-jobs/debug/' \
    | grep -v '/oracle/' \
    | awk -F/ '{n[$2]++; print n[$2], $2, $0}' \
    | sort -k1,1n -k2,2 \
    | awk '{print $3}')

count=$(echo "$trials" | grep -c . || true)

if [ "$DRY_RUN" = true ]; then
    echo "$trials"
    echo "--- $count trials, would run $PARALLEL at a time"
    exit 0
fi

echo "$count trials, $PARALLEL at a time"
echo "judges:         $([ "$UNSUPERVISED" = true ] && echo unsupervised || echo supervised)"
echo "per-trial logs: $LOG_DIR"
echo "summary:        $SUMMARY_LOG"
mkdir -p "$LOG_DIR"

# One log file per trial: with several running at once a shared log interleaves into
# something unreadable. The console gets one ok/FAIL line per trial instead.
echo "$trials" | xargs -P "$PARALLEL" -I{} sh -c '
    log="$1/$(echo "$2" | tr / _).log"
    $0 "$2" > "$log" 2>&1 \
        && echo "ok   $2" || echo "FAIL $2"
    ' "$JUDGE_CMD" "$LOG_DIR" {} | tee "$SUMMARY_LOG"

echo
echo "Done. Check for judges that produced nothing:"
echo "  python3 harbor-scripts/check_trial_health.py"
