"""In-memory state for project runs and iteration history."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskRunState:
    """Tracks per-task progress and evidence across iterations."""

    task: dict[str, Any]
    iterations: list[dict[str, Any]] = field(default_factory=list)
    status: str = "pending"

    def add_iteration(self, payload: dict[str, Any]) -> None:
        self.iterations.append(payload)

    @property
    def attempt_count(self) -> int:
        return len(self.iterations)


@dataclass
class RunMemoryStore:
    """In-memory run state for a single project execution."""

    idea: str
    prd: str = ""
    tasks: list[TaskRunState] = field(default_factory=list)
    evidence_logs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_prd(self, prd: str) -> None:
        self.prd = prd

    def set_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self.tasks = [TaskRunState(task=task) for task in tasks]

    def get_task(self, task_id: str) -> TaskRunState:
        for task_state in self.tasks:
            if task_state.task.get("id") == task_id:
                return task_state
        raise KeyError(f"Unknown task_id: {task_id}")

    def add_evidence(self, evidence: dict[str, Any]) -> None:
        self.evidence_logs.append(evidence)

    def as_dict(self) -> dict[str, Any]:
        return {
            "idea": self.idea,
            "prd": self.prd,
            "tasks": [
                {
                    "task": task_state.task,
                    "status": task_state.status,
                    "attempt_count": task_state.attempt_count,
                    "iterations": task_state.iterations,
                }
                for task_state in self.tasks
            ],
            "evidence_logs": self.evidence_logs,
            "metadata": self.metadata,
        }
