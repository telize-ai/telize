from pathlib import Path

import pytest

from telize.config import load_spec
from telize.runtime import WorkflowRunner
from telize.runtime.actions.chat import ChatActionExecutor
from telize.runtime.actions.registry import ActionRegistry
from telize.runtime.actions.shell import ShellActionExecutor

FIXTURES = Path(__file__).parent / "fixtures"


def test_chat_step_returns_user_input(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
flows:
  main:
    steps:
      - name: user_chat
        uses: chat
        message: "What is your name?"
      - name: greet
        uses: shell
        run: echo "hello {{ steps.user_chat.output }}"
""",
        encoding="utf-8",
    )

    registry = ActionRegistry()
    registry.register(ChatActionExecutor(prompt_user_fn=lambda _msg: "Ada"))
    registry.register(ShellActionExecutor())

    state = WorkflowRunner(load_spec(workflow), workflow, registry=registry).run()
    assert state.steps["user_chat"].output == "Ada"
    assert state.steps["greet"].output.strip() == "hello Ada"


def test_chat_step_without_message(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
flows:
  main:
    steps:
      - name: user_chat
        uses: chat
""",
        encoding="utf-8",
    )

    registry = ActionRegistry()
    registry.register(ChatActionExecutor(prompt_user_fn=lambda _msg: "plain reply"))

    state = WorkflowRunner(load_spec(workflow), workflow, registry=registry).run()
    assert state.steps["user_chat"].output == "plain reply"


def test_chat_message_supports_templates(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
flows:
  main:
    steps:
      - name: seed
        uses: shell
        run: echo -n topic
      - name: user_chat
        uses: chat
        message: "Continue on {{ steps.seed.output }}:"
""",
        encoding="utf-8",
    )

    seen: list[str] = []

    def capture(message: str) -> str:
        seen.append(message)
        return "ok"

    registry = ActionRegistry()
    registry.register(ShellActionExecutor())
    registry.register(ChatActionExecutor(prompt_user_fn=capture))

    WorkflowRunner(load_spec(workflow), workflow, registry=registry).run()
    assert seen == ["Continue on topic:"]


def test_chat_eof_raises_keyboard_interrupt(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
flows:
  main:
    steps:
      - name: user_chat
        uses: chat
""",
        encoding="utf-8",
    )

    def raise_eof(_message: str) -> str:
        raise EOFError

    registry = ActionRegistry()
    registry.register(ChatActionExecutor(prompt_user_fn=raise_eof))

    with pytest.raises(KeyboardInterrupt):
        WorkflowRunner(load_spec(workflow), workflow, registry=registry).run()
