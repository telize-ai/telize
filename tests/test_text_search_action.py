from __future__ import annotations

import json
import math
import time
from pathlib import Path

import pytest

from telize.config import load_spec
from telize.exceptions import ConfigError
from telize.runtime import WorkflowRunner


def _mock_embed(_model_config: object, texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        values = [0.0] * 8
        lower = text.lower()
        values[0] += lower.count("project") * 3.0
        values[1] += lower.count("x") * 3.0
        for token in lower.split():
            values[hash(token) % 8] += 1.0
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        vectors.append([value / norm for value in values])
    return vectors


@pytest.fixture(autouse=True)
def _patch_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("telize.runtime.actions.text_search.embed_texts", _mock_embed)


def _write_search_workflow(
    tmp_path: Path,
    *,
    ttl: int = 3600,
    search: str = "project X",
) -> Path:
    docs = tmp_path / "data" / "files"
    docs.mkdir(parents=True)
    (docs / "alpha.md").write_text(
        "Notes about project X milestones and delivery.",
        encoding="utf-8",
    )
    (docs / "beta.md").write_text("Unrelated cooking recipes and pantry ideas.", encoding="utf-8")

    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        f"""
config:
  entrypoint: main
models:
  embeddings:
    provider: local
    model: sentence-transformers/all-MiniLM-L6-v2
flows:
  main:
    steps:
      - name: search_local
        uses: text_search
        path: {docs.as_posix()}
        ttl: {ttl}
        model: embeddings
        search: "{search}"
        top_k: 1
""",
        encoding="utf-8",
    )
    return workflow


def test_text_search_returns_relevant_chunks(tmp_path: Path) -> None:
    workflow = _write_search_workflow(tmp_path)

    state = WorkflowRunner(load_spec(workflow), workflow).run()
    output = state.steps["search_local"].output

    assert "project X" in output
    assert "alpha.md" in output
    assert output.startswith("## Result 1")


def test_text_search_creates_cache_files(tmp_path: Path) -> None:
    workflow = _write_search_workflow(tmp_path)

    WorkflowRunner(load_spec(workflow), workflow).run()

    cache_dir = tmp_path / ".cache"
    assert (cache_dir / "search_local.db").exists()
    assert (cache_dir / "search_local.meta.json").exists()


def test_text_search_reindexes_when_source_file_changes(tmp_path: Path) -> None:
    workflow = _write_search_workflow(tmp_path)
    runner = WorkflowRunner(load_spec(workflow), workflow)
    runner.run()

    meta_path = tmp_path / ".cache" / "search_local.meta.json"
    first_indexed_at = json.loads(meta_path.read_text(encoding="utf-8"))["indexed_at"]

    docs = tmp_path / "data" / "files"
    (docs / "gamma.md").write_text("New file about project X expansion.", encoding="utf-8")
    time.sleep(0.01)

    runner.run()
    second_indexed_at = json.loads(meta_path.read_text(encoding="utf-8"))["indexed_at"]
    assert second_indexed_at > first_indexed_at


def test_text_search_reindexes_when_ttl_expires(tmp_path: Path) -> None:
    workflow = _write_search_workflow(tmp_path, ttl=1)
    runner = WorkflowRunner(load_spec(workflow), workflow)
    runner.run()

    meta_path = tmp_path / ".cache" / "search_local.meta.json"
    first_indexed_at = json.loads(meta_path.read_text(encoding="utf-8"))["indexed_at"]

    time.sleep(1.05)
    runner.run()
    second_indexed_at = json.loads(meta_path.read_text(encoding="utf-8"))["indexed_at"]
    assert second_indexed_at > first_indexed_at


def test_unknown_text_search_model_rejected(tmp_path: Path) -> None:
    path = tmp_path / "workflow.yaml"
    path.write_text(
        """
config:
  entrypoint: main
models:
  embeddings:
    provider: local
    model: sentence-transformers/all-MiniLM-L6-v2
flows:
  main:
    steps:
      - name: search_local
        uses: text_search
        path: ./docs
        model: missing
        search: hello
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="unknown model"):
        load_spec(path)
