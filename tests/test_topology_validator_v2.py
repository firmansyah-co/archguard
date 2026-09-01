"""
Unit tests for GitTopologyValidator (TOP-001 through TOP-005).
Standards: ISO/IEC/IEEE 12207:2017 / IEEE 828-2012.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import subprocess
import pytest
from archguard.core.config import ArchGuardConfig, GitTopologyConfig, RequiredBranchConfig
from archguard.core.models import Severity
from archguard.validators.topology_validator_v2 import GitTopologyValidator


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Fixture creating a clean git repository."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "ArchGuard Test"], tmp_path)
    run_git(["config", "user.email", "test@archguard.dev"], tmp_path)
    # Initial commit
    (tmp_path / "README.md").write_text("# ArchGuard Test\n", encoding="utf-8")
    run_git(["add", "README.md"], tmp_path)
    run_git(["commit", "-m", "chore: initial commit"], tmp_path)
    return tmp_path


def test_top_001_missing_required_branch_dual_trunk(git_repo: Path):
    """TOP-001: Dual-trunk configuration flags missing 'dev' branch."""
    config = ArchGuardConfig(
        git_topology=GitTopologyConfig(
            enabled=True,
            topology_type="dual-trunk",
            required_branches=[
                RequiredBranchConfig(name="main"),
                RequiredBranchConfig(name="dev"),
            ],
        )
    )
    validator = GitTopologyValidator(root_dir=git_repo, config=config)
    res = validator.validate()

    assert not res.passed
    top1_violations = [v for v in res.violations if v.rule_id == "TOP-001"]
    assert len(top1_violations) == 1
    assert "Missing required trunk branch 'dev'" in top1_violations[0].message


def test_top_001_passes_when_required_branches_exist(git_repo: Path):
    """TOP-001: Dual-trunk passes when both main and dev exist."""
    run_git(["branch", "dev"], git_repo)

    config = ArchGuardConfig(
        git_topology=GitTopologyConfig(
            enabled=True,
            topology_type="dual-trunk",
            required_branches=[
                RequiredBranchConfig(name="main"),
                RequiredBranchConfig(name="dev"),
            ],
        )
    )
    validator = GitTopologyValidator(root_dir=git_repo, config=config)
    res = validator.validate()

    top1_violations = [v for v in res.violations if v.rule_id == "TOP-001"]
    assert len(top1_violations) == 0


def test_top_001_single_trunk_library_mode(git_repo: Path):
    """TOP-001: Single-trunk library mode only requires main."""
    config = ArchGuardConfig(
        git_topology=GitTopologyConfig(
            enabled=True,
            topology_type="single-trunk",
        )
    )
    validator = GitTopologyValidator(root_dir=git_repo, config=config)
    res = validator.validate()

    top1_violations = [v for v in res.violations if v.rule_id == "TOP-001"]
    assert len(top1_violations) == 0


def test_top_002_invalid_branch_naming(git_repo: Path):
    """TOP-002: Flags invalid branch naming patterns."""
    # Create invalid branches
    run_git(["branch", "feature/my-feature"], git_repo)  # Should be feat/*
    run_git(["branch", "random_branch_name"], git_repo)
    # Create valid branch
    run_git(["branch", "feat/my-valid-feature"], git_repo)

    config = ArchGuardConfig(
        git_topology=GitTopologyConfig(
            enabled=True,
            topology_type="single-trunk",
        )
    )
    validator = GitTopologyValidator(root_dir=git_repo, config=config)
    res = validator.validate()

    top2_violations = [v for v in res.violations if v.rule_id == "TOP-002"]
    flagged_branches = {v.message for v in top2_violations}
    assert any("feature/my-feature" in msg for msg in flagged_branches)
    assert any("random_branch_name" in msg for msg in flagged_branches)
    assert not any("feat/my-valid-feature" in msg for msg in flagged_branches)


def test_top_002_valid_branch_prefixes(git_repo: Path):
    """TOP-002: Valid prefixes pass without violations."""
    for prefix in ["feat", "fix", "refactor", "chore", "ci", "docs"]:
        run_git(["branch", f"{prefix}/valid-test-branch"], git_repo)

    config = ArchGuardConfig(
        git_topology=GitTopologyConfig(
            enabled=True,
            topology_type="single-trunk",
        )
    )
    validator = GitTopologyValidator(root_dir=git_repo, config=config)
    res = validator.validate()

    top2_violations = [v for v in res.violations if v.rule_id == "TOP-002"]
    assert len(top2_violations) == 0


def test_top_002_ignores_synthetic_ci_branches(git_repo: Path):
    """TOP-002: Ignores synthetic CI branches (pull/*, gh-pages, etc.)."""
    run_git(["branch", "pull/2/merge"], git_repo)
    run_git(["branch", "pull/45/head"], git_repo)
    run_git(["branch", "gh-pages"], git_repo)

    config = ArchGuardConfig(
        git_topology=GitTopologyConfig(
            enabled=True,
            topology_type="single-trunk",
        )
    )
    validator = GitTopologyValidator(root_dir=git_repo, config=config)
    res = validator.validate()

    top2_violations = [v for v in res.violations if v.rule_id == "TOP-002"]
    assert len(top2_violations) == 0


def test_top_005_stale_ephemeral_branch(git_repo: Path):
    """TOP-005: Flags ephemeral branches exceeding max age hours."""
    # Create an old commit 5 days ago
    old_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    
    run_git(["checkout", "-b", "feat/stale-feature"], git_repo)
    (git_repo / "stale.txt").write_text("stale content\n", encoding="utf-8")
    run_git(["add", "stale.txt"], git_repo)
    
    # Commit with explicit past date
    env = {"GIT_AUTHOR_DATE": old_date, "GIT_COMMITTER_DATE": old_date}
    subprocess.run(
        ["git", "commit", "-m", "feat: old work in progress"],
        cwd=str(git_repo),
        env={**dict(os.environ), **env},
        check=True,
    )
    run_git(["checkout", "main"], git_repo)

    config = ArchGuardConfig(
        git_topology=GitTopologyConfig(
            enabled=True,
            topology_type="single-trunk",
            ephemeral_branch_max_age_hours=48,
        )
    )
    validator = GitTopologyValidator(root_dir=git_repo, config=config)
    res = validator.validate()

    top5_violations = [v for v in res.violations if v.rule_id == "TOP-005"]
    assert len(top5_violations) == 1
    assert "feat/stale-feature" in top5_violations[0].message
    assert top5_violations[0].severity == Severity.WARNING


def test_topology_validator_disabled_skips(git_repo: Path):
    """Validator skips when git_topology.enabled is False."""
    config = ArchGuardConfig(
        git_topology=GitTopologyConfig(enabled=False)
    )
    validator = GitTopologyValidator(root_dir=git_repo, config=config)
    res = validator.validate()

    assert res.passed
    assert res.checked_files_count == 0
    assert res.metadata["status"] == "disabled"
