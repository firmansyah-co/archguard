"""
Abstract base class for all ArchGuard deterministic validators.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from archguard.core.config import ArchGuardConfig
from archguard.core.models import CheckResult, StandardRef


class BaseValidator(ABC):
    """Base validator enforcing ISO/IEC/IEEE and RFC standards."""

    name: str = "base_validator"
    standard: StandardRef = StandardRef.ISO_42010

    def __init__(self, root_dir: Path, config: Optional[ArchGuardConfig] = None) -> None:
        self.root_dir = root_dir.resolve()
        self.config = config or ArchGuardConfig.load()

    @abstractmethod
    def validate(self) -> CheckResult:
        """Run deterministic static validation and return CheckResult."""
        pass
