import subprocess
import sys
import tomllib
from pathlib import Path

from telize import __version__


def _pyproject_version() -> str:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def test_version_constant() -> None:
    assert __version__ == _pyproject_version()


def test_cli_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "telize", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == f"telize {__version__}"
