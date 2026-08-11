#!/usr/bin/env python3
"""PreToolUse checker for new dbt models in the cal-itp warehouse.

Reads a Claude Code hook payload from stdin and applies two policy rules to
new .sql files under <project root>/warehouse/models/. The project root comes
from `git -C <payload cwd> rev-parse --show-toplevel` — never from file_path,
__file__ or ${CLAUDE_PLUGIN_ROOT}, because an installed plugin runs from
Claude's cache outside the project it is checking.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

WRITE_TOOLS = {"Write", "Edit"}
MODELS_SUBPATH = ("warehouse", "models")
PREFIX_THRESHOLD = 10


def read_payload():
    """Return the hook payload dict, or None when stdin is not a JSON object."""
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def find_project_root(cwd):
    """Return the git top-level for the session directory, or None."""
    if not isinstance(cwd, str) or not cwd:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def resolve_target(file_path, project_root):
    """Resolve file_path against project_root, preserving absolute paths."""
    if not isinstance(file_path, str) or not file_path:
        return None
    try:
        candidate = Path(file_path)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        # resolve() collapses symlinks and `..` segments before any scope check
        return candidate.resolve()
    except (OSError, ValueError, RuntimeError):
        return None


def accepted_prefixes(layer_dir, target):
    """Prefixes used by PREFIX_THRESHOLD+ existing .sql files in the layer.

    Prefixes are measured from the filenames on disk, never hardcoded: the
    repository has no staging_prefixes key, so existing filenames are the
    only authority.
    """
    counts = {}
    for sql_file in layer_dir.rglob("*.sql"):
        if sql_file == target:
            continue
        prefix = sql_file.stem.split("_", 1)[0]
        counts[prefix] = counts.get(prefix, 0) + 1
    return {prefix for prefix, count in counts.items() if count >= PREFIX_THRESHOLD}


def is_documented(target):
    """True when a YAML file in the model's own directory declares `name: <stem>`.

    Only the model's own directory counts — a YAML file in the parent
    directory does not document this directory.
    """
    pattern = re.compile(
        r"^\s*-?\s*name:\s*[\"']?" + re.escape(target.stem) + r"[\"']?\s*$",
        re.MULTILINE,
    )
    for suffix in ("*.yml", "*.yaml"):
        for yaml_file in target.parent.glob(suffix):
            try:
                text = yaml_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if pattern.search(text):
                return True
    return False


def main():
    """Exit protocol.

    0 = continue: expected skips (non-matching tool, malformed payload,
        out-of-scope path, undeterminable project root), existing files,
        and compliant new models.
    1 = unexpected checker error; a concise diagnostic goes to stderr.
    2 = policy violation; every violation is written to stderr first.
    """
    try:
        payload = read_payload()
        if payload is None:
            return 0  # malformed or non-object payload -> expected skip

        if payload.get("tool_name") not in WRITE_TOOLS:
            return 0  # not a Write/Edit call -> expected skip

        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            return 0  # invalid tool_input -> expected skip

        project_root = find_project_root(payload.get("cwd"))
        if project_root is None:
            return 0  # no session repository -> nothing can be in scope

        target = resolve_target(tool_input.get("file_path"), project_root)
        if target is None:
            return 0  # invalid file path -> expected skip

        # Path-scope check: only .sql files under THIS project root's
        # warehouse/models/ are in scope. An absolute path into a decoy
        # repository elsewhere on disk falls outside and is skipped.
        models_root = project_root.joinpath(*MODELS_SUBPATH)
        if target.suffix != ".sql" or not target.is_relative_to(models_root):
            return 0

        # Creation-only check: the rules govern new models, so an existing
        # file is never evaluated.
        if target.exists():
            return 0

        relative_parts = target.relative_to(models_root).parts
        layer_dir = (
            models_root / relative_parts[0] if len(relative_parts) > 1 else models_root
        )

        violations = []

        prefix = target.stem.split("_", 1)[0]
        allowed = accepted_prefixes(layer_dir, target)
        if prefix not in allowed:
            expected = ", ".join(sorted(allowed)) or "none"
            violations.append(
                f"naming: prefix '{prefix}_' is not established in "
                f"{layer_dir.name}/ (prefixes with >={PREFIX_THRESHOLD} models: {expected})"
            )

        if not is_documented(target):
            violations.append(
                f"documentation: no 'name: {target.stem}' entry in a .yml/.yaml "
                f"file in {target.parent}/"
            )

        # Policy decision: any violation blocks the write (2); a clean new
        # model continues (0).
        if violations:
            print(f"check_model: blocked {target}", file=sys.stderr)
            for violation in violations:
                print(f"  - {violation}", file=sys.stderr)
            return 2

        return 0

    except Exception as exc:  # unexpected checker error; never print the payload
        print(
            f"check_model: unexpected {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
