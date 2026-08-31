"""
Component Proliferation & Raw Primitive Usage Validator.
Enforces shared design system component reuse in domain pages and flags raw primitives.
Standard: ISO/IEC 25010:2023 (Reusability & Modularity) / W3C DTCG 2025.10.
"""

import re
from pathlib import Path
from typing import List
from archguard.core.models import CheckResult, Severity, StandardRef, Violation
from archguard.validators.base import BaseValidator


RAW_JSX_ELEMENT_PATTERN = re.compile(r"<([a-z0-9]+)(\s|>|/)")


class ComponentValidator(BaseValidator):
    name = "component_validator"
    standard = StandardRef.ISO_25010

    def validate(self) -> CheckResult:
        if not self.config.components.enabled:
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": "disabled"},
            )

        violations: List[Violation] = []
        checked_count = 0
        forbidden_primitives = set(self.config.components.forbidden_raw_primitives)

        for pages_rel in self.config.components.pages_dirs:
            pages_dir = self.root_dir / pages_rel
            if not pages_dir.exists():
                continue

            for file_path in pages_dir.rglob("*"):
                if not file_path.is_file() or file_path.suffix not in {".tsx", ".jsx", ".vue"}:
                    continue
                if "node_modules" in file_path.parts or "dist" in file_path.parts:
                    continue

                checked_count += 1
                rel_path_str = str(file_path.relative_to(self.root_dir))

                try:
                    lines = file_path.read_text(encoding="utf-8").splitlines()
                except Exception:
                    continue

                for line_idx, line in enumerate(lines, start=1):
                    # Check for raw primitives in page files
                    for match in RAW_JSX_ELEMENT_PATTERN.finditer(line):
                        tag_name = match.group(1).lower()
                        if tag_name in forbidden_primitives:
                            violations.append(
                                Violation(
                                    rule_id="ISO-25010-001",
                                    standard=self.standard,
                                    severity=Severity.ERROR,
                                    message=f"Raw HTML primitive '<{tag_name}>' used in domain page. Design system violation.",
                                    file_path=rel_path_str,
                                    line_number=line_idx,
                                    context_snippet=line.strip(),
                                    remediation_hint=f"Replace raw '<{tag_name}>' with standardized design system component from components/common/.",
                                )
                            )

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0
        return CheckResult(
            validator_name=self.name,
            standard=self.standard,
            passed=passed,
            violations=violations,
            checked_files_count=checked_count,
            metadata={"pages_dirs": self.config.components.pages_dirs},
        )
