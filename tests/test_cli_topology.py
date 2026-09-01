"""
CLI integration tests for ArchGuard Git Topology commands.
"""

from pathlib import Path
import subprocess
from typer.testing import CliRunner
from archguard.cli.main import app

runner = CliRunner()


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def test_cli_topology_init(tmp_path: Path):
    """Test 'archguard topology init' creates config and dev branch."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    (tmp_path / "README.md").write_text("# Init\n", encoding="utf-8")
    run_git(["add", "README.md"], tmp_path)
    run_git(["commit", "-m", "chore: init"], tmp_path)

    res = runner.invoke(app, ["topology", "init", "--path", str(tmp_path), "--type", "production", "--create-dev"])
    assert res.exit_code == 0
    assert "Git topology initialized" in res.stdout

    # Check that dev branch now exists
    proc = subprocess.run(["git", "branch", "--list", "dev"], cwd=str(tmp_path), capture_output=True, text=True)
    assert "dev" in proc.stdout


def test_cli_topology_validate(tmp_path: Path):
    """Test 'archguard topology validate' runs audit and outputs JSON."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    (tmp_path / "README.md").write_text("# Init\n", encoding="utf-8")
    run_git(["add", "README.md"], tmp_path)
    run_git(["commit", "-m", "chore: init"], tmp_path)
    run_git(["branch", "dev"], tmp_path)

    res = runner.invoke(app, ["topology", "validate", "--path", str(tmp_path)])
    assert res.exit_code == 0
    assert '"passed": true' in res.stdout


def test_cli_check_with_topology_flag(tmp_path: Path):
    """Test 'archguard check --topology' runs Git topology and repo hygiene checks."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    (tmp_path / "README.md").write_text("# Init\n", encoding="utf-8")
    (tmp_path / "docs" / "adr").mkdir(parents=True, exist_ok=True)
    run_git(["add", "."], tmp_path)
    run_git(["commit", "-m", "chore: init"], tmp_path)
    run_git(["branch", "dev"], tmp_path)

    res = runner.invoke(app, ["check", "--path", str(tmp_path), "--topology"])
    assert res.exit_code == 0
    # Both topology validators should be present in output (may be truncated in table display)
    assert "topology_valida" in res.stdout or "git_topology" in res.stdout
    assert "PASSED" in res.stdout
