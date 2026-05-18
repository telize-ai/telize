from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from telize.config.models import WorkflowSpec
from telize.exceptions import ConfigError, ExecutionError
from telize.templating.load import render_env_templates


def _apply_load_time_templates(raw: dict[str, Any]) -> dict[str, Any]:
    """Expand `{{ env.* }}` in YAML before validation; leave runtime templates intact."""
    try:
        rendered = render_env_templates(raw)
    except ExecutionError as exc:
        raise ConfigError(str(exc)) from exc
    if not isinstance(rendered, dict):
        raise ConfigError("Expected a YAML mapping at the root after template rendering")
    return rendered


def load_spec(path: Path) -> WorkflowSpec:
    """Load and validate a Telize workflow YAML file."""
    if not path.is_file():
        raise ConfigError(f"File not found: {path}")

    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    if raw is None:
        raise ConfigError(f"Empty YAML file: {path}")
    if not isinstance(raw, dict):
        raise ConfigError(f"Expected a YAML mapping at the root of {path}")

    raw = _apply_load_time_templates(raw)

    try:
        return WorkflowSpec.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid workflow spec in {path}:\n{exc}") from exc
