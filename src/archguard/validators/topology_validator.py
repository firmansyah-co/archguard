"""
Repository Topology & Architectural Hygiene Validator.
Enforces clean root directory (zero ad-hoc scripts), strict structure, and ADR tracking.
Standard: ISO/IEC/IEEE 12207:2017 / ISO/IEC/IEEE 42010:2022.
"""

from pathlib import Path
from typing import List
from archguard.core.models import CheckResult, Severity, StandardRef, Violation
from archguard.validators.base import BaseValidator


class TopologyValidator(BaseValidator):
    name = "topology_validator"
    standard = StandardRef.ISO_12207

    def validate(self) -> CheckResult:
        if not self.config.topology.enabled:
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": "disabled"},
            )

        violations: List[Violation] = []
        checked_count = 0

        forbidden_exts = set(self.config.topology.forbidden_root_extensions)
        allowed_files = set(self.config.topology.allowed_root_files)

        # 1. Scan root directory for ad-hoc scripts or unapproved scratchpad files
        for entry in self.root_dir.iterdir():
            if entry.name.startswith(".git"):
                continue

            checked_count += 1
            if entry.is_file():
                if entry.suffix in forbidden_exts and entry.name not in allowed_files:
                    violations.append(
                        Violation(
                            rule_id="ISO-12207-001",
                            standard=self.standard,
                            severity=Severity.ERROR,
                            message=f"Forbidden ad-hoc script or scratchpad file '{entry.name}' in project root directory.",
                            file_path=entry.name,
                            remediation_hint=f"Move '{entry.name}' to 'scripts/', 'tests/', or execute inside '/tmp/' / worktree.",
                        )
                    )

        # 2. Verify Architecture Decision Records (ADR) directory
        if self.config.topology.require_adr_dir:
            adr_dir = self.root_dir / self.config.topology.adr_dir
            if not adr_dir.exists():
                violations.append(
                    Violation(
                        rule_id="ISO-42010-002",
                        standard=StandardRef.ISO_42010,
                        severity=Severity.WARNING,
                        message=f"Architecture Decision Record directory '{self.config.topology.adr_dir}' is missing.",
                        file_path=self.config.topology.adr_dir,
                        remediation_hint=f"Create '{self.config.topology.adr_dir}' to record key architectural decisions.",
                    )
                )

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0
        return CheckResult(
            validator_name=self.name,
            standard=self.standard,
            passed=passed,
            violations=violations,
            checked_files_count=checked_count,
            metadata={"adr_dir": self.config.topology.adr_dir},
        )
