"""
Unit tests for ArchGuard core updater module.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import yaml

from archguard.core.updater import (
    ARCHGUARD_REPO_URL,
    perform_project_update,
    perform_self_update,
    sync_archguard_config,
    sync_hermes_skill,
)


def test_sync_hermes_skill_creates_symlink(tmp_path: Path):
    source_skill = tmp_path / "repo" / "skills" / "archguard"
    source_skill.mkdir(parents=True, exist_ok=True)
    (source_skill / "SKILL.md").write_text("test skill", encoding="utf-8")

    target_link = tmp_path / "hermes" / "skills" / "engineering" / "archguard"

    assert sync_hermes_skill(source_skill, target_link) is True
    assert target_link.is_symlink()
    assert target_link.resolve() == source_skill.resolve()
    assert (target_link / "SKILL.md").read_text(encoding="utf-8") == "test skill"


def test_sync_hermes_skill_overwrites_stale_symlink(tmp_path: Path):
    old_source = tmp_path / "old"
    old_source.mkdir(parents=True, exist_ok=True)

    target_link = tmp_path / "hermes" / "skills" / "engineering" / "archguard"
    target_link.parent.mkdir(parents=True, exist_ok=True)
    target_link.symlink_to(old_source)

    new_source = tmp_path / "repo" / "skills" / "archguard"
    new_source.mkdir(parents=True, exist_ok=True)

    assert sync_hermes_skill(new_source, target_link) is True
    assert target_link.is_symlink()
    assert target_link.resolve() == new_source.resolve()


def test_sync_hermes_skill_nonexistent_source(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist"
    target_link = tmp_path / "hermes" / "skills" / "engineering" / "archguard"
    assert sync_hermes_skill(non_existent, target_link) is False


def test_sync_archguard_config_creates_default(tmp_path: Path):
    cfg_path = tmp_path / "archguard.yaml"
    status = sync_archguard_config(cfg_path)
    assert status == "created"
    assert cfg_path.exists()

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data["version"] == "1.0"
    assert "tokens" in data
    assert "layers" in data
    assert "components" in data
    assert "specs" in data
    assert "topology" in data


def test_sync_archguard_config_updates_missing_sections(tmp_path: Path):
    cfg_path = tmp_path / "archguard.yaml"
    initial_data = {
        "version": "1.0",
        "project_type": "custom",
        "tokens": {
            "enabled": True,
            "scan_paths": ["custom/src"],
        },
    }
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(initial_data, f)

    status = sync_archguard_config(cfg_path)
    assert status == "synchronized"

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Preserves customized values
    assert data["project_type"] == "custom"
    assert data["tokens"]["scan_paths"] == ["custom/src"]
    # Adds missing top-level sections
    assert "layers" in data
    assert "components" in data
    assert "specs" in data
    assert "topology" in data


def test_perform_project_update(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)

    res = perform_project_update(tmp_path)
    assert res["success"] is True
    assert res["workflow_updated"] is True
    assert (tmp_path / ".github" / "workflows" / "archguard-governance.yml").exists()
    assert res["hook_updated"] is True
    assert (tmp_path / ".git" / "hooks" / "pre-push").exists()
    assert res["config_status"] in {"created", "synchronized", "up_to_date"}
    assert (tmp_path / "archguard.yaml").exists()


@patch("subprocess.run")
def test_perform_self_update_local_git(mock_subproc, tmp_path: Path):
    repo_path = tmp_path / "archguard"
    git_dir = repo_path / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    skill_dir = repo_path / "skills" / "archguard"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("skill", encoding="utf-8")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "abc1234 - feat: update (2026-08-31)"
    mock_proc.stderr = ""
    mock_subproc.return_value = mock_proc

    target_skill = tmp_path / "hermes" / "skills" / "engineering" / "archguard"

    res = perform_self_update(
        repo_path=repo_path,
        hermes_skill_target=target_skill,
    )

    assert res["success"] is True
    assert res["method"] == "local_git"
    assert res["git_pulled"] is True
    assert res["pip_upgraded"] is True
    assert res["skill_synced"] is True
    assert target_skill.is_symlink()


@patch("subprocess.run")
def test_perform_self_update_remote(mock_subproc, tmp_path: Path):
    repo_path = tmp_path / "non_existent_repo"
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = ""
    mock_proc.stderr = ""
    mock_subproc.return_value = mock_proc

    res = perform_self_update(repo_path=repo_path)
    assert res["success"] is True
    assert res["method"] == "remote_pip"
    assert res["pip_upgraded"] is True
