---
name: archguard
description: "Deterministic ISO/IEC/IEEE, W3C DTCG, and RFC architecture governance engine."
version: 1.0.0
author: Firmansyah Consulting & Enterprise Systems
license: Apache-2.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Architecture, Governance, ISO, W3C, RFC, Quality, Static-Analysis, Token-Enforcement]
---

# ArchGuard Architecture Governance Engine

Deterministic ISO/IEC/IEEE, W3C DTCG, and RFC standards enforcement for autonomous agents and enterprise teams.

## When to Use

- When scaffolding new frontend, backend, or fullstack repositories.
- Before committing or pushing code to ensure zero architectural degradation.
- When validating design system token adherence (W3C DTCG).
- When validating Hexagonal / Clean Architecture boundaries (ISO/IEC/IEEE 42010).
- When validating living specifications and contracts (ISO/IEC/IEEE 29148).
- When preventing component proliferation and raw HTML primitive pollution (ISO/IEC 25010).
- When maintaining clean workspace topology and zero ad-hoc root scripts (ISO/IEC/IEEE 12207).

---

## Quickstart Commands

```bash
# 1. Initialize project with ISO topology and configs
archguard init --type fullstack

# 2. Run all deterministic architecture checks
archguard check --all

# 3. Run specific standards audits
archguard check --tokens
archguard check --layers
archguard check --specs
archguard check --topology
archguard check --components

# 4. Install pre-push Git hook
archguard hook install

# 5. Generate GitHub Actions CI workflow
archguard ci-gen
```

---

## Standards Enforcement Matrix

| Standard | Domain | Gate Checked |
|---|---|---|
| **ISO/IEC/IEEE 42010:2022** | Layer Architecture | No database / query imports in API controllers. Clean hexagonal boundaries. |
| **ISO/IEC/IEEE 29148:2018** | Living Specifications | `specs/NNN-*/spec.md` structure, frontmatter, machine-readable contracts (YAML/JSON). |
| **ISO/IEC 25010:2023** | Component Reusability | Rejects raw HTML primitives (`<button>`, `<input>`) in domain pages. Enforces shared design system components. |
| **W3C DTCG 2025.10** | Closed-Set Tokens | Rejects hardcoded `#hex`, `rgb()`, and pixel dimensions. Enforces `var(--color-*)` and `var(--space-*)`. |
| **ISO/IEC/IEEE 12207:2017** | Workspace Topology | Zero ad-hoc scripts (`.py`, `.sh`, `.ts`) in root directory. Enforces `docs/adr/` tracking. |
| **RFC 7807 / RFC 9457** | Problem Details | Machine-readable HTTP API error payload contracts. |

---

## Autonomous Agent Integration (Hermes Pattern)

When writing code in any project governed by ArchGuard:

1. **Check First**: Read `archguard.yaml` to discover project layer rules and token registries.
2. **Token Compliance**: Always import tokens from `frontend/src/styles/tokens.css` or use CSS variables. Never introduce raw hex colors.
3. **Layer Separation**: Put business logic in `service/` and persistence in `repository/`. Never import DB drivers into `api/`.
4. **Pre-PR Audit**: Always execute `archguard check --all` before creating a pull request.
