#!/usr/bin/env python3
"""
ArchGuard Automated Runner Script for Autonomous Multi-Agent Workflows.
Executes deterministic validation checks, produces RFC 7807 structured JSON diagnostics,
and returns clean exit codes.
"""

import json
import sys
from pathlib import Path
from archguard.core.config import ArchGuardConfig
from archguard.validators import run_all_checks


def main() -> int:
    root_dir = Path.cwd()
    config = ArchGuardConfig.load()
    suite_result = run_all_checks(root_dir=root_dir, config=config)

    # Output machine-readable JSON for agent consumption if flagged
    if "--json" in sys.argv:
        print(json.dumps(suite_result.model_dump(), indent=2))
    else:
        status_text = "PASSED" if suite_result.passed else "FAILED"
        print(f"[ArchGuard Runner] Status: {status_text}")
        print(f"Total Errors: {suite_result.total_errors}, Warnings: {suite_result.total_warnings}")
        print(f"Files Audited: {suite_result.total_files_checked}")

    return 0 if suite_result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
