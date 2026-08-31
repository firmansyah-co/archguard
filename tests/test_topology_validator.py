"""
Unit tests for ISO/IEC/IEEE 12207 Repository Topology Validator.
"""

from pathlib import Path
from archguard.core.config import ArchGuardConfig, TopologyConfig
from archguard.validators.topology_validator import TopologyValidator


def test_topology_validator_passes_on_clean_workspace(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Project", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'", encoding="utf-8")
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    (adr_dir / "0001-record.md").write_text("# ADR", encoding="utf-8")

    config = ArchGuardConfig(
        topology=TopologyConfig(
            forbidden_root_extensions=[".sh", ".py", ".ts"],
            allowed_root_files=["pyproject.toml", "README.md"],
            require_adr_dir=True,
            adr_dir="docs/adr",
        )
    )

    validator = TopologyValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert len(result.violations) == 0


def test_topology_validator_fails_on_adhoc_root_script(tmp_path: Path):
    (tmp_path / "scratchpad.py").write_text("print('test')", encoding="utf-8")

    config = ArchGuardConfig(
        topology=TopologyConfig(
            forbidden_root_extensions=[".sh", ".py", ".ts"],
            allowed_root_files=["pyproject.toml", "README.md"],
            require_adr_dir=False,
        )
    )

    validator = TopologyValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-12207-001" for v in result.violations)
