# Evaluation Runbook

Reproducible playbook for evaluating LLM/code-agent output that reformats complex biology datasets. A fresh Claude agent reading this file should be able to (a) understand the project, (b) launch per-trial subagents that produce extraction files, and (c) drive the interactive rating loop with a human evaluator.

---

## 1. Project context

We ran two code agents — `claude-code` and `codex` — three times each on each of 8 biology datasets, asking them to write a `convert_data.py` that reformats raw data into a decoder-friendly schema. We are now evaluating the resulting code.

**Datasets (8 total)**
- With reference solution under `manual/<dataset>/`: `allen2p`, `lee2025`, `majnik2025`, `sosa2024`
- Without reference: `hasnain2024`, `map`, `mouseland`, `zhang2025`

**On-disk layout**
- Working directory: `/groups/zhang/home/zhangl5/Data-Format/evaluation/`
- Trial paths: `evaluation/harbor-jobs/<dataset>/<agent_folder>/<timestamp>__<HH-MM-SS>_trial{1,2,3}/verifier/snapshot/`
- Per snapshot: `convert_data.py`, `CONVERSION_NOTES.md`, `README.md`, plus run outputs (`conversion_full_out.txt`, `verification_full_out.txt`) at snapshot top-level OR inside `snapshot/cache/`.
- Reference solutions (4 datasets): `/groups/zhang/home/zhangl5/Data-Format/manual/<dataset>/DECISIONS.md`

**Quirks**
- The "claude" agent folder is named **`claude-code/`** for `allen2p`, `mouseland`, `zhang2025`, but **`claude/`** for `hasnain2024`, `lee2025`, `majnik2025`, `sosa2024`. Always normalize the label to `claude-code` in our eval files.
- Skip any folder matching `*_badtrial*` (a re-run replaced it).
- Skip the `oracle/` folder entirely (not part of the eval).
- Trial timestamp prefixes vary across agents within the same dataset, so always glob `*_trial{1,2,3}` rather than hardcoding the timestamp.

---

## 2. Evaluation rubric

The reference `DECISIONS.md` defines the question list — a structured Q&A about the conversion pipeline. Each numbered question (e.g. `1-a`, `1-b`, ..., `9-e`) has three sub-parts in the reference:
- **i.** prose answer
- **ii.** code excerpt
- **iii.** reasoning

Question outline (from the allen2p reference; per-dataset count varies in sections 3+):
- **1.** Data structure — loading, subjects, sessions, trials, QC filtering
- **2.** Neural data — source, processing, QC, temporal binning, per-trial alignment
- **3–7.** Per-output variables (e.g. running speed, pupil, image identity, image change, trial outcome) — source, processing, alignment
- **8.** Error / missing-data handling
- **9.** Performance — slowest steps, vectorization, repeated work, memory

**Rating scale (user assigns):** `better | match | ok | concerning | incorrect | missing` — comparison is against the reference under `manual/<dataset>/DECISIONS.md`.

---

## 3. Workflow overview

Per dataset (start with the 4 that have references):

1. **Folder setup.** Ensure `evaluation/eval/<dataset>/` exists.
2. **Spawn 6 per-trial subagents** (one per trial: 3 claude-code + 3 codex). Each writes a per-trial extraction file `evaluation/eval/<dataset>/<agent>_trial<N>.md` containing every question, with neutral notes/code excerpts and blank `Rating`/`Note` placeholders. Subagent prompt template in §4.
3. **Interactive Q-by-Q rating in main chat.** For each question: pull that question's section from each of the 6 trial files, shuffle to anonymous labels (Sample A–F), present each with notes excerpt + code excerpt + neutral 1–3 sentence "what this does", user assigns rating + note, then reveal the A–F → (agent, trial) mapping. Ratings are written back into the per-trial files (replacing the blank placeholders) before moving on.

**Division of labor:** Claude assembles evidence and shuffles. The user assigns ratings and writes notes. Don't pre-fill ratings — that defeats the purpose.

---

## 4. Per-trial subagent prompt (TEMPLATE)

Spawn one `general-purpose` background subagent per trial. Substitute these placeholders:
- `<DATASET>` — e.g. `allen2p`
- `<AGENT_FOLDER>` — `claude-code` or `claude` (depending on dataset; see §1 quirks)
- `<AGENT_LABEL>` — always normalized to `claude-code` or `codex` in the OUTPUT
- `<N>` — `1`, `2`, or `3`

