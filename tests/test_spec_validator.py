"""
Unit tests for ISO/IEC/IEEE 29148 Living Specification Validator.
"""

from pathlib import Path
from archguard.core.config import ArchGuardConfig, SpecConfig
from archguard.validators.spec_validator import SpecValidator


def test_spec_validator_passes_on_valid_spec(tmp_path: Path):
    spec_dir = tmp_path / "specs" / "001-auth"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text(
        "---\nid: SPEC-001\ntitle: Auth Feature\nversion: 1.0.0\nstatus: approved\n---\n\n# Spec\n\n```yaml\nschema: test\n```\n",
        encoding="utf-8",
    )
    (spec_dir / "tasks.md").write_text("- [ ] Task 1", encoding="utf-8")

    config = ArchGuardConfig(
        specs=SpecConfig(
            specs_dir="specs",
            require_contracts=True,
            require_traceability=True,
            require_tasks_sync=True,
        )
    )

    validator = SpecValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert len(result.violations) == 0


def test_spec_validator_fails_missing_spec_md(tmp_path: Path):
    spec_dir = tmp_path / "specs" / "001-auth"
    spec_dir.mkdir(parents=True, exist_ok=True)

    config = ArchGuardConfig(specs=SpecConfig(specs_dir="specs"))
    validator = SpecValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-29148-001" for v in result.violations)


def test_spec_validator_fails_missing_frontmatter(tmp_path: Path):
    spec_dir = tmp_path / "specs" / "001-auth"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text("# Spec without frontmatter\n```yaml\nx: 1\n```", encoding="utf-8")

    config = ArchGuardConfig(specs=SpecConfig(specs_dir="specs"))
    validator = SpecValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-29148-003" for v in result.violations)


def test_spec_validator_fails_missing_contract(tmp_path: Path):
    spec_dir = tmp_path / "specs" / "001-auth"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec.md").write_text(
        "---\nid: SPEC-001\ntitle: Auth Feature\nversion: 1.0.0\nstatus: approved\n---\n\n# Narrative text only without code block.\n",
        encoding="utf-8",
    )

    config = ArchGuardConfig(specs=SpecConfig(specs_dir="specs", require_contracts=True))
    validator = SpecValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-29148-006" for v in result.violations)
