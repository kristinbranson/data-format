# Document AI-generated code decisions

Document the decisions of another agentic AI system for a rubric of decision points.

**Agentic AI Inputs**:
- Instructions: `/tests/instruction_reference.md`
- Reference code, text, and data are in `/app/code/`, `/app/paper.pdf`, `/app/methods.txt`, `/app/data/`. Descriptions are available in `/tests/instruction_reference.md`

**Agentic AI Outputs**:
- The code the AI created is in `/app`
  /app/
  │
  ├── CONVERSION_NOTES.md                    # Agent"s documentation of conversion decisions,
  │                                          # sanity checks, and validation results.
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

- The AI's process is recorded in `/logs/agent/trajectory.json` (ATIF format).
  This is a JSON file with the following structure:
  ```json
  {
    "schema_version": "ATIF-v1.2",
    "session_id": "...",
    "agent": {"name": "...", "version": "...", "model_name": "..."},
    "steps": [
      {
        "step_id": 1,
        "source": "user" | "agent" | "system",
        "message": "text content",
        "reasoning_content": "agent's internal reasoning (if available)",
        "tool_calls": [{"tool_call_id": "...", "function_name": "Write", "arguments": {...}}],
        "observation": {"results": [{"content": "tool output"}]}
      },
      ...
    ],
    "final_metrics": {"total_prompt_tokens": ..., "total_completion_tokens": ..., "total_steps": ...}
  }
  ```
  Each step is a message, tool call, or tool result. Agent reasoning, code written
  (via Write/Edit tools), and shell commands (via Bash/exec tools) are all captured
  in the steps list. This is the PRIMARY SOURCE for reconstructing what the agent did.

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

2-e. What is the temporal resolution (time bin size) of the converted data? Is any temporal rebinning applied?

3-a. What variables in the raw data is `input` *Environment geometry* derived from?

3-b. What processing is involved in computing `input` *Environment geometry*?

3-c. How is the `input` *Environment geometry* aligned with the neural data? 

4-a. What variables in the raw data is `output` *Mouse position* derived from?

4-b. What processing is involved in computing `output` *Mouse position*?

4-c. How is `output` *Mouse position* thresholded into categories?

4-d. How is `output` *Mouse position* aligned with the neural data?

5-a. What is the temporal resolution (time bin size) of the converted data? Is any temporal rebinning applied?

5-b. How are the neural, input, and output data temporally aligned?

6. How are minor issues in the data (e.g., missing data, malformed entries) handled?

7-a. What are the most time-consuming steps of the code?

7-b. What loops in the code could have been vectorized to improve efficiency?

7-c. What processing does the code repeat multiple times?

7-d. What unnecessary processing does the code do that is discarded in downstream analyses?

8. How are minor mistakes in the data, e.g. missing data, handled?

9-a. What are the most time-consuming steps of the code?

9-b. What loops in the code could have been vectorized to improve efficiency?

9-c. What processing does the code repeat multiple times?

9-d. What unnecessary processing does the code do that is discarded in downstream analyses?


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

## 9-d. What unnecessary processing does the code do that is discarded in downstream analyses?

i. <Decisions>

ii. <Code snippets>

iii. <Justification>
```
