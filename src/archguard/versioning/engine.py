"""
Git-Derived Deterministic Versioning Engine.
Derives semantic version numbers deterministically from Git history, commit distance,
Conventional Commits semantic signals, and SHA hashes.
Standards: SemVer 2.0.0 / Conventional Commits 1.0.0 / PEP 440 / IEEE 828-2012.
"""

import ast
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from archguard.core.config import ArchGuardConfig, VersionFileConfig
from archguard.core.models import CheckResult, Severity, StandardRef, Violation


def run_git_command(args: List[str], cwd: Path) -> Tuple[int, str, str]:
    """Execute a git command in cwd and return (exit_code, stdout, stderr)."""
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


@dataclass
class VersionInfo:
    base_version: str
    major: int
    minor: int
    patch: int
    distance: int
    sha: str
    branch: str
    bump_type: str
    computed_pep440: str
    computed_semver: str


class VersioningEngine:
    """Core deterministic versioning calculation and file synchronization engine."""

    def __init__(self, root_dir: Optional[Path] = None, config: Optional[ArchGuardConfig] = None) -> None:
        self.root_dir = (root_dir or Path.cwd()).resolve()
        self.config = config or ArchGuardConfig.load()

    def get_current_branch(self) -> str:
        """Detect current active git branch."""
        code, out, _ = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], self.root_dir)
        if code == 0 and out and out != "HEAD":
            return out
        # Fallback if detached HEAD (e.g. in CI)
        code, out, _ = run_git_command(["name-rev", "--name-only", "HEAD"], self.root_dir)
        if code == 0 and out:
            return out.split("/")[-1]
        return "main"

    def get_short_sha(self) -> str:
        """Retrieve 7-character short commit SHA."""
        code, out, _ = run_git_command(["rev-parse", "--short=8", "HEAD"], self.root_dir)
        if code == 0 and out:
            return out
        return "0000000"

    def get_last_release_tag(self, tag_prefix: str = "v") -> Tuple[Optional[str], int, int, int]:
        """
        Find last release tag via git describe / tag list.
        Returns (tag_name, major, minor, patch).
        """
        # Try git describe --tags --abbrev=0
        code, out, _ = run_git_command(["describe", "--tags", "--abbrev=0"], self.root_dir)
        tag_name: Optional[str] = None
        if code == 0 and out:
            tag_name = out
        else:
            # Try listing tags sorted by version
            code_list, out_list, _ = run_git_command(["tag", "--list", f"{tag_prefix}*", "--sort=-v:refname"], self.root_dir)
            if code_list == 0 and out_list:
                tags = [t.strip() for t in out_list.splitlines() if t.strip()]
                if tags:
                    tag_name = tags[0]

        if not tag_name:
            return None, 0, 1, 0

        # Parse SemVer from tag
        clean_tag = tag_name
        if clean_tag.startswith(tag_prefix):
            clean_tag = clean_tag[len(tag_prefix):]
        
        # Match X.Y.Z
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)", clean_tag)
        if match:
            return tag_name, int(match.group(1)), int(match.group(2)), int(match.group(3))
        
        # Fallback for 2-digit e.g. 0.1
        match2 = re.match(r"^(\d+)\.(\d+)", clean_tag)
        if match2:
            return tag_name, int(match2.group(1)), int(match2.group(2)), 0

        return tag_name, 0, 1, 0

    def get_commit_distance(self, tag_name: Optional[str]) -> int:
        """Calculate commit count since tag or from repository root."""
        if tag_name:
            code, out, _ = run_git_command(["rev-list", f"{tag_name}..HEAD", "--count"], self.root_dir)
            if code == 0 and out.isdigit():
                return int(out)
        else:
            code, out, _ = run_git_command(["rev-list", "--count", "HEAD"], self.root_dir)
            if code == 0 and out.isdigit():
                return int(out)
        return 0

    def get_commits_since(self, tag_name: Optional[str]) -> List[str]:
        """Extract commit messages since last tag."""
        if tag_name:
            code, out, _ = run_git_command(["log", f"{tag_name}..HEAD", "--pretty=format:%s%n%b---END---"], self.root_dir)
        else:
            code, out, _ = run_git_command(["log", "--pretty=format:%s%n%b---END---"], self.root_dir)

        if code != 0 or not out:
            return []

        commits = [c.strip() for c in out.split("---END---") if c.strip()]
        return commits

    def analyze_conventional_commits(self, commits: List[str]) -> str:
        """
        Analyze commit messages to determine semantic increment signal:
        - BREAKING CHANGE or feat!/fix! -> 'major'
        - feat -> 'minor'
        - fix/perf/refactor/chore -> 'patch'
        """
        if not commits:
            return "patch"

        has_major = False
        has_minor = False

        for msg in commits:
            # Check for breaking change indicators
            if "BREAKING CHANGE:" in msg or "BREAKING-CHANGE:" in msg:
                return "major"
            
            first_line = msg.splitlines()[0].strip()
            # Match type(scope)!: or type!:
            if re.match(r"^[a-zA-Z0-9_-]+(\([^)]+\))?!:", first_line):
                return "major"

            # Check for minor indicators (feat)
            if re.match(r"^feat(\([^)]+\))?:", first_line):
                has_minor = True

        if has_major:
            return "major"
        if has_minor:
            return "minor"
        return "patch"

    def compute_version(self, branch: Optional[str] = None, version_format: Optional[str] = None) -> str:
        """
        Compute deterministic version string based on branch and format.
        format options: 'pep440' (default for python) or 'semver'.
        """
        info = self.get_version_info(branch=branch)
        fmt = (version_format or self.config.git_versioning.version_scheme).lower()
        if fmt == "semver":
            return info.computed_semver
        return info.computed_pep440

    def get_version_info(self, branch: Optional[str] = None) -> VersionInfo:
        """Compute full structured version metadata."""
        active_branch = branch or self.get_current_branch()
        tag_prefix = self.config.git_versioning.tag_prefix
        tag_name, maj, min_, pat = self.get_last_release_tag(tag_prefix=tag_prefix)
        distance = self.get_commit_distance(tag_name)
        commits = self.get_commits_since(tag_name)
        bump_type = self.analyze_conventional_commits(commits)
        sha = self.get_short_sha()
        base_ver = f"{maj}.{min_}.{pat}"

        # Determine release vs pre-release
        is_main_trunk = active_branch in ("main", "master", "release")
        prerelease_id = self.config.git_versioning.dev_prerelease_identifier or "alpha"

        if is_main_trunk:
            if distance == 0 and tag_name:
                pep440 = base_ver
                semver = base_ver
            else:
                # Calculate bumped release version
                if bump_type == "major":
                    new_maj, new_min, new_pat = maj + 1, 0, 0
                elif bump_type == "minor":
                    new_maj, new_min, new_pat = maj, min_ + 1, 0
                else:
                    new_maj, new_min, new_pat = maj, min_, pat + 1
                
                bumped = f"{new_maj}.{new_min}.{new_pat}"
                pep440 = bumped
                semver = bumped
        else:
            # Pre-release / dev branch calculation
            if distance == 0:
                pep440 = f"{base_ver}"
                semver = f"{base_ver}"
            else:
                pep440 = f"{base_ver}a{distance}+g{sha}"
                semver = f"{base_ver}-{prerelease_id}.{distance}+g{sha}"

        return VersionInfo(
            base_version=base_ver,
            major=maj,
            minor=min_,
            patch=pat,
            distance=distance,
            sha=sha,
            branch=active_branch,
            bump_type=bump_type,
            computed_pep440=pep440,
            computed_semver=semver,
        )

    def sync_version_files(self, version: Optional[str] = None, dry_run: bool = False) -> Dict[str, Tuple[str, str]]:
        """
        Synchronize computed version across pyproject.toml, package.json, and __init__.py files.
        Returns a mapping of {filepath: (old_version, new_version)}.
        """
        target_version = version or self.compute_version()
        changes: Dict[str, Tuple[str, str]] = {}
        version_files = self.config.git_versioning.version_files

        for vf in version_files:
            # Handle glob patterns in path
            matched_paths: List[Path] = []
            if "*" in vf.path:
                matched_paths = list(self.root_dir.glob(vf.path))
            else:
                p = self.root_dir / vf.path
                if p.exists():
                    matched_paths = [p]

            for path in matched_paths:
                if not path.is_file():
                    continue

                try:
                    content = path.read_text(encoding="utf-8")
                    pattern = re.compile(vf.pattern)
                    match = pattern.search(content)
                    if match:
                        old_ver = match.group(1)
                        if old_ver != target_version:
                            # Construct replacement
                            # Keep matched prefix and suffix
                            span = match.span(1)
                            new_content = content[:span[0]] + target_version + content[span[1]:]
                            rel_path = str(path.relative_to(self.root_dir))
                            changes[rel_path] = (old_ver, target_version)
                            if not dry_run:
                                path.write_text(new_content, encoding="utf-8")
                except Exception:
                    continue

        return changes

    def detect_manual_edits(self) -> List[Violation]:
        """
        Detect manual version edits in production code files.
        Rule: ISO-VER-001 (IEEE 828 / SemVer 2.0.0).
        """
        violations: List[Violation] = []
        if not self.config.git_versioning.ban_manual_version_edits:
            return violations

        computed_pep = self.compute_version(version_format="pep440")
        computed_sem = self.compute_version(version_format="semver")
        # Extract base release version (X.Y.Z) for comparison
        base_clean = computed_pep.split("a")[0].split("+")[0]

        # Scan python files for __version__ AST assignments
        python_files = list(self.root_dir.glob("src/**/*.py")) + list(self.root_dir.glob("backend/**/*.py"))
        for py_file in python_files:
            if any(part in py_file.parts for part in ("tests", "test", ".venv", "venv", "build", "dist")):
                continue

            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id in ("__version__", "VERSION"):
                                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                    found_val = node.value.value
                                    # Check if hardcoded literal deviates from computed versions
                                    if (
                                        found_val != computed_pep
                                        and found_val != computed_sem
                                        and found_val != base_clean
                                        and not found_val.startswith("0.0.0")
                                    ):
                                        rel = str(py_file.relative_to(self.root_dir))
                                        violations.append(
                                            Violation(
                                                rule_id="ISO-VER-001",
                                                standard=StandardRef.SEMVER_2,
                                                severity=Severity.ERROR,
                                                message=(
                                                    f"Manual hardcoded version literal '{found_val}' detected in '{rel}'. "
                                                    f"Versions must be computed from Git history (computed: '{computed_pep}')."
                                                ),
                                                file_path=rel,
                                                line_number=node.lineno,
                                                context_snippet=f"{target.id} = \"{found_val}\"",
                                                remediation_hint="Use 'archguard version sync' or derive version dynamically from Git metadata.",
                                            )
                                        )
            except Exception:
                continue

        return violations
