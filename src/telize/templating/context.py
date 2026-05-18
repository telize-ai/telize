from __future__ import annotations

import os
from typing import Any


def build_env_context() -> dict[str, Any]:
    """Jinja context with environment variables (`{{ env.VAR }}`)."""
    return {"env": dict(os.environ)}
