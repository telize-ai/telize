from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def mock_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid requiring a running Ollama instance during unit tests."""
    monkeypatch.setattr(
        "telize.runtime.actions.llm.generate_completion",
        lambda _ctx, prompt: f"ollama:{prompt}",
    )
