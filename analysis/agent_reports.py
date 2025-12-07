#!/usr/bin/env python3
"""
Generate conversation analytics from Claude-style JSONL logs.

This script reads one or more conversation subdirectories and produces, for each,
the required outputs described in AGENTS.md:
  - all_data.json
  - 01_intervention_summary.md
  - 02_work_summary.md
  - 03_token_usage.md
  - 04_timing.md
  - 05_file_index.json

Usage:
    python agent_reports.py <parent_dir> [--conversation SUBDIR ...]

If --conversation is omitted, every first-level subdirectory in <parent_dir> that
contains at least one .jsonl file will be processed.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ----------------------------- Data containers ----------------------------- #

@dataclass
class Record:
    raw: Dict[str, Any]
    file_path: Path
    line_no: int
    timestamp: Optional[datetime]
    timestamp_raw: Optional[str]
    file_index: int


@dataclass
class StepEntry:
    step_number: int
    role: str
    step_type: str
    content_raw: Any
    display_content: str
    summarized_content: Optional[str]
    tool_calls: List[Dict[str, Any]]
    tool_type: Optional[str]
    token_count: Optional[float]
    timestamps: Dict[str, Optional[Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


# ----------------------------- Parsing helpers ----------------------------- #

def parse_timestamp(value: Any) -> Optional[datetime]:
    """Convert various timestamp formats to timezone-aware datetime."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            return datetime.fromisoformat(text)
        except Exception:
            return None
    return None


def extract_timestamp(record: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[str]]:
    """Pull the best available timestamp from a record."""
    for key in ("timestamp", "time", "created_at", "createdAt", "ts"):
        if key in record:
            ts = parse_timestamp(record.get(key))
            if ts:
                return ts, record.get(key)
    snapshot_ts = record.get("snapshot", {}).get("timestamp")
    ts = parse_timestamp(snapshot_ts)
    if ts:
        return ts, snapshot_ts
    message_ts = record.get("message", {}).get("timestamp")
    ts = parse_timestamp(message_ts)
    if ts:
        return ts, message_ts
    return None, None


def extract_end_timestamp(record: Dict[str, Any]) -> Tuple[Optional[datetime], Optional[str]]:
    """Extract an end timestamp if present."""
    for key in ("end_timestamp", "end_time", "completed_at", "finished_at"):
        if key in record:
            ts = parse_timestamp(record.get(key))
            if ts:
                return ts, record.get(key)
    return None, None


