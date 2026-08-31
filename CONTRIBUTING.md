# Contributing to ArchGuard

We welcome contributions to ArchGuard! Please review these guidelines before submitting a pull request.

## Development Workflow

1. Fork and clone the repository.
2. Set up virtual environment and dependencies:
   ```bash
   pip install uv
   uv pip install --system -e ".[dev]"
   ```
3. Run test suite:
   ```bash
   pytest tests/
   ```
4. Run self-governance checks:
   ```bash
   archguard check --all
   ```

## Commit Standards

ArchGuard strictly follows Conventional Commits 1.0.0 in ASD-STE100 English:
- `feat(scope): ...`
- `fix(scope): ...`
- `refactor(scope): ...`
- `test(scope): ...`
- `docs(scope): ...`
