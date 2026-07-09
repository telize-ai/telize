from __future__ import annotations

from telize.config.models import LlmStep, ModelConfig, Step, TextSearchStep
from telize.exceptions import ExecutionError
from telize.providers import get_llm_client
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.state import StepResult


def resolve_model_config(ctx: ActionContext, step: LlmStep | TextSearchStep) -> ModelConfig:
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

        prompt = ctx.renderer.render(step.prompt)
        output = generate_completion(ctx, step, prompt)
        return StepResult(name=step.name, output=output)
