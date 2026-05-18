from pathlib import Path

import pytest

from telize.config import load_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "hello_agent.yaml"
FIXTURES = Path(__file__).parent / "fixtures"


def test_load_hello_agent_example() -> None:
    spec = load_spec(EXAMPLE)
    assert spec.config.entrypoint == "release_pipeline"
    assert spec.config.api_base_url == "http://localhost:11434"
    assert spec.config.model == "qwen3.5:4b"
    assert "release_pipeline" in spec.flows
    assert "risk_assessment_swarm" in spec.flows

    main = spec.flows["release_pipeline"]
    assert len(main.steps) == 10
    assert main.steps[0].uses == "input"
    assert main.steps[2].uses == "llm"

    swarm = spec.flows["risk_assessment_swarm"]
    assert len(swarm.steps) == 2
    assert swarm.steps[0].name == "legal_agent"


def test_llm_step_fields() -> None:
    spec = load_spec(EXAMPLE)
    hashtags = spec.flows["release_pipeline"].steps[5]
    assert hashtags.name == "generate_hashtags"
    assert hashtags.uses == "llm"
    assert hashtags.loop is not None
    assert hashtags.loop.split_by == ","


def test_duplicate_step_names_rejected() -> None:
    from telize.exceptions import ConfigError

    with pytest.raises(ConfigError, match="duplicate step name"):
        load_spec(FIXTURES / "invalid_duplicate_step.yaml")
