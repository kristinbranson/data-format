1. Copy -r `data-format/template-harbor-task` to `data-format/harbor-tasks/<taskname>`
2. Meld `data-format/prompts/harbor_instructions_v4.md` with `data-format/prompts/<taskname>_prompt_v3.md` to create `data-format/prompts/<taskname>_prompt_v4.md`
3. Copy `data-format/prompts/<taskname>_prompt_v4.md` to `data-format/harbor-tasks/<taskname>/instruction.md`
4. Copy references into `data-format/harbor-tasks/<taskname>/environment`:
  - `data-format/auto/<taskname>/paper.pdf`
  - `data-format/auto/<taskname>/methods.txt`
  - `data-format/auto/<taskname>/code`
5. Modify `data-format/harbor-tasks/<taskname>/environment/docker-compose.yaml` to point to the location of the data for this task
6. Copy manual solution from `data-format/manual/<taskname>/convert_data.py` to `data-format/harbor-tasks/<taskname>/solution`
7. Modify `data-format/harbor-tasks/<taskname>/solution/solve.sh` to include commands tailored to this task
7. Tailor a version of `data-format/harbor-tasks/sosa2024/tests/decisions_instructions.md` for this task, put in `data-format/harbor-tasks/<taskname>/tests/decisions_instructions.md`
8.
```bash
cd data-format/harbor-tasks/<taskname>/tests
cp ../instruction.md instruction_reference.md
cp ../solution/convert_data.py reference_convert_data.py
```
9. Follow instructions in `decisions_instructions.md` to create `data-format/harbor-tasks/<taskname>/tests/reference_DECISIONS.md`
10. Generate reference stats by running `data-format/harbor-scripts/generate_reference_stats.sh <taskname>`