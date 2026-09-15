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

# 1. Replace top-level files (skip snapshot/ and judge/).
# metrics.json is MERGED instead of replaced, because --judges-only reruns only
# populate judge keys — a wholesale copy would wipe out the pytest-produced
# fields (ratios, matches, decoder accuracy, etc.) from the original run.
for f in "$NEWDIR"/*; do
    name=$(basename "$f")
    case "$name" in
        snapshot|judge) continue ;;
        metrics.json)
            echo "Merge metrics.json (base + rerun, rerun keys win on overlap)"
            if [ "$DRY_RUN" = false ]; then
                python3 - "$BASEDIR/metrics.json" "$f" <<'PY'
import json, sys
base_path, new_path = sys.argv[1], sys.argv[2]
def load(p):
    try:
        with open(p) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
merged = load(base_path)
merged.update(load(new_path))
with open(base_path, "w") as fh:
    json.dump(merged, fh, indent=2)
PY
            fi
            continue
            ;;
    esac
    if [ -f "$f" ]; then
        echo "Replace $name"
        if [ "$DRY_RUN" = false ]; then
            cp "$f" "$BASEDIR/$name"
        fi
    fi
done

# A rerun that supplies reward.json makes any inherited reward.txt stale, and stale in the
# worst way: harbor prefers reward.json, so the merged trial scores correctly while the
# file with the obvious name still shows the old run's outcome. Tasks used to write both
# (reward.txt early as a crash fallback, reward.json at the end with the average); the ones
# that now write only reward.json leave nothing to overwrite the inherited copy.
if [ -f "$NEWDIR/reward.json" ] && [ -f "$BASEDIR/reward.txt" ] && [ ! -f "$NEWDIR/reward.txt" ]; then
    echo "Remove stale reward.txt (superseded by the rerun's reward.json)"
    [ "$DRY_RUN" = false ] && rm -f "$BASEDIR/reward.txt"
fi

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
    # reward.json first, matching harbor's own precedence. reward.txt carries the outcome
    # alone and is never updated after judging, so reading it reported 0 for a trial that
    # scored 0.43 -- and after this merge it may not exist at all.
    # The pass/fail key is 'outcome_all'; 'outcome' is its name in the earliest reward.json
    # files. A missing 'process' means the judges were switched off or did not finish.
    echo "Reward: $(python3 -c "
import json, pathlib
j = pathlib.Path('$BASEDIR/reward.json'); t = pathlib.Path('$BASEDIR/reward.txt')
if j.is_file():
    d = json.loads(j.read_text())
    outcome = d.get('outcome_all', d.get('outcome'))
    per_category = d.get('outcome_mean_per_category')
    parts = [f'outcome_all={outcome:.1f}']
    if per_category is not None:
        parts.append(f'per_category={per_category:.4f}')
    parts.append(f\"process={d['process']:.4f}\" if 'process' in d
                 else 'no process score: judges off or did not finish')
    print(f\"{d['reward']:.4f} ({'; '.join(parts)})\")
elif t.is_file():
    print(f'{float(t.read_text()):.4f}  (reward.txt: outcome only)')
else:
    print('N/A')
" 2>/dev/null || echo 'N/A')"
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
