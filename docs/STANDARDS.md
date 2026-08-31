# ArchGuard International Standards Compliance Matrix

This document provides detailed normative mappings between international engineering standards and ArchGuard deterministic validation engines.

---

## 1. ISO/IEC/IEEE 42010:2022 — Architecture Description & Layer Boundaries

### Objective
Ensure systems have modular, loosely coupled architectures with clear separation of concerns and unidirectional dependencies.

### Implementation in ArchGuard (`archguard.validators.layer_validator`)
- **AST Parsing**: Analyzes Python `import` and `from ... import` statements statically.
- **Rules Enforced**:
  - `API -> Service`: Allowed.
  - `API -> Repository`: **FORBIDDEN (ISO-42010-001)**. Prevents data access leaking into presentation controllers.
  - `API -> Database Drivers (SQLAlchemy, SQLModel, Psycopg)`: **FORBIDDEN**.
  - `Models -> API/Service`: **FORBIDDEN**. Domain models must remain pure and free from upstream dependencies.

---

## 2. ISO/IEC/IEEE 29148:2018 — Requirements Engineering & Living Specs

### Objective
Maintain verifiable, living requirements specifications synchronized with implementation tasks and structured machine-readable contracts.

### Implementation in ArchGuard (`archguard.validators.spec_validator`)
- **Spec Metadata**: Enforces YAML frontmatter in all `specs/NNN-*/spec.md` files (`id`, `title`, `version`, `status`).
- **Machine-Readable Contracts**: Enforces presence of structured interface schemas (YAML register maps, JSON Schema, or TypeScript interfaces) to eliminate narrative ambiguity.
- **Traceability**: Requires companion `tasks.md` containing executable Work Breakdown Structure items.

---

## 3. ISO/IEC 25010:2023 — Software Product Quality & Modularity

### Objective
Enforce high modularity, reusability, and maintainability across frontend component hierarchies.

### Implementation in ArchGuard (`archguard.validators.component_validator`)
- **Design System Adherence**: Forbids raw HTML primitives (`<button>`, `<input>`, `<select>`, `<textarea>`) inside domain pages.
- **Component Silos**: Enforces usage of approved shared components located under `components/common/`.

---

## 4. W3C DTCG 2025.10 — Closed-Set Design Tokens

### Objective
Eliminate visual drift and hardcoded styling by binding all styling attributes to semantic design token custom properties.

### Implementation in ArchGuard (`archguard.validators.token_validator`)
- **Closed Registry**: Scans CSS/SCSS and JSX/TSX for CSS variable usage (`var(--token-name)`) and ensures every token is formally declared in `tokens.css` or `global.css`.
- **Zero Raw Color Codes**: Flags unapproved `#hex` and `rgb()` values.
- **Dimension Tokenization**: Warns against hardcoded pixel values for layout properties (`height`, `width`, `padding`, `margin`).

---

## 5. ISO/IEC/IEEE 12207:2017 & IEEE 828 — Repository Hygiene & Life Cycle

### Objective
Maintain clean project workspaces, prevent execution of ad-hoc scratchpad scripts in project roots, and maintain explicit architectural decision records.

### Implementation in ArchGuard (`archguard.validators.topology_validator`)
- **Zero Ad-hoc Root Scripts**: Rejects unapproved `.py`, `.sh`, `.ts`, `.js` files in the repository root directory.
- **ADR Governance**: Enforces presence of `docs/adr/` directory with formal decision records.

---

## 6. RFC 7807 & RFC 9457 — Problem Details for HTTP APIs

### Objective
Provide standard, machine-readable format for HTTP API error responses.

### Implementation in ArchGuard
- Scaffolds API templates and spec schemas that mandate `application/problem+json` error responses containing `type`, `title`, `status`, `detail`, and `instance`.
