from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from telize.exceptions import ConfigError


def parse_key_value_pairs(pairs: list[str] | None) -> dict[str, Any]:
    """Parse repeated ``KEY=VALUE`` CLI arguments into a mapping."""
    if not pairs:
        return {}
    result: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ConfigError(f"Invalid --input (expected KEY=VALUE): {pair!r}")
        key, _, value = pair.partition("=")
        key = key.strip()
        if not key:
            raise ConfigError(f"Invalid --input (empty key): {pair!r}")
        result[key] = value
    return result


def normalize_cli_input(raw: Any, *, source: str) -> dict[str, Any]:
    """Map parsed CLI input to workflow input; plain text becomes ``{\"text\": ...}``."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        return {"text": raw}
    if isinstance(raw, (bool, int, float)):
        return {"text": str(raw)}
    raise ConfigError(
        f"Workflow input from {source} must be a mapping or plain text, "
        f"got {type(raw).__name__}"
    )


def load_input_from_text(text: str, *, source: str, parse_json: bool = False) -> dict[str, Any]:
    if not text.strip():
        return {}
    if parse_json:
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}
        return normalize_cli_input(raw, source=source)
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError:
        return {"text": text}
    return normalize_cli_input(raw, source=source)


def load_input_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Input file not found: {path}")
    text = path.read_text(encoding="utf-8")
    source = str(path)
    if path.suffix.lower() == ".txt":
        return {"text": text}
    return load_input_from_text(text, source=source, parse_json=path.suffix.lower() == ".json")


def load_input_stdin() -> dict[str, Any]:
    text = sys.stdin.read()
    if not text.strip():
        return {}
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError:
        return {"text": text.rstrip("\n")}
    return normalize_cli_input(raw, source="stdin")


def merge_workflow_input(
    *sources: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Merge input mappings; later sources override earlier keys."""
    merged: dict[str, Any] = {}
    for source in sources:
        if source:
            merged.update(source)
    return merged


def resolve_cli_workflow_input(
    *,
    pairs: list[str] | None = None,
    input_file: Path | None = None,
    input_stdin: bool = False,
) -> dict[str, Any]:
    """Build workflow input from CLI flags (file, then stdin, then key=value pairs)."""
    from_file: dict[str, Any] = {}
    from_stdin: dict[str, Any] = {}
    if input_file is not None:
        from_file = load_input_file(input_file)
    if input_stdin:
        from_stdin = load_input_stdin()
    from_pairs = parse_key_value_pairs(pairs)
    return merge_workflow_input(from_file, from_stdin, from_pairs)
