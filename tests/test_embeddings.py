from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from telize.config.models import ModelConfig
from telize.exceptions import ExecutionError
from telize.providers.embeddings import embed_texts


def test_embed_texts_local() -> None:
    model_config = ModelConfig(provider="local", model="sentence-transformers/all-MiniLM-L6-v2")
    mock_model = MagicMock()
    mock_model.embed.return_value = [
        np.array([1.0, 0.0], dtype=np.float32),
        np.array([0.0, 1.0], dtype=np.float32),
    ]

    with patch("telize.providers.local._load_model", return_value=mock_model):
        vectors = embed_texts(model_config, ["hello", "world"])

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    mock_model.embed.assert_called_once_with(["hello", "world"])


def test_embed_texts_unknown_provider() -> None:
    model_config = ModelConfig(provider="openai", model="nomic-embed-text")
    with pytest.raises(ExecutionError, match="not supported"):
        embed_texts(model_config, ["hello"])
