"""
Unit tests for ISO/IEC/IEEE 42010 Layer Architecture Validator.
"""

from pathlib import Path
from archguard.core.config import ArchGuardConfig, LayerConfig
from archguard.validators.layer_validator import LayerValidator


def test_layer_validator_clean_architecture_passes(tmp_path: Path):
    api_dir = tmp_path / "backend" / "src" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "user_route.py").write_text(
        "from backend.src.service.user_service import UserService\n\ndef get_user():\n    return UserService().get()\n",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        layers=LayerConfig(
            backend_root="backend/src",
            layers=["api", "service", "repository", "models"],
            forbidden_dependencies={"api": ["repository", "sqlalchemy"]},
        )
    )

    validator = LayerValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert len(result.violations) == 0


def test_layer_validator_fails_when_api_imports_repository(tmp_path: Path):
    api_dir = tmp_path / "backend" / "src" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "bad_route.py").write_text(
        "from backend.src.repository.user_repo import UserRepository\n\ndef direct_db():\n    return UserRepository().fetch_all()\n",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        layers=LayerConfig(
            backend_root="backend/src",
            layers=["api", "service", "repository", "models"],
            forbidden_dependencies={"api": ["repository", "sqlalchemy"]},
        )
    )

    validator = LayerValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-42010-001" for v in result.violations)


def test_layer_validator_fails_when_api_imports_sqlalchemy(tmp_path: Path):
    api_dir = tmp_path / "backend" / "src" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "bad_route.py").write_text(
        "import sqlalchemy\n\ndef direct_sql():\n    pass\n",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        layers=LayerConfig(
            backend_root="backend/src",
            layers=["api", "service", "repository", "models"],
            forbidden_dependencies={"api": ["repository", "sqlalchemy"]},
        )
    )

    validator = LayerValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-42010-001" for v in result.violations)
