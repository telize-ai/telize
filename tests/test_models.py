from pathlib import Path

import pytest

from telize.config import load_spec
from telize.config.models import LoopConfig

FIXTURES = Path(__file__).parent / "fixtures"
HELLO_AGENT = FIXTURES / "hello_agent_workflow.yaml"


def test_load_hello_agent_fixture() -> None:
    spec = load_spec(HELLO_AGENT)
    assert spec.config.entrypoint == "release_pipeline"
    assert spec.models["default"].api_url == "http://localhost:11434"
    assert spec.models["default"].model == "qwen3.5:4b"
    assert spec.models["default"].system_prompt == "You are a helpful assistant."
    assert spec.models["default"].thinking is True
    assert "release_pipeline" in spec.flows
    assert "risk_assessment_swarm" in spec.flows

    main = spec.flows["release_pipeline"]
    assert len(main.steps) == 10
    assert main.steps[0].uses == "input"
    assert main.steps[2].uses == "llm"
    assert main.steps[2].model == "default"

    swarm = spec.flows["risk_assessment_swarm"]
    assert len(swarm.steps) == 2
    assert swarm.steps[0].name == "legal_agent"


def test_loop_config_default_split_by() -> None:
    loop = LoopConfig(items="{{ steps.foo.output }}")
    assert loop.split_by == "\n<|separator|>\n"
    assert loop.separator == "\n<|separator|>\n"


def test_vars_default_empty() -> None:
    spec = load_spec(HELLO_AGENT)
    assert spec.vars == {}


def test_vars_loaded_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "workflow.yaml"
    path.write_text(
        """
config:
  entrypoint: main
vars:
  hosts: "192.168.0.1, 192.168.0.2"
  retry: true
  count: 3
flows:
  main:
    steps:
      - name: noop
        uses: shell
        run: echo ok
""",
        encoding="utf-8",
    )
    spec = load_spec(path)
    assert spec.vars["hosts"] == "192.168.0.1, 192.168.0.2"
    assert spec.vars["retry"] is True
    assert spec.vars["count"] == 3


def test_llm_step_fields() -> None:
    spec = load_spec(HELLO_AGENT)
    hashtags = spec.flows["release_pipeline"].steps[5]
    assert hashtags.name == "generate_hashtags"
    assert hashtags.uses == "llm"
    assert hashtags.model == "default"
    assert hashtags.loop is not None
    assert hashtags.loop.split_by == ","


def test_duplicate_step_names_rejected() -> None:
    from telize.exceptions import ConfigError

    with pytest.raises(ConfigError, match="duplicate step name"):
        load_spec(FIXTURES / "invalid_duplicate_step.yaml")


def test_unknown_llm_model_rejected(tmp_path: Path) -> None:
    from telize.exceptions import ConfigError

    path = tmp_path / "workflow.yaml"
    path.write_text(
        """
config:
  entrypoint: main
models:
  default:
    provider: openai
    model: m
    api_url: http://localhost:11434
flows:
  main:
    steps:
      - name: a
        uses: llm
        model: missing
        prompt: hi
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="unknown model"):
        load_spec(path)


def test_model_thinking_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "workflow.yaml"
    path.write_text(
        """
config:
  entrypoint: main
models:
  default:
    provider: openai
    model: m
    api_url: http://localhost:11434
    thinking: false
flows:
  main:
    steps:
      - name: a
        uses: llm
        model: default
        prompt: hi
""",
        encoding="utf-8",
    )
    spec = load_spec(path)
    assert spec.models["default"].thinking is False
