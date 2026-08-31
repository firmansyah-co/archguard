"""
Unit tests for W3C DTCG Token Validator.
"""

from pathlib import Path
from archguard.core.config import ArchGuardConfig, TokenConfig
from archguard.validators.token_validator import TokenValidator


def test_token_validator_passes_when_clean(tmp_path: Path):
    tokens_file = tmp_path / "frontend" / "src" / "styles" / "tokens.css"
    tokens_file.parent.mkdir(parents=True, exist_ok=True)
    tokens_file.write_text(
        ":root {\n  --color-primary: #0284c7;\n  --space-md: 16px;\n}\n",
        encoding="utf-8",
    )

    component_file = tmp_path / "frontend" / "src" / "components" / "Card.tsx"
    component_file.parent.mkdir(parents=True, exist_ok=True)
    component_file.write_text(
        "export const Card = () => <div style={{ color: 'var(--color-primary)' }}>Card</div>;\n",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        tokens=TokenConfig(
            token_files=["frontend/src/styles/tokens.css"],
            scan_paths=["frontend/src"],
            allowed_hex_colors=[],
        )
    )

    validator = TokenValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert len(result.violations) == 0


def test_token_validator_fails_on_undeclared_var(tmp_path: Path):
    tokens_file = tmp_path / "frontend" / "src" / "styles" / "tokens.css"
    tokens_file.parent.mkdir(parents=True, exist_ok=True)
    tokens_file.write_text(":root { --color-primary: #0284c7; }", encoding="utf-8")

    comp_file = tmp_path / "frontend" / "src" / "comp.tsx"
    comp_file.parent.mkdir(parents=True, exist_ok=True)
    comp_file.write_text("const c = 'var(--undeclared-color)';", encoding="utf-8")

    config = ArchGuardConfig(
        tokens=TokenConfig(
            token_files=["frontend/src/styles/tokens.css"],
            scan_paths=["frontend/src"],
        )
    )

    validator = TokenValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "W3C-DTCG-001" for v in result.violations)


def test_token_validator_fails_on_raw_hex(tmp_path: Path):
    comp_file = tmp_path / "frontend" / "src" / "comp.tsx"
    comp_file.parent.mkdir(parents=True, exist_ok=True)
    comp_file.write_text("const color = '#ff0044';", encoding="utf-8")

    config = ArchGuardConfig(
        tokens=TokenConfig(
            token_files=[],
            scan_paths=["frontend/src"],
            allowed_hex_colors=[],
        )
    )

    validator = TokenValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "W3C-DTCG-002" for v in result.violations)


def test_token_validator_fails_on_raw_rgb(tmp_path: Path):
    comp_file = tmp_path / "frontend" / "src" / "comp.tsx"
    comp_file.parent.mkdir(parents=True, exist_ok=True)
    comp_file.write_text("const c = 'rgba(255, 0, 0, 0.5)';", encoding="utf-8")

    config = ArchGuardConfig(
        tokens=TokenConfig(
            token_files=[],
            scan_paths=["frontend/src"],
        )
    )

    validator = TokenValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "W3C-DTCG-003" for v in result.violations)
