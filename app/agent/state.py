from typing import TypedDict

from app.agent.models import (
    ArtifactReference,
    Finding,
    RequestAnalysis,
    ValidationResult,
    WorkspaceFile,
)
from app.skills.models import SkillMetadata


class AgentState(TypedDict):
    user_id: str
    thread_id: str
    request: str

    request_analysis: RequestAnalysis | None

    discovered_skills: list[SkillMetadata]
    selected_skills: list[str]
    loaded_skills: dict[str, str]

    workspace_files: list[WorkspaceFile]
    source_contents: dict[str, str]

    findings: list[Finding]

    generated_output: str | None
    generated_artifact: ArtifactReference | None

    validation_result: ValidationResult | None

    approval_request: dict | None
    approval_status: str | None
    approval_decision: str | None
    approval_feedback: str | None

    status: str
    error: str | None