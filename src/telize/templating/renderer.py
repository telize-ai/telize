from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError, UndefinedError

from telize.exceptions import ExecutionError


def build_jinja_environment() -> Environment:
    return Environment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )


class TemplateRenderer:
    """Render Jinja2 templates embedded in workflow fields."""

    def __init__(self, context: Mapping[str, Any]) -> None:
        self._env = build_jinja_environment()
        self._context = dict(context)

    def render(self, template: str) -> str:
        if "{{" not in template and "{%" not in template:
            return template
        try:
            return self._env.from_string(template).render(**self._context)
        except (TemplateError, UndefinedError) as exc:
            raise ExecutionError(f"Template error: {exc}") from exc

    def render_mapping(self, data: dict[str, Any]) -> dict[str, Any]:
        return {key: self._render_value(val) for key, val in data.items()}

    def _render_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.render(value)
        if isinstance(value, dict):
            return {key: self._render_value(val) for key, val in value.items()}
        if isinstance(value, list):
            return [self._render_value(item) for item in value]
        return value
