"""
ArchGuard self-upgrade, skill synchronization, and project asset updater.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from archguard import __version__
from archguard.templates.scaffold import (
    DEFAULT_ARCHGUARD_CONFIG_YAML,
    PRE_PUSH_HOOK_SCRIPT,
    WORKFLOW_TEMPLATE,
)

ARCHGUARD_REPO_URL = "https://github.com/firmansyah-co/archguard.git"
DEFAULT_REPO_PATH = Path("/home/adrian/Projects/archguard")
HERMES_SKILL_LINK_PATH = Path("/home/adrian/.hermes/skills/engineering/archguard")


def get_default_repo_path() -> Path:
    """Resolve default ArchGuard repository path."""
    fixed_path = Path("/home/adrian/Projects/archguard")
    if fixed_path.exists():
        return fixed_path
    home_path = Path.home() / "Projects" / "archguard"
    if home_path.exists():
        return home_path
    return fixed_path


def get_default_skill_link_path() -> Path:
    """Resolve default Hermes engineering skill symlink path."""
    fixed_path = Path("/home/adrian/.hermes/skills/engineering/archguard")
    if fixed_path.parent.exists():
        return fixed_path
    home_path = Path.home() / ".hermes" / "skills" / "engineering" / "archguard"
    return home_path



def sync_hermes_skill(
    skill_source_dir: Path,
    target_link: Path = HERMES_SKILL_LINK_PATH,
) -> bool:
    """
    Ensure a valid symlink exists from target_link to skill_source_dir.
    Creates parent directories if necessary.
    """
    if not skill_source_dir.exists():
        return False

    target_link = target_link.resolve() if target_link.is_symlink() and not target_link.exists() else target_link
    target_parent = target_link.parent
    target_parent.mkdir(parents=True, exist_ok=True)

    # Check if target already points to the correct location
    if target_link.is_symlink():
        try:
            current_target = os.readlink(target_link)
            if Path(current_target).resolve() == skill_source_dir.resolve():
                return True
            target_link.unlink()
        except OSError:
            target_link.unlink(missing_ok=True)
    elif target_link.exists():
        if target_link.is_dir():
            shutil.rmtree(target_link)
        else:
            target_link.unlink()

    target_link.symlink_to(skill_source_dir.resolve())
    return True


def sync_archguard_config(config_path: Path) -> str:
    """
    Synchronize archguard.yaml config.
    Creates with default template if missing, or updates missing sections.
    """
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(DEFAULT_ARCHGUARD_CONFIG_YAML, encoding="utf-8")
        return "created"

    try:
        content = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
    except Exception:
        data = {}

    default_data = yaml.safe_load(DEFAULT_ARCHGUARD_CONFIG_YAML)
    updated = False

    for key, val in default_data.items():
        if key not in data:
            data[key] = val
            updated = True
        elif isinstance(val, dict) and isinstance(data.get(key), dict):
            for sub_k, sub_v in val.items():
                if sub_k not in data[key]:
                    data[key][sub_k] = sub_v
                    updated = True

    if updated:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        return "synchronized"

    return "up_to_date"


def perform_self_update(
    repo_path: Optional[Path] = None,
    remote_url: str = ARCHGUARD_REPO_URL,
    hermes_skill_target: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Self-upgrade ArchGuard via git pull and pip re-install, and sync Hermes skill.
    """
    target_repo = repo_path or get_default_repo_path()
    git_dir = target_repo / ".git"
    skill_target = hermes_skill_target or get_default_skill_link_path()

    result: Dict[str, Any] = {
        "success": True,
        "method": "local_git" if git_dir.exists() else "remote_pip",
        "repo_path": str(target_repo),
        "git_pulled": False,
        "commit_info": "",
        "pip_upgraded": False,
        "skill_synced": False,
        "skill_path": str(skill_target),
        "errors": [],
    }


    if git_dir.exists():
        # 1. Git pull
        try:
            pull_proc = subprocess.run(
                ["git", "-C", str(target_repo), "pull", "origin", "main"],
                capture_output=True,
                text=True,
                check=False,
            )
            if pull_proc.returncode == 0:
                result["git_pulled"] = True
            else:
                result["errors"].append(f"git pull failed: {pull_proc.stderr.strip()}")

            log_proc = subprocess.run(
                ["git", "-C", str(target_repo), "log", "-1", "--pretty=format:%h - %s (%ci)"],
                capture_output=True,
                text=True,
                check=False,
            )
            if log_proc.returncode == 0:
                result["commit_info"] = log_proc.stdout.strip()
        except Exception as e:
            result["errors"].append(f"Git operation failed: {str(e)}")

        # 2. Pip editable install
        try:
            pip_proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(target_repo)],
                capture_output=True,
                text=True,
                check=False,
            )
            if pip_proc.returncode == 0:
                result["pip_upgraded"] = True
            else:
                result["errors"].append(f"pip install -e failed: {pip_proc.stderr.strip()}")
                result["success"] = False
        except Exception as e:
            result["errors"].append(f"Pip install failed: {str(e)}")
            result["success"] = False

        # 3. Hermes skill sync
        skill_src = target_repo / "skills" / "archguard"
        if skill_src.exists():
            synced = sync_hermes_skill(skill_src, target_link=skill_target)
            result["skill_synced"] = synced

    else:
        # Remote pip upgrade
        try:
            pip_proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", f"git+{remote_url}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if pip_proc.returncode == 0:
                result["pip_upgraded"] = True
            else:
                result["errors"].append(f"pip install git+ failed: {pip_proc.stderr.strip()}")
                result["success"] = False
        except Exception as e:
            result["errors"].append(f"Pip upgrade failed: {str(e)}")
            result["success"] = False

        # Check if local skill exists in fallback locations
        fallback_skill = Path("skills/archguard")
        if fallback_skill.exists():
            synced = sync_hermes_skill(fallback_skill, target_link=skill_target)
            result["skill_synced"] = synced


    if result["errors"] and not result["pip_upgraded"]:
        result["success"] = False

    return result


