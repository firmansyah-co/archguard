---
id: SPEC-002
title: Git Topology & Deterministic Versioning Engine
version: 1.0.0
status: draft
standard: ISO/IEC/IEEE 29148:2018
tier: 0
layer: governance
divisions: [software]
created: 2026-09-01
depends_on: [SPEC-001]
standards:
  - "SemVer 2.0.0 (Semantic Versioning Specification)"
  - "Conventional Commits 1.0.0"
  - "ISO/IEC/IEEE 12207:2017 (Software Life Cycle Processes - Configuration Management)"
  - "IEEE 828-2012 (Configuration Management in Systems and Software Engineering)"
  - "ISO/IEC/IEEE 29148:2018 (Requirements Engineering)"
  - "PEP 440 (Version Identification and Dependency Specification)"
---

# SPEC-002: Git Topology & Deterministic Versioning Engine

## 1. Metadata
- **Spec ID**: `002`
- **Title**: Git Topology & Deterministic Versioning Engine
- **Status**: Draft
- **Tier**: Tier 0 (Governance & CI/CD)
- **Author**: Aria (CEO) & Head of Software
- **Standards**: SemVer 2.0.0, Conventional Commits 1.0.0, ISO/IEC/IEEE 12207:2017, IEEE 828-2012, PEP 440

---

## 2. Executive Summary & Problem Statement

Modern software engineering requires two critical governance capabilities:
1. **Branch Topology Enforcement**: Ensuring repositories follow professional branching strategies with appropriate protection rules and merge policies.
2. **Deterministic Version Calculation**: Eliminating manual version bumps by deriving version numbers mathematically from Git history.

Currently:
- Developers manually create branches without standardized naming conventions.
- Version numbers are manually edited in multiple files, leading to:
  - Human error and omissions
  - Merge conflicts when parallel branches claim the same version
  - Inability to reconstruct exact code state from version identifier
  - Loss of traceability between releases and commit history

**SPEC-002 introduces two complementary engines**:
1. **Dual-Trunk Dual-Gate Topology Validator**: Enforces professional branch structure and protection rules.
2. **Git-Derived Versioning Calculator**: Computes version numbers deterministically from Git metadata.

---

## 3. Architecture Overview

### 3.1 Dual-Trunk Dual-Gate Branch Topology

