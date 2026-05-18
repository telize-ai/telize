from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest

from telize.config import load_spec
from telize.exceptions import ConfigError

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "hello_simple.yaml"


def test_api_base_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "192.168.1.50")
    spec = load_spec(EXAMPLE)
    assert spec.config.api_base_url == "http://192.168.1.50"


def test_missing_env_var_in_config(tmp_path: Path) -> None:
    path = tmp_path / "workflow.yaml"
    path.write_text(
        dedent("""
            config:
              entrypoint: main
              api_base_url: http://{{ env.TELIZE_MISSING_VAR_XYZ }}:11434
            flows:
              main:
                steps:
                  - name: a
                    uses: shell
                    run: echo ok
        """),
        encoding="utf-8",
    )
    env_before = os.environ.pop("TELIZE_MISSING_VAR_XYZ", None)
    try:
        with pytest.raises(ConfigError, match=r"TELIZE_MISSING_VAR_XYZ|Template error"):
            load_spec(path)
    finally:
        if env_before is not None:
            os.environ["TELIZE_MISSING_VAR_XYZ"] = env_before


def test_env_in_step_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELIZE_GREETING", "from-env")
    path = tmp_path / "workflow.yaml"
    path.write_text(
        dedent("""
            config:
              entrypoint: main
            flows:
              main:
                steps:
                  - name: a
                    uses: shell
                    run: echo "{{ env.TELIZE_GREETING }}"
        """),
        encoding="utf-8",
    )
    spec = load_spec(path)
    step = spec.flows["main"].steps[0]
    assert step.uses == "shell"
    assert step.run == 'echo "from-env"'
