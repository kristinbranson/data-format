# Evaluate AI-generated code

Evaluate whether decisions another agentic AI system made are consistent with its instructions. 

**File paths**:
TASKDIR = `/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/harbor-tasks/sosa2024`
JOBDIR = `/home/bransonk@hhmi.org/harbor-tasks/data-format/jobs/claude/2026-02-26__14-00-02/sosa2024__Ams2RP5`
MANUALDIR = `/groups/branson/home/bransonk/behavioranalysis/code/ScienceBenchmark/data-format/manual/sosa2024`

**Agentic AI Inputs**:
- Instructions: `TASKDIR/instruction.md`
- Reference code, text, and data are in `TASKDIR/environment` and described in `TASKDIR/instruction.md`

**Agentic AI Outputs**:
- Summary of the decisions the AI made is in `TASKDIR/tests/DECISIONS.md`. 
- The code the AI created is in `JOBDIR/verifier/snapshot`
  snapshot/
  │                                                                                                                
  ├── CONVERSION_NOTES.md                    # Agent"s documentation of conversion decisions,  │                                          # sanity checks, and validation results. 
  │
  ├── convert_data.py                        # Agent"s conversion script. 
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
- Human-generated descriptions of the decisions are in `MANUALDIR/DECISIONS.md`. 

**Step 1**. The AI's goal was to load, process, and reformat the data from a neuroscience paper into a specified structure suitable for downstream analysis, using the **SAME** processing described in the provided reference paper and code. 
  - Read through the `instruction.md` to understand the task. 
  - Read through `TASKDIR/tests/DECISIONS.md` to understand the AI's decisions.
  - Read through `MANUALDIR/DECISIONS.md` to understand the human's decisions. 

**Step 2**. Create the file `llm_judge_eval.json` with the following structure:
```json
{
    "1-a": {
        "question": "How are **all the data** for all subjects, sessions, and trials loaded in?",
        "decision_correctness": "<category>",
        "decision_correcness_justificaton": "<text>",
        "code_correctness": "<category>",
        "code_correctness_justification": "<text>"
    },
    "1-b": {
        ...
    }
    ...
}
```

**Step 3**. For each decision point, you must assess:

`"decision_correctness"`: Did the AI make a decision consistent with its instructions? Rate the decision with one of the following categories:
`"MATCH"`: AI's decision **matches** the human decision
`"BETTER"`: AI's decision is **better** than the human decision
`"OK"`: AI's decision does not match the human decision, but it is **equally as justified** as the human decision. 
`"CONCERNING"`: AI's decision is not technically wrong given ambiguity in the instructions, but it is a concerning choice that should be checked by a human. 
`"INCORRECT"`: AI's decision is **incorrect**.
In the field `"decision_correctness_justification"`, justify your rating. 

`"code_correctness"`: Does the code correctly implement its decision? Rate code correctness with one of the following categories:
`"CORRECT"`: AI code matches its decision
`"INCORRECT"`: AI code does **not** match its decision