Professional software projects follow a **Two-Tier Integration Model**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DUAL-TRUNK DUAL-GATE TOPOLOGY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tier 1: PRODUCTION TRUNK (main)                                             │
│   - Protected branch (no direct push)                                       │
│   - Merge only via Release PR from dev                                      │
│   - Immutable release tags (v1.0.0, v1.1.0)                                 │
│   - Requires approval + field testing sign-off                              │
│                                                                             │
│ Tier 2: INTEGRATION TRUNK (dev / develop)                                   │
│   - Protected branch (no direct push)                                       │
│   - Merge only via feature/fix PRs                                          │
│   - Pre-release versions (alpha/beta)                                       │
│   - CI/CD automated testing required                                        │
│                                                                             │
│ Tier 3: SHORT-LIVED WORKER BRANCHES                                         │
│   - Ephemeral (< 24-48 hours)                                               │
│   - Naming convention: feat/*, fix/*, refactor/*, chore/*, ci/*             │
│   - Auto-delete after merge                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Branch Naming Standards**:
- `feat/<scope>-<description>` — New features
- `fix/<scope>-<description>` — Bug fixes
- `refactor/<scope>-<description>` — Code refactoring
- `chore/<scope>-<description>` — Maintenance tasks
- `ci/<scope>-<description>` — CI/CD improvements
- `docs/<scope>-<description>` — Documentation updates

**Workflow Patterns**:
1. **Library/Tool Projects** (ArchGuard, CLI tools):
   - Single trunk (`main`) with direct feature PRs
   - Fast release cycle
   - Trunk-Based Development (TBD) / GitHub Flow

2. **Production Systems** (LycanEdge, SCADA, embedded):
   - Dual trunk (`main` + `dev`)
   - `main` = sacred production zone
   - `dev` = integration + pre-release testing
   - GitFlow Modern (Dual-Trunk Dual-Gate)

---

### 3.2 Git-Derived Deterministic Versioning

Version numbers are **never manually edited**. Instead, they are computed from:
1. **Last Release Tag**: Anchor point in Git history
2. **Commit Distance**: Number of commits since last tag
3. **Conventional Commits**: Semantic analysis of commit messages
4. **Git SHA**: Unique commit identifier

**Mathematical Formula**:
```
Version = LastTag + ConventionalBump(CommitLog) + Distance + CommitHash
```

**Example Calculation**:
```bash
# Current state
$ git describe --tags --long
v0.6.0-84-g4791541e

# Interpretation
Base Tag:        v0.6.0
Commit Distance: 84 commits ahead
Commit Hash:     4791541e

# Version output
Dev branch:      0.6.0a84+g4791541e  (Python PEP 440)
                 0.6.0-alpha.84+g4791541e  (SemVer)
Main branch:     0.7.0  (if 84 commits contain feat:)
                 0.6.1  (if only fix: commits)
```

**Conventional Commits Semantic Rules**:
| Commit Type | Branch = `dev` | Branch = `main` |
|-------------|----------------|-----------------|
| `feat:` | Increment alpha counter | Increment MINOR |
| `fix:` | Increment alpha counter | Increment PATCH |
| `feat!:` or `BREAKING CHANGE:` | Increment alpha counter | Increment MAJOR |
| `refactor:`, `perf:`, `chore:` | Increment alpha counter | Increment PATCH |

---

## 4. Requirements Specification

### 4.1 Topology Validator Requirements

**REQ-TOP-001**: System SHALL detect missing required branches (`main`, `dev` for production projects).

**REQ-TOP-002**: System SHALL validate branch naming conventions against professional standards.

**REQ-TOP-003**: System SHALL verify branch protection rules are enabled on production and integration trunks.

**REQ-TOP-004**: System SHALL detect violations of merge policies (direct push to protected branches).

**REQ-TOP-005**: System SHALL support configuration for single-trunk (library) vs dual-trunk (production) topologies.

### 4.2 Versioning Calculator Requirements

**REQ-VER-001**: System SHALL derive version numbers from Git history without manual intervention.

**REQ-VER-002**: System SHALL parse Conventional Commits to determine semantic version bumps.

**REQ-VER-003**: System SHALL generate PEP 440 compliant versions for Python projects.

**REQ-VER-004**: System SHALL generate SemVer 2.0.0 compliant versions for JavaScript/TypeScript projects.

**REQ-VER-005**: System SHALL include Git commit hash in pre-release versions for traceability.

**REQ-VER-006**: System SHALL support reconstruction of exact code state from version identifier.

**REQ-VER-007**: System SHALL detect and reject manual version edits in production code files.

---

## 5. Machine-Readable Interface Contracts

### 5.1 CLI Interface Contract

```yaml
schema_version: "1.0"
contract_name: "GitTopologyAndVersioningContract"

cli_commands:
  - name: "check"
    subcommands:
      - name: "--topology"
        description: "Validate Git branch structure and protection rules"
        exit_codes:
          0: "Topology compliant"
          1: "Topology violations detected"
      
      - name: "--versioning"
        description: "Validate version derivation and detect manual edits"
        exit_codes:
          0: "Versioning compliant"
          1: "Manual version edits detected"
  
  - name: "version"
    subcommands:
      - name: "compute"
        description: "Calculate current version from Git history"
        options:
          - "--format": ["pep440", "semver"]
          - "--branch": "Branch name (defaults to current)"
        output: "Computed version string to stdout"
      
      - name: "sync"
        description: "Update version files with computed version"
        options:
          - "--dry-run": "Show changes without writing"
        targets:
          - "pyproject.toml"
          - "package.json"
          - "src/**/__init__.py"

  - name: "topology"
    subcommands:
      - name: "init"
        description: "Initialize dual-trunk topology with protection rules"
        options:
          - "--type": ["library", "production"]
          - "--create-dev": "Create and protect dev branch"
        
      - name: "validate"
        description: "Validate current repository topology"
        output: "Structured JSON topology report"
```

### 5.2 Configuration Schema

```yaml
# archguard.yaml
git_topology:
  enabled: true
  topology_type: "dual-trunk"  # Options: "single-trunk", "dual-trunk"
  
  required_branches:
    - name: "main"
      protected: true
      require_pr: true
      require_approvals: 1
      require_ci_pass: true
    
    - name: "dev"
      protected: true
      require_pr: true
      require_ci_pass: true
  
  branch_naming_patterns:
    feature: "^feat/[a-z0-9-]+$"
    bugfix: "^fix/[a-z0-9-]+$"
    refactor: "^refactor/[a-z0-9-]+$"
    chore: "^chore/[a-z0-9-]+$"
    ci: "^ci/[a-z0-9-]+$"
    docs: "^docs/[a-z0-9-]+$"
  
  ephemeral_branch_max_age_hours: 48

git_versioning:
  enabled: true
  version_scheme: "pep440"  # Options: "pep440", "semver"
  
  # Files that contain version strings
  version_files:
    - path: "pyproject.toml"
      pattern: 'version\s*=\s*"([^"]+)"'
    - path: "src/*/\__init__.py"
      pattern: '__version__\s*=\s*"([^"]+)"'
    - path: "package.json"
      pattern: '"version":\s*"([^"]+)"'
  
  # Conventional commit type mappings
  commit_types:
    major: ["feat!"]
    minor: ["feat"]
    patch: ["fix", "perf", "refactor"]
  
  # Ban manual version edits in production code
  ban_manual_version_edits: true
  
  # Tag prefix for releases
  tag_prefix: "v"
  
  # Pre-release identifier for dev branch
  dev_prerelease_identifier: "alpha"
