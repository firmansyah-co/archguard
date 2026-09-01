"""
Project topology templates and initializers for ArchGuard.
"""

from pathlib import Path
from typing import Optional


DEFAULT_ARCHGUARD_CONFIG_YAML = """# ArchGuard Architecture Governance Engine Configuration
# Compliance: ISO/IEC/IEEE 42010, ISO/IEC/IEEE 29148, W3C DTCG, RFC 7807

version: "1.0"
project_type: "fullstack"

tokens:
  enabled: true
  token_files:
    - "frontend/src/styles/tokens.css"
    - "frontend/src/styles/global.css"
    - "src/styles/tokens.css"
    - "src/styles/global.css"
  scan_paths:
    - "frontend/src"
    - "src/components"
    - "src/pages"
  allowed_hex_colors: []

layers:
  enabled: true
  backend_root: "backend/src"
  layers:
    - "api"
    - "service"
    - "repository"
    - "models"
    - "core"
  forbidden_dependencies:
    api:
      - "repository"
      - "sqlalchemy"
      - "sqlmodel"
      - "psycopg"
    models:
      - "api"
      - "service"
      - "repository"
    service:
      - "api"
    repository:
      - "api"

components:
  enabled: true
  pages_dirs:
    - "frontend/src/pages"
    - "src/pages"
  common_components_dirs:
    - "frontend/src/components/common"
    - "src/components/common"
  forbidden_raw_primitives:
    - "button"
    - "input"
    - "select"
    - "textarea"
    - "table"
    - "dialog"

specs:
  enabled: true
  specs_dir: "specs"
  require_contracts: true
  require_traceability: true
  require_tasks_sync: true

topology:
  enabled: true
  forbidden_root_extensions:
    - ".sh"
    - ".py"
    - ".js"
    - ".ts"
    - ".tmp"
    - ".bak"
  allowed_root_files:
    - "pyproject.toml"
    - "package.json"
    - "README.md"
    - "LICENSE"
    - ".gitignore"
    - ".env.example"
    - "Dockerfile"
    - "docker-compose.yml"
    - "Makefile"
    - "archguard.yaml"
    - "archguard.yml"
    - "tsconfig.json"
    - "vite.config.ts"
  require_adr_dir: true
  adr_dir: "docs/adr"

integrity:
  enabled: true
  production_paths:
    - "frontend/src"
    - "backend/src"
    - "src"
  test_paths:
    - "tests"
    - "test"
    - "__tests__"
    - "frontend/src/tests"
    - "backend/tests"
    - "src/tests"
    - "mocks"
    - "__mocks__"
    - "fixtures"
  ban_unanchored_synthetic_literals: true
  ban_heuristic_state_inference: true
  ban_synthetic_fallbacks: true
  ban_mock_artifacts_in_production: true

git_topology:
  enabled: true
  topology_type: "dual-trunk"
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
  version_scheme: "pep440"
  version_files:
    - path: "pyproject.toml"
      pattern: 'version\\s*=\\s*"([^"]+)"'
    - path: "src/*/__init__.py"
      pattern: '__version__\\s*=\\s*"([^"]+)"'
    - path: "package.json"
      pattern: '"version":\\s*"([^"]+)"'
  commit_types:
    major: ["feat!"]
    minor: ["feat"]
    patch: ["fix", "perf", "refactor"]
  ban_manual_version_edits: true
  tag_prefix: "v"
  dev_prerelease_identifier: "alpha"
"""


TOKENS_CSS_TEMPLATE = """:root {
  /* W3C DTCG 2025.10 Token Registry */
  --color-primary: #0284c7;
  --color-primary-hover: #0369a1;
  --color-surface-bg: #09090b;
  --color-surface-card: #18181b;
  --color-border: #27272a;
  --color-text-main: #f4f4f5;
  --color-text-muted: #a1a1aa;

  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
}
"""


SPEC_TEMPLATE = """---
id: SPEC-001
title: Example Feature Architecture & Requirements
version: 1.0.0
status: approved
standard: ISO/IEC/IEEE 29148:2018
author: ArchGuard Governance
---

# Feature Architecture & Requirements Specification

## 1. Context & Objectives
Complies with ISO/IEC/IEEE 29148:2018 and ISO/IEC/IEEE 42010:2022.

## 2. Requirements Traceability Matrix
- **REQ-001**: System shall authenticate users via OAuth2/OIDC.
- **REQ-002**: API responses for errors shall comply with RFC 7807.

## 3. Machine-Readable Interface Contracts

```yaml
schema_version: "1.0"
contract_name: "UserAuthContract"
endpoints:
  - path: "/api/v1/auth/login"
    method: "POST"
    request:
      content_type: "application/json"
      fields:
        username: "string"
        password: "string"
    responses:
      200:
        content_type: "application/json"
        fields:
          access_token: "string"
          token_type: "bearer"
      400:
        content_type: "application/problem+json"
```

## 4. Verification Plan
- Unit tests under `tests/unit/`
- Integration tests under `tests/integration/`
"""


