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


def test_token_validator_respects_allow_layout_pixel_literals_and_micro_spacing(tmp_path: Path):
    css_file = tmp_path / "frontend" / "src" / "style.css"
    css_file.parent.mkdir(parents=True, exist_ok=True)
    css_file.write_text(
        "div {\n  padding: 1px;\n  margin: 0px;\n  height: 2px;\n  width: 200px;\n}\n",
        encoding="utf-8",
    )

    # 1. Default (allow_layout_pixel_literals=False, ignore_micro_spacing=True): 200px is flagged, 0px/1px/2px ignored
    config_default = ArchGuardConfig(
        tokens=TokenConfig(
            token_files=[],
            scan_paths=["frontend/src"],
            allow_layout_pixel_literals=False,
            ignore_micro_spacing=True,
        )
    )
    res1 = TokenValidator(root_dir=tmp_path, config=config_default).validate()
    w3c_4_violations = [v for v in res1.violations if v.rule_id == "W3C-DTCG-004"]
    assert len(w3c_4_violations) == 1
    assert "width: 200px" in w3c_4_violations[0].message

    # 2. ignore_micro_spacing=False: all 4 are flagged
    config_strict = ArchGuardConfig(
        tokens=TokenConfig(
            token_files=[],
            scan_paths=["frontend/src"],
            allow_layout_pixel_literals=False,
            ignore_micro_spacing=False,
        )
    )
    res2 = TokenValidator(root_dir=tmp_path, config=config_strict).validate()
    w3c_4_violations_strict = [v for v in res2.violations if v.rule_id == "W3C-DTCG-004"]
    assert len(w3c_4_violations_strict) == 4

    # 3. allow_layout_pixel_literals=True: skipped completely
    config_allowed = ArchGuardConfig(
        tokens=TokenConfig(
            token_files=[],
            scan_paths=["frontend/src"],
            allow_layout_pixel_literals=True,
            ignore_micro_spacing=False,
        )
    )
    res3 = TokenValidator(root_dir=tmp_path, config=config_allowed).validate()
    w3c_4_violations_allowed = [v for v in res3.violations if v.rule_id == "W3C-DTCG-004"]
    assert len(w3c_4_violations_allowed) == 0
