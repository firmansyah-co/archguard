"""
ArchGuard configuration parsing and schema validation.
"""

from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class TokenConfig(BaseModel):
    enabled: bool = True
    token_files: List[str] = Field(
        default_factory=lambda: [
            "frontend/src/styles/tokens.css",
            "frontend/src/styles/global.css",
            "src/styles/tokens.css",
            "src/styles/global.css",
            "tokens.json",
        ]
    )
    scan_paths: List[str] = Field(
        default_factory=lambda: ["frontend/src", "src/components", "src/pages"]
    )
    allowed_hex_colors: List[str] = Field(default_factory=list)
    enforce_unitless_zero: bool = True


class LayerConfig(BaseModel):
    enabled: bool = True
    backend_root: str = "backend/src"
    layers: List[str] = Field(
        default_factory=lambda: ["api", "service", "repository", "models", "core"]
    )
    forbidden_dependencies: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "api": ["repository", "sqlalchemy", "sqlmodel", "psycopg", "tortoise", "prisma"],
            "models": ["api", "service", "repository"],
            "service": ["api"],
            "repository": ["api"],
        }
    )


class ComponentConfig(BaseModel):
    enabled: bool = True
    pages_dirs: List[str] = Field(
        default_factory=lambda: ["frontend/src/pages", "src/pages", "frontend/src/views"]
    )
    common_components_dirs: List[str] = Field(
        default_factory=lambda: ["frontend/src/components/common", "src/components/common"]
    )
    forbidden_raw_primitives: List[str] = Field(
        default_factory=lambda: ["button", "input", "select", "textarea", "table", "dialog"]
    )
    max_unshared_components_per_page: int = 4


class SpecConfig(BaseModel):
    enabled: bool = True
    specs_dir: str = "specs"
    require_contracts: bool = True
    require_traceability: bool = True
    require_tasks_sync: bool = True


class TopologyConfig(BaseModel):
    enabled: bool = True
    forbidden_root_extensions: List[str] = Field(
        default_factory=lambda: [".sh", ".py", ".js", ".ts", ".tmp", ".bak", ".scratch"]
    )
    allowed_root_files: List[str] = Field(
        default_factory=lambda: [
            "pyproject.toml",
            "package.json",
            "README.md",
            "LICENSE",
            ".gitignore",
            ".env.example",
            "Dockerfile",
            "docker-compose.yml",
            "Makefile",
            "archguard.yaml",
            "archguard.yml",
            "tsconfig.json",
            "vite.config.ts",
            "tailwind.config.js",
            "hatch.toml",
            "poetry.lock",
            "Cargo.toml",
            "Cargo.lock",
        ]
    )
    require_adr_dir: bool = True
    adr_dir: str = "docs/adr"


class DataIntegrityConfig(BaseModel):
    enabled: bool = True
    production_paths: List[str] = Field(
        default_factory=lambda: [
            "frontend/src",
            "backend/src",
            "src",
        ]
    )
    test_paths: List[str] = Field(
        default_factory=lambda: [
            "tests",
            "test",
            "__tests__",
            "frontend/src/tests",
            "backend/tests",
            "src/tests",
            "mocks",
            "__mocks__",
            "fixtures",
        ]
    )
    ban_unanchored_synthetic_literals: bool = True
    ban_heuristic_state_inference: bool = True
    ban_synthetic_fallbacks: bool = True
    ban_mock_artifacts_in_production: bool = True
    domain_keys: List[str] = Field(
        default_factory=lambda: [
            "value",
            "status",
            "telemetry",
            "metrics",
            "oee",
            "packets",
            "latency",
            "user",
            "token",
            "voltage",
            "current",
            "temperature",
            "pressure",
            "speed",
            "frequency",
            "power",
        ]
    )
    operational_states: List[str] = Field(
        default_factory=lambda: [
            "EXECUTE",
            "ONLINE",
            "FAULT",
            "IDLE",
            "SUSPENDED",
            "STOPPED",
            "STARTING",
            "COMPLETING",
            "COMPLETE",
            "HOLDING",
            "ABORTED",
            "RUNNING",
            "ERROR",
            "WARNING",
            "EMERGENCY",
        ]
    )
    mock_keywords: List[str] = Field(
        default_factory=lambda: [
            "mock",
            "dummy",
            "fake",
            "stub",
            "sampleData",
            "sample_data",
            "mockData",
            "mock_data",
            "fakeData",
            "fake_data",
            "dummyData",
            "dummy_data",
        ]
    )


class ArchGuardConfig(BaseModel):
    version: str = "1.0"
    project_name: Optional[str] = None
    project_type: str = "fullstack"
    tokens: TokenConfig = Field(default_factory=TokenConfig)
    layers: LayerConfig = Field(default_factory=LayerConfig)
    components: ComponentConfig = Field(default_factory=ComponentConfig)
    specs: SpecConfig = Field(default_factory=SpecConfig)
    topology: TopologyConfig = Field(default_factory=TopologyConfig)
    integrity: DataIntegrityConfig = Field(default_factory=DataIntegrityConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "ArchGuardConfig":
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return cls(**data)
        
        candidates = [Path("archguard.yaml"), Path("archguard.yml"), Path(".archguard.yaml")]
        for p in candidates:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    return cls(**data)
        
        return cls()
