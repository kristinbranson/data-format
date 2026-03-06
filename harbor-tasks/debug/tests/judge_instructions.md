Write the following content to the file `DECISIONS.md`:

```
# Decisions

## 1-a. How is the data generated?

i. Random data generated with numpy, seed 42.

ii. `np.random.randn(nneurons, T)`

iii. Debug task for infrastructure testing.
```

Then write the following JSON to the file `llm_judge_eval.json`:

```json
{
    "1-a": {
        "question": "How is the data generated?",
        "decision_correctness": "MATCH",
        "decision_correctness_justification": "Debug task, dummy evaluation.",
        "code_correctness": "CORRECT",
        "code_correctness_justification": "Debug task, dummy evaluation."
    }
}
```
