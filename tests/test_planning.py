from __future__ import annotations

from pathlib import Path

from telize.config import load_spec
from telize.runtime.planning import estimate_step_count

ROOT = Path(__file__).resolve().parents[1]


def test_estimate_spec_reference_steps() -> None:
    spec = load_spec(ROOT / "examples" / "spec_reference.yaml")
    count = estimate_step_count(spec, "release_pipeline")
    # 10 steps in main + 2 in subflow referenced once
    assert count == 12
