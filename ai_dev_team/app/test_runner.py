"""Pytest generation and execution utilities."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from ai_dev_team.app.agents import TestFile
from ai_dev_team.app.codebase import CodebaseManager


@dataclass
class PytestRunner:
    """Write test files and execute pytest against the workspace."""

    workspace_path: Path
    timeout_seconds: int = 20

    def write_tests(self, tests: list[TestFile]) -> list[str]:
        manager = CodebaseManager(self.workspace_path)
        manager.ensure_structure()
        return manager.write_tests(tests)

    def run(self) -> dict[str, Any]:
        start = perf_counter()
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "tests"],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            elapsed_ms = int((perf_counter() - start) * 1000)
            return {
                "success": completed.returncode == 0,
                "timed_out": False,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "elapsed_ms": elapsed_ms,
                "command": [sys.executable, "-m", "pytest", "-q", "tests"],
            }
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((perf_counter() - start) * 1000)
            return {
                "success": False,
                "timed_out": True,
                "exit_code": -1,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "elapsed_ms": elapsed_ms,
                "command": [sys.executable, "-m", "pytest", "-q", "tests"],
            }
