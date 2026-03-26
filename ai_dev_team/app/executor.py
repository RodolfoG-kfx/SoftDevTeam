"""Application execution runtime utilities."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any


@dataclass
class Executor:
    """Run workspace entrypoints with timeout controls."""

    workspace_path: Path
    timeout_seconds: int = 15

    def run_main(self) -> dict[str, Any]:
        return self.run_file("main.py")

    def run_file(self, relative_path: str) -> dict[str, Any]:
        target = self.workspace_path / relative_path
        start = perf_counter()
        try:
            completed = subprocess.run(
                [sys.executable, str(target)],
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
                "command": [sys.executable, relative_path],
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
                "command": [sys.executable, relative_path],
            }
