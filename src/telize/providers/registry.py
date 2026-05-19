from __future__ import annotations

from collections.abc import Callable

from telize.config.models import ModelConfig
from telize.exceptions import ExecutionError
from telize.providers.base import LLMClient

ProviderFactory = Callable[[ModelConfig], LLMClient]

_REGISTRY: dict[str, ProviderFactory] = {}


def register_provider(name: str, factory: ProviderFactory) -> None:
    """Register a provider factory under ``name`` (e.g. ``"openai"``)."""
    _REGISTRY[name] = factory


def get_llm_client(model_config: ModelConfig) -> LLMClient:
    """Instantiate the LLM client for ``model_config.provider``."""
    try:
        factory = _REGISTRY[model_config.provider]
    except KeyError as exc:
        known = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise ExecutionError(
            f"Unknown LLM provider {model_config.provider!r}. Registered providers: {known}"
        ) from exc
    return factory(model_config)


def registered_providers() -> tuple[str, ...]:
    """Return registered provider names (for diagnostics)."""
    return tuple(sorted(_REGISTRY))
