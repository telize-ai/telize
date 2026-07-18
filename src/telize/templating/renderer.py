from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError, UndefinedError
from jinja2.nativetypes import NativeEnvironment

from telize.exceptions import ExecutionError

_FALSE_STRINGS = frozenset({"", "false", "0", "no", "off", "none", "null"})
_TRUE_STRINGS = frozenset({"true", "1", "yes", "on"})


def build_jinja_environment() -> Environment:
    return Environment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def build_native_jinja_environment() -> NativeEnvironment:
    return NativeEnvironment(
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def coerce_condition_result(value: Any) -> bool:
    """Convert a native Jinja result into a boolean condition outcome."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _FALSE_STRINGS:
            return False
        if text in _TRUE_STRINGS:
            return True
        return bool(text)
    return bool(value)


class TemplateRenderer:
    """Render Jinja2 templates embedded in workflow fields."""

    def __init__(self, context: Mapping[str, Any]) -> None:
        self._env = build_jinja_environment()
        self._native_env = build_native_jinja_environment()
        self._context = dict(context)

    def render(self, template: str) -> str:
        if "{{" not in template and "{%" not in template:
            return template
        try:
            return self._env.from_string(template).render(**self._context)
        except (TemplateError, UndefinedError) as exc:
            raise ExecutionError(f"Template error: {exc}") from exc

    def evaluate(self, template: str) -> bool:
        """Evaluate a Jinja expression as a boolean (used by step ``when``)."""
        try:
            result = self._native_env.from_string(template.strip()).render(**self._context)
        except (TemplateError, UndefinedError) as exc:
            raise ExecutionError(f"Template error: {exc}") from exc
        return coerce_condition_result(result)

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
