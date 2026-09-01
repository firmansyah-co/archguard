"""
CLI integration tests for ArchGuard Deterministic Versioning commands.
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


def test_cli_version_compute(tmp_path: Path):
    """Test 'archguard version compute' calculates version from Git history."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    (tmp_path / "README.md").write_text("# Init\n", encoding="utf-8")
    run_git(["add", "README.md"], tmp_path)
    run_git(["commit", "-m", "chore: initial release"], tmp_path)
    run_git(["tag", "-a", "v0.1.0", "-m", "Release v0.1.0"], tmp_path)

    res = runner.invoke(app, ["version", "compute", "--path", str(tmp_path), "--format", "pep440"])
    assert res.exit_code == 0
    assert "0.1.0" in res.stdout


def test_cli_version_compute_with_distance(tmp_path: Path):
    """Test 'archguard version compute' includes distance + SHA for dev/pre-release."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    (tmp_path / "README.md").write_text("# Init\n", encoding="utf-8")
    run_git(["add", "README.md"], tmp_path)
    run_git(["commit", "-m", "chore: initial"], tmp_path)
    run_git(["tag", "-a", "v0.1.0", "-m", "Release v0.1.0"], tmp_path)
    
    # Add another commit after tag
    (tmp_path / "feature.txt").write_text("feature\n", encoding="utf-8")
    run_git(["add", "feature.txt"], tmp_path)
    run_git(["commit", "-m", "feat: add feature"], tmp_path)

    res = runner.invoke(app, ["version", "compute", "--path", str(tmp_path), "--format", "pep440", "--branch", "dev"])
    assert res.exit_code == 0
    # Expect pre-release format: 0.1.0a1+g<sha>
    assert "0.1.0a1+g" in res.stdout


def test_cli_version_sync_dry_run(tmp_path: Path):
    """Test 'archguard version sync --dry-run' shows changes without modifying files."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "testpkg"\nversion = "0.0.0"\n', encoding="utf-8")
    
    (tmp_path / "README.md").write_text("# Init\n", encoding="utf-8")
    run_git(["add", "."], tmp_path)
    run_git(["commit", "-m", "chore: initial"], tmp_path)
    run_git(["tag", "-a", "v0.1.0", "-m", "Release v0.1.0"], tmp_path)

    res = runner.invoke(app, ["version", "sync", "--path", str(tmp_path), "--dry-run"])
    assert res.exit_code == 0
    assert "DRY RUN" in res.stdout
    assert "0.0.0" in res.stdout
    assert "0.1.0" in res.stdout
    
    # Verify file not actually modified
    assert 'version = "0.0.0"' in pyproject.read_text(encoding="utf-8")


def test_cli_version_sync_applies_changes(tmp_path: Path):
    """Test 'archguard version sync' actually modifies version files."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "testpkg"\nversion = "0.0.0"\n', encoding="utf-8")
    
    (tmp_path / "README.md").write_text("# Init\n", encoding="utf-8")
    run_git(["add", "."], tmp_path)
    run_git(["commit", "-m", "chore: initial"], tmp_path)
    run_git(["tag", "-a", "v0.2.0", "-m", "Release v0.2.0"], tmp_path)

    res = runner.invoke(app, ["version", "sync", "--path", str(tmp_path)])
    assert res.exit_code == 0
    assert "Synchronized" in res.stdout or "in sync" in res.stdout.lower()
    
    # Verify file was actually modified
    content = pyproject.read_text(encoding="utf-8")
    assert 'version = "0.2.0"' in content


def test_cli_check_with_versioning_flag(tmp_path: Path):
    """Test 'archguard check --versioning' runs versioning validator."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "Test User"], tmp_path)
    run_git(["config", "user.email", "test@test.com"], tmp_path)
    (tmp_path / "README.md").write_text("# Init\n", encoding="utf-8")
    run_git(["add", "README.md"], tmp_path)
    run_git(["commit", "-m", "chore: init"], tmp_path)

    res = runner.invoke(app, ["check", "--path", str(tmp_path), "--versioning"])
    assert res.exit_code == 0
    assert "versioning_validator" in res.stdout
