"""
W3C DTCG Token Validator.
Enforces closed-set token registry, eliminates arbitrary hardcoded styling,
hex codes, pixel dimensions, and undeclared CSS custom properties.
Standard: W3C DTCG 2025.10 / ISO/IEC 25010:2023.
"""

import re
from pathlib import Path
from typing import List, Set
from archguard.core.models import CheckResult, Severity, StandardRef, Violation
from archguard.validators.base import BaseValidator


HEX_COLOR_PATTERN = re.compile(r"(?<!&)#([0-9a-fA-F]{3,8})\b")
RGB_COLOR_PATTERN = re.compile(r"\brgba?\s*\([^)]+\)")
CSS_VAR_USAGE_PATTERN = re.compile(r"var\(\s*(--[a-zA-Z0-9\-_]+)")
CSS_VAR_DECLARATION_PATTERN = re.compile(r"(--[a-zA-Z0-9\-_]+)\s*:")
HARDCODED_PIXEL_PATTERN = re.compile(r"\b(height|width|padding|margin|gap|top|bottom|left|right)\s*:\s*([0-9]+px)\b")


class TokenValidator(BaseValidator):
    name = "token_validator"
    standard = StandardRef.W3C_DTCG

    def _extract_declared_tokens(self) -> Set[str]:
        declared: Set[str] = set()
        for token_file_rel in self.config.tokens.token_files:
            token_path = self.root_dir / token_file_rel
            if token_path.exists() and token_path.is_file():
                try:
                    content = token_path.read_text(encoding="utf-8")
                    for match in CSS_VAR_DECLARATION_PATTERN.finditer(content):
                        declared.add(match.group(1))
                except Exception:
                    pass
        return declared

    def validate(self) -> CheckResult:
        if not self.config.tokens.enabled:
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": "disabled"},
            )

        declared_tokens = self._extract_declared_tokens()
        violations: List[Violation] = []
        checked_count = 0

        scan_extensions = {".css", ".scss", ".tsx", ".jsx", ".vue", ".html"}
        allowed_hex = {h.lower() for h in self.config.tokens.allowed_hex_colors}

        token_file_abs = {
            (self.root_dir / f).resolve()
            for f in self.config.tokens.token_files
            if (self.root_dir / f).exists()
        }

        for scan_rel in self.config.tokens.scan_paths:
            scan_dir = self.root_dir / scan_rel
            if not scan_dir.exists():
                continue

            for file_path in scan_dir.rglob("*"):
                if not file_path.is_file() or file_path.suffix not in scan_extensions:
                    continue
                if file_path.resolve() in token_file_abs:
                    continue
                if "node_modules" in file_path.parts or ".next" in file_path.parts or "dist" in file_path.parts:
                    continue

                checked_count += 1
                rel_path_str = str(file_path.relative_to(self.root_dir))

                try:
                    lines = file_path.read_text(encoding="utf-8").splitlines()
                except Exception:
                    continue

                for line_idx, line in enumerate(lines, start=1):
                    # Check for undeclared CSS variable usage if tokens are declared
                    if declared_tokens:
                        for var_match in CSS_VAR_USAGE_PATTERN.finditer(line):
                            var_name = var_match.group(1)
                            if var_name not in declared_tokens:
                                violations.append(
                                    Violation(
                                        rule_id="W3C-DTCG-001",
                                        standard=self.standard,
                                        severity=Severity.ERROR,
                                        message=f"Undeclared design token variable '{var_name}' used outside closed token registry.",
                                        file_path=rel_path_str,
                                        line_number=line_idx,
                                        context_snippet=line.strip(),
                                        remediation_hint=f"Declare '{var_name}' in your token manifest or use an approved token.",
                                    )
                                )

                    # Check for raw hex colors in styling/components
                    for hex_match in HEX_COLOR_PATTERN.finditer(line):
                        hex_val = f"#{hex_match.group(1)}".lower()
                        if hex_val not in allowed_hex:
                            violations.append(
                                Violation(
                                    rule_id="W3C-DTCG-002",
                                    standard=self.standard,
                                    severity=Severity.ERROR,
                                    message=f"Hardcoded raw hex color '{hex_val}' detected.",
                                    file_path=rel_path_str,
                                    line_number=line_idx,
                                    context_snippet=line.strip(),
                                    remediation_hint="Use semantic design token variable var(--color-*) instead of raw hex.",
                                )
                            )

                    # Check for raw RGB/RGBA colors
                    for rgb_match in RGB_COLOR_PATTERN.finditer(line):
                        violations.append(
                            Violation(
                                rule_id="W3C-DTCG-003",
                                standard=self.standard,
                                severity=Severity.ERROR,
                                message=f"Hardcoded rgb/rgba color '{rgb_match.group(0)}' detected.",
                                file_path=rel_path_str,
                                line_number=line_idx,
                                context_snippet=line.strip(),
                                remediation_hint="Use semantic design token variable instead of inline rgb/rgba.",
                            )
                        )

                    # Check for hardcoded pixel dimensions on layout properties in CSS
                    if file_path.suffix in {".css", ".scss"} and not self.config.tokens.allow_layout_pixel_literals:
                        for px_match in HARDCODED_PIXEL_PATTERN.finditer(line):
                            prop, val = px_match.group(1), px_match.group(2)
                            if self.config.tokens.ignore_micro_spacing and val in {"0px", "1px", "2px"}:
                                continue
                            violations.append(
                                Violation(
                                    rule_id="W3C-DTCG-004",
                                    standard=self.standard,
                                    severity=Severity.WARNING,
                                    message=f"Hardcoded pixel dimension '{prop}: {val}' detected.",
                                    file_path=rel_path_str,
                                    line_number=line_idx,
                                    context_snippet=line.strip(),
                                    remediation_hint=f"Use tokenized spacing variable var(--space-*) or sizing token for '{prop}'.",
                                )
                            )

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0
        return CheckResult(
            validator_name=self.name,
            standard=self.standard,
            passed=passed,
            violations=violations,
            checked_files_count=checked_count,
            metadata={"declared_tokens_count": len(declared_tokens)},
        )
