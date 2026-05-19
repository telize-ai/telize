from __future__ import annotations

from pathlib import Path

import pytest

from telize.config import load_spec
from telize.config.models import GlobalConfig, LlmStep, ModelConfig
from telize.runtime.actions.base import ActionContext
from telize.runtime.actions.llm import render_system_prompt, resolve_model_config
from telize.runtime.context import build_template_context
from telize.runtime.state import ExecutionState
from telize.templating import TemplateRenderer

FIXTURE = Path(__file__).parent / "fixtures" / "hello_agent_workflow.yaml"


def test_load_system_prompt_from_yaml() -> None:
    spec = load_spec(FIXTURE)
    assert spec.models["default"].system_prompt == "You are a helpful assistant."


def test_render_system_prompt_with_jinja(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELIZE_ROLE", "editor")
    model_config = ModelConfig(
        provider="openai",
        model="m",
        system_prompt="Role: {{ env.TELIZE_ROLE }}",
    )
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main"),
        models={"default": model_config},
        base_path=Path("."),
    )
    step = LlmStep(name="a", model="default", prompt="hi")
    renderer = TemplateRenderer(build_template_context(state))
    ctx = ActionContext(state=state, renderer=renderer, base_path=Path("."))
    assert render_system_prompt(ctx, resolve_model_config(ctx, step)) == "Role: editor"


def test_render_system_prompt_none_when_unset() -> None:
    model_config = ModelConfig(provider="openai", model="m")
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main"),
        models={"default": model_config},
        base_path=Path("."),
    )
    step = LlmStep(name="a", model="default", prompt="hi")
    renderer = TemplateRenderer(build_template_context(state))
    ctx = ActionContext(state=state, renderer=renderer, base_path=Path("."))
    assert render_system_prompt(ctx, resolve_model_config(ctx, step)) is None
