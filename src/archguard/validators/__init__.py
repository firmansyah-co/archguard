"""
Validator module exports and unified test suite runner.
"""

from pathlib import Path
from typing import List, Optional
from archguard.core.config import ArchGuardConfig
from archguard.core.models import CheckResult, Severity, SuiteResult
from archguard.validators.base import BaseValidator
from archguard.validators.token_validator import TokenValidator
from archguard.validators.layer_validator import LayerValidator
from archguard.validators.component_validator import ComponentValidator
from archguard.validators.spec_validator import SpecValidator
from archguard.validators.topology_validator import TopologyValidator
from archguard.validators.data_integrity_validator import DataIntegrityValidator


ALL_VALIDATORS = [
    TokenValidator,
    LayerValidator,
    ComponentValidator,
    SpecValidator,
    TopologyValidator,
    DataIntegrityValidator,
]


def run_all_checks(
    root_dir: Optional[Path] = None,
    config: Optional[ArchGuardConfig] = None,
    validators: Optional[List[type[BaseValidator]]] = None,
) -> SuiteResult:
    """Run specified or all validators and aggregate diagnostic metrics."""
    target_dir = (root_dir or Path.cwd()).resolve()
    target_config = config or ArchGuardConfig.load()
    target_validators = validators or ALL_VALIDATORS

    results: List[CheckResult] = []
    total_violations = 0
    total_errors = 0
    total_warnings = 0
    total_files = 0

    for val_cls in target_validators:
        validator = val_cls(root_dir=target_dir, config=target_config)
        res = validator.validate()
        results.append(res)
        total_files += res.checked_files_count
        total_violations += len(res.violations)
        total_errors += len([v for v in res.violations if v.severity == Severity.ERROR])
        total_warnings += len([v for v in res.violations if v.severity == Severity.WARNING])

    all_passed = all(r.passed for r in results)
    return SuiteResult(
        passed=all_passed,
        results=results,
        total_violations=total_violations,
        total_errors=total_errors,
        total_warnings=total_warnings,
        total_files_checked=total_files,
    )


__all__ = [
    "BaseValidator",
    "TokenValidator",
    "LayerValidator",
    "ComponentValidator",
    "SpecValidator",
    "TopologyValidator",
    "ALL_VALIDATORS",
    "run_all_checks",
]