def render_content_text(content: Any) -> str:
    """Flatten message content into a readable string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        rendered = []
        for part in content:
            if not isinstance(part, dict):
                rendered.append(str(part))
                continue
            p_type = part.get("type")
            if p_type in ("text", "input_text", "output_text", "commentary") or "text" in part:
                rendered.append(part.get("text", ""))
            elif p_type == "thinking":
                rendered.append(f"[thinking] {part.get('thinking', '')}")
            elif p_type == "tool_use":
                name = part.get("name", "unknown_tool")
                tool_input = part.get("input")
                rendered.append(f"[tool_use:{name}] input={json.dumps(tool_input, ensure_ascii=False)}")
            elif p_type == "tool_result":
                name = part.get("name", part.get("tool_use_id", "tool_result"))
                rendered.append(f"[tool_result:{name}] {json.dumps(part.get('content'), ensure_ascii=False)}")
            else:
                rendered.append(json.dumps(part, ensure_ascii=False))
        return "\n".join(rendered)
    return json.dumps(content, ensure_ascii=False)


def extract_tool_calls(content: Any) -> List[Dict[str, Any]]:
    """Extract tool use entries from message content."""
    tool_calls: List[Dict[str, Any]] = []
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "tool_use":
                tool_calls.append(
                    {
                        "id": part.get("id"),
                        "name": part.get("name"),
                        "input": part.get("input"),
                    }
                )
    return tool_calls


def extract_role(record: Dict[str, Any]) -> str:
    """Determine role with graceful fallback."""
    return (
        record.get("role")
        or record.get("payload", {}).get("role")
        or record.get("type")
        or record.get("payload", {}).get("type")
        or record.get("message", {}).get("role")
        or "unknown"
    )


def extract_content(record: Dict[str, Any]) -> Any:
    """Fetch message content from common layouts (Claude, Codex, etc.)."""
    if isinstance(record.get("message"), dict):
        msg_content = record.get("message", {}).get("content")
        if msg_content is not None:
            return msg_content
    if isinstance(record.get("payload"), dict):
        payload_content = record["payload"].get("content")
        if payload_content is not None:
            return payload_content
        if "instructions" in record["payload"]:
            return record["payload"].get("instructions")
    return record.get("content")


def has_user_text_content(content: Any) -> bool:
    """Return True if content carries user-authored text (not tool_result-only)."""
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                if part.get("type") in ("text", "input_text", "output_text", "commentary") or "text" in part:
                    return True
            elif isinstance(part, str):
                return True
    return False


def is_tool_result_only(content: Any) -> bool:
    """Detect tool_result-only payloads (no user-authored text)."""
    if isinstance(content, list) and content:
        return all(isinstance(part, dict) and part.get("type") == "tool_result" for part in content)
    return False


def is_out_of_context_restart(text: str) -> bool:
    """Heuristic to skip synthetic 'out of context' restarts from being counted as interventions."""
    lowered = text.lower()
    return "out of context" in lowered or "context reset" in lowered or "restarting context" in lowered


def extract_token_count(record: Dict[str, Any]) -> Optional[float]:
    """Compute a token count from available usage fields."""
    usage = (
        record.get("usage")
        or record.get("message", {}).get("usage")
        or record.get("payload", {}).get("usage")
    )
    if not isinstance(usage, dict):
        return None
    if "total_tokens" in usage and isinstance(usage["total_tokens"], (int, float)):
        return float(usage["total_tokens"])
    numeric_keys = [
        "input_tokens",
        "output_tokens",
        "prompt_tokens",
        "completion_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    ]
    total = 0.0
    found = False
    for key in numeric_keys:
        value = usage.get(key)
        if isinstance(value, (int, float)):
            total += float(value)
            found = True
    return total if found else None


def summarize_text(text: str, max_len: int = 300) -> str:
    """Return a summary string; short text is returned verbatim."""
    if len(text) <= max_len:
        return text
    head = text[: max_len // 2]
    tail = text[-max_len // 2 :]
    return f"{head} ... {tail}"


def categorize_user_message(text: str, context: str = "") -> Tuple[List[str], bool, Optional[str]]:
    """
    Assign categories and stage using the OpenAI API with the confirmed definitions in AGENTS.md.
    Returns (categories, correction_flag, stage). Raises an explicit exception on failure so callers can log.
    """
    try:
        import os
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package is not installed; cannot categorize")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set; cannot categorize")

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You are a classifier. Choose zero or more categories and one stage based on the user message.\n"
        "Categories:\n"
        "1. Workflow Progression / Next Step — user asks to proceed, continue, or move the work forward.\n"
        "2. Spec Refinement — user refines requirements, scope, or desired outputs.\n"
        "3. Correction — user flags an error, mismatch, or requests a fix/improvement.\n"
        "4. User Question — user asks a question about the work, data, or approach.\n"
        "5. User Information — user provides a status/progress update without requesting action.\n"
        "6. Request — user asks for a specific action or new task (not necessarily a correction).\n"
        "7. Result Review / Approval or Rejection — user reviews results and reacts (accept/reject/concern).\n"
        "Stages:\n"
        "1. Initialization — setup and starting instructions/context.\n"
        "2. Conversion — data loading and conversion.\n"
        "3. Visualization — plotting or visualization.\n"
        "4. Documentation — notes, README, logging progress.\n"
        "5. Validation — verifying data structure and values, decoder training.\n"
        "6. Cleanup — final tidy-up, directory clean.\n"
        "Respond with JSON: {\"categories\": [...], \"stage\": \"StageName\"}."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"User message: {text}\n\nRecent context (previous steps): {context or 'n/a'}",
                },
            ],
            temperature=0,
            max_tokens=200,
        )
        content = resp.choices[0].message.content
        parsed = json.loads(content)
        cats = parsed.get("categories", []) if isinstance(parsed, dict) else []
        categories = [str(c) for c in cats if isinstance(c, str)]
        stage = parsed.get("stage") if isinstance(parsed, dict) else None
        if isinstance(stage, str):
            stage = stage.strip()
        else:
            stage = None
    except Exception as exc:
        raise RuntimeError(f"OpenAI categorization failed: {exc}") from exc
    correction = "Correction" in categories
    return categories, correction, stage


def compute_stats(numbers: List[float]) -> Dict[str, Optional[float]]:
    """Compute descriptive statistics for a numeric series."""
    if not numbers:
        return {"mean": None, "median": None, "stdev": None, "min": None, "max": None, "count": 0, "total": 0}
    return {
        "mean": statistics.mean(numbers),
        "median": statistics.median(numbers),
        "stdev": statistics.stdev(numbers) if len(numbers) > 1 else 0.0,
        "min": min(numbers),
        "max": max(numbers),
        "count": len(numbers),
        "total": sum(numbers),
    }


# ----------------------------- Core processing ----------------------------- #

def load_summaries(convo_dir: Path) -> Dict[str, str]:
    """Load precomputed LLM summaries for this conversation, if present."""
    summary_path = convo_dir / "convo.summaries.json"
    if not summary_path.exists():
        return {}
    try:
        data = json.loads(summary_path.read_text())
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        # Support legacy list-of-dicts format: [{"step": 1, "summary": "..."}]
        if isinstance(data, list):
            mapped: Dict[str, str] = {}
            for entry in data:
                if isinstance(entry, dict) and "step" in entry and "summary" in entry:
                    mapped[str(entry["step"])] = str(entry["summary"])
            if mapped:
                return mapped
    except Exception:
        pass
    return {}

def load_records(convo_dir: Path) -> Tuple[List[Record], List[str]]:
    """Load all JSONL records for a conversation directory."""
    warnings: List[str] = []
    jsonl_paths = sorted(p for p in convo_dir.rglob("*.jsonl") if p.is_file())
    records: List[Record] = []
    for file_index, path in enumerate(jsonl_paths):
        with path.open() as handle:
            for line_no, line in enumerate(handle, 1):
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    warnings.append(f"Failed to parse {path.name} line {line_no}: {exc}")
                    continue
                ts, ts_raw = extract_timestamp(raw)
                record = Record(
                    raw=raw,
                    file_path=path,
                    line_no=line_no,
                    timestamp=ts,
                    timestamp_raw=ts_raw,
                    file_index=file_index,
                )
                records.append(record)
    return records, warnings


def build_steps(
    records: List[Record],
    warnings: List[str],
    summary_map: Dict[str, str],
) -> Tuple[
    List[StepEntry],
    Dict[int, Optional[float]],
    Dict[str, List[float]],
    Dict[int, Dict[str, Optional[Any]]],
    Dict[str, Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """Construct step entries and derived aggregates."""
    def classify_step_type(role: str, tool_type: Optional[str], display_content: str) -> str:
        if tool_type:
            return tool_type
        if "[thinking]" in display_content:
            return "thinking"
        if role == "assistant":
            return "assistant-text"
        if role == "user":
            return "user-text"
        return role or "unknown"

    # Sort records chronologically, fallback to file/line order.
    def sort_key(rec: Record):
        return (
            0 if rec.timestamp else 1,
            rec.timestamp or datetime.max.replace(tzinfo=timezone.utc),
            rec.file_index,
            rec.line_no,
        )

    sorted_records = sorted(records, key=sort_key)

    steps: List[StepEntry] = []
    tokens_per_step: Dict[int, Optional[float]] = {}
    tokens_per_tool: Dict[str, List[float]] = defaultdict(list)
    timing_per_step: Dict[int, Dict[str, Optional[Any]]] = {}
    timing_per_tool: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"durations": []})
    interventions: List[Dict[str, Any]] = []

    for idx, rec in enumerate(sorted_records, 1):
        raw = rec.raw
        content_raw = extract_content(raw)
        role = extract_role(raw)
        # Reclassify tool_result-only payloads away from "user" to avoid false interventions.
        if role == "user" and is_tool_result_only(content_raw):
            role = "tool"
        display_content = render_content_text(content_raw) if content_raw is not None else ""
        summary = summary_map.get(str(idx)) or summarize_text(display_content)
        tool_calls = extract_tool_calls(content_raw)
        tool_type = tool_calls[0]["name"] if tool_calls else None
        token_count = extract_token_count(raw)
        step_type = classify_step_type(role, tool_type, display_content)
        if token_count is not None:
            tokens_per_step[idx] = token_count
            tokens_per_tool[step_type].append(token_count)
        else:
            tokens_per_step[idx] = None

        start_ts = rec.timestamp
        end_ts, end_ts_raw = extract_end_timestamp(raw)
        duration = None
        if start_ts and end_ts:
            duration = (end_ts - start_ts).total_seconds()
        elif isinstance(raw.get("duration"), (int, float)):
            duration = float(raw["duration"])
        elif isinstance(raw.get("latency"), (int, float)):
            duration = float(raw["latency"])

        timing_per_step[idx] = {
            "start": start_ts.isoformat() if start_ts else None,
            "end": end_ts.isoformat() if end_ts else None,
            "duration": duration,
        }
        if tool_type and duration is not None:
            timing_per_tool[tool_type]["durations"].append(duration)

        step_entry = StepEntry(
            step_number=idx,
            role=role,
            step_type=step_type,
            content_raw=content_raw,
            display_content=display_content,
            summarized_content=summary,
            tool_calls=tool_calls,
            tool_type=tool_type,
            token_count=token_count,
            timestamps={"start": timing_per_step[idx]["start"], "end": timing_per_step[idx]["end"], "duration": duration},
            metadata={"file": str(rec.file_path.name), "line": rec.line_no, "timestamp_raw": rec.timestamp_raw, "end_timestamp_raw": end_ts_raw},
        )
        steps.append(step_entry)

        if role == "user" and has_user_text_content(content_raw):
            # Skip autogenerated interruption placeholders (not real user text).
            if isinstance(display_content, str) and display_content.strip().startswith("[Request interrupted"):
                continue
            if isinstance(display_content, str) and is_out_of_context_restart(display_content):
                continue
            prev_entries = []
            if len(steps) >= 2:
                prev_entries.append(steps[-2])
            if len(steps) >= 3:
                prev_entries.append(steps[-3])
            context_parts = []
            for prev in prev_entries:
                prev_summary = prev.summarized_content or summarize_text(prev.display_content)
                context_parts.append(f"Step {prev.step_number}: {prev_summary}")
            context_str = " | ".join(context_parts)
            trigger = None
            if prev_entries:
                trigger = prev_entries[0].summarized_content or summarize_text(prev_entries[0].display_content)
            try:
                categories, correction, stage = categorize_user_message(display_content, context=context_str)
            except Exception as exc:
                warnings.append(f"categorization_failed_step_{idx}: {exc}")
                categories, correction, stage = [], False, None
            interventions.append(
                {
                    "raw_message": display_content,
                    "categories": categories,
                    "stage": stage,
                    "preceding_step": idx - 1 if idx > 1 else None,
                    "trigger": trigger,
                    "caused_correction_or_branch": correction,
                }
            )

    # Complete timing_per_tool stats
    for tool, payload in timing_per_tool.items():
        payload["stats"] = compute_stats(payload["durations"])

    # Add warnings for missing data
    missing_ts = [s.step_number for s in steps if not s.timestamps["start"]]
    if missing_ts:
        warnings.append(f"Missing timestamps for steps: {missing_ts}")
    missing_tokens = [step for step, tok in tokens_per_step.items() if tok is None]
    if missing_tokens:
        warnings.append(f"Missing token usage for steps: {missing_tokens}")

    return steps, tokens_per_step, tokens_per_tool, timing_per_step, timing_per_tool, interventions


# ----------------------------- Markdown builders --------------------------- #

def write_intervention_summary(path: Path, interventions: List[Dict[str, Any]]) -> None:
    lines = ["# Intervention Summary", ""]
    if not interventions:
        lines.append("No user interventions detected.")
    for idx, iv in enumerate(interventions, 1):
        lines.append(f"## Intervention {idx}")
        lines.append(f"- Quote: \"{iv['raw_message']}\"")
        lines.append(f"- Categories: {', '.join(iv['categories'])}")
        lines.append(f"- Stage: {iv.get('stage')}")
        lines.append(f"- Step before message: {iv.get('preceding_step')}")
        trigger = iv.get("trigger")
        if isinstance(trigger, str):
            trigger = " ".join(trigger.split())
        lines.append(f"- Trigger: {trigger}")
        lines.append(f"- Caused correction/branch: {'Yes' if iv.get('caused_correction_or_branch') else 'No'}")
        lines.append("")
    path.write_text("\n".join(lines))


def write_category_totals(path: Path, interventions: List[Dict[str, Any]]) -> None:
    from collections import Counter
    lines = ["# Intervention Category Totals", ""]
    if not interventions:
        lines.append("No user interventions detected.")
    else:
        cat_counts = Counter()
        for iv in interventions:
            for c in iv.get("categories", []):
                cat_counts[c] += 1
        lines.append("| Category | Count |")
        lines.append("| --- | --- |")
        for cat, count in sorted(cat_counts.items(), key=lambda kv: kv[0].lower()):
            lines.append(f"| {cat} | {count} |")
    path.write_text("\n".join(lines))


def write_work_summary(path: Path, steps: List[StepEntry]) -> None:
    lines = ["# Work Summary", ""]
    def trunc(text: str, limit: int = 120) -> str:
        return text if len(text) <= limit else text[: limit - 3] + "..."

    def clean_text(val: Any) -> str:
        """Collapse whitespace/newlines for display."""
        return " ".join(str(val).split())

    def render_structured(val: Any, indent: str = "    ") -> None:
        """Render dicts/lists as nested bullets."""
        if isinstance(val, dict):
            for k, v in val.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{indent}- {k}:")
                    render_structured(v, indent + "  ")
                else:
                    lines.append(f"{indent}- {k}: {trunc(clean_text(v))}")
        elif isinstance(val, list):
            items = val
            if len(items) > 3:
                items = items[:2] + ["__ELLIPSIS__"] + items[-1:]
            for item in items:
                if item == "__ELLIPSIS__":
                    lines.append(f"{indent}- ...")
                    continue
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent}-")
                    render_structured(item, indent + "  ")
                else:
                    lines.append(f"{indent}- {trunc(clean_text(item))}")
        else:
            lines.append(f"{indent}- {trunc(clean_text(val))}")

    assistant_steps = [s for s in steps if s.role == "assistant"]
    if not assistant_steps:
        lines.append("No assistant steps found.")
    for step in assistant_steps:
        title = step.summarized_content or (step.display_content[:80] if step.display_content else f"Step {step.step_number}")
        lines.append(f"## Step {step.step_number}: {title}")
        if step.display_content and not step.tool_calls:
            content_full = clean_text(step.display_content)
            content = content_full if len(content_full) <= 600 else (content_full[:300] + " ... " + content_full[-300:])
            lines.append(f"- Content: {content}")
        lines.append(f"- Tool: {step.tool_type or 'None'}")
        if step.tool_calls:
            lines.append(f"- Tool calls:")
            for call in step.tool_calls:
                call_id = call.get("id") or call.get("name") or "unknown"
                lines.append(f"  - id: {call_id}")
                # If there is structured input, render important bits instead of raw JSON.
                call_input = call.get("input")
                if isinstance(call_input, dict) and "todos" in call_input and isinstance(call_input["todos"], list):
                    todos = call_input["todos"]
                    if len(todos) > 3:
                        todos_to_show = todos[:2] + [None] + todos[-1:]
                    else:
                        todos_to_show = todos
                    for todo in todos_to_show:
                        if todo is None:
                            lines.append("  - content: ...")
                        elif isinstance(todo, dict) and "content" in todo:
                            lines.append(f"  - content: {trunc(clean_text(todo.get('content')))}")
                elif isinstance(call_input, (dict, list)):
                    lines.append("  - input:")
                    render_structured(call_input, indent="    ")
                elif call_input is not None:
                    lines.append(f"  - input: {trunc(json.dumps(call_input, ensure_ascii=False))}")
        lines.append(f"- Tokens: {step.token_count if step.token_count is not None else 'n/a'}")
        lines.append(f"- Timestamp: {step.timestamps.get('start')}")
        lines.append("")
    path.write_text("\n".join(lines))


def write_token_usage(path: Path, steps: List[StepEntry], tokens_per_tool: Dict[str, List[float]]) -> None:
    lines = ["# Token Usage", "", "## Per-Step Tokens", "", "| Step | Type | Tokens | Cumulative |", "| --- | --- | --- | --- |"]
    cumulative = 0.0
    for step in sorted(steps, key=lambda s: s.step_number):
        count = step.token_count
        if count is None:
            display = "n/a"
        else:
            cumulative += count
            display = f"{int(count)}"
        lines.append(f"| {step.step_number} | {step.step_type} | {display} | {int(cumulative) if cumulative else 0} |")
    lines.append("")
    lines.append("## Tool-Level Statistics")
    if not tokens_per_tool:
        lines.append("No tool token usage recorded.")
    else:
        lines.append("")
        lines.append("| Type | Mean | Median | Stdev | Min | Max | Calls | Total |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for tool, counts in tokens_per_tool.items():
            stats = compute_stats(counts)
            lines.append(
                f"| {tool} | {stats['mean'] or 0:.2f} | {stats['median'] or 0:.2f} | {stats['stdev'] or 0:.2f} | "
                f"{stats['min'] or 0:.2f} | {stats['max'] or 0:.2f} | {stats['count']} | {int(stats['total'])} |"
            )
    path.write_text("\n".join(lines))


def write_timing(path: Path, timing_per_step: Dict[int, Dict[str, Optional[Any]]], timing_per_tool: Dict[str, Dict[str, Any]]) -> None:
    timestamps_available = any(v.get("start") or v.get("end") or v.get("duration") for v in timing_per_step.values())
    if not timestamps_available:
        path.write_text("**Timing data unavailable: no timestamp fields found.**\n")
        return

    lines = ["# Timing", "", "## Per-Step Timing", "", "| Step | Start | End | Duration (s) |", "| --- | --- | --- | --- |"]
    for step in sorted(timing_per_step.keys()):
        entry = timing_per_step[step]
        duration = entry.get("duration")
        duration_str = f"{duration:.2f}" if isinstance(duration, (int, float)) else "n/a"
        lines.append(f"| {step} | {entry.get('start') or 'n/a'} | {entry.get('end') or 'n/a'} | {duration_str} |")
    lines.append("")
    lines.append("## Per-Tool Timing")
    if not timing_per_tool:
        lines.append("No tool timing data available.")
    else:
        lines.append("")
        lines.append("| Tool | Mean | Median | Stdev | Min | Max | Total Duration | Calls |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for tool, payload in timing_per_tool.items():
            stats = payload.get("stats", {})
            total = sum(payload.get("durations", [])) if payload.get("durations") else 0
            lines.append(
                f"| {tool} | {stats.get('mean') or 0:.2f} | {stats.get('median') or 0:.2f} | "
                f"{stats.get('stdev') or 0:.2f} | {stats.get('min') or 0:.2f} | {stats.get('max') or 0:.2f} | "
                f"{total:.2f} | {stats.get('count', 0)} |"
            )
    path.write_text("\n".join(lines))


def write_file_index(path: Path) -> None:
    manifest = {
        "markdown_outputs": [
            "01_intervention_summary.md",
            "02_work_summary.md",
            "03_intervention_category_totals.md",
            "04_token_usage.md",
        ],
        "JSON": "all_data.json",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(manifest, indent=2))


# ----------------------------- Orchestration ------------------------------- #

def process_conversation(convo_dir: Path) -> None:
    records, warnings = load_records(convo_dir)
    summary_map = load_summaries(convo_dir)
    if not records:
        print(f"[WARN] No records found in {convo_dir}")
        return

    steps, tokens_per_step, tokens_per_tool, timing_per_step, timing_per_tool, interventions = build_steps(
        records, warnings, summary_map
    )

    all_data = {
        "steps": [
            {
                "step_number": s.step_number,
                "role": s.role,
                "step_type": s.step_type,
                "content_raw": s.content_raw,
                "display_content": s.display_content,
                "summarized_content": s.summarized_content,
                "tool_calls": s.tool_calls,
                "tool_type": s.tool_type,
                "token_count": s.token_count,
                "timestamps": s.timestamps,
                "metadata": s.metadata,
            }
            for s in steps
        ],
        "interventions": interventions,
        "tokens_per_step": {str(k): v for k, v in tokens_per_step.items()},
        "tokens_per_tool": tokens_per_tool,
        "timing_per_step": {str(k): v for k, v in timing_per_step.items()},
        "timing_per_tool": timing_per_tool,
        "meta": {
            "data_version": "1.0",
            "agent_version": "analysis-1.0",
            "warnings": warnings,
            "input_files": [str(p) for p in sorted({rec.file_path for rec in records})],
        },
    }

    (convo_dir / "all_data.json").write_text(json.dumps(all_data, indent=2, ensure_ascii=False))
    write_intervention_summary(convo_dir / "01_intervention_summary.md", interventions)
    write_work_summary(convo_dir / "02_work_summary.md", steps)
    write_category_totals(convo_dir / "03_intervention_category_totals.md", interventions)
    write_token_usage(convo_dir / "04_token_usage.md", steps, tokens_per_tool)
    write_file_index(convo_dir / "05_file_index.json")


def discover_conversations(parent_dir: Path, specific: Optional[List[str]]) -> List[Path]:
    if specific:
        return [parent_dir / name for name in specific]
    conversations = []
    for entry in sorted(parent_dir.iterdir()):
        if entry.is_dir():
            if any(entry.glob("*.jsonl")) or any(entry.rglob("*.jsonl")):
                conversations.append(entry)
    return conversations


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate conversation analytics per AGENTS.md")
    parser.add_argument("parent_dir", help="Parent directory containing conversation subdirectories")
    parser.add_argument("--conversation", action="append", help="Specific conversation subdirectory names to process (relative to parent_dir)")
    args = parser.parse_args()

    parent_dir = Path(args.parent_dir).resolve()
    convo_dirs = discover_conversations(parent_dir, args.conversation)
    if not convo_dirs:
        print(f"No conversation directories found under {parent_dir}")
        return

    for convo_dir in convo_dirs:
        print(f"Processing {convo_dir} ...")
        process_conversation(convo_dir)
    print("Done.")


if __name__ == "__main__":
    main()
