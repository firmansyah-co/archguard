"""
ArchGuard Templates module exports.
"""

from archguard.templates.scaffold import (
    DEFAULT_ARCHGUARD_CONFIG_YAML,
    PRE_PUSH_HOOK_SCRIPT,
    WORKFLOW_TEMPLATE,
    scaffold_project,
)

__all__ = [
    "scaffold_project",
    "DEFAULT_ARCHGUARD_CONFIG_YAML",
    "PRE_PUSH_HOOK_SCRIPT",
    "WORKFLOW_TEMPLATE",
]

