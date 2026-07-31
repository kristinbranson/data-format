# Setting up a new harbor task

1. Copy -r `data-format/template-harbor-task` to `data-format/harbor-tasks/<taskname>`
2. Meld`data-format/prompts/harbor_instructions_v4.md` with either:
- `data-format/prompts/<taskname>_prompt_v3.md`
- OR `data-format/prompt_v4/<taskname>_prompt_v4.md`
to create `data-format/prompt_v4/<taskname>_prompt_v4.md`
3. Copy `data-format/prompt_v4/<taskname>_prompt_v4.md` to `data-format/harbor-tasks/<taskname>/instruction.md`
4. Copy references into `data-format/harbor-tasks/<taskname>/environment`:
  - `data-format/auto/<taskname>/paper.pdf`
  - `data-format/auto/<taskname>/methods.txt`
  - `data-format/auto/<taskname>/code`
5. Modify `data-format/harbor-tasks/<taskname>/environment/docker-compose.yaml` to point to the location of the data for this task
6. Copy manual solution from `data-format/manual/<taskname>/convert_data.py` to `data-format/harbor-tasks/<taskname>/solution`
7. Modify `data-format/harbor-tasks/<taskname>/solution/solve.sh` to include commands tailored to this task
8. Tailor a version of `data-format/harbor-tasks/sosa2024/tests/judge_instructions.md` for this task, put in `data-format/harbor-tasks/<taskname>/tests/judge_instructions.md`
9.
```bash
cd data-format/harbor-tasks/<taskname>/tests
cp ../instruction.md instruction_reference.md
cp ../solution/convert_data.py reference_convert_data.py
```
10. Ask Claude: Follow instructions in `decisions_instructions.md` to create `reference_DECISIONS.md` based on ../solution/convert_data.py
11. Generate reference stats by running `data-format/harbor-scripts/generate_reference_stats.sh <taskname>`

---

# Converting an unsupervised task to supervised

Worked example below: `map`, converted from `manual/chen2024/` on 2026-07-30.

## 1. Make the manual solution runnable by solve.sh

Harbor mounts `solution/` at **`/solution`** in the container
(`harbor-kai/src/harbor/models/trial/paths.py:32`) while the dataset is mounted
read-only at `/app/data`, so `solve.sh` calls

    python3 /solution/convert_data.py --datadir /app/data <outfile>

The manual script must therefore accept `--datadir`. If it hardcodes its data location
(chen2024 used `DATA_DIR = <script dir>/data`, which would resolve to `/solution/data`),
add the flag with the old value as the default so running it by hand is unchanged:

    ap.add_argument('--datadir', default=DATA_DIR, help='directory holding the raw files')

Edit `manual/<name>/convert_data.py`, not the copies — see step 2. Verify with the same
argument shape `solve.sh` uses:

    python manual/<name>/convert_data.py --sample --datadir data/<task> /tmp/x.pkl

and check the per-session counts against `manual/<name>/conversion_full_out.txt`.

## 2. Copy the human solution into the task

Three byte-identical copies is the invariant; every supervised task satisfies it. 

    cp manual/<name>/convert_data.py harbor-tasks/<task>/solution/convert_data.py
    cp manual/<name>/convert_data.py harbor-tasks/<task>/tests/reference_convert_data.py
    cp manual/<name>/DECISIONS.md    harbor-tasks/<task>/tests/reference_DECISIONS.md

Do this for <task> and <task>_minimal.

## 3. Split the judge instructions into a supervised/unsupervised pair

Supervised tasks carry both unsupervised and supervised judge instructions

```bash
cp harbor-tasks/<task>/tests/judge_instructions.md \
       harbor-tasks/<task>/tests/judge_instructions_unsupervised.md
```

meld `judge_instructions.md` with the a supervised judge instruction file to make them the same

```bash
meld harbor-tasks/<task>/tests/judge_instructions.md \
     harbor-tasks/sosa2024/tests/judge_instructions.md
```

Copy these to harbor-tasks/<task>_minimal/tests/

```bash
cp harbor-tasks/<task>/tests/judge_instructions.md \
       harbor-tasks/<task>_minimal/tests/judge_instructions.md
cp harbor-tasks/<task>/tests/judge_instructions_unsupervised.md \
       harbor-tasks/<task>_minimal/tests/judge_instructions_unsupervised.md
```

## The six hunks modified for converting from unsupervised to supervised:

1. Add to *Available Files*, after the trajectory paragraph:

       **Human Reference Solution**:
       - Human-generated solution code: `/tests/reference_convert_data.py`
       - Human-generated decision descriptions: `/tests/reference_DECISIONS.md`

2. Append to the "two output files" sentence: "Write these files to the directory you
   are currently in, not to `/app/` or any other directory."
3. Add to **Step 1**, before the bullet that reads the AI's code:

       - Read `/tests/reference_DECISIONS.md` to understand the human reference decisions.
       - Read `/tests/reference_convert_data.py` to understand the human reference code.

4. In Step 3, replace the "No human reference solution is available for this task…"
   sentence with "Compare the AI's decisions (from Step 2) against the human reference
   solution (`/tests/reference_DECISIONS.md` and `/tests/reference_convert_data.py`)."
5. Widen the `decision_correctness` rubric from 3 categories to 5, adding:

       - `"BETTER"`: AI's decision is **better** than the human decision
       - `"OK"`: AI's decision does not match the human decision, but it is **equally as justified**

   and rewording `"MATCH"` to "matches the human decision".
   `tests/compute_reward.py` already scores all five (`MATCH`/`BETTER` 1.0, `OK` 0.75,
   `CONCERNING` 0.25, `INCORRECT` 0.0), so no scoring code changes.

## 4. Generate the reference stats

```bash
harbor-scripts/generate_reference_stats.sh <task>
```

Runs the oracle arm with `--disable-verification`; `solve.sh` calls
`train_decoder.py --stats-json`. Output lands at

    jobs/oracle/<timestamp>/<task>__<hash>/verifier/snapshot/stats_full.json

Check that snapshot's `verification_full_out.txt` reports no errors and
`train_decoder_full_out.txt` is above chance on every output before trusting it.

## 5. Install the stats

```bash
cp <harbor-jobs>/oracle/<timestamp>/<task>_<hash>/verifier/snapshot/stats_full.json harbor-tasks/<task>/tests/reference_stats_full.json
cp <harbor-jobs>/oracle/<timestamp>/<task>_<hash>/verifier/snapshot/stats_full.json harbor-tasks/<task>_minimal/tests/reference_stats_full.json
```

Compare its key set against an existing one: `data_summary`, per-output
`validation_balanced_accuracy`, `chance_uniform`, `chance_majority`, `rng_state`.

## 6. 

Update the metrics.json:

```bash
# dry-run
python harbor-scripts/rerun_metrics.py --all --task <task> --task <task>_minimal --reference-only
# overwrite
python harbor-scripts/rerun_metrics.py --all --task <task> --task <task>_minimal --reference-only --write --force
```
