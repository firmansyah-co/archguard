# Work Breakdown Structure (WBS) Tasks

Specification Ref: `SPEC-002`
Compliance: ISO/IEC/IEEE 29148 / ASD-STE100

- [x] Task 1: Define Git Topology configuration schemas and data models in `archguard/core/config.py`.
- [x] Task 2: Implement IEEE 828 dual-trunk topology validator in `archguard/validators/topology_validator_v2.py`.
- [x] Task 3: Implement branch naming convention pattern checks (feat/*, fix/*, refactor/*, chore/*, ci/*, docs/*).
- [x] Task 4: Implement stale ephemeral branch age detection (TOP-005).
- [x] Task 5: Implement direct push and reflog audit rules (TOP-004).
- [x] Task 6: Implement SemVer 2.0.0 and PEP 440 Git-derived deterministic versioning engine in `archguard/versioning/engine.py`.
- [x] Task 7: Implement AST scanner for manual hardcoded version edits.
- [x] Task 8: Implement version synchronizer across pyproject.toml, package.json, and `__init__.py`.
- [x] Task 9: Implement CLI subcommands `archguard topology` and `archguard version`.
- [x] Task 10: Implement unit and integration test suite in `tests/test_topology_validator_v2.py`, `tests/test_cli_topology.py`, and `tests/test_versioning_engine.py`.
- [x] Task 11: Implement CI synthetic branch handling and Python 3.10 datetime compatibility.
- [x] Task 12: Validate end-to-end governance gates with `archguard check --all`.
