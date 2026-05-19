from __future__ import annotations

from typing import Protocol, Self, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal chat interface shared by all LLM providers."""

    def chat(self, prompt: str, *, system: str | None = None) -> str:
        """Return the assistant reply for a user prompt."""
        ...

    def close(self) -> None:
        """Release underlying connections."""
        ...

    def __enter__(self) -> Self: ...

    def __exit__(self, *args: object) -> None: ...
