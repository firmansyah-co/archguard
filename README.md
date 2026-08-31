# ArchGuard: Enterprise Architecture Governance Engine

[![CI](https://github.com/firmansyah-co/archguard/actions/workflows/ci.yml/badge.svg)](https://github.com/firmansyah-co/archguard/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Standards Compliance](https://img.shields.io/badge/standards-ISO%20%2F%20W3C%20%2F%20RFC-emerald)](docs/STANDARDS.md)

**ArchGuard** is a deterministic static architecture governance engine designed for modern enterprise software systems, autonomous multi-agent coding loops (Hermes Agent), and mission-critical SCADA/OT/IT infrastructure.

ArchGuard mathematically verifies architectural integrity, design tokens, layer boundaries, and living requirements specifications across repositories with zero LLM context rot.

---

## 🏛️ Standards Enforced

ArchGuard turns abstract standards into automated, non-bypassable CI/CD gates:

```
+-----------------------------------------------------------------------------------+
|                           ARCHGUARD GOVERNANCE ENGINE                             |
+-----------------------------------------------------------------------------------+
|  ISO/IEC/IEEE 42010:2022   | Clean Architecture & Hexagonal Layer Separation       |
|  ISO/IEC/IEEE 29148:2018   | Living Specifications & Machine-Readable Contracts   |
|  ISO/IEC 25010:2023        | Software Modularity, Component Reusability & Quality  |
|  ISO/IEC/IEEE 29119:2022   | Software Testing Taxonomy & Evidence Verification     |
|  ISO/IEC/IEEE 12207:2017   | Software Life Cycle Processes & Repository Hygiene    |
|  W3C DTCG 2025.10          | Closed-Set Design Tokens & Zero Hardcoded Styling     |
|  RFC 7807 / RFC 9457       | Problem Details for HTTP APIs Error Contracts         |
|  ASD-STE100 Issue 8        | Simplified Technical English Documentation Standards  |
+-----------------------------------------------------------------------------------+
```

---

## 🚀 Quick Start

### Installation

```bash
# Via pip / uv
pip install archguard

# Or with uv
uv pip install archguard
```

### Initialize a New Project Topology

```bash
# Scaffold ISO/W3C compliant structure
archguard init --type fullstack
```

Supported project archetypes: `fullstack`, `react-fastapi`, `scada`, `library`, `backend-only`.

### Run Governance Audits

```bash
# Run all standards validators
archguard check --all

# Run specific validators
archguard check --tokens      # W3C DTCG design tokens
archguard check --layers      # ISO 42010 hexagonal boundaries
archguard check --specs       # ISO 29148 living specs & contracts
archguard check --topology    # ISO 12207 clean root & ADR tracking
archguard check --components  # ISO 25010 component reusability
```

### Install Git Hooks

```bash
# Installs deterministic pre-push gate into .git/hooks/
archguard hook install
```

### Generate GitHub Actions CI Workflow

```bash
# Creates .github/workflows/archguard-governance.yml
archguard ci-gen
```

---

## 🧩 Validation Engines

### 1. W3C DTCG Token Validator (`--tokens`)
- Validates that CSS and components use variables declared in closed token manifests (`tokens.css`, `global.css`).
- Flags hardcoded `#hex` colors, `rgb()` expressions, and un-tokenized layout dimensions.

### 2. Hexagonal Layer Boundary Validator (`--layers`)
- Parses Python AST to verify strict unidirectional data flow (`API` -> `Service` -> `Repository` -> `Models`).
- Rejects direct database driver imports (SQLAlchemy, SQLModel, Psycopg) inside API controllers.

### 3. Living Specification & Contract Validator (`--specs`)
- Enforces ISO/IEC/IEEE 29148 metadata frontmatter in `specs/NNN-*/spec.md`.
- Requires machine-readable interface contracts in YAML, JSON, or TypeScript schemas.
- Validates companion `tasks.md` Work Breakdown Structure (WBS) synchronization.

### 4. Component Reusability Validator (`--components`)
- Prevents component proliferation in frontend domain views.
- Rejects raw HTML primitives (`<button>`, `<input>`, `<select>`) in domain pages, enforcing reusable primitives from `components/common/`.

### 5. Repository Topology & Hygiene Validator (`--topology`)
- Enforces zero ad-hoc/scratchpad scripts in the repository root directory.
- Requires active Architecture Decision Record (ADR) tracking in `docs/adr/`.

---

## 🤖 Hermes Agent & Autonomous Coding Integration

ArchGuard is natively integrated with [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Load the bundled skill:
```bash
hermes skill install skills/archguard
```

See [docs/HERMES_INTEGRATION.md](docs/HERMES_INTEGRATION.md) for full orchestration patterns.

---

## 📁 Repository Structure

```
archguard/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── reusable-archguard-gate.yml
├── docs/
│   ├── STANDARDS.md
│   ├── HERMES_INTEGRATION.md
│   └── adr/
│       └── 0001-initial-architecture.md
├── skills/
│   └── archguard/
│       ├── SKILL.md
│       └── scripts/run_archguard.py
├── specs/
│   └── 001-initial-architecture/
│       ├── spec.md
│       └── tasks.md
├── src/
│   └── archguard/
│       ├── cli/
│       ├── core/
│       ├── templates/
│       └── validators/
├── tests/
│   ├── test_cli.py
│   ├── test_component_validator.py
│   ├── test_layer_validator.py
│   ├── test_spec_validator.py
│   ├── test_token_validator.py
│   └── test_topology_validator.py
├── pyproject.toml
├── archguard.yaml
├── LICENSE
└── README.md
```

---

## 📄 License

ArchGuard is open-source software licensed under the **Apache 2.0 License**.

Owned and maintained by **Firmansyah Consulting & Enterprise Systems** (`firmansyah-co`).
