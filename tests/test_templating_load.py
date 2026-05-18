from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from telize.config import load_spec
from telize.templating.load import _references_only_env, render_env_templates


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("http://{{ env.HOST }}:11434", True),
        ("{{ steps.foo.output }}", False),
        ("host={{ env.HOST }} path={{ steps.x.output }}", False),
        ("plain text", False),
    ],
)
def test_references_only_env(template: str, expected: bool) -> None:
    assert _references_only_env(template) is expected


def test_runtime_prompt_unchanged_at_load(tmp_path: Path) -> None:
    path = tmp_path / "workflow.yaml"
    path.write_text(
        dedent("""
            config:
              entrypoint: main
            flows:
              main:
                steps:
                  - name: a
                    uses: llm
                    prompt: "Result: {{ steps.other.output }}"
        """),
        encoding="utf-8",
    )
    spec = load_spec(path)
    step = spec.flows["main"].steps[0]
    assert step.prompt == "Result: {{ steps.other.output }}"


def test_render_env_templates_nested() -> None:
    data = {
        "config": {"api_base_url": "http://{{ env.HOST }}:11434"},
        "flows": {"main": {"steps": [{"prompt": "{{ steps.x.output }}"}]}},
    }
    import os

    os.environ["HOST"] = "ollama.local"
    rendered = render_env_templates(data)
    assert rendered["config"]["api_base_url"] == "http://ollama.local:11434"
    assert rendered["flows"]["main"]["steps"][0]["prompt"] == "{{ steps.x.output }}"
