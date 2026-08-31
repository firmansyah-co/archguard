"""
Unit tests for ISO/IEC 25010 Component Reusability Validator.
"""

from pathlib import Path
from archguard.core.config import ArchGuardConfig, ComponentConfig
from archguard.validators.component_validator import ComponentValidator


def test_component_validator_passes_when_using_shared_components(tmp_path: Path):
    pages_dir = tmp_path / "frontend" / "src" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "Dashboard.tsx").write_text(
        "import { Button } from '../components/common/Button';\nexport const Dashboard = () => <Button>Click</Button>;\n",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        components=ComponentConfig(
            pages_dirs=["frontend/src/pages"],
            forbidden_raw_primitives=["button", "input"],
        )
    )

    validator = ComponentValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert len(result.violations) == 0


def test_component_validator_fails_on_raw_button_in_page(tmp_path: Path):
    pages_dir = tmp_path / "frontend" / "src" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "Dashboard.tsx").write_text(
        "export const Dashboard = () => <div><button onClick={() => {}}>Click</button></div>;\n",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        components=ComponentConfig(
            pages_dirs=["frontend/src/pages"],
            forbidden_raw_primitives=["button", "input"],
        )
    )

    validator = ComponentValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-25010-001" for v in result.violations)
