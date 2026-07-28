#!/usr/bin/env python3
"""Propagate pinned harness/model versions from a dated config to every consumer.

Most consumers read the config at runtime, but two cannot and must carry the
values literally:

  * each task's ``environment/Dockerfile``, which installs the judge CLIs at
    image build time -- a Dockerfile cannot read JSON;
  * each task's ``tests/versions.json``, which ships into the verifier container
    so the judge scripts can read the model (the container cannot see the host
    config).

Editing those 18+18 files by hand every time a version is bumped is not viable,
so this rewrites them from the config instead. ``--check`` reports drift without
writing, which is what CI or a pre-sweep guard should call.

Usage:
    python apply_versions.py                    # apply the newest config_*.json
    python apply_versions.py --check            # report drift, exit 1 if any
    python apply_versions.py --versions harbor-scripts/config_20260728.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "harbor-scripts"
TEMPLATE_DIR = REPO_ROOT / "template-harbor-task"

# The two install lines in every task Dockerfile. Each pattern captures the
# command prefix in group 1 and the currently pinned version (if any) in group 2,
# so an unpinned line is matched and repaired rather than skipped.
CLAUDE_INSTALL_RE = re.compile(r"(curl -fsSL https://claude\.ai/install\.sh \| bash)"
                               r"(?: -s -- (\S+))?")
CODEX_INSTALL_RE = re.compile(r"(npm i -g @openai/codex)(?:@(\S+))?")


def newest_config() -> Path | None:
    """Return the newest dated config, or None.

    Named config_<YYYYMMDD>.json so a lexical sort is chronological.
    """
    configs = sorted(SCRIPTS_DIR.glob("config_*.json"))
    return configs[-1] if configs else None


def dockerfiles() -> list[Path]:
    """Every Dockerfile that installs the judge CLIs.

    Includes the template and all task copies. allen2p and allen2p_minimal are
    excluded from sync_template.py because their environment differs, but they
    still need the pins, so they are covered here.
    """
    return sorted((REPO_ROOT / "harbor-tasks").glob("*/environment/Dockerfile")) + \
        [TEMPLATE_DIR / "environment" / "Dockerfile"]


def versions_files() -> list[Path]:
    """Every tests/versions.json that ships into a verifier container."""
    return sorted((REPO_ROOT / "harbor-tasks").glob("*/tests/versions.json")) + \
        [TEMPLATE_DIR / "tests" / "versions.json"]


def render_versions_json(cfg: dict, source_name: str) -> str:
    """Build the contents of tests/versions.json from the source config.

    Args:
        cfg: parsed source config, with a top-level "tools" mapping.
        source_name: filename of the source config, recorded in the header so a
            reader can tell where the values came from.

    Returns:
        JSON text, newline-terminated.
    """
    out = {
        "_comment": [
            f"GENERATED from harbor-scripts/{source_name} by apply_versions.py.",
            "Do not edit here -- edit the source config and re-run that script.",
            "Ships into the verifier container as /tests/versions.json, where the",
            "judge scripts read the model; the container cannot see the host config.",
            "One entry per tool: agent and judge share a CLI by construction.",
        ],
        "tools": cfg["tools"],
    }
    return json.dumps(out, indent=2) + "\n"


def patch_dockerfile(text: str, claude_version: str, codex_version: str) -> str:
    """Return `text` with both CLI install lines pinned to the given versions."""
    text = CLAUDE_INSTALL_RE.sub(rf"\1 -s -- {claude_version}", text, count=1)
    text = CODEX_INSTALL_RE.sub(rf"\1@{codex_version}", text, count=1)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--versions", type=Path, default=None,
                        help="source config (default: newest config_*.json)")
    parser.add_argument("--check", action="store_true",
                        help="report drift without writing; exit 1 if any")
    args = parser.parse_args()

    source = args.versions or newest_config()
    if source is None or not source.is_file():
        sys.exit(f"no config found (looked for {SCRIPTS_DIR}/config_*.json)")
    cfg = json.loads(source.read_text())
    try:
        claude_version = cfg["tools"]["claude"]["harness_version"]
        codex_version = cfg["tools"]["codex"]["harness_version"]
    except KeyError as exc:
        sys.exit(f"{source}: missing tools.<tool>.harness_version: {exc}")

    print(f"source: {source}")
    print(f"  claude harness {claude_version}   codex harness {codex_version}\n")

    stale: list[Path] = []

    for path in dockerfiles():
        current = path.read_text()
        wanted = patch_dockerfile(current, claude_version, codex_version)
        if current == wanted:
            continue
        stale.append(path)
        rel = path.relative_to(REPO_ROOT)
        if args.check:
            print(f"  DRIFT  {rel}")
        else:
            path.write_text(wanted)
            print(f"  wrote  {rel}")

    wanted_json = render_versions_json(cfg, source.name)
    for path in versions_files():
        current = path.read_text() if path.is_file() else ""
        if current == wanted_json:
            continue
        stale.append(path)
        rel = path.relative_to(REPO_ROOT)
        if args.check:
            print(f"  DRIFT  {rel}")
        else:
            path.write_text(wanted_json)
            print(f"  wrote  {rel}")

    n_files = len(dockerfiles()) + len(versions_files())
    if args.check:
        if stale:
            print(f"\n{len(stale)} of {n_files} file(s) out of step with {source.name}")
            print("Run without --check to fix.")
            sys.exit(1)
        print(f"\nall {n_files} files in step with {source.name}")
    else:
        print(f"\n{len(stale)} of {n_files} file(s) updated")


if __name__ == "__main__":
    main()
