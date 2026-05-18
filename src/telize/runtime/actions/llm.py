from __future__ import annotations

from pathlib import Path

from telize.config.models import LlmStep, Step
from telize.exceptions import ExecutionError
from telize.providers.ollama import OllamaClient
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.context import build_template_context
from telize.runtime.paths import resolve_under_base
from telize.runtime.state import StepResult
from telize.templating.renderer import TemplateRenderer


def render_system_prompt(ctx: ActionContext) -> str | None:
    """Render config.system_prompt with the current execution context."""
    raw = ctx.state.config.system_prompt
    if not raw:
        return None
    return ctx.renderer.render(raw)


def generate_completion(ctx: ActionContext, prompt: str) -> str:
    """Send a prompt to Ollama using workflow global config."""
    system = render_system_prompt(ctx)
    with OllamaClient.from_config(ctx.state.config) as client:
        return client.chat(prompt, system=system)


class LlmActionExecutor(ActionExecutor):
    """LLM steps backed by a local Ollama instance."""

    uses = "llm"

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        if not isinstance(step, LlmStep):
            raise ExecutionError(f"expected llm step, got {step.uses}")

        if step.loop is None:
            prompt = ctx.renderer.render(step.prompt)
            output = generate_completion(ctx, prompt)
            return _finalize(step, output, ctx)

        loop = step.loop
        items_raw = ctx.renderer.render(loop.items)
        items = [part.strip() for part in items_raw.split(loop.split_by) if part.strip()]
        system = render_system_prompt(ctx)
        outputs: list[str] = []
        with OllamaClient.from_config(ctx.state.config) as client:
            for item in items:
                loop_ctx = build_template_context(ctx.state, item=item)
                loop_renderer = TemplateRenderer(loop_ctx)
                prompt = loop_renderer.render(step.prompt)
                outputs.append(client.chat(prompt, system=system))
        combined = "\n---\n".join(outputs)
        return _finalize(step, combined, ctx)


def _finalize(step: LlmStep, output: str, ctx: ActionContext) -> StepResult:
    output_path: Path | None = None
    if step.output_to is not None:
        output_path = resolve_under_base(ctx.base_path, ctx.renderer.render(step.output_to))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    return StepResult(name=step.name, output=output, output_path=output_path)
