from __future__ import annotations

from telize.config.models import ModelConfig
from telize.exceptions import ExecutionError
from telize.providers.local import embed_texts as embed_texts_local


def embed_texts(model_config: ModelConfig, texts: list[str]) -> list[list[float]]:
    """Return embedding vectors for ``texts`` using the configured provider."""
    if not texts:
        return []

    if model_config.provider == "local":
        return embed_texts_local(model_config, texts)

    msg = (
        f"Embedding provider {model_config.provider!r} is not supported. "
        "Use provider: local with a HuggingFace model id "
        "(e.g. sentence-transformers/all-MiniLM-L6-v2)."
    )
    raise ExecutionError(msg)
