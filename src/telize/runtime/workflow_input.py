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


def load_input_mapping(raw: Any, *, source: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Workflow input from {source} must be a mapping, got {type(raw).__name__}"
        )
    return dict(raw)


def load_input_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Input file not found: {path}")
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        raw = json.loads(text) if suffix == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"Invalid workflow input in {path}: {exc}") from exc
    return load_input_mapping(raw, source=str(path))


def load_input_stdin() -> dict[str, Any]:
    text = sys.stdin.read()
    if not text.strip():
        return {}
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid workflow input on stdin: {exc}") from exc
    return load_input_mapping(raw, source="stdin")


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
