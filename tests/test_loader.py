from pathlib import Path
from textwrap import dedent

import pytest

from telize.config import load_spec
from telize.exceptions import ConfigError

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_minimal_workflow() -> None:
    spec = load_spec(FIXTURES / "minimal_workflow.yaml")
    assert spec.config.entrypoint == "main"
    assert len(spec.flows["main"].steps) == 2


def test_missing_file() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_spec(FIXTURES / "missing.yaml")


def test_invalid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("config: [\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_spec(path)


def test_unknown_entrypoint(tmp_path: Path) -> None:
    path = tmp_path / "bad_entry.yaml"
    path.write_text(
        dedent("""
            config:
              entrypoint: missing
            flows:
              main:
                steps:
                  - name: a
                    uses: shell
                    run: echo
        """),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="Invalid workflow spec"):
        load_spec(path)
