from __future__ import annotations

from pathlib import Path

import pytest

from telize.config import load_spec
from telize.config.models import GlobalConfig
from telize.runtime.actions.llm import render_system_prompt
from telize.runtime.context import build_template_context
from telize.runtime.state import ExecutionState
from telize.templating import TemplateRenderer


def test_load_system_prompt_from_yaml() -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "hello_agent.yaml"
    spec = load_spec(example)
    assert spec.config.system_prompt == "You are a helpful assistant."


def test_render_system_prompt_with_jinja(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELIZE_ROLE", "editor")
    state = ExecutionState(
        config=GlobalConfig(
            entrypoint="main",
            system_prompt="Role: {{ env.TELIZE_ROLE }}",
        ),
        base_path=Path("."),
    )
    from telize.runtime.actions.base import ActionContext

    renderer = TemplateRenderer(build_template_context(state))
    ctx = ActionContext(state=state, renderer=renderer, base_path=Path("."))
    assert render_system_prompt(ctx) == "Role: editor"


def test_render_system_prompt_none_when_unset() -> None:
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main"),
        base_path=Path("."),
    )
    from telize.runtime.actions.base import ActionContext

    renderer = TemplateRenderer(build_template_context(state))
    ctx = ActionContext(state=state, renderer=renderer, base_path=Path("."))
    assert render_system_prompt(ctx) is None