def perform_project_update(target_dir: Path) -> Dict[str, Any]:
    """
    Update project assets (.github/workflows, .git/hooks, archguard.yaml).
    """
    target = target_dir.resolve()
    result: Dict[str, Any] = {
        "target_dir": str(target),
        "workflow_updated": False,
        "workflow_path": "",
        "hook_updated": False,
        "hook_path": "",
        "hook_skipped": False,
        "config_status": "",
        "config_path": "",
        "success": True,
        "errors": [],
    }

    # 1. Refresh workflow
    try:
        wf_dir = target / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        wf_file = wf_dir / "archguard-governance.yml"
        wf_file.write_text(WORKFLOW_TEMPLATE, encoding="utf-8")
        result["workflow_updated"] = True
        result["workflow_path"] = str(wf_file)
    except Exception as e:
        result["errors"].append(f"Failed updating workflow: {str(e)}")
        result["success"] = False

    # 2. Refresh pre-push hook
    git_dir = target / ".git"
    if git_dir.exists():
        try:
            hook_dir = git_dir / "hooks"
            hook_dir.mkdir(parents=True, exist_ok=True)
            hook_file = hook_dir / "pre-push"
            hook_file.write_text(PRE_PUSH_HOOK_SCRIPT, encoding="utf-8")
            hook_file.chmod(0o755)
            result["hook_updated"] = True
            result["hook_path"] = str(hook_file)
        except Exception as e:
            result["errors"].append(f"Failed updating pre-push hook: {str(e)}")
            result["success"] = False
    else:
        result["hook_skipped"] = True

    # 3. Synchronize configuration
    try:
        cfg_file = target / "archguard.yaml"
        status = sync_archguard_config(cfg_file)
        result["config_status"] = status
        result["config_path"] = str(cfg_file)
    except Exception as e:
        result["errors"].append(f"Failed syncing config: {str(e)}")
        result["success"] = False

    return result
