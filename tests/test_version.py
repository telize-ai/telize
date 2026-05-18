import subprocess
import sys

from telize import __version__


def test_version_constant() -> None:
    assert __version__ == "0.1.0"


def test_cli_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "telize", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == f"telize {__version__}"
