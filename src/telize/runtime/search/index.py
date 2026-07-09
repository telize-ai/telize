from __future__ import annotations

import contextlib
import json
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from telize.console.terminal import get_console
from telize.runtime.search.chunking import semantic_chunk_text

COLLECTION_NAME = "chunks"
EMBED_BATCH_SIZE = 64
CHROMA_ADD_BATCH_SIZE = 500


@dataclass(frozen=True)
class SearchHit:
    document: str
    source: str
    chunk_index: int
    score: float


@dataclass(frozen=True)
class IndexConfig:
    step_name: str
    source_dir: Path
    include: str
    model_name: str
    model_provider: str
    chunk_size: int
    chunk_overlap: int
    semantic_threshold: float
    ttl: int


def cache_paths(base_path: Path, step_name: str) -> tuple[Path, Path]:
    cache_dir = base_path / ".cache"
    return cache_dir / f"{step_name}.db", cache_dir / f"{step_name}.meta.json"


def ensure_index(
    *,
    base_path: Path,
    config: IndexConfig,
    embed: Callable[[list[str]], list[list[float]]],
) -> Collection:
    db_path, meta_path = cache_paths(base_path, config.step_name)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    source_files = _collect_files(config.source_dir, config.include)
    file_mtimes = {
        str(path.relative_to(config.source_dir)): path.stat().st_mtime for path in source_files
    }
    current_meta = _build_meta(config, file_mtimes)
    stored_meta = _read_meta(meta_path)

    client = chromadb.PersistentClient(path=str(db_path))
    if not _needs_reindex(db_path, stored_meta, current_meta, config.ttl):
        return client.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    collection = _write_index(client, config, source_files, embed)
    meta_path.write_text(json.dumps(current_meta, indent=2), encoding="utf-8")
    return collection


def search_index(
    collection: Collection,
    *,
    query: str,
    embed: Callable[[list[str]], list[list[float]]],
    top_k: int,
    min_score: float | None,
) -> list[SearchHit]:
    if collection.count() == 0:
        return []

    query_embedding = embed([query])[0]
    raw = collection.query(
        query_embeddings=cast(Any, [query_embedding]),
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = (raw.get("documents") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]
    distances = (raw.get("distances") or [[]])[0]

    hits: list[SearchHit] = []
    for document, metadata, distance in zip(documents, metadatas, distances, strict=True):
        if document is None:
            continue
        score = 1.0 - float(distance)
        if min_score is not None and score < min_score:
            continue
        meta = metadata or {}
        hits.append(
            SearchHit(
                document=document,
                source=str(meta.get("source", "")),
                chunk_index=int(cast(Any, meta.get("chunk_index", 0))),
                score=score,
            )
        )
    return hits


def format_hits(hits: list[SearchHit]) -> str:
    if not hits:
        return ""
    parts: list[str] = []
    for index, hit in enumerate(hits, start=1):
        header = (
            f"## Result {index} (score: {hit.score:.3f}, "
            f"source: {hit.source}, chunk: {hit.chunk_index})"
        )
        parts.append(f"{header}\n\n{hit.document}")
    return "\n\n<|separator|>\n\n".join(parts)


def _needs_reindex(
    db_path: Path,
    stored_meta: dict[str, Any] | None,
    current_meta: dict[str, Any],
    ttl: int,
) -> bool:
    if not db_path.exists() or stored_meta is None:
        return True
    if stored_meta.get("index_config") != current_meta.get("index_config"):
        return True
    if stored_meta.get("files") != current_meta.get("files"):
        return True
    indexed_at = float(stored_meta.get("indexed_at", 0.0))
    return bool(ttl > 0 and (time.time() - indexed_at) > ttl)


def _build_meta(config: IndexConfig, file_mtimes: dict[str, float]) -> dict[str, Any]:
    return {
        "indexed_at": time.time(),
        "index_config": {
            "model_provider": config.model_provider,
            "model_name": config.model_name,
            "include": config.include,
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap,
            "semantic_threshold": config.semantic_threshold,
        },
        "files": file_mtimes,
    }


def _read_meta(meta_path: Path) -> dict[str, Any] | None:
    if not meta_path.is_file():
        return None
    try:
        return cast(dict[str, Any], json.loads(meta_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        return None


def _collect_files(source_dir: Path, include: str) -> list[Path]:
    pattern = include if "/" in include or "**" in include else f"**/{include}"
    return sorted(path for path in source_dir.glob(pattern) if path.is_file())


def _write_index(
    client: ClientAPI,
    config: IndexConfig,
    source_files: list[Path],
    embed: Callable[[list[str]], list[list[float]]],
) -> Collection:
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []

    for file_path in _iter_files_with_progress(source_files, config.source_dir):
        rel_source = str(file_path.relative_to(config.source_dir))
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            get_console().print(
                f"[yellow]Skipping[/] [dim]{rel_source}[/] (not valid UTF-8 text)",
            )
            continue
        chunks = semantic_chunk_text(
            text,
            embed=embed,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            semantic_threshold=config.semantic_threshold,
        )
        for chunk_index, chunk in enumerate(chunks):
            ids.append(f"{rel_source}:{chunk_index}")
            documents.append(chunk)
            metadatas.append({"source": rel_source, "chunk_index": chunk_index})

    collection = _reset_collection(client)
    if not documents:
        return collection

    for start in range(0, len(documents), CHROMA_ADD_BATCH_SIZE):
        end = start + CHROMA_ADD_BATCH_SIZE
        batch_docs = documents[start:end]
        batch_embeddings = _embed_in_batches(embed, batch_docs)
        collection.add(
            ids=ids[start:end],
            documents=batch_docs,
            metadatas=cast(Any, metadatas[start:end]),
            embeddings=cast(Any, batch_embeddings),
        )
    return collection


def _embed_in_batches(
    embed: Callable[[list[str]], list[list[float]]],
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        vectors.extend(embed(texts[start : start + EMBED_BATCH_SIZE]))
    return vectors


def _reset_collection(client: ClientAPI) -> Collection:
    with contextlib.suppress(Exception):
        client.delete_collection(COLLECTION_NAME)
    return client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _iter_files_with_progress(source_files: list[Path], source_dir: Path) -> Iterator[Path]:
    """Yield source files, showing a Rich progress bar when writing to a terminal."""
    if not source_files:
        return

    console = get_console()
    if not console.is_terminal:
        yield from source_files
        return

    with Progress(
        SpinnerColumn(style="#a371f7"),
        TextColumn("[bold bright_blue]Indexing[/]"),
        BarColumn(
            bar_width=32,
            complete_style="bright_blue",
            finished_style="blue",
        ),
        MofNCompleteColumn(),
        TextColumn("•"),
        TextColumn("[dim]{task.fields[file]}[/]"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("index", total=len(source_files), file="")
        for file_path in source_files:
            rel_source = str(file_path.relative_to(source_dir))
            if len(rel_source) > 40:
                rel_source = f"…{rel_source[-39:]}"
            progress.update(task, file=rel_source)
            yield file_path
            progress.advance(task)