TASKS_TEMPLATE = """# Work Breakdown Structure (WBS) Tasks

Specification Ref: `SPEC-001`
Compliance: ISO/IEC/IEEE 29148 / ASD-STE100

- [ ] Task 1: Initialize database migration script.
- [ ] Task 2: Implement domain model and repository.
- [ ] Task 3: Implement business service layer.
- [ ] Task 4: Implement API router returning RFC 7807 errors.
- [ ] Task 5: Build frontend components using tokens.
"""


ADR_TEMPLATE = """# ADR-0001: Architecture Decision Record Template

## Context & Problem Statement
Record key architectural decisions under ISO/IEC/IEEE 42010:2022.

## Decision Drivers
- Modularity & Reusability (ISO 25010)
- Deterministic Verification (ISO 29119)
- W3C DTCG Tokenization

## Considered Options
1. Monolithic coupled structure
2. Layered Hexagonal / Clean Architecture

## Decision Outcome
Chosen Option: Hexagonal / Clean Architecture.
"""


PRE_PUSH_HOOK_SCRIPT = """#!/usr/bin/env bash
# ArchGuard Automated Pre-Push Governance Gate
echo "===> [ArchGuard] Running deterministic architecture governance checks..."
if command -v archguard >/dev/null 2>&1; then
    archguard check --all
    exit $?
elif command -v uv >/dev/null 2>&1; then
    uv run archguard check --all
    exit $?
elif command -v python3 >/dev/null 2>&1; then
    python3 -m archguard.cli.main check --all
    exit $?
else
    echo "Warning: archguard executable not found in PATH. Skipping hook."
    exit 0
fi
"""


WORKFLOW_TEMPLATE = """name: ArchGuard Architecture Governance Gate

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main, dev ]

jobs:
  archguard-audit:
    name: ISO & W3C Standards Validation
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install ArchGuard
        run: |
          pip install uv
          uv pip install --system . || uv pip install --system archguard

      - name: Run Deterministic ArchGuard Gate
        run: |
          archguard check --all
"""



def scaffold_project(target_dir: Path, project_type: str = "fullstack") -> None:
    """Scaffold standard ISO/W3C compliant project topology."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Config file
    (target_dir / "archguard.yaml").write_text(DEFAULT_ARCHGUARD_CONFIG_YAML, encoding="utf-8")

    # 2. ADR Directory
    adr_dir = target_dir / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    (adr_dir / "0001-record-architecture-decisions.md").write_text(ADR_TEMPLATE, encoding="utf-8")

    # 3. Specs Directory
    spec_dir = target_dir / "specs" / "001-initial-architecture"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text(SPEC_TEMPLATE, encoding="utf-8")
    (spec_dir / "tasks.md").write_text(TASKS_TEMPLATE, encoding="utf-8")

    # 4. Topology based on project_type
    if project_type in {"fullstack", "react-fastapi", "scada"}:
        # Frontend
        styles_dir = target_dir / "frontend" / "src" / "styles"
        styles_dir.mkdir(parents=True, exist_ok=True)
        (styles_dir / "tokens.css").write_text(TOKENS_CSS_TEMPLATE, encoding="utf-8")

        common_comp = target_dir / "frontend" / "src" / "components" / "common"
        common_comp.mkdir(parents=True, exist_ok=True)
        (common_comp / "Button.tsx").write_text(
            """import React from 'react';\n\nexport const Button: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = (props) => {\n  return <button style={{ backgroundColor: 'var(--color-primary)' }} {...props} />;\n};\n""",
            encoding="utf-8",
        )

        pages_dir = target_dir / "frontend" / "src" / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        (pages_dir / "Dashboard.tsx").write_text(
            """import React from 'react';\nimport { Button } from '../components/common/Button';\n\nexport const Dashboard: React.FC = () => {\n  return (\n    <div>\n      <h1>System Dashboard</h1>\n      <Button onClick={() => alert('ok')}>Action</Button>\n    </div>\n  );\n};\n""",
            encoding="utf-8",
        )

        # Backend
        for layer in ["api", "service", "repository", "models", "core"]:
            layer_dir = target_dir / "backend" / "src" / layer
            layer_dir.mkdir(parents=True, exist_ok=True)
            (layer_dir / "__init__.py").write_text("", encoding="utf-8")

        # Sample service and api
        (target_dir / "backend" / "src" / "service" / "user_service.py").write_text(
            "class UserService:\n    def get_user(self, user_id: str):\n        return {'id': user_id, 'name': 'Operator'}\n",
            encoding="utf-8",
        )
        (target_dir / "backend" / "src" / "api" / "routes.py").write_text(
            "from backend.src.service.user_service import UserService\n\ndef get_user_endpoint():\n    service = UserService()\n    return service.get_user('usr_123')\n",
            encoding="utf-8",
        )

    elif project_type == "backend-only":
        for layer in ["api", "service", "repository", "models", "core"]:
            layer_dir = target_dir / "backend" / "src" / layer
            layer_dir.mkdir(parents=True, exist_ok=True)
            (layer_dir / "__init__.py").write_text("", encoding="utf-8")

    # .gitignore
    (target_dir / ".gitignore").write_text(
        "__pycache__/\n*.py[cod]\nnode_modules/\ndist/\n.venv/\n.env\n",
        encoding="utf-8",
    )
