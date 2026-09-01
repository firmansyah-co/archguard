"""
Data Integrity & Zero-Mock AST Invariants Validator.
Enforces deterministic data flow, bans synthetic/mock domain literals, heuristic state inference,
and synthetic magic number fallbacks in production boundaries.
Standard: ISO/IEC 25010:2023 (Data Integrity & Fault Tolerance).
"""

import ast
import re
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple
from archguard.core.models import CheckResult, Severity, StandardRef, Violation
from archguard.validators.base import BaseValidator


# Pattern for JS/TS nullish coalescing or logical OR with numeric literals:
# e.g. latency ?? 4.2, packets || 28450, data.speed ?? 120
NULLISH_OR_MAGIC_NUMBER_PATTERN = re.compile(
    r"""(?:\b([a-zA-Z0-9_$.?]+)\s*(?:\?\?|\|\|)\s*([0-9]+(?:\.[0-9]+)?)\b)"""
)

# Pattern for JS/TS object / array property declarations
JS_PROPERTY_PATTERN = re.compile(r"""(?:(['"]?)([a-zA-Z0-9_]+)\1\s*:\s*)""")

# Pattern for JS/TS variable, function, class, or type declarations
JS_DECLARATION_IDENTIFIERS_PATTERN = re.compile(
    r"""(?:(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=|function\s+([a-zA-Z0-9_$]+)|class\s+([a-zA-Z0-9_$]+)|type\s+([a-zA-Z0-9_$]+)|interface\s+([a-zA-Z0-9_$]+)|import\s+\{\s*([^}]+)\s*\}|import\s+([a-zA-Z0-9_$]+))"""
)


