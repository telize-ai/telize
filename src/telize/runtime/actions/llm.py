from __future__ import annotations

from pathlib import Path

from telize.config.models import LlmStep, ModelConfig, Step
from telize.exceptions import ExecutionError
from telize.providers import get_llm_client
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.context import build_template_context
from telize.runtime.paths import resolve_under_base
from telize.runtime.state import StepResult
from telize.templating.renderer import TemplateRenderer


def resolve_model_config(ctx: ActionContext, step: LlmStep) -> ModelConfig:
    """Look up the model definition referenced by an llm step."""
    try:
        return ctx.state.models[step.model]
    except KeyError as exc:
        known = ", ".join(sorted(ctx.state.models)) or "(none)"
        raise ExecutionError(f"Unknown model {step.model!r}. Defined models: {known}") from exc


def render_system_prompt(ctx: ActionContext, model_config: ModelConfig) -> str | None:
    """Render model system_prompt with the current execution context."""
    raw = model_config.system_prompt
    if not raw:
        return None
    return ctx.renderer.render(raw)


def generate_completion(ctx: ActionContext, step: LlmStep, prompt: str) -> str:
    """Send a prompt to the LLM provider configured for the step's model."""
    model_config = resolve_model_config(ctx, step)
    system = render_system_prompt(ctx, model_config)
    with get_llm_client(model_config) as client:
        return client.chat(prompt, system=system)


class LlmActionExecutor(ActionExecutor):
    """LLM steps backed by a named model from the workflow `models` section."""

    uses = "llm"

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        if not isinstance(step, LlmStep):
            raise ExecutionError(f"expected llm step, got {step.uses}")

        if step.loop is None:
            prompt = ctx.renderer.render(step.prompt)
            output = generate_completion(ctx, step, prompt)
            return _finalize(step, output, ctx)

        loop = step.loop
        model_config = resolve_model_config(ctx, step)
        system = render_system_prompt(ctx, model_config)
        items_raw = ctx.renderer.render(loop.items)
        items = [part.strip() for part in items_raw.split(loop.split_by) if part.strip()]
        outputs: list[str] = []
        with get_llm_client(model_config) as client:
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
