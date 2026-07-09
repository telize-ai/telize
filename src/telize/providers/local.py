from __future__ import annotations

from functools import lru_cache

from fastembed import TextEmbedding

from telize.config.models import ModelConfig
from telize.exceptions import ExecutionError


@lru_cache(maxsize=8)
def _load_model(model_name: str) -> TextEmbedding:
    try:
        return TextEmbedding(model_name=model_name)
    except Exception as exc:
        raise ExecutionError(f"Could not load local embedding model {model_name!r}: {exc}") from exc


def embed_texts(model_config: ModelConfig, texts: list[str]) -> list[list[float]]:
    """Embed texts with a local ONNX model via fastembed (no API, no LangChain)."""
    if not texts:
        return []

    model = _load_model(model_config.model)
    return [list(vector) for vector in model.embed(texts)]
