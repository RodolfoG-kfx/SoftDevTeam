"""Workspace git initialization and commit helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitManager:
    """Wrap minimal git operations for the generated workspace."""

    workspace_path: Path

    def ensure_repo(self) -> None:
        if not (self.workspace_path / ".git").exists():
            self._run_git(["init"])

    def commit_all(self, message: str) -> bool:
        self.ensure_repo()
        self._run_git(["add", "."])
        status = self._run_git(["status", "--porcelain"], check=False)
        if not status.stdout.strip():
            return False
        self._run_git(["commit", "-m", message])
        return True

    def _run_git(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            check=check,
        )
