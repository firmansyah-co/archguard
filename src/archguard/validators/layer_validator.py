"""
Hexagonal & Clean Architecture Layer Boundary Validator.
Enforces strict unidirectional dependency flow across API, Service, Repository, and Model layers.
Standard: ISO/IEC/IEEE 42010:2022 / ISO/IEC 25010:2023.
"""

import ast
from pathlib import Path
from typing import List, Tuple
from archguard.core.models import CheckResult, Severity, StandardRef, Violation
from archguard.validators.base import BaseValidator


class LayerValidator(BaseValidator):
    name = "layer_validator"
    standard = StandardRef.ISO_42010

    def _extract_imports(self, file_path: Path) -> List[Tuple[str, int]]:
        imports: List[Tuple[str, int]] = []
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except Exception:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append((node.module, node.lineno))
                    for alias in node.names:
                        imports.append((f"{node.module}.{alias.name}", node.lineno))
        return imports

    def validate(self) -> CheckResult:
        if not self.config.layers.enabled:
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": "disabled"},
            )

        violations: List[Violation] = []
        checked_count = 0
        backend_root = self.root_dir / self.config.layers.backend_root

        if not backend_root.exists():
            return CheckResult(
                validator_name=self.name,
                standard=self.standard,
                passed=True,
                checked_files_count=0,
                metadata={"status": f"path {self.config.layers.backend_root} not found"},
            )

        forbidden_rules = self.config.layers.forbidden_dependencies

        for py_file in backend_root.rglob("*.py"):
            if py_file.name.startswith("__") and py_file.name != "__init__.py":
                continue
            if "venv" in py_file.parts or ".venv" in py_file.parts or "tests" in py_file.parts:
                continue

            checked_count += 1
            rel_path = py_file.relative_to(self.root_dir)
            rel_path_str = str(rel_path)

            # Determine layer of current file
            current_layer = None
            for part in rel_path.parts:
                if part in self.config.layers.layers:
                    current_layer = part
                    break

            if not current_layer:
                continue

            forbidden_targets = forbidden_rules.get(current_layer, [])
            if not forbidden_targets:
                continue

            imports = self._extract_imports(py_file)
            for imp_module, lineno in imports:
                for forbidden in forbidden_targets:
                    # Check for direct or submodule forbidden import
                    parts = imp_module.split(".")
                    if forbidden in parts or imp_module == forbidden or imp_module.startswith(f"{forbidden}."):
                        violations.append(
                            Violation(
                                rule_id="ISO-42010-001",
                                standard=self.standard,
                                severity=Severity.ERROR,
                                message=f"Layer '{current_layer}' imports forbidden module/layer '{forbidden}' (found: '{imp_module}').",
                                file_path=rel_path_str,
                                line_number=lineno,
                                context_snippet=f"import / from ... {imp_module}",
                                remediation_hint=f"Decouple '{current_layer}' from '{forbidden}'. Route data access through the Service layer.",
                            )
                        )

        passed = len([v for v in violations if v.severity == Severity.ERROR]) == 0
        return CheckResult(
            validator_name=self.name,
            standard=self.standard,
            passed=passed,
            violations=violations,
            checked_files_count=checked_count,
            metadata={"backend_root": self.config.layers.backend_root},
        )
