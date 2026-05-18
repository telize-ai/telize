from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from telize.runtime.state import ExecutionState
from telize.templating.context import build_env_context


def build_template_context(
    state: ExecutionState,
    *,
    item: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the Jinja context available in workflow templates."""
    ctx: dict[str, Any] = {
        **build_env_context(),
        "steps": state.steps_view(),
        "config": state.config.model_dump(exclude_none=True),
        "input": dict(state.workflow_input),
    }
    if item is not None:
        ctx["item"] = item
    if extra:
        ctx.update(extra)
    return ctx