class DataIntegrityValidator(BaseValidator):
    name = "data_integrity_validator"
    standard = StandardRef.ISO_25010_DATA

    def _is_test_or_mock_path(self, path: Path) -> bool:
        """Determine if a file is located in a test, mock, or fixture path."""
        rel_parts = [p.lower() for p in path.relative_to(self.root_dir).parts]
        test_path_patterns = [p.lower().strip("/\\") for p in self.config.integrity.test_paths]

        for pattern in test_path_patterns:
            pat_parts = pattern.split("/")
            for i in range(len(rel_parts) - len(pat_parts) + 1):
                if rel_parts[i : i + len(pat_parts)] == pat_parts:
                    return True

        filename = path.name.lower()
        if (
            filename.startswith("test_")
            or filename.endswith("_test.py")
            or filename.endswith(".test.ts")
            or filename.endswith(".test.tsx")
            or filename.endswith(".test.js")
            or filename.endswith(".test.jsx")
            or filename.endswith(".spec.ts")
            or filename.endswith(".spec.tsx")
            or filename.endswith(".spec.js")
            or filename.endswith(".spec.jsx")
        ):
            return True

        return False

    def _get_python_literal_depth_and_domain_keys(
        self, node: ast.AST, domain_keys: Set[str], current_depth: int = 1
    ) -> Tuple[int, Set[str]]:
        max_depth = current_depth
        found_keys: Set[str] = set()

        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    if k.value.lower() in domain_keys:
                        found_keys.add(k.value)
                if isinstance(v, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
                    d, sub_keys = self._get_python_literal_depth_and_domain_keys(
                        v, domain_keys, current_depth + 1
                    )
                    max_depth = max(max_depth, d)
                    found_keys.update(sub_keys)
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for elt in node.elts:
                if isinstance(elt, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
                    d, sub_keys = self._get_python_literal_depth_and_domain_keys(
                        elt, domain_keys, current_depth + 1
                    )
                    max_depth = max(max_depth, d)
                    found_keys.update(sub_keys)

        return max_depth, found_keys

    def _check_python_ast(self, file_path: Path, rel_path_str: str) -> List[Violation]:
        """Perform Python AST checks for data integrity invariants."""
        violations: List[Violation] = []
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except Exception:
            return violations

        domain_keys = set(self.config.integrity.domain_keys)
        operational_states = set(self.config.integrity.operational_states)
        mock_keywords = [k.lower() for k in self.config.integrity.mock_keywords]

        # 1. Check for mock/synthetic identifiers (Rule ISO-25010-INT-004) via AST
        if self.config.integrity.ban_mock_artifacts_in_production:
            for node in ast.walk(tree):
                ident_candidates: List[Tuple[str, int]] = []
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    ident_candidates.append((node.id, node.lineno))
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    ident_candidates.append((node.name, node.lineno))
                elif isinstance(node, ast.arg):
                    ident_candidates.append((node.arg, node.lineno))
                elif isinstance(node, ast.alias):
                    ident_candidates.append((node.asname or node.name, getattr(node, "lineno", 1)))

                for ident, lineno in ident_candidates:
                    ident_lower = ident.lower()
                    # Skip meta/config rule identifiers
                    if (
                        ident_lower.endswith(("_keywords", "_keyword", "_patterns", "_pattern", "_rule", "_rules", "_config", "_option", "_options", "_flag", "_flags", "_validator"))
                        or ident_lower.startswith(("ban_", "allow_", "ignore_", "check_", "has_", "is_"))
                    ):
                        continue

                    if any(
                        ident_lower == kw
                        or ident_lower.startswith(f"{kw}_")
                        or ident_lower.startswith(kw)
                        or ident_lower.endswith(f"_{kw}")
                        for kw in mock_keywords
                    ):
                        violations.append(
                            Violation(
                                rule_id="ISO-25010-INT-004",
                                standard=self.standard,
                                severity=Severity.ERROR,
                                message=(
                                    f"Mock/Synthetic identifier '{ident}' declared in production boundary. "
                                    f"Mock artifacts, sample fixtures, and fake datasets are strictly confined to test suites."
                                ),
                                file_path=rel_path_str,
                                line_number=lineno,
                                context_snippet=ident,
                                remediation_hint=f"Remove '{ident}' from production code or relocate fixture to tests/ or mocks/ directory.",
                            )
                        )

        # 2. Check for deep nested dictionary/list literals defining domain keys (Rule ISO-25010-INT-001)
        if self.config.integrity.ban_unanchored_synthetic_literals:
            reported_lines = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        val = node.value
                        if isinstance(val, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
                            depth, found_keys = self._get_python_literal_depth_and_domain_keys(
                                val, domain_keys
                            )
                            if depth >= 2 and found_keys and node.lineno not in reported_lines:
                                reported_lines.add(node.lineno)
                                violations.append(
                                    Violation(
                                        rule_id="ISO-25010-INT-001",
                                        standard=self.standard,
                                        severity=Severity.ERROR,
                                        message=(
                                            f"Unanchored deep synthetic domain literal (depth={depth}, keys={sorted(list(found_keys))}) "
                                            f"detected in production code. Static mock/synthetic data is prohibited."
                                        ),
                                        file_path=rel_path_str,
                                        line_number=node.lineno,
                                        context_snippet=ast.unparse(target)
                                        if hasattr(ast, "unparse")
                                        else None,
                                        remediation_hint="Source domain models and telemetry directly from network I/O, API responses, or typed parameters.",
                                    )
                                )

        # 3. Check for heuristic state inference (Rule ISO-25010-INT-002)
        if self.config.integrity.ban_heuristic_state_inference:
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    for op, comparator in zip(node.ops, node.comparators):
                        if isinstance(op, (ast.In, ast.NotIn)):
                            state_val = None
                            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                                state_val = node.left.value
                            elif isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                                state_val = comparator.value

                            if state_val and state_val.upper() in operational_states:
                                violations.append(
                                    Violation(
                                        rule_id="ISO-25010-INT-002",
                                        standard=self.standard,
                                        severity=Severity.ERROR,
                                        message=(
                                            f"Heuristic state inference detected: string membership check on operational state '{state_val}'. "
                                            f"Operational state must be resolved via deterministic enum/schema parsing."
                                        ),
                                        file_path=rel_path_str,
                                        line_number=node.lineno,
                                        remediation_hint="Use explicit enum comparisons or typed schema models (e.g. StateEnum(value)) instead of string heuristics.",
                                    )
                                )

        # 4. Check for synthetic magic number fallbacks (Rule ISO-25010-INT-003)
        if self.config.integrity.ban_synthetic_fallbacks:
            for node in ast.walk(tree):
                if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                    for val in node.values[1:]:
                        if isinstance(val, ast.Constant) and isinstance(val.value, (int, float)) and val.value != 0:
                            left_repr = (
                                ast.unparse(node.values[0]).lower()
                                if hasattr(ast, "unparse")
                                else ""
                            )
                            if any(k.lower() in left_repr for k in domain_keys):
                                violations.append(
                                    Violation(
                                        rule_id="ISO-25010-INT-003",
                                        standard=self.standard,
                                        severity=Severity.ERROR,
                                        message=(
                                            f"Synthetic magic number fallback '{val.value}' assigned to domain expression '{left_repr}'. "
                                            f"Bypassing missing telemetry with fake non-zero constants violates data integrity."
                                        ),
                                        file_path=rel_path_str,
                                        line_number=node.lineno,
                                        remediation_hint="Preserve null/None state or handle missing values explicitly with standard None/Option types.",
                                    )
                                )
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                    if len(node.args) >= 2:
                        key_arg = node.args[0]
                        default_arg = node.args[1]
                        if isinstance(key_arg, ast.Constant) and str(key_arg.value).lower() in domain_keys:
                            if isinstance(default_arg, ast.Constant) and isinstance(default_arg.value, (int, float)) and default_arg.value != 0:
                                violations.append(
                                    Violation(
                                        rule_id="ISO-25010-INT-003",
                                        standard=self.standard,
                                        severity=Severity.ERROR,
                                        message=(
                                            f"Synthetic magic number fallback '{default_arg.value}' used as default for domain key '{key_arg.value}'. "
                                            f"Hardcoded fake metrics violate ISO 25010 data integrity."
                                        ),
                                        file_path=rel_path_str,
                                        line_number=node.lineno,
                                        remediation_hint="Default to None or raise explicit telemetry missing exception.",
                                    )
                                )

        return violations

    def _strip_comments_and_strings(self, line: str) -> str:
        """Strip inline comments and string contents from a JS/TS line for syntax inspection."""
        clean = line.split("//")[0]
        # Replace string literal contents with empty quotes
        clean = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', clean)
        clean = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", "''", clean)
        clean = re.sub(r"`[^`\\]*(?:\\.[^`\\]*)*`", "``", clean)
        return clean

    def _check_js_ts_file(self, file_path: Path, rel_path_str: str) -> List[Violation]:
        """Perform static analysis on JS/TS/TSX/JSX files for data integrity invariants."""
        violations: List[Violation] = []
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return violations

        lines = content.splitlines()
        domain_keys = set(self.config.integrity.domain_keys)
        operational_states = set(self.config.integrity.operational_states)
        mock_keywords = [k.lower() for k in self.config.integrity.mock_keywords]

        # 1. Rule ISO-25010-INT-004: Mock Artifacts in Production Boundaries
        if self.config.integrity.ban_mock_artifacts_in_production:
            for line_idx, line in enumerate(lines, start=1):
                clean_no_comment = line.split("//")[0].strip()
                if not clean_no_comment or clean_no_comment.startswith("*"):
                    continue

                for match in JS_DECLARATION_IDENTIFIERS_PATTERN.finditer(clean_no_comment):
                    # Group captures
                    for group_idx in range(1, 8):
                        captured = match.group(group_idx)
                        if not captured:
                            continue
                        # If captured is a list of imports inside { a, b, c }
                        idents = [i.strip().split(" as ")[-1].strip() for i in captured.split(",")]
                        for ident in idents:
                            if not ident:
                                continue
                            ident_lower = ident.lower()
                            if any(
                                ident_lower == kw
                                or ident_lower.startswith(f"{kw}_")
                                or ident_lower.startswith(kw)
                                or ident_lower.endswith(f"_{kw}")
                                for kw in mock_keywords
                            ):
                                violations.append(
                                    Violation(
                                        rule_id="ISO-25010-INT-004",
                                        standard=self.standard,
                                        severity=Severity.ERROR,
                                        message=(
                                            f"Mock/Synthetic identifier '{ident}' detected in production boundary. "
                                            f"Mock artifacts, sample fixtures, and fake datasets are strictly confined to test suites."
                                        ),
                                        file_path=rel_path_str,
                                        line_number=line_idx,
                                        context_snippet=clean_no_comment,
                                        remediation_hint=f"Remove '{ident}' from production code or relocate fixture to tests/ or mocks/ directory.",
                                    )
                                )

        # 2. Rule ISO-25010-INT-001: Unanchored Deep Synthetic Domain Literals
        if self.config.integrity.ban_unanchored_synthetic_literals:
            violations.extend(self._scan_js_deep_literals(content, lines, rel_path_str, domain_keys))

        # 3. Rule ISO-25010-INT-002: Heuristic State Inference from Strings
        if self.config.integrity.ban_heuristic_state_inference:
            for line_idx, line in enumerate(lines, start=1):
                clean_no_comment = line.split("//")[0].strip()
                if not clean_no_comment or clean_no_comment.startswith("*"):
                    continue

                for state in operational_states:
                    if (
                        f'.includes("{state}")' in line
                        or f".includes('{state}')" in line
                        or f'.includes(`{state}`)' in line
                    ):
                        violations.append(
                            Violation(
                                rule_id="ISO-25010-INT-002",
                                standard=self.standard,
                                severity=Severity.ERROR,
                                message=(
                                    f"Heuristic state inference detected: string substring matching '.includes(\"{state}\")' "
                                    f"used to determine operational state. States must be typed enums."
                                ),
                                file_path=rel_path_str,
                                line_number=line_idx,
                                context_snippet=clean_no_comment,
                                remediation_hint=f"Parse state into strongly-typed enum/union values instead of substring matching.",
                            )
                        )
                    elif (
                        f"/{state}/i.test(" in line
                        or f"/{state}/.test(" in line
                        or f'new RegExp("{state}")' in line
                    ):
                        violations.append(
                            Violation(
                                rule_id="ISO-25010-INT-002",
                                standard=self.standard,
                                severity=Severity.ERROR,
                                message=(
                                    f"Heuristic state inference detected: regex pattern matching on operational state '{state}'. "
                                    f"States must be validated against a deterministic finite state machine (PackML / ISO 13849)."
                                ),
                                file_path=rel_path_str,
                                line_number=line_idx,
                                context_snippet=clean_no_comment,
                                remediation_hint="Use deterministic state machine models (ISA-TR88 PackML / ISO 13849).",
                            )
                        )

        # 4. Rule ISO-25010-INT-003: Synthetic Magic Number Fallbacks
        if self.config.integrity.ban_synthetic_fallbacks:
            for line_idx, line in enumerate(lines, start=1):
                clean_no_comment = line.split("//")[0].strip()
                if not clean_no_comment or clean_no_comment.startswith("*"):
                    continue

                for match in NULLISH_OR_MAGIC_NUMBER_PATTERN.finditer(line):
                    var_expr = match.group(1)
                    num_val = match.group(2)
                    try:
                        f_val = float(num_val)
                        if f_val != 0:
                            var_lower = var_expr.lower()
                            if any(dk.lower() in var_lower for dk in domain_keys):
                                violations.append(
                                    Violation(
                                        rule_id="ISO-25010-INT-003",
                                        standard=self.standard,
                                        severity=Severity.ERROR,
                                        message=(
                                            f"Synthetic magic number fallback '{num_val}' assigned via '??' or '||' to domain expression '{var_expr}'. "
                                            f"Bypassing missing telemetry with fake non-zero constants violates data integrity."
                                        ),
                                        file_path=rel_path_str,
                                        line_number=line_idx,
                                        context_snippet=clean_no_comment,
                                        remediation_hint="Preserve null/undefined state or display an explicit 'N/A' indicator in the UI.",
                                    )
                                )
                    except ValueError:
                        pass

        return violations

    def _scan_js_deep_literals(
        self, content: str, lines: List[str], rel_path_str: str, domain_keys: Set[str]
    ) -> List[Violation]:
        """Detect multi-level deep JS/TS object/array literals with domain keys in production code."""
        violations: List[Violation] = []
        brace_stack = []
        object_depth = 0
        current_obj_keys: List[Tuple[str, int]] = []

        for line_idx, line in enumerate(lines, start=1):
            clean = line.split("//")[0].strip()
            if not clean or clean.startswith("*"):
                continue

            for m in JS_PROPERTY_PATTERN.finditer(clean):
                key = m.group(2)
                if key.lower() in domain_keys:
                    current_obj_keys.append((key, line_idx))

            for char in clean:
                if char in "{[":
                    brace_stack.append((char, line_idx))
                    object_depth = len(brace_stack)
                elif char in "}]":
                    if brace_stack:
                        open_char, open_line = brace_stack.pop()
                        if object_depth >= 2 and current_obj_keys:
                            keys_found = [k for k, l in current_obj_keys if l >= open_line]
                            if len(keys_found) >= 2 or (len(keys_found) >= 1 and object_depth >= 3):
                                if not any(v.line_number == open_line for v in violations):
                                    violations.append(
                                        Violation(
                                            rule_id="ISO-25010-INT-001",
                                            standard=self.standard,
                                            severity=Severity.ERROR,
                                            message=(
                                                f"Unanchored deep synthetic domain literal (depth={object_depth}, keys={sorted(list(set(keys_found)))}) "
                                                f"detected in production file. Hardcoded mock fixtures in production boundaries are prohibited."
                                            ),
                                            file_path=rel_path_str,
                                            line_number=open_line,
                                            context_snippet=lines[open_line - 1].strip(),
                                            remediation_hint="Bind component data to live props, React Query hooks, or API client streams.",
                                        )
                                    )
                        object_depth = len(brace_stack)
                        if object_depth == 0:
                            current_obj_keys.clear()

        return violations

    def validate(self) -> CheckResult:
        if not self.config.integrity.enabled:
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": "disabled"},
            )

        violations: List[Violation] = []
        checked_count = 0
        supported_extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}

        for prod_rel in self.config.integrity.production_paths:
            prod_dir = self.root_dir / prod_rel
            if not prod_dir.exists():
                continue

            for file_path in prod_dir.rglob("*"):
                if not file_path.is_file() or file_path.suffix not in supported_extensions:
                    continue
                if any(
                    part in file_path.parts
                    for part in [
                        "node_modules",
                        ".venv",
                        "venv",
                        "dist",
                        ".next",
                        "__pycache__",
                        ".git",
                    ]
                ):
                    continue
                if self._is_test_or_mock_path(file_path):
                    continue

                checked_count += 1
                rel_path_str = str(file_path.relative_to(self.root_dir))

                # Python specific checks
                if file_path.suffix == ".py":
                    violations.extend(self._check_python_ast(file_path, rel_path_str))
                # TypeScript / JavaScript specific checks
                elif file_path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
                    violations.extend(self._check_js_ts_file(file_path, rel_path_str))

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0
        return CheckResult(
            validator_name=self.name,
            standard=self.standard,
            passed=passed,
            violations=violations,
            checked_files_count=checked_count,
            metadata={"production_paths": self.config.integrity.production_paths},
        )