```
You're building one trial's evaluation file — pure neutral extraction, no rating/judging/comparison. The human evaluator will rate later.

## Inputs

- Reference DECISIONS.md (for the question list ONLY — do NOT include reference answers in your output): /groups/zhang/home/zhangl5/Data-Format/manual/<DATASET>/DECISIONS.md
- This trial's snapshot — discover via glob: /groups/zhang/home/zhangl5/Data-Format/evaluation/harbor-jobs/<DATASET>/<AGENT_FOLDER>/*_trial<N>/verifier/snapshot/
- Snapshot has convert_data.py, CONVERSION_NOTES.md, README.md. Conversion output txt files (conversion_full_out.txt, verification_full_out.txt) may be at snapshot top-level OR snapshot/cache/ — check both, especially for Q 9-a about timing.

## Output

Write to: /groups/zhang/home/zhangl5/Data-Format/evaluation/eval/<DATASET>/<AGENT_LABEL>_trial<N>.md

Folder ALREADY EXISTS. DO NOT mkdir.

## CRITICAL — Write incrementally

1. Read reference DECISIONS.md to extract the ordered question list (e.g. 1-a, 1-b, ..., 9-e). Copy question texts verbatim. Do NOT include reference answers (i/ii/iii) in your output.
2. Read the trial's convert_data.py and CONVERSION_NOTES.md (and README.md if useful) ONCE.
3. Use ONE Write call to create the file with: header + trial path line + Q 1-a section + trailing `---`.
4. Use ONE Edit call PER REMAINING QUESTION to append it before the final `---`. Replace the trailing `---` with `<new question section>\n\n---`.
5. Each Edit is small. Do NOT re-Write the whole file. Do NOT batch multiple questions into one Edit.

(Why incremental: large single-shot Writes were failing silently in the background-agent UX. Per-question Edit appends are tiny and reliable.)

## File format

# <DATASET> — <AGENT_LABEL> / trial<N>

Trial path: `<actual *_trial<N> path you discovered>`

---

## Q 1-a. <question text copied verbatim from reference>

**Notes excerpt** (CONVERSION_NOTES.md / README.md):
> [relevant lines or "(none)"; cite file path:line range]

**Code** (convert_data.py:<line_start>-<line_end>):
```python
[tight 5–30 line excerpt; multiple short snippets fine]
```

**What this does:** [1–3 sentence neutral description. NO judgments, NO comparisons, NO ratings.]

**Rating:** _(to be filled by evaluator)_

**Note:** _(to be filled by evaluator)_

---

(repeat the question section for every question in the reference, in order)

## Rules

- Pure neutral extraction. Never rate, judge, or compare. Don't mention or contrast with the reference — describe what THIS trial does.
- Code excerpts tight (~5–30 lines). Cite line ranges. Don't dump whole files.
- If this trial doesn't address a question: Notes excerpt: (none), Code: (no relevant code found), one-line "What this does" noting the absence.
- Preserve question numbering exactly.
- Always include the empty Rating/Note placeholders for every question.

When done, briefly report (under 100 words): questions covered, the trial path used, final file size in KB.
```

---

## 5. Launching the 6 subagents (per dataset)

Launch all 6 in parallel as background subagents:

| # | description | `<AGENT_FOLDER>` | `<AGENT_LABEL>` | `<N>` |
|---|---|---|---|---|
| 1 | `<dataset> claude-code trial1` | per dataset (see §1) | `claude-code` | `1` |
| 2 | `<dataset> claude-code trial2` | per dataset | `claude-code` | `2` |
| 3 | `<dataset> claude-code trial3` | per dataset | `claude-code` | `3` |
| 4 | `<dataset> codex trial1` | `codex` | `codex` | `1` |
| 5 | `<dataset> codex trial2` | `codex` | `codex` | `2` |
| 6 | `<dataset> codex trial3` | `codex` | `codex` | `3` |

Each subagent should produce a file ~30–40 KB covering all questions in the reference. Wait for all 6 completion notifications before starting interactive rating.

---

## 6. Interactive rating loop (after subagents complete)

For each question in order (1-a, 1-b, ..., 9-e):

1. Extract that question's section from all 6 per-trial files.
2. Pick a fresh random shuffle to label them Sample A–F (don't reuse the same shuffle across questions).
3. Present in chat:
   - The question text + a one-line summary of the reference's approach (so the user has the comparison anchor).
   - For each Sample A–F: notes excerpt + code excerpt + 1–3 sentence "what this does". Do NOT reveal which agent/trial.
4. Wait for user's ratings (e.g. `A: match, B: concerning — uses wrong column, C: ok, ...`).
5. Reveal the A–F → (agent, trial) mapping.
6. Write each rating + note back to the corresponding per-trial file, replacing the `**Rating:** _(to be filled by evaluator)_` and `**Note:** _(to be filled by evaluator)_` placeholders for that question.
7. Move to next question.

---

## 7. Permissions setup (one-time per machine)

`evaluation/.claude/settings.local.json` should grant Read/Write/Edit on `/groups/zhang/home/zhangl5/Data-Format/**` and add it to `additionalDirectories`, so subagents can reach `manual/` and `harbor-jobs/` without permission prompts. Without this, background subagents stall on permission prompts.

---

## 8. After the 4 reference-backed datasets

For `hasnain2024`, `map`, `mouseland`, `zhang2025` (no reference solution), this workflow needs adaptation — TBD whether to rate on absolute correctness, or skip rating entirely and just collect descriptions.
