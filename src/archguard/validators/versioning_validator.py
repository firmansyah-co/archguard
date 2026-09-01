"""
Versioning and Manual Edit Governance Validator.
Standards: SemVer 2.0.0 / IEEE 828-2012 / PEP 440.
"""

from typing import Any, Dict, List
from archguard.core.models import CheckResult, Severity, StandardRef, Violation
from archguard.validators.base import BaseValidator
from archguard.versioning.engine import VersioningEngine


class VersioningValidator(BaseValidator):
    name = "versioning_validator"
    standard = StandardRef.SEMVER_2

    def validate(self) -> CheckResult:
        if not self.config.git_versioning.enabled:
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": "disabled"},
            )

        engine = VersioningEngine(root_dir=self.root_dir, config=self.config)
        violations = engine.detect_manual_edits()
        
        info = engine.get_version_info()
        metadata: Dict[str, Any] = {
            "computed_pep440": info.computed_pep440,
            "computed_semver": info.computed_semver,
            "base_version": info.base_version,
            "distance": info.distance,
            "sha": info.sha,
            "branch": info.branch,
        }

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0
        return CheckResult(
            validator_name=self.name,
            standard=self.standard,
            passed=passed,
            violations=violations,
            checked_files_count=len(self.config.git_versioning.version_files),
            metadata=metadata,
        )
