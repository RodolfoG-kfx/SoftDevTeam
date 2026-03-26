"""Orchestration pipeline for iterative multi-agent delivery."""

from __future__ import annotations

from ai_dev_team.app.agents import AgentClient, AgentOutputError
from ai_dev_team.app.codebase import CodebaseManager
from ai_dev_team.app.config import get_settings
from ai_dev_team.app.executor import Executor
from ai_dev_team.app.git_manager import GitManager
from ai_dev_team.app.memory import RunMemoryStore
from ai_dev_team.app.scorer import DeliveryScorer
from ai_dev_team.app.test_runner import PytestRunner


def run_project(idea: str) -> dict:
    settings = get_settings()
    codebase = CodebaseManager(settings.workspace_path)
    codebase.ensure_structure()

    memory = RunMemoryStore(idea=idea)
    agents = AgentClient(settings=settings)
    executor = Executor(
        workspace_path=settings.workspace_path,
        timeout_seconds=settings.exec_timeout_seconds,
    )
    pytest_runner = PytestRunner(
        workspace_path=settings.workspace_path,
        timeout_seconds=settings.pytest_timeout_seconds,
    )
    git = GitManager(workspace_path=settings.workspace_path)
    scorer = DeliveryScorer(max_iterations=settings.max_iterations)

    try:
        pm_output = agents.plan_with_pm(idea=idea, codebase_snapshot=codebase.snapshot())
    except AgentOutputError as exc:
        return {
            "status": "failed",
            "iterations": 0,
            "score": 0,
            "summary": f"PM planning failed: {exc}",
        }

    tasks = [task.model_dump() for task in pm_output.tasks]
    memory.set_prd(pm_output.prd)
    memory.set_tasks(tasks)
    memory.metadata["task_count"] = len(tasks)

    total_iterations = 0
    task_scores: list[int] = []
    passed_tasks = 0
    failed_tasks = 0

    for task in tasks:
        task_state = memory.get_task(task["id"])
        previous_feedback: list[str] = []
        task_passed = False
        last_iteration_payload: dict = {}

        for iteration in range(1, settings.max_iterations + 1):
            total_iterations += 1
            try:
                engineer_output = agents.draft_engineering_changes(
                    idea=idea,
                    prd=memory.prd,
                    task=task,
                    codebase_snapshot=codebase.snapshot(),
                    iteration=iteration,
                    previous_feedback=previous_feedback,
                )
            except AgentOutputError as exc:
                task_state.status = "failed"
                task_state.add_iteration(
                    {
                        "iteration": iteration,
                        "error": f"Engineer output invalid: {exc}",
                    }
                )
                break

            applied_changes = codebase.apply_changes(engineer_output.changes)
            git.commit_all(
                f"task:{task['id']} iteration:{iteration} engineer changes"
            )

            execution_output = executor.run_main()

            try:
                test_output = agents.draft_tests(
                    task=task,
                    codebase_snapshot=codebase.snapshot(),
                    execution_output=execution_output,
                )
            except AgentOutputError as exc:
                task_state.status = "failed"
                task_state.add_iteration(
                    {
                        "iteration": iteration,
                        "engineer_changes": applied_changes,
                        "execution_output": execution_output,
                        "error": f"Test engineer output invalid: {exc}",
                    }
                )
                break

            written_tests = pytest_runner.write_tests(test_output.tests)
            git.commit_all(f"task:{task['id']} iteration:{iteration} generated tests")
            pytest_output = pytest_runner.run()

            try:
                qa_output = agents.qa_review(
                    task=task,
                    execution_output=execution_output,
                    pytest_output=pytest_output,
                )
                tech_lead_output = agents.tech_lead_review(
                    prd=memory.prd,
                    task=task,
                    qa_output=qa_output.model_dump(),
                    engineer_rationale=engineer_output.rationale,
                )
            except AgentOutputError as exc:
                task_state.status = "failed"
                task_state.add_iteration(
                    {
                        "iteration": iteration,
                        "engineer_changes": applied_changes,
                        "written_tests": written_tests,
                        "execution_output": execution_output,
                        "pytest_output": pytest_output,
                        "error": f"Review output invalid: {exc}",
                    }
                )
                break

            completion_met = (
                execution_output["success"]
                and pytest_output["success"]
                and not qa_output.critical_blockers
                and tech_lead_output.approved
            )

            iteration_payload = {
                "iteration": iteration,
                "engineer_changes": applied_changes,
                "engineer_rationale": engineer_output.rationale,
                "engineer_risks": engineer_output.risks,
                "written_tests": written_tests,
                "test_focus_areas": test_output.focus_areas,
                "execution_output": execution_output,
                "pytest_output": pytest_output,
                "qa_output": qa_output.model_dump(),
                "tech_lead_output": tech_lead_output.model_dump(),
                "completion_met": completion_met,
            }
            task_state.add_iteration(iteration_payload)
            memory.add_evidence(
                {
                    "task_id": task["id"],
                    "iteration": iteration,
                    "execution_success": execution_output["success"],
                    "pytest_success": pytest_output["success"],
                    "qa_verdict": qa_output.verdict,
                    "critical_blockers": qa_output.critical_blockers,
                    "tech_lead_approved": tech_lead_output.approved,
                }
            )

            last_iteration_payload = iteration_payload
            if completion_met:
                task_state.status = "completed"
                task_passed = True
                break

            previous_feedback = [
                *(f"QA blocker: {blocker}" for blocker in qa_output.critical_blockers),
                *(f"QA bug: {bug.description}" for bug in qa_output.bugs),
                *(f"Tech lead violation: {v}" for v in tech_lead_output.violations),
                *(
                    f"Tech lead refactor: {instruction}"
                    for instruction in tech_lead_output.refactor_instructions
                ),
            ]

        if not task_passed and task_state.status != "failed":
            task_state.status = "failed"

        bug_count = len(last_iteration_payload.get("qa_output", {}).get("bugs", []))
        qa_blockers = len(
            last_iteration_payload.get("qa_output", {}).get("critical_blockers", [])
        )
        task_score = scorer.score_task(
            iterations_used=task_state.attempt_count,
            bug_count=bug_count,
            execution_success=bool(
                last_iteration_payload.get("execution_output", {}).get("success", False)
            ),
            pytest_success=bool(
                last_iteration_payload.get("pytest_output", {}).get("success", False)
            ),
            qa_blockers=qa_blockers,
            tech_lead_approved=bool(
                last_iteration_payload.get("tech_lead_output", {}).get("approved", False)
            ),
        )
        task_scores.append(task_score)
        if task_state.status == "completed":
            passed_tasks += 1
        else:
            failed_tasks += 1

    score = scorer.score_project(task_scores=task_scores, total_iterations=total_iterations)
    status = "success" if failed_tasks == 0 and passed_tasks > 0 else "partial_success"
    if passed_tasks == 0:
        status = "failed"

    memory.metadata.update(
        {
            "total_iterations": total_iterations,
            "passed_tasks": passed_tasks,
            "failed_tasks": failed_tasks,
            "task_scores": task_scores,
            "project_score": score,
            "status": status,
        }
    )

    return {
        "status": status,
        "iterations": total_iterations,
        "score": score,
        "summary": (
            f"Completed {passed_tasks}/{len(tasks)} tasks across "
            f"{total_iterations} iterations."
        ),
        "artifacts": {
            "workspace_path": str(settings.workspace_path),
            "memory": memory.as_dict(),
        },
    }
