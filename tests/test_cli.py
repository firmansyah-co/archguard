"""
Integration tests for ArchGuard CLI commands.
"""

from pathlib import Path
from typer.testing import CliRunner
from archguard.cli.main import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ArchGuard Architecture Governance Engine" in result.stdout


def test_cli_init_and_check_scaffold(tmp_path: Path):
    # 1. Test init command
    init_res = runner.invoke(app, ["init", "--target", str(tmp_path), "--type", "fullstack"])
    assert init_res.exit_code == 0
    assert (tmp_path / "archguard.yaml").exists()
    assert (tmp_path / "docs" / "adr").exists()
    assert (tmp_path / "specs" / "001-initial-architecture" / "spec.md").exists()
    assert (tmp_path / "frontend" / "src" / "styles" / "tokens.css").exists()

    # 2. Test check command against scaffolded directory
    check_res = runner.invoke(app, ["check", "--path", str(tmp_path), "--all"])
    assert check_res.exit_code == 0
    assert "ZERO GOVERNANCE VIOLATIONS DETECTED" in check_res.stdout


def test_cli_ci_gen(tmp_path: Path):
    out_dir = tmp_path / ".github" / "workflows"
    gen_res = runner.invoke(app, ["ci-gen", "--out", str(out_dir)])
    assert gen_res.exit_code == 0
    assert (out_dir / "archguard-governance.yml").exists()


def test_cli_hook_install(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    hook_res = runner.invoke(app, ["hook", "install", "--git-dir", str(git_dir)])
    assert hook_res.exit_code == 0
    assert (git_dir / "hooks" / "pre-push").exists()


def test_cli_check_integrity_flag(tmp_path: Path):
    init_res = runner.invoke(app, ["init", "--target", str(tmp_path), "--type", "fullstack"])
    assert init_res.exit_code == 0

    # Test check with --integrity flag only
    check_res = runner.invoke(app, ["check", "--path", str(tmp_path), "--integrity"])
    assert check_res.exit_code == 0
    assert "data_integrity" in check_res.stdout
    assert "PASSED" in check_res.stdout


def test_cli_update_command(tmp_path: Path):
    # 1. Test update --project on empty dir
    res_proj = runner.invoke(app, ["update", "--project", "--target", str(tmp_path)])
    assert res_proj.exit_code == 0
    assert (tmp_path / ".github" / "workflows" / "archguard-governance.yml").exists()
    assert (tmp_path / "archguard.yaml").exists()
    assert "Project Asset Synchronization Matrix" in res_proj.stdout

    # 2. Test update default execution
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    res_default = runner.invoke(app, ["update", "--target", str(tmp_path)])
    assert res_default.exit_code == 0
    assert "ArchGuard Maintenance & Update" in res_default.stdout

