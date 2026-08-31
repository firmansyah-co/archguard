"""
ISO/IEC/IEEE 29148 Living Specification & Machine-Readable Contract Validator.
Validates spec frontmatter, traceability matrices, structured contracts, and tasks synchronization.
Standard: ISO/IEC/IEEE 29148:2018 / ISO/IEC/IEEE 42010:2022.
"""

from pathlib import Path
from typing import List
import yaml
from archguard.core.models import CheckResult, Severity, StandardRef, Violation
from archguard.validators.base import BaseValidator


class SpecValidator(BaseValidator):
    name = "spec_validator"
    standard = StandardRef.ISO_29148

    def validate(self) -> CheckResult:
        if not self.config.specs.enabled:
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": "disabled"},
            )

        violations: List[Violation] = []
        checked_count = 0
        specs_dir = self.root_dir / self.config.specs.specs_dir

        if not specs_dir.exists():
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": f"specs dir '{self.config.specs.specs_dir}' not present"},
            )

        for feature_dir in specs_dir.iterdir():
            if not feature_dir.is_dir() or feature_dir.name.startswith("."):
                continue

            spec_file = feature_dir / "spec.md"
            checked_count += 1

            if not spec_file.exists():
                violations.append(
                    Violation(
                        rule_id="ISO-29148-001",
                        standard=self.standard,
                        severity=Severity.ERROR,
                        message=f"Missing 'spec.md' in feature specification directory '{feature_dir.name}'.",
                        file_path=str(feature_dir.relative_to(self.root_dir)),
                        remediation_hint="Create an ISO 29148 compliant 'spec.md' file with requirements and contracts.",
                    )
                )
                continue

            rel_spec_str = str(spec_file.relative_to(self.root_dir))
            try:
                content = spec_file.read_text(encoding="utf-8")
            except Exception as e:
                violations.append(
                    Violation(
                        rule_id="ISO-29148-002",
                        standard=self.standard,
                        severity=Severity.ERROR,
                        message=f"Failed to read 'spec.md': {str(e)}",
                        file_path=rel_spec_str,
                    )
                )
                continue

            # Check for Frontmatter metadata
            if not content.startswith("---"):
                violations.append(
                    Violation(
                        rule_id="ISO-29148-003",
                        standard=self.standard,
                        severity=Severity.ERROR,
                        message="Missing YAML frontmatter in 'spec.md'.",
                        file_path=rel_spec_str,
                        line_number=1,
                        remediation_hint="Add YAML frontmatter with id, title, version, status, and standard fields.",
                    )
                )
            else:
                try:
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        required_fields = ["id", "title", "version", "status"]
                        for rf in required_fields:
                            if rf not in frontmatter:
                                violations.append(
                                    Violation(
                                        rule_id="ISO-29148-004",
                                        standard=self.standard,
                                        severity=Severity.ERROR,
                                        message=f"Missing required frontmatter field '{rf}' in 'spec.md'.",
                                        file_path=rel_spec_str,
                                        remediation_hint=f"Define '{rf}: ...' in YAML frontmatter.",
                                    )
                                )
                except Exception as e:
                    violations.append(
                        Violation(
                            rule_id="ISO-29148-005",
                            standard=self.standard,
                            severity=Severity.ERROR,
                            message=f"Invalid YAML frontmatter syntax: {str(e)}",
                            file_path=rel_spec_str,
                            line_number=1,
                        )
                    )

            # Check for Structured Contracts (Machine-Readable YAML/JSON/TypeScript blocks)
            if self.config.specs.require_contracts:
                has_contract = "```yaml" in content or "```json" in content or "```typescript" in content or "```ts" in content
                if not has_contract:
                    violations.append(
                        Violation(
                            rule_id="ISO-29148-006",
                            standard=self.standard,
                            severity=Severity.ERROR,
                            message="No machine-readable contract block (YAML/JSON/TypeScript) declared in 'spec.md'.",
                            file_path=rel_spec_str,
                            remediation_hint="Provide a structured contract block (e.g. YAML register map or TypeScript interface).",
                        )
                    )

            # Check for Tasks sync file
            if self.config.specs.require_tasks_sync:
                tasks_file = feature_dir / "tasks.md"
                if not tasks_file.exists():
                    violations.append(
                        Violation(
                            rule_id="ISO-29148-007",
                            standard=self.standard,
                            severity=Severity.WARNING,
                            message=f"Missing companion 'tasks.md' Work Breakdown Structure in '{feature_dir.name}'.",
                            file_path=str(feature_dir.relative_to(self.root_dir)),
                            remediation_hint="Create 'tasks.md' containing task checklist synced with requirements.",
                        )
                    )

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0
        return CheckResult(
            validator_name=self.name,
            standard=self.standard,
            passed=passed,
            violations=violations,
            checked_files_count=checked_count,
            metadata={"specs_dir": self.config.specs.specs_dir},
        )