```

---

## 6. Implementation Architecture

### 6.1 Topology Validator (`topology_validator_v2.py`)

**Components**:
1. **Branch Discovery Engine**: Enumerates all local and remote branches
2. **Protection Rules Checker**: Validates GitHub/GitLab branch protection settings
3. **Naming Convention Validator**: Regex-based pattern matching for branch names
4. **Merge Policy Auditor**: Analyzes Git log for direct pushes to protected branches
5. **Topology Reporter**: Generates structured JSON reports with violations

**Detection Rules**:
- **TOP-001**: Missing required branches (configurable: `main`, `dev`)
- **TOP-002**: Invalid branch naming (non-compliant with conventions)
- **TOP-003**: Unprotected trunk branches
- **TOP-004**: Direct push to protected branch detected in reflog
- **TOP-005**: Stale ephemeral branches (age > configured threshold)

### 6.2 Versioning Calculator (`versioning_engine.py`)

**Components**:
1. **Git Metadata Extractor**: Parses `git describe`, tags, commit history
2. **Conventional Commits Parser**: Analyzes commit messages for semantic signals
3. **Version Bump Calculator**: Determines MAJOR.MINOR.PATCH increments
4. **Format Converter**: Transforms version to PEP 440 or SemVer
5. **File Synchronizer**: Updates version strings in project files
6. **Manual Edit Detector**: AST scans for hardcoded version literals

**Core Algorithm**:
```python
def compute_version(branch: str, format: str) -> str:
    """
    Deterministically compute version from Git history.
    
    1. Find last release tag via `git describe --tags --abbrev=0`
    2. Count commit distance: `git rev-list <tag>..HEAD --count`
    3. Parse commits since tag: extract types (feat, fix, feat!)
    4. Determine semantic bump:
       - BREAKING CHANGE → MAJOR
       - feat → MINOR
       - fix/refactor/perf → PATCH
    5. Format based on branch:
       - main → X.Y.Z (clean release)
       - dev → X.Y.ZaN+gSHA (pre-release with distance)
    """
    last_tag = git_last_tag()
    distance = git_commit_distance(last_tag)
    commits = git_log_since(last_tag)
    
    bump_type = analyze_conventional_commits(commits)
    base_version = parse_semver(last_tag)
    
    if branch == "main":
        return bump_version(base_version, bump_type)
    else:  # dev or feature branches
        sha = git_short_sha()
        if format == "pep440":
            return f"{base_version}a{distance}+g{sha}"
        else:  # semver
            return f"{base_version}-alpha.{distance}+g{sha}"
```

### 6.3 Integration Points

**CLI Integration**:
```bash
# Topology validation
archguard check --topology

# Versioning validation
archguard check --versioning

# Combined governance check
archguard check --all  # Includes topology + versioning + existing gates

# Version calculation
archguard version compute --format pep440
# Output: 0.6.0a84+g4791541e

# Sync version files
archguard version sync --dry-run
# Shows: Would update pyproject.toml, src/archguard/__init__.py

# Initialize topology
archguard topology init --type production --create-dev
```

**CI/CD Integration**:
```yaml
# .github/workflows/governance.yml
- name: ArchGuard Topology & Versioning Gate
  run: |
    archguard check --topology --versioning
```

**Git Hooks Integration**:
```bash
# Pre-commit hook
archguard check --versioning  # Blocks manual version edits

# Pre-push hook
archguard check --topology    # Validates branch naming
```

---

## 7. Validation & Verification Plan

### 7.1 Unit Tests

**Test Coverage**:
- `tests/test_topology_validator.py`:
  - Branch naming validation (valid/invalid patterns)
  - Required branch detection
  - Protection rule verification
  - Stale branch detection
  
- `tests/test_versioning_engine.py`:
  - Git metadata extraction
  - Conventional commit parsing
  - Version bump calculation (major/minor/patch)
  - PEP 440 format generation
  - SemVer format generation
  - Manual edit detection

### 7.2 Integration Tests

**Scenarios**:
1. **Clean Repository**: No violations → Exit 0
2. **Missing dev Branch**: Dual-trunk project without dev → Violation detected
3. **Invalid Branch Name**: `feature/new-thing` instead of `feat/new-thing` → Violation
4. **Manual Version Edit**: Hardcoded version in code → Violation
5. **Version Reconstruction**: Given version string, checkout exact commit → Success

### 7.3 End-to-End Validation

**Test Sequence**:
```bash
# 1. Initialize fresh dual-trunk topology
archguard topology init --type production --create-dev

