from __future__ import annotations

import math
import re
from collections.abc import Callable

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE_RE.split(text.strip()) if part.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def semantic_chunk_text(
    text: str,
    *,
    embed: Callable[[list[str]], list[list[float]]],
    chunk_size: int,
    chunk_overlap: int,
    semantic_threshold: float,
) -> list[str]:
    """Split text at semantic boundaries using embedding similarity between sentences."""
    sentences = split_sentences(text)
    if not sentences:
        return []
    if len(sentences) == 1 and len(sentences[0]) <= chunk_size:
        return sentences

    embeddings = embed(sentences)
    chunks: list[str] = []
    current = sentences[0]

    for index in range(1, len(sentences)):
        sentence = sentences[index]
        similarity = cosine_similarity(embeddings[index - 1], embeddings[index])
        candidate = f"{current} {sentence}".strip()
        should_split = similarity < semantic_threshold or len(candidate) > chunk_size
        if should_split and current.strip():
            chunks.append(current.strip())
            overlap = _tail_overlap(current, chunk_overlap)
            current = f"{overlap} {sentence}".strip() if overlap else sentence
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return _merge_small_chunks(chunks, chunk_size)


def _tail_overlap(text: str, overlap: int) -> str:
    if overlap <= 0 or len(text) <= overlap:
        return ""
    return text[-overlap:]


def _merge_small_chunks(chunks: list[str], chunk_size: int) -> list[str]:
    if not chunks:
        return []
    merged: list[str] = []
    buffer = chunks[0]
    for chunk in chunks[1:]:
        if len(buffer) + len(chunk) + 1 <= chunk_size:
            buffer = f"{buffer} {chunk}".strip()
        else:
            merged.append(buffer)
            buffer = chunk
    merged.append(buffer)
    return merged
