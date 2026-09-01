"""
Core models, result types, and diagnostic data structures for ArchGuard.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class StandardRef(str, Enum):
    ISO_42010 = "ISO/IEC/IEEE 42010:2022"
    ISO_29148 = "ISO/IEC/IEEE 29148:2018"
    ISO_25010 = "ISO/IEC 25010:2023"
    ISO_25010_DATA = "ISO/IEC 25010:2023 (Data Integrity)"
    ISO_29119 = "ISO/IEC/IEEE 29119:2022"
    ISO_12207 = "ISO/IEC/IEEE 12207:2017"
    IEEE_828 = "IEEE 828-2012"
    SEMVER_2 = "SemVer 2.0.0"
    CONVENTIONAL_COMMITS = "Conventional Commits 1.0.0"
    PEP_440 = "PEP 440"
    W3C_DTCG = "W3C DTCG 2025.10"
    RFC_7807 = "RFC 7807 / RFC 9457"
    ASD_STE100 = "ASD-STE100 Issue 8"


class Violation(BaseModel):
    rule_id: str
    standard: StandardRef
    severity: Severity = Severity.ERROR
    message: str
    file_path: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    context_snippet: Optional[str] = None
    remediation_hint: Optional[str] = None


class CheckResult(BaseModel):
    validator_name: str
    standard: StandardRef
    passed: bool
    violations: List[Violation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checked_files_count: int = 0


class SuiteResult(BaseModel):
    passed: bool
    results: List[CheckResult] = Field(default_factory=list)
    total_violations: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_files_checked: int = 0