# 2. Validate topology compliance
archguard check --topology
# Expected: PASS

# 3. Compute version from history
VERSION=$(archguard version compute --format pep440)
echo "Computed version: $VERSION"

# 4. Verify version contains Git SHA
echo "$VERSION" | grep -q '+g[0-9a-f]\{7,\}'
# Expected: Match found

# 5. Test manual edit detection
echo '__version__ = "99.99.99"' >> src/archguard/__init__.py
archguard check --versioning
# Expected: FAIL with violation ISO-VER-001

# 6. Cleanup
git restore src/archguard/__init__.py
```

---

## 8. Standards Compliance Matrix

| Standard | Clause | Requirement | Implementation |
|----------|--------|-------------|----------------|
| ISO/IEC/IEEE 12207:2017 | 6.3.5 | Configuration management SHALL provide traceability to baseline | Git SHA embedded in version string enables exact reconstruction |
| IEEE 828-2012 | 5.1.3 | Version identification SHALL uniquely identify configuration items | Deterministic version calculation from Git metadata |
| SemVer 2.0.0 | § 2 | Version format MUST be X.Y.Z | Versioning engine generates compliant format |
| Conventional Commits 1.0.0 | § 1 | Commits SHOULD follow structured format | Parser extracts semantic signals from commit messages |
| PEP 440 | § 4 | Pre-release versions SHALL include identifier | Dev versions formatted as X.Y.ZaN+localversion |

---

## 9. Migration & Adoption Strategy

### 9.1 Existing Projects

**Phase 1: Assessment**
```bash
# Audit current state
archguard check --topology --versioning
# Review violations report
```

**Phase 2: Topology Alignment**
```bash
# For dual-trunk projects
git checkout -b dev
git push -u origin dev
archguard topology init --type production
```

**Phase 3: Version Cleanup**
```bash
# Remove manual version edits
git log --all --grep="version" --oneline
# Ensure last manual version is tagged
git tag -a v0.6.0 -m "Release 0.6.0"
# Future versions computed automatically
```

### 9.2 New Projects

**Initial Setup**:
```bash
# 1. Initialize repository
git init
git remote add origin <url>

# 2. Setup topology
archguard topology init --type library  # or --type production

# 3. Enable versioning
archguard version sync  # Initializes version files at 0.1.0a0

# 4. Install pre-commit hooks
archguard hook install
```

---

## 10. Appendices

### A. Reference Implementation Tools

**Existing Ecosystem Tools**:
- **Python**: `setuptools_scm`, `bump2version`, `semantic-release`
- **JavaScript**: `semantic-release`, `standard-version`, `lerna`
- **.NET**: `GitVersion`, `minver`
- **Rust**: `cargo-release` with `workspace.version`

**ArchGuard Differentiation**:
- Universal (language-agnostic)
- Integrated with full governance suite
- Enforces topology + versioning simultaneously
- Works without external dependencies (pure Git)

### B. Git Commands Reference

```bash
# Last release tag
git describe --tags --abbrev=0
# Example: v0.6.0

# Commit distance from tag
git rev-list v0.6.0..HEAD --count
# Example: 84

# Short commit hash
git rev-parse --short HEAD
# Example: 4791541e

# Full describe with distance
git describe --tags --long --always
# Example: v0.6.0-84-g4791541e

# Commits since tag with messages
git log v0.6.0..HEAD --pretty=format:"%s"
```

### C. Version Format Examples

**PEP 440 (Python)**:
```
0.6.0a84+g4791541e  → Alpha pre-release
0.6.0b3             → Beta pre-release
0.6.0rc1            → Release candidate
0.6.0               → Stable release
0.6.0.post1         → Post-release patch
```

**SemVer 2.0.0 (JavaScript/Universal)**:
```
0.6.0-alpha.84+g4791541e  → Alpha pre-release with metadata
0.6.0-beta.3              → Beta pre-release
0.6.0-rc.1                → Release candidate
0.6.0                     → Stable release
```

---

## 11. Success Metrics

**Quantitative**:
- 100% of version numbers derived from Git (0 manual edits)
- < 5 seconds for version calculation on any repository size
- 0 merge conflicts on version files across parallel PRs
- 100% traceability: any version → exact commit reconstruction

**Qualitative**:
- Developer cognitive load eliminated (no version number decisions)
- CI/CD logs contain precise version identifiers
- Release notes auto-generated from commit history
- Audit trails satisfy ISO/IEEE compliance requirements

---

**Status**: Draft → Awaiting Review & Approval
**Next Steps**:
1. Technical review by Head of Software
2. Prototype implementation in ArchGuard
3. Pilot testing on ArchGuard itself (dogfooding)
4. Rollout to LycanEdge Platform
5. Mark as Approved after successful validation
