from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid requiring a live LLM endpoint during unit tests."""
    monkeypatch.setattr(
        "telize.runtime.actions.llm.generate_completion",
        lambda _ctx, _step, prompt: f"llm:{prompt}",
    )
