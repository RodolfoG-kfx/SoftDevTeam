"""Scoring utilities for delivery outcomes."""

from __future__ import annotations

from dataclasses import dataclass


def _clamp(value: int, lower: int = 0, upper: int = 100) -> int:
    return max(lower, min(upper, value))


@dataclass
class DeliveryScorer:
    """Compute a delivery score from runtime outcomes."""

    max_iterations: int

    def score_task(
        self,
        *,
        iterations_used: int,
        bug_count: int,
        execution_success: bool,
        pytest_success: bool,
        qa_blockers: int,
        tech_lead_approved: bool,
    ) -> int:
        score = 100
        score -= max(0, iterations_used - 1) * 7
        score -= max(0, bug_count) * 5
        score -= max(0, qa_blockers) * 15
        if not execution_success:
            score -= 25
        if not pytest_success:
            score -= 25
        if not tech_lead_approved:
            score -= 20
        return _clamp(score)

    def score_project(self, task_scores: list[int], total_iterations: int) -> int:
        if not task_scores:
            return 0
        average = sum(task_scores) / len(task_scores)
        iteration_penalty = max(0, total_iterations - self.max_iterations) * 3
        return _clamp(int(round(average - iteration_penalty)))
