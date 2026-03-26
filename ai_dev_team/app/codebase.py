"""Workspace file IO helpers and snapshot utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_dev_team.app.agents import FileChange, TestFile


DEFAULT_DIRECTORIES = ("services", "models", "utils", "tests")
SNAPSHOT_FILE_LIMIT = 50
SNAPSHOT_CHARS_PER_FILE = 3000


@dataclass
class CodebaseManager:
    """Manage generated code inside the workspace directory."""

    workspace_path: Path

    def ensure_structure(self) -> None:
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        for directory in DEFAULT_DIRECTORIES:
            (self.workspace_path / directory).mkdir(parents=True, exist_ok=True)
        main_file = self.workspace_path / "main.py"
        if not main_file.exists():
            main_file.write_text(
                'def main() -> None:\n    print("hello from workspace")\n\n\nif __name__ == "__main__":\n    main()\n',
                encoding="utf-8",
            )

    def apply_changes(self, changes: list[FileChange]) -> list[str]:
        applied: list[str] = []
        for change in changes:
            target = self._resolve_workspace_path(change.path)
            if change.action == "delete":
                if target.exists():
                    target.unlink()
                    applied.append(f"deleted:{change.path}")
                else:
                    applied.append(f"missing-delete:{change.path}")
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change.content, encoding="utf-8")
            applied.append(f"{change.action}:{change.path}")
        return applied

    def write_tests(self, tests: list[TestFile]) -> list[str]:
        written: list[str] = []
        for test_file in tests:
            relative = test_file.path.lstrip("/\\")
            if not relative.startswith("tests/") and not relative.startswith("tests\\"):
                relative = f"tests/{relative}"
            target = self._resolve_workspace_path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(test_file.content, encoding="utf-8")
            written.append(str(target.relative_to(self.workspace_path)).replace("\\", "/"))
        return written

    def read_file(self, relative_path: str) -> str:
        target = self._resolve_workspace_path(relative_path)
        return target.read_text(encoding="utf-8")

    def snapshot(self, file_limit: int = SNAPSHOT_FILE_LIMIT) -> str:
        lines = ["# Workspace Snapshot"]
        files = sorted(
            path
            for path in self.workspace_path.rglob("*")
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
        )
        for path in files[:file_limit]:
            rel = path.relative_to(self.workspace_path).as_posix()
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if len(content) > SNAPSHOT_CHARS_PER_FILE:
                content = f"{content[:SNAPSHOT_CHARS_PER_FILE]}\n# ...truncated..."
            lines.append(f"\n## {rel}\n```python\n{content}\n```")
        if len(files) > file_limit:
            lines.append(f"\n# ... {len(files) - file_limit} additional files omitted ...")
        return "\n".join(lines)

    def _resolve_workspace_path(self, relative_path: str) -> Path:
        candidate = (self.workspace_path / relative_path.lstrip("/\\")).resolve()
        workspace_root = self.workspace_path.resolve()
        try:
            candidate.relative_to(workspace_root)
        except ValueError as exc:
            raise ValueError(f"Path escapes workspace: {relative_path}") from exc
        return candidate
