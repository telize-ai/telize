from pathlib import Path

from telize.config.models import GlobalConfig
from telize.runtime.context import build_template_context
from telize.runtime.state import ExecutionState, StepResult
from telize.templating import TemplateRenderer


def test_render_step_output() -> None:
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main"),
        base_path=Path("."),
    )
    state.set_step(StepResult(name="greeter", output="Hello, world!"))
    renderer = TemplateRenderer(build_template_context(state))
    result = renderer.render("Greeting: {{ steps.greeter.output }}")
    assert result == "Greeting: Hello, world!"


def test_render_env() -> None:
    import os

    os.environ["TELIZE_TEST_VAR"] = "secret"
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main"),
        base_path=Path("."),
    )
    renderer = TemplateRenderer(build_template_context(state))
    assert renderer.render("{{ env.TELIZE_TEST_VAR }}") == "secret"
