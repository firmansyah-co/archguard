"""
Unit tests for ISO/IEC 25010:2023 Universal Data Integrity & Zero-Mock Validator.
"""

from pathlib import Path
from archguard.core.config import ArchGuardConfig, DataIntegrityConfig
from archguard.validators.data_integrity_validator import DataIntegrityValidator


def test_data_integrity_passes_on_clean_production_code(tmp_path: Path):
    backend_src = tmp_path / "backend" / "src"
    backend_src.mkdir(parents=True, exist_ok=True)
    (backend_src / "telemetry_service.py").write_text(
        """
class TelemetryService:
    def process_frame(self, frame_bytes: bytes) -> dict:
        parsed = self.parser.parse(frame_bytes)
        return parsed
""",
        encoding="utf-8",
    )

    frontend_src = tmp_path / "frontend" / "src"
    frontend_src.mkdir(parents=True, exist_ok=True)
    (frontend_src / "TelemetryDisplay.tsx").write_text(
        """
import React from 'react';
import { TelemetryProps } from './types';

export const TelemetryDisplay: React.FC<TelemetryProps> = ({ telemetry }) => {
    if (!telemetry) return <div>No Telemetry</div>;
    return <div>{telemetry.value}</div>;
};
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(
            production_paths=["backend/src", "frontend/src"],
            test_paths=["tests"],
        )
    )

    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert len(result.violations) == 0


def test_rule_001_flags_deep_synthetic_literals_python(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "feed.py").write_text(
        """
# Hardcoded fake telemetry payload
SYNTHETIC_DATA = {
    "device_01": {
        "telemetry": {
            "value": 42.5,
            "status": "ONLINE"
        }
    }
}
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-25010-INT-001" for v in result.violations)


def test_rule_001_flags_deep_synthetic_literals_typescript(tmp_path: Path):
    src = tmp_path / "frontend" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "constants.ts").write_text(
        """
export const INITIAL_METRICS = [
    {
        id: "motor_1",
        metrics: {
            oee: 88.5,
            latency: 14.2
        }
    }
];
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["frontend/src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-25010-INT-001" for v in result.violations)


def test_rule_001_ignores_test_and_mock_directories(tmp_path: Path):
    test_dir = tmp_path / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "test_fixture.py").write_text(
        """
MOCK_PAYLOAD = {
    "telemetry": {
        "value": 100.0,
        "status": "EXECUTE"
    }
}
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["."], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert len(result.violations) == 0


def test_rule_002_flags_heuristic_state_inference_python(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "state_resolver.py").write_text(
        """
def check_state(status_text: str) -> bool:
    if "EXECUTE" in status_text:
        return True
    return False
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-25010-INT-002" for v in result.violations)


def test_rule_002_flags_heuristic_state_inference_typescript(tmp_path: Path):
    src = tmp_path / "frontend" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "StatusBadge.tsx").write_text(
        """
export function getStatus(rawStatus: string) {
    if (rawStatus.includes("FAULT")) {
        return "CRITICAL";
    }
    return "NORMAL";
}
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["frontend/src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-25010-INT-002" for v in result.violations)


def test_rule_003_flags_synthetic_magic_number_fallbacks_python(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "gateway.py").write_text(
        """
def extract_latency(packet: dict) -> float:
    return packet.get("latency", 4.2)
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-25010-INT-003" for v in result.violations)


def test_rule_003_flags_synthetic_magic_number_fallbacks_typescript(tmp_path: Path):
    src = tmp_path / "frontend" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "MetricsCard.tsx").write_text(
        """
export const MetricsCard = ({ latency, packets }: any) => {
    const displayLatency = latency ?? 4.2;
    const displayPackets = packets || 28450;
    return <div>{displayLatency} / {displayPackets}</div>;
};
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["frontend/src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    violations = [v for v in result.violations if v.rule_id == "ISO-25010-INT-003"]
    assert len(violations) >= 2


def test_rule_004_flags_mock_artifacts_in_production(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "feed.ts").write_text(
        """
const sampleData = { id: 1 };
const mockTelemetry = fetchLiveTelemetry();
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-25010-INT-004" for v in result.violations)


def test_data_integrity_disabled_skips(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "mock.ts").write_text("const mockTelemetry = 123;\n", encoding="utf-8")

    config = ArchGuardConfig(integrity=DataIntegrityConfig(enabled=False))
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert result.checked_files_count == 0


def test_rule_001_precision_refinements_select_options_and_state_setters(tmp_path: Path):
    src = tmp_path / "frontend" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "SelectOptions.tsx").write_text(
        """
export const SELECT_OPTIONS = [
    { value: "direct", label: "Direct Inbound" },
    { value: "batched", label: "Batched Buffer" }
];

export function handleUpdate() {
    setFilter({ status: "ACTIVE", value: "test" });
}
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["frontend/src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is True
    assert len(result.violations) == 0


def test_rule_001_flags_multiple_numeric_mock_metrics(tmp_path: Path):
    src = tmp_path / "frontend" / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "MockMetrics.tsx").write_text(
        """
export const MOCK_TELEMETRY = {
    plant_a: {
        oee_percent: 88.5,
        mtbf_hours: 720.0
    },
    plant_b: {
        jitter_ms: 0.32,
        total_packets: 28450
    }
};
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["frontend/src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    assert any(v.rule_id == "ISO-25010-INT-001" for v in result.violations)


def test_rule_003_ignores_config_defaults_and_flags_telemetry_keys(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "config_and_telemetry.py").write_text(
        """
def load_config(opts: dict):
    # Valid config defaults - must NOT be flagged
    ntp_port = opts.get("ntp_port", 123)
    timeout_ms = opts.get("timeout_ms", 5000)
    retention_days = opts.get("retention_days", 30)
    return ntp_port, timeout_ms, retention_days

def get_live_latency(payload: dict):
    # Synthetic telemetry default - MUST be flagged
    return payload.get("latency_ms", 12.5)
""",
        encoding="utf-8",
    )

    config = ArchGuardConfig(
        integrity=DataIntegrityConfig(production_paths=["src"], test_paths=["tests"])
    )
    validator = DataIntegrityValidator(root_dir=tmp_path, config=config)
    result = validator.validate()
    assert result.passed is False
    int3_violations = [v for v in result.violations if v.rule_id == "ISO-25010-INT-003"]
    assert len(int3_violations) == 1
    assert "latency_ms" in int3_violations[0].message

