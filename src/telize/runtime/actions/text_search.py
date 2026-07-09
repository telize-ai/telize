from __future__ import annotations

from telize.config.models import Step, TextSearchStep
from telize.exceptions import ExecutionError
from telize.providers.embeddings import embed_texts
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.actions.llm import resolve_model_config
from telize.runtime.paths import resolve_under_base
from telize.runtime.search import IndexConfig, ensure_index, format_hits, search_index
from telize.runtime.state import StepResult


class TextSearchActionExecutor(ActionExecutor):
    uses = "text_search"

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        if not isinstance(step, TextSearchStep):
            raise ExecutionError(f"expected text_search step, got {step.uses}")

        model_config = resolve_model_config(ctx, step)
        source_dir = resolve_under_base(ctx.base_path, step.path)
        if not source_dir.is_dir():
            raise ExecutionError(f"text_search path not found: {source_dir}")

        query = ctx.renderer.render(step.search)
        index_config = IndexConfig(
            step_name=step.name,
            source_dir=source_dir,
            include=step.include,
            model_name=model_config.model,
            model_provider=model_config.provider,
            chunk_size=step.chunk_size,
            chunk_overlap=step.chunk_overlap,
            semantic_threshold=step.semantic_threshold,
            ttl=step.ttl,
        )

        def embed(texts: list[str]) -> list[list[float]]:
            return embed_texts(model_config, texts)

        collection = ensure_index(
            base_path=ctx.base_path,
            config=index_config,
            embed=embed,
        )
        hits = search_index(
            collection,
            query=query,
            embed=embed,
            top_k=step.top_k,
            min_score=step.min_score,
        )
        output = format_hits(hits)
        return StepResult(name=step.name, output=output)
