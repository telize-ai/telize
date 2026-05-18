from __future__ import annotations

import re
from typing import Any

from telize.templating.context import build_env_context
from telize.templating.renderer import TemplateRenderer

# Matches {{ expr }} and {{- expr -}} (no nested braces).
_TEMPLATE_REF = re.compile(r"\{\{-?\s*([^}%]+?)\s*-?\}\}")


def _references_only_env(template: str) -> bool:
    """True when every Jinja expression in the string uses only `env.*`."""
    refs = _TEMPLATE_REF.findall(template)
    if not refs:
        return False
    return all(ref.strip().startswith("env.") for ref in refs)


def render_env_templates(value: Any) -> Any:
    """Recursively render strings that reference `{{ env.VAR }}` at load time.

    Runtime templates (`steps.*`, `item`, etc.) are left unchanged so they can
    be resolved when the workflow executes.
    """
    renderer = TemplateRenderer(build_env_context())

    def walk(node: Any) -> Any:
        if isinstance(node, str):
            if _references_only_env(node):
                return renderer.render(node)
            return node
        if isinstance(node, dict):
            return {key: walk(val) for key, val in node.items()}
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(value)
