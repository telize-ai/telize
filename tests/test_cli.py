import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "spec_reference.yaml"


def test_validate_example() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "telize", "-f", str(EXAMPLE), "--validate-only"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "release_pipeline" in result.stdout


def test_run_minimal_fixture() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "telize", "-f", str(FIXTURES / "shell_only.yaml")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "greet" in result.stdout
    assert "hello telize" in result.stdout
