from __future__ import annotations

from pathlib import Path


def resolve_under_base(base: Path, relative: str) -> Path:
    """Resolve a path relative to the workflow file directory."""
    path = Path(relative)
    return path if path.is_absolute() else (base / path).resolve()
