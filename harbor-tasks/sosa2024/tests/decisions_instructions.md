# Document AI-generated code decisions

Document the decisions of another agentic AI system for a rubric of decision points.

**File paths**:
TASKDIR = `/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks/sosa2024`
JOBDIR = `/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs/claude/2026-02-26__14-00-02/sosa2024__Ams2RP5`
MANUALDIR = `/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/manual/sosa2024`

**Agentic AI Inputs**:
- Instructions: `TASKDIR/instruction.md`
- Reference code, text, and data are in `TASKDIR/environment` and described in `TASKDIR/instruction.md`

**Agentic AI Outputs**:
- The code the AI created is in `JOBDIR/verifier/snapshot`
  snapshot/
  │                                                                                                                
  ├── CONVERSION_NOTES.md                    # Agent's documentation of conversion decisions,  │                                          # sanity checks, and validation results. 
  │
  ├── convert_data.py                        # Agent's conversion script. 
  │
  ├── converted_data.pkl                     # Full converted dataset in target format.
  │                                          # Contains neural, input, output, metadata.
  │
  ├── README.md                              # User-facing documentation.
  │
  ├── conversion_full_out.txt                # stdout from full conversion run.
  │
  ├── verification_full_out.txt              # stdout from `train_decoder.py --verify-only`
  │                                          # on full data.
  │
  ├── train_decoder_full_out.txt             # stdout from full decoder training.

- The AI's process is recorded in the directory `JOBDIR/agent`.  Relevant files include:
  agent/
  ├── claude-code.txt                    # Stream-JSON trajectory log (341 lines, 2.2MB)
  │                                      # One JSON object per line: tool_use events (Read, Write,
  │                                      # Edit, Bash, Grep, etc.), assistant messages, system init,
  │                                      # and final result. PRIMARY SOURCE for reconstructing what
  │                                      # the agent did.
  └── sessions/                          # Claude Code internal session state
      ├── .claude.json                   #   Session config: tool usage counts, OAuth account info,
      │                                  #   timestamps
      └── projects/-app/
          ├── <session-id>.jsonl         #   FULL CONVERSATION TRANSCRIPT (255 lines, 1.8MB)
          │                              #   Each line is a JSON object with role (user/assistant),
          │                              #   content (text + tool_use + tool_result blocks).
          │                              #   This is the richest source for reconstruction.
          ├── <session-id>/
          │   ├── subagents/             #   Transcripts from Task tool subagents
          │   │   ├── agent-*.jsonl      #   3 subagent transcripts (18-90 lines each)
          │   └── tool-results/          #   Cached large tool results (39-51KB each)
          │       ├── b1312x90z.txt      #   Truncated tool outputs stored by ID
          │       ├── ...


**Human Solution**:
- The human-generated solution code is in `MANUALDIR/convert_data.py`
- Human-generated answers to the questions below are in `MANUALDIR/DECISIONS.md`. You may use these answers to understand **how** to answer the questions below. 

**Step 1**. The AI's goal was to load, process, and reformat the data from a neuroscience paper into a specified structure suitable for downstream analysis, using the **SAME** processing described in the provided reference paper and code. Read through the `instruction.md` to understand the task. 

**Step 2**. Create the file `DECISIONS.md` with the template shown at the end of this document. 

**Step 3**. Answer the following questions about the AI-generated solution in `DECISIONS.md`. For each question:
i. Summarize the relevant code or decisions.
ii. Provide code snippets from `convert_data.py`.
iii. Summarize the agentic AI's justification for its decisions. 

1-a.  How are **all the data** for all subjects, sessions, and trials loaded in?

1-b. How are the data split into subjects (mice)?

1-c. How are the data split into sessions? 

1-d. How are the data split into trials? 

1-e. How are trials filtered based on quality controls? 

2-a. What variables in the raw data is the `neural` data derived from? 

2-b. How is the `neural` data processed? 

2-c. How is the `neural` data filtered based on quality controls?

2-d. How is the per-trial `neural` data aligned to the event described in the `instructions`? 

2-e. How is the per-trial `neural` data aligned to the event described in the `instructions`? 

3-a. What variables in the raw data is `input` *Time from start of trial in seconds* derived from? 

3-b. What processing is involved in computing `input` *Time from start of trial in seconds*?

3-c. How is the `input` *Time from start of trial in seconds* aligned with the neural data? 

4-a. What variables in the raw data is `input` *Environment type* derived from? 

4-b. What processing is involved in computing `input` *Environment type*?

5-a. What variables in the raw data is `input` *Trial number* derived from?

5-b. What processing is involved in computing `input` *Trial number*?

6-a. What variables in the raw data is `input` *Previous trial outcome* derived from?

6-b. What processing is involved in computing `input` *Previous trial outcome*?

7-a. What variables in the raw data is `output` *Distance to reward zone* derived from?

7-b. What processing is involved in computing `output` *Distance to reward zone*?

7-c. How is `output` *Distance to reward zone* thresholded into categories?

7-d. How is `output` *Distance to reward zone* aligned with the neural data?

8-a. What variables in the raw data is `output` *Absolute position* derived from?

8-b. What processing is involved in computing `output` *Absolute position*?

8-c. How is `output` *Absolute position* thresholded into categories?

8-d. How is `output` *Absolute position* aligned with the neural data?

9-a. What variables in the raw data is `output` *Lick* derived from?

9-b. What processing is involved in computing `output` *Lick*?

9-c. How is `output` *Lick* aligned with the neural data?

10-a. What variables in the raw data is `output` *Reward zone location* derived from?

10-b. What processing is involved in computing `output` *Reward zone location*?

11-a. What variables in the raw data is `output` *Reward outcome* derived from?

11-b. What processing is involved in computing `output` *Reward outcome*?

12. How are minor mistakes in the data, e.g. missing data, handled?

13-a. What are the most time-consuming steps of the code?

13-b. What loops in the code could have been vectorized to improve efficiency?

13-c. What processing does the code repeat multiple times?

13-d. What unnecessary processing does the code do that is discarded in downstream analyses?


## DECISONS.md Template

**Create this file IMMEDIATELY in Step 2. Follow this template exactly:**

```markdown
# Decisions

## 1-a. How are **all the data** for all subjects, sessions, and trials loaded in?

i. <Decisions>

ii. <Code snippets>

iii. <Justification>

## 1-b. How are the data split into subjects? 

i. <Decisions>

ii. <Code snippets>

iii. <Justification>

...

## 4-b. What processing is involved in computing `input` *Environment type*?

i. <Decisions>

ii. <Code snippets>

iii. <Justification>
```
