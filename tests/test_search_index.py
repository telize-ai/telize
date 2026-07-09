from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import telize.runtime.search.index as index_module
from telize.runtime.search.index import CHROMA_ADD_BATCH_SIZE, IndexConfig, _write_index


def test_write_index_batches_chroma_add_calls(tmp_path: Path) -> None:
    client = MagicMock()
    collection = MagicMock()
    client.create_collection.return_value = collection

    source_dir = tmp_path / "docs"
    source_dir.mkdir()
    file_path = source_dir / "big.txt"
    file_path.write_text("word " * 5000, encoding="utf-8")

    chunk_count = CHROMA_ADD_BATCH_SIZE + 10
    source_files = [file_path]
    config = IndexConfig(
        step_name="search",
        source_dir=source_dir,
        include="*.txt",
        model_name="test",
        model_provider="local",
        chunk_size=1000,
        chunk_overlap=0,
        semantic_threshold=0.0,
        ttl=3600,
    )

    def embed(texts: list[str]) -> list[list[float]]:
        return [[float(index)] for index, _ in enumerate(texts)]

    original_iter = index_module._iter_files_with_progress
    original_chunk = index_module.semantic_chunk_text

    try:
        index_module._iter_files_with_progress = lambda files, _dir: iter(files)
        index_module.semantic_chunk_text = lambda *_args, **_kwargs: [
            f"chunk-{index}" for index in range(chunk_count)
        ]

        _write_index(client, config, source_files, embed)
    finally:
        index_module._iter_files_with_progress = original_iter
        index_module.semantic_chunk_text = original_chunk

    assert collection.add.call_count == 2
    assert len(collection.add.call_args_list[0].kwargs["ids"]) == CHROMA_ADD_BATCH_SIZE
    assert len(collection.add.call_args_list[1].kwargs["ids"]) == 10
