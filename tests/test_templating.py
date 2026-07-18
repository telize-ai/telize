from pathlib import Path

import pytest

from telize.config.models import GlobalConfig
from telize.exceptions import ExecutionError
from telize.runtime.context import build_template_context
from telize.runtime.state import ExecutionState, StepResult
from telize.templating import TemplateRenderer
from telize.templating.renderer import coerce_condition_result


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


def test_render_vars() -> None:
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main"),
        base_path=Path("."),
        vars={"hosts": "192.168.0.1, 192.168.0.2", "retry": True},
    )
    renderer = TemplateRenderer(build_template_context(state))
    assert renderer.render("{{ vars.hosts }}") == "192.168.0.1, 192.168.0.2"
    assert renderer.render("retry={{ vars.retry }}") == "retry=True"


def test_evaluate_in_and_not_in() -> None:
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main"),
        base_path=Path("."),
    )
    state.set_step(StepResult(name="classify", output="status=ready keyword=ship-it"))
    renderer = TemplateRenderer(build_template_context(state))
    assert renderer.evaluate("{{ 'keyword=ship-it' in steps.classify.output }}") is True
    assert renderer.evaluate("{{ 'keyword=hold' in steps.classify.output }}") is False
    assert renderer.evaluate("{{ 'keyword=hold' not in steps.classify.output }}") is True


def test_evaluate_undefined_raises() -> None:
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main"),
        base_path=Path("."),
    )
    renderer = TemplateRenderer(build_template_context(state))
    with pytest.raises(ExecutionError, match="Template error"):
        renderer.evaluate("{{ 'x' in steps.missing.output }}")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (None, False),
        (0, False),
        (1, True),
        ("", False),
        ("false", False),
        ("True", True),
        ("yes", True),
        ("ship-it", True),
    ],
)
def test_coerce_condition_result(value: object, expected: bool) -> None:
    assert coerce_condition_result(value) is expected
