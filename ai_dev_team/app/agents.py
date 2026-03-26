"""OpenAI agent wrappers and strict schema validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Iterable, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ai_dev_team.app.config import Settings
from ai_dev_team.app.prompts import (
    ENGINEER_SYSTEM_PROMPT,
    PM_SYSTEM_PROMPT,
    QA_SYSTEM_PROMPT,
    TECH_LEAD_SYSTEM_PROMPT,
    TEST_ENGINEER_SYSTEM_PROMPT,
    build_role_input,
)


class AgentOutputError(RuntimeError):
    """Raised when an agent returns invalid output repeatedly."""


class TaskItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    acceptance_criteria: list[str]


class PMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prd: str
    tasks: list[TaskItem]


class FileChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    action: str = Field(pattern=r"^(create|update|delete)$")
    content: str = ""


class EngineerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: list[FileChange]
    rationale: str
    risks: list[str]


class TestFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    content: str


class TestEngineerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tests: list[TestFile]
    focus_areas: list[str]


class BugItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: str = Field(pattern=r"^(low|medium|high|critical)$")
    file: str
    description: str
    evidence: str


class QAOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bugs: list[BugItem]
    critical_blockers: list[str]
    verdict: str = Field(pattern=r"^(pass|fail)$")


class TechLeadOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    violations: list[str]
    refactor_instructions: list[str]


ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass
class AgentClient:
    """Role-specific OpenAI agent wrappers with strict JSON validation."""

    settings: Settings
    max_parse_retries: int = 2

    def __post_init__(self) -> None:
        self._client = OpenAI(api_key=self.settings.openai_api_key)

    def plan_with_pm(self, idea: str, codebase_snapshot: str = "") -> PMOutput:
        return self._run_role(
            system_prompt=PM_SYSTEM_PROMPT,
            payload={"idea": idea, "codebase_snapshot": codebase_snapshot},
            output_model=PMOutput,
        )

    def draft_engineering_changes(
        self,
        *,
        idea: str,
        prd: str,
        task: dict[str, Any],
        codebase_snapshot: str,
        iteration: int,
        previous_feedback: Iterable[str] | None = None,
    ) -> EngineerOutput:
        return self._run_role(
            system_prompt=ENGINEER_SYSTEM_PROMPT,
            payload={
                "idea": idea,
                "prd": prd,
                "task": task,
                "codebase_snapshot": codebase_snapshot,
                "iteration": iteration,
                "previous_feedback": list(previous_feedback or []),
            },
            output_model=EngineerOutput,
        )

    def draft_tests(
        self,
        *,
        task: dict[str, Any],
        codebase_snapshot: str,
        execution_output: dict[str, Any] | None = None,
    ) -> TestEngineerOutput:
        return self._run_role(
            system_prompt=TEST_ENGINEER_SYSTEM_PROMPT,
            payload={
                "task": task,
                "codebase_snapshot": codebase_snapshot,
                "execution_output": execution_output or {},
            },
            output_model=TestEngineerOutput,
        )

    def qa_review(
        self,
        *,
        task: dict[str, Any],
        execution_output: dict[str, Any],
        pytest_output: dict[str, Any],
    ) -> QAOutput:
        return self._run_role(
            system_prompt=QA_SYSTEM_PROMPT,
            payload={
                "task": task,
                "execution_output": execution_output,
                "pytest_output": pytest_output,
            },
            output_model=QAOutput,
        )

    def tech_lead_review(
        self,
        *,
        prd: str,
        task: dict[str, Any],
        qa_output: dict[str, Any],
        engineer_rationale: str,
    ) -> TechLeadOutput:
        return self._run_role(
            system_prompt=TECH_LEAD_SYSTEM_PROMPT,
            payload={
                "prd": prd,
                "task": task,
                "qa_output": qa_output,
                "engineer_rationale": engineer_rationale,
            },
            output_model=TechLeadOutput,
        )

    def _run_role(
        self,
        *,
        system_prompt: str,
        payload: dict[str, Any],
        output_model: type[ModelT],
    ) -> ModelT:
        last_error: Exception | None = None
        user_message = build_role_input(payload)
        for _ in range(self.max_parse_retries + 1):
            raw = self._complete(system_prompt=system_prompt, user_message=user_message)
            try:
                parsed = self._extract_json(raw)
                return output_model.model_validate(parsed)
            except (JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
        raise AgentOutputError(
            f"{output_model.__name__} validation failed after retries: {last_error}"
        )

    def _complete(self, *, system_prompt: str, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        if not content:
            raise AgentOutputError("Received empty response from model")
        return content.strip()

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = "".join(part for part in parts if "json" not in part.lower()).strip()

        try:
            decoded = json.loads(cleaned)
        except JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("No JSON object found in model output") from None
            decoded = json.loads(cleaned[start : end + 1])

        if not isinstance(decoded, dict):
            raise ValueError("Top-level model output must be a JSON object")
        return decoded


__all__ = [
    "AgentClient",
    "AgentOutputError",
    "PMOutput",
    "EngineerOutput",
    "TestEngineerOutput",
    "QAOutput",
    "TechLeadOutput",
]
