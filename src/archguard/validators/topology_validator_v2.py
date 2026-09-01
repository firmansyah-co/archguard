"""
Git Topology & Dual-Trunk Dual-Gate Branch Architecture Validator.
Enforces branch structure, protection rules, naming conventions, merge policies, and stale branch detection.
Standards: ISO/IEC/IEEE 12207:2017 / IEEE 828-2012 / ISO/IEC/IEEE 29148:2018.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple
from archguard.core.config import ArchGuardConfig
from archguard.core.models import CheckResult, Severity, StandardRef, Violation
from archguard.validators.base import BaseValidator


def run_git_cmd(args: List[str], cwd: Path) -> Tuple[int, str, str]:
    """Execute git command safely and return exit_code, stdout, stderr."""
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


class GitTopologyValidator(BaseValidator):
    name = "git_topology_validator"
    standard = StandardRef.IEEE_828

    def validate(self) -> CheckResult:
        if not self.config.git_topology.enabled:
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": "disabled"},
            )

        violations: List[Violation] = []
        metadata: Dict[str, Any] = {}

        # Verify if root_dir is a git repository
        git_dir = self.root_dir / ".git"
        if not git_dir.exists():
            # Check if inside a worktree or git submodule
            code, out, _ = run_git_cmd(["rev-parse", "--is-inside-work-tree"], self.root_dir)
            if code != 0 or out.lower() != "true":
                # Not a git repo, return warning or pass with note
                return CheckResult(
                    validator_name=self.name,
                    standard=self.standard,
                    passed=True,
                    checked_files_count=0,
                    metadata={"status": "skipped", "reason": "not_a_git_repository"},
                )

        # 1. Discover local and remote branches
        branches = self._get_branches()
        metadata["branches"] = branches

        # Rule TOP-001: Missing required branches
        violations.extend(self._check_required_branches(branches))

        # Rule TOP-002: Invalid branch naming patterns
        violations.extend(self._check_branch_naming(branches))

        # Rule TOP-003: Unprotected trunk branches (local inspection + API if configured)
        violations.extend(self._check_branch_protection(branches))

        # Rule TOP-004: Direct push to protected branch detected via git log / reflog
        violations.extend(self._check_direct_pushes(branches))

        # Rule TOP-005: Stale ephemeral branches
        violations.extend(self._check_stale_branches(branches))

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0
        return CheckResult(
            validator_name=self.name,
            standard=self.standard,
            passed=passed,
            violations=violations,
            checked_files_count=len(branches),
            metadata=metadata,
        )

    def _get_branches(self) -> List[Dict[str, Any]]:
        """List local and remote tracking branches."""
        branches: List[Dict[str, Any]] = []
        # Format: refname:short|committerdate:iso-strict|objectname
        fmt = "%(refname:short)|%(committerdate:iso-strict)|%(objectname)"
        code, out, _ = run_git_cmd(["for-each-ref", f"--format={fmt}", "refs/heads/", "refs/remotes/"], self.root_dir)
        if code != 0 or not out:
            return branches

        seen_names: Set[str] = set()
        for line in out.splitlines():
            parts = line.split("|")
            if len(parts) >= 3:
                full_name = parts[0]
                date_str = parts[1]
                commit_sha = parts[2]

                # Skip HEAD and symbolic refs
                if "HEAD" in full_name:
                    continue

                # Strip origin/ or upstream/ for remote branches if needed
                short_name = full_name
                is_remote = full_name.startswith("origin/") or full_name.startswith("remotes/")
                if is_remote:
                    short_name = full_name.split("/", 1)[1] if "/" in full_name else full_name
                
                # Skip remote name aliases (origin, upstream without branch suffix)
                if short_name in ("origin", "upstream", "remotes"):
                    continue

                if short_name not in seen_names:
                    seen_names.add(short_name)
                    branches.append({
                        "name": short_name,
                        "full_ref": full_name,
                        "is_remote": is_remote,
                        "date": date_str,
                        "sha": commit_sha,
                    })

        return branches

    def _check_required_branches(self, branches: List[Dict[str, Any]]) -> List[Violation]:
        """TOP-001: Check for required branches based on topology type."""
        violations: List[Violation] = []
        branch_names = {b["name"] for b in branches}
        topology_type = self.config.git_topology.topology_type

        # Build list of required branch names
        required_branch_configs = self.config.git_topology.required_branches
        if topology_type == "single-trunk":
            # For single-trunk library, only main is required
            req_names = ["main"]
        else:
            # Dual-trunk (production) requires main and dev
            req_names = [rb.name for rb in required_branch_configs]
            if not req_names:
                req_names = ["main", "dev"]

        for req in req_names:
            # Check if req or origin/req exists in branch_names
            if req not in branch_names and f"origin/{req}" not in branch_names:
                violations.append(
                    Violation(
                        rule_id="TOP-001",
                        standard=self.standard,
                        severity=Severity.ERROR,
                        message=f"Missing required trunk branch '{req}' for '{topology_type}' topology.",
                        file_path=".git/refs/heads",
                        remediation_hint=f"Create and push branch '{req}': git checkout -b {req} && git push -u origin {req}",
                    )
                )

        return violations

    def _check_branch_naming(self, branches: List[Dict[str, Any]]) -> List[Violation]:
        """TOP-002: Check that branch names adhere to conventions."""
        violations: List[Violation] = []
        patterns = self.config.git_topology.branch_naming_patterns
        trunk_names = {"main", "master", "dev", "develop", "stage", "staging", "prod", "production"}
        
        # Compile regex patterns
        compiled_patterns = [re.compile(p) for p in patterns.values()]

        for branch in branches:
            name = branch["name"]
            if name in trunk_names or name.startswith("tags/"):
                continue

            # Release branch pattern exception (e.g. release/v1.0.0 or release/1.0.0)
            if re.match(r"^release/v?[0-9.]+(-[a-z0-9.]+)?$", name):
                continue

            matched = any(p.match(name) for p in compiled_patterns)
            if not matched:
                violations.append(
                    Violation(
                        rule_id="TOP-002",
                        standard=self.standard,
                        severity=Severity.ERROR,
                        message=f"Invalid branch naming pattern '{name}'. Must match standard prefixes (feat/*, fix/*, refactor/*, chore/*, ci/*, docs/*).",
                        file_path=f".git/refs/heads/{name}",
                        remediation_hint=f"Rename branch using standard convention: git branch -m {name} feat/<scope>-<description>",
                    )
                )

        return violations

    def _check_branch_protection(self, branches: List[Dict[str, Any]]) -> List[Violation]:
        """TOP-003: Verify protection rules on trunk branches."""
        violations: List[Violation] = []
        
        # Check if remote repository metadata or gh/gitlab CLI is accessible
        # If gh CLI is available and authenticated, query branch protection
        if shutil.which("gh"):
            for req_branch in self.config.git_topology.required_branches:
                if not req_branch.protected:
                    continue
                code, out, _ = run_git_cmd(
                    ["config", "--get", f"branch.{req_branch.name}.protected"],
                    self.root_dir
                )
                # Query gh api if possible
                try:
                    gh_proc = subprocess.run(
                        ["gh", "api", f"repos/:owner/:repo/branches/{req_branch.name}/protection"],
                        cwd=str(self.root_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=False,
                        timeout=5,
                    )
                    if gh_proc.returncode == 0:
                        data = json.loads(gh_proc.stdout)
                        # Check PR requirements
                        if req_branch.require_pr and "required_pull_request_reviews" not in data:
                            violations.append(
                                Violation(
                                    rule_id="TOP-003",
                                    standard=self.standard,
                                    severity=Severity.ERROR,
                                    message=f"Trunk branch '{req_branch.name}' lacks required pull request review protection on GitHub.",
                                    file_path=".github/branch-protection",
                                    remediation_hint=f"Enable 'Require a pull request before merging' on '{req_branch.name}'.",
                                )
                            )
                except Exception:
                    # Non-fatal if offline / no remote access
                    pass

        return violations

    def _check_direct_pushes(self, branches: List[Dict[str, Any]]) -> List[Violation]:
        """TOP-004: Direct push to protected branch detection via Git history/reflog."""
        violations: List[Violation] = []
        # Check merge policies on main/dev: commits directly on main that are not merge commits or signed off
        # Check git log on main if dual-trunk
        if self.config.git_topology.topology_type == "dual-trunk":
            # For dual-trunk, commits on main should ideally be PR merge commits or release tags
            # Inspect last 10 commits on main
            code, out, _ = run_git_cmd(
                ["log", "main", "--max-count=10", "--merges", "--pretty=format:%H"],
                self.root_dir
            )
            # This is an audit tool; we check reflog if available
            code_reflog, reflog_out, _ = run_git_cmd(
                ["reflog", "show", "main", "--max-count=20"],
                self.root_dir
            )
            if code_reflog == 0 and reflog_out:
                for line in reflog_out.splitlines():
                    if "commit (initial)" in line:
                        continue
                    # If reflog explicitly indicates a forced push or direct commit without merge/pull
                    if "commit: direct" in line.lower() or "push --force" in line.lower():
                        violations.append(
                            Violation(
                                rule_id="TOP-004",
                                standard=self.standard,
                                severity=Severity.ERROR,
                                message=f"Direct push or force push violation detected on protected branch 'main': {line}",
                                file_path=".git/logs/refs/heads/main",
                                remediation_hint="Ensure all changes to protected branches are merged via PRs with status checks.",
                            )
                        )

        return violations

    def _check_stale_branches(self, branches: List[Dict[str, Any]]) -> List[Violation]:
        """TOP-005: Stale ephemeral branches (age > ephemeral_branch_max_age_hours)."""
        violations: List[Violation] = []
        max_age_hours = self.config.git_topology.ephemeral_branch_max_age_hours
        trunk_names = {"main", "master", "dev", "develop", "stage", "staging", "prod", "production"}

        now = datetime.now(timezone.utc)

        for branch in branches:
            name = branch["name"]
            if name in trunk_names:
                continue

            date_str = branch.get("date")
            if not date_str:
                continue

            try:
                # Parse ISO date
                branch_date = datetime.fromisoformat(date_str)
                age_hours = (now - branch_date).total_seconds() / 3600.0
                if age_hours > max_age_hours:
                    violations.append(
                        Violation(
                            rule_id="TOP-005",
                            standard=self.standard,
                            severity=Severity.WARNING,
                            message=f"Ephemeral branch '{name}' is stale (age: {age_hours:.1f}h > max allowed {max_age_hours}h).",
                            file_path=f".git/refs/heads/{name}",
                            remediation_hint=f"Merge and delete branch '{name}' or update it with fresh commits.",
                        )
                    )
            except Exception:
                pass

        return violations
