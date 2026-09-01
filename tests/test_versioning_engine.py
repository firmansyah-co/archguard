"""
Unit tests for VersioningEngine and VersioningValidator.
Standards: SemVer 2.0.0 / Conventional Commits 1.0.0 / PEP 440 / IEEE 828-2012.
"""

from pathlib import Path
import subprocess
import pytest
from archguard.core.config import ArchGuardConfig, GitVersioningConfig, VersionFileConfig
from archguard.versioning.engine import VersioningEngine


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
def git_repo_with_tags(tmp_path: Path) -> Path:
    """Fixture creating a git repository with release tags and commits."""
    run_git(["init", "-b", "main"], tmp_path)
    run_git(["config", "user.name", "ArchGuard Test"], tmp_path)
    run_git(["config", "user.email", "test@archguard.dev"], tmp_path)

    # Initial commit & v0.1.0 tag
    (tmp_path / "README.md").write_text("# Initial\n", encoding="utf-8")
    run_git(["add", "README.md"], tmp_path)
    run_git(["commit", "-m", "chore: initial release"], tmp_path)
    run_git(["tag", "-a", "v0.1.0", "-m", "Release v0.1.0"], tmp_path)

    return tmp_path


def test_version_compute_exact_tag_on_main(git_repo_with_tags: Path):
    """When on exact tag with distance 0 on main, computed version equals base tag."""
    engine = VersioningEngine(root_dir=git_repo_with_tags)
    info = engine.get_version_info(branch="main")

    assert info.base_version == "0.1.0"
    assert info.distance == 0
    assert info.computed_pep440 == "0.1.0"
    assert info.computed_semver == "0.1.0"


def test_version_compute_conventional_minor_bump(git_repo_with_tags: Path):
    """Commits containing 'feat:' trigger MINOR bump on main, or alpha pre-release on dev."""
    # Add a feat commit
    (git_repo_with_tags / "file1.txt").write_text("feature\n", encoding="utf-8")
    run_git(["add", "file1.txt"], git_repo_with_tags)
    run_git(["commit", "-m", "feat(auth): implement oauth login"], git_repo_with_tags)

    engine = VersioningEngine(root_dir=git_repo_with_tags)
    
    # On main branch: bumps minor (0.1.0 -> 0.2.0)
    ver_main = engine.compute_version(branch="main", version_format="pep440")
    assert ver_main == "0.2.0"

    # On dev branch: 0.1.0a1+g<sha>
    info_dev = engine.get_version_info(branch="dev")
    assert info_dev.distance == 1
    assert info_dev.bump_type == "minor"
    assert info_dev.computed_pep440.startswith("0.1.0a1+g")
    assert info_dev.computed_semver.startswith("0.1.0-alpha.1+g")


def test_version_compute_conventional_major_bump(git_repo_with_tags: Path):
    """Commits with 'feat!:' or 'BREAKING CHANGE:' trigger MAJOR bump."""
    (git_repo_with_tags / "file2.txt").write_text("breaking\n", encoding="utf-8")
    run_git(["add", "file2.txt"], git_repo_with_tags)
    run_git(["commit", "-m", "feat(api)!: redesign entire endpoint schema\n\nBREAKING CHANGE: endpoints renamed"], git_repo_with_tags)

    engine = VersioningEngine(root_dir=git_repo_with_tags)
    info_main = engine.get_version_info(branch="main")

    assert info_main.bump_type == "major"
    assert info_main.computed_pep440 == "1.0.0"


def test_version_compute_conventional_patch_bump(git_repo_with_tags: Path):
    """Commits with only 'fix:' trigger PATCH bump on main."""
    (git_repo_with_tags / "file3.txt").write_text("fix\n", encoding="utf-8")
    run_git(["add", "file3.txt"], git_repo_with_tags)
    run_git(["commit", "-m", "fix: correct null pointer exception in parser"], git_repo_with_tags)

    engine = VersioningEngine(root_dir=git_repo_with_tags)
    info_main = engine.get_version_info(branch="main")

    assert info_main.bump_type == "patch"
    assert info_main.computed_pep440 == "0.1.1"


def test_sync_version_files(git_repo_with_tags: Path):
    """Synchronizes version string in pyproject.toml and __init__.py."""
    pyproject = git_repo_with_tags / "pyproject.toml"
    pyproject.write_text('[project]\nname = "testpkg"\nversion = "0.0.0"\n', encoding="utf-8")

    init_file = git_repo_with_tags / "src" / "testpkg" / "__init__.py"
    init_file.parent.mkdir(parents=True, exist_ok=True)
    init_file.write_text('"""Init"""\n__version__ = "0.0.0"\n', encoding="utf-8")

    config = ArchGuardConfig(
        git_versioning=GitVersioningConfig(
            version_files=[
                VersionFileConfig(path="pyproject.toml", pattern=r'version\s*=\s*"([^"]+)"'),
                VersionFileConfig(path="src/*/__init__.py", pattern=r'__version__\s*=\s*"([^"]+)"'),
            ]
        )
    )

    engine = VersioningEngine(root_dir=git_repo_with_tags, config=config)
    changes = engine.sync_version_files(version="0.1.0", dry_run=False)

    assert len(changes) == 2
    assert 'version = "0.1.0"' in pyproject.read_text(encoding="utf-8")
    assert '__version__ = "0.1.0"' in init_file.read_text(encoding="utf-8")


def test_detect_manual_version_edits(git_repo_with_tags: Path):
    """Detects manual version edit when hardcoded version deviates from git history."""
    init_file = git_repo_with_tags / "src" / "pkg" / "__init__.py"
    init_file.parent.mkdir(parents=True, exist_ok=True)
    # Hardcode an unauthorized manual version edit
    init_file.write_text('__version__ = "99.99.99"\n', encoding="utf-8")

    engine = VersioningEngine(root_dir=git_repo_with_tags)
    violations = engine.detect_manual_edits()

    assert len(violations) == 1
    assert violations[0].rule_id == "ISO-VER-001"
    assert "99.99.99" in violations[0].message
