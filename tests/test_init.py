import subprocess
import sys
from pathlib import Path

import pytest

from telize.exceptions import ConfigError
from telize.scaffold import create_starter_project, normalize_flow_name


def test_normalize_flow_name_strips_yaml_suffix() -> None:
    assert normalize_flow_name("demo.yaml") == "demo"
    assert normalize_flow_name("demo.yml") == "demo"


def test_normalize_flow_name_rejects_invalid() -> None:
    with pytest.raises(ConfigError, match="empty"):
        normalize_flow_name("  ")

    with pytest.raises(ConfigError, match="invalid flow name"):
        normalize_flow_name("../escape")

    with pytest.raises(ConfigError, match="invalid flow name"):
        normalize_flow_name("-bad-start")


def test_create_starter_project_writes_files(tmp_path: Path) -> None:
    result = create_starter_project("my_flow", target_dir=tmp_path)

    assert result.workflow == tmp_path / "my_flow.yaml"
    assert result.readme == tmp_path / "README.md"
    assert result.process_module == tmp_path / "scripts" / "process.py"
    assert result.workflow.is_file()
    assert result.readme.is_file()
    assert result.process_module.is_file()
    assert "scripts.process.process_func" in result.workflow.read_text(encoding="utf-8")


def test_create_starter_project_refuses_overwrites(tmp_path: Path) -> None:
    create_starter_project("demo", target_dir=tmp_path)

    with pytest.raises(ConfigError, match="refusing to overwrite"):
        create_starter_project("demo", target_dir=tmp_path)


def test_init_workflow_runs_end_to_end(tmp_path: Path) -> None:
    create_starter_project("demo", target_dir=tmp_path)
    workflow = tmp_path / "demo.yaml"

    result = subprocess.run(
        [sys.executable, "-m", "telize", "-f", str(workflow)],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert "Received text of length: 9" in result.stdout


def test_cli_init_creates_and_prints_next_steps(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "telize", "--init", "hello"],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert (tmp_path / "hello.yaml").is_file()
    assert (tmp_path / "scripts" / "process.py").is_file()
    assert "telize -f hello.yaml" in result.stdout


def test_cli_init_conflicts_with_file_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "telize", "--init", "demo", "-f", "demo.yaml"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "cannot use --init together with -f/--file" in result.stderr
