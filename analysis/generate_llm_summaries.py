#!/usr/bin/env python3
"""
Generate one-sentence, LLM-written summaries for each step in a conversation JSONL.

This script aligns step numbering with `agent_reports.py` by reusing its
load/build logic so that `convo.summaries.json` lines up with `all_data.json`.

Usage:
  python generate_llm_summaries.py --conversation MAP \
      --model gpt-4o-mini \
      --output-format txt \
      --max-steps 20

Notes:
  - Requires OPENAI_API_KEY in the environment.
  - Reads all *.jsonl files in the conversation directory.
  - Writes numbered summaries to convo.summaries.txt (or convo.summaries.json).
  - Safe to re-run; overwrites the output file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # Deferred error until runtime

# Optional progress bar
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# Reuse agent_reports helpers to mirror step ordering used in all_data.json.
try:
    from agent_reports import load_records as ar_load_records, build_steps  # type: ignore
except ImportError:
    ar_load_records = None
    build_steps = None


def summarize_step(client: Any, model: str, step_num: int, role: str, display_content: str, tool_type: str | None) -> str:
    """Use OpenAI chat API to generate a concise, single-sentence summary."""
    flat_short = display_content if len(display_content) <= 1200 else display_content[:1200] + " ... [truncated]"
    system_prompt = (
        "You write single-sentence summaries of assistant/user/tool steps. "
        "Keep it under 35 words, include the key action or statement, and mention tool names/purpose when relevant."
    )
    tool_note = f" Tool: {tool_type}." if tool_type else ""
    user_prompt = f"Step {step_num} ({role}){tool_note}: {flat_short}"

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=80,
    )
    return resp.choices[0].message.content.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LLM summaries for conversation JSONL (aligned with all_data.json steps).")
    parser.add_argument("--conversation", required=True, help="Conversation directory name (e.g., MAP)")
    parser.add_argument("--parent-dir", default=".", help="Parent directory containing conversation folders")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model name")
    parser.add_argument("--output-format", choices=["txt", "json"], default="txt", help="Output format")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between API calls (seconds)")
    parser.add_argument("--max-steps", type=int, default=None, help="Limit number of steps to summarize (for debugging)")
    parser.add_argument("--skip-if-existing", action="store_true", help="Skip processing if convo.summaries.json/txt already exists")
    parser.add_argument("--resume-if-existing", action="store_true", help="Resume from existing summaries instead of overwriting")
    args = parser.parse_args()

    if OpenAI is None:
        sys.stderr.write("openai package is not installed. pip install openai\n")
        sys.exit(1)
    if ar_load_records is None or build_steps is None:
        sys.stderr.write("agent_reports.py not found; cannot mirror step numbering\n")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        sys.stderr.write("OPENAI_API_KEY not set\n")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    convo_dir = Path(args.parent_dir) / args.conversation
    if not convo_dir.exists():
        sys.stderr.write(f"Conversation directory not found: {convo_dir}\n")
        sys.exit(1)

    out_path = convo_dir / ("convo.summaries.json" if args.output_format == "json" else "convo.summaries.txt")
    if args.skip_if_existing and out_path.exists():
        print(f"Skipping {convo_dir} because {out_path.name} already exists.")
        return

    # Load existing summaries if present so we can resume.
    summaries: Dict[str, str] = {}
    if args.resume_if_existing and out_path.exists():
        try:
            if args.output_format == "json":
                data = json.loads(out_path.read_text())
                if isinstance(data, dict):
                    summaries = {str(k): str(v) for k, v in data.items()}
            else:
                for line in out_path.read_text().splitlines():
                    if "." in line:
                        prefix, rest = line.split(".", 1)
                        if prefix.strip().isdigit():
                            summaries[prefix.strip()] = rest.strip()
        except Exception:
            summaries = {}

    records, warnings = ar_load_records(convo_dir)
    if not records:
        sys.stderr.write("No JSONL records found.\n")
        sys.exit(1)
    for warn in warnings:
        sys.stderr.write(f"Warning: {warn}\n")

    # Build steps exactly as agent_reports does so numbering matches all_data.json.
    steps, *_ = build_steps(records, warnings, summary_map={})

    max_steps = args.max_steps or len(steps)
    steps_to_process = steps[:max_steps]

    iterator = steps_to_process
    if tqdm is not None:
        iterator = tqdm(steps_to_process, desc="Summarizing steps", unit="step")

    for step in iterator:
        if str(step.step_number) in summaries:
            continue  # already summarized
        summary = summarize_step(
            client,
            args.model,
            step.step_number,
            step.role,
            step.display_content or "",
            step.tool_type,
        )
        summaries[str(step.step_number)] = summary
        time.sleep(args.delay)

        # Persist after every step so partial progress is saved.
        if args.output_format == "json":
            out_path.write_text(json.dumps(summaries, indent=2))
        else:
            lines = [f"{step_num}. {summaries[step_num]}" for step_num in sorted(summaries, key=lambda x: int(x))]
            out_path.write_text("\n".join(lines) + "\n")

    print(f"Wrote {len(summaries)} summaries to {out_path}")


if __name__ == "__main__":
    main()
