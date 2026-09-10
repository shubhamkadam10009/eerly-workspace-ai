from pydantic import BaseModel, Field

from app.agent.models import Finding, ValidationResult


class AgentRunRequest(BaseModel):
    """HTTP request to start an agent execution."""

    request: str = Field(min_length=1)
    thread_id: str | None = None


class AgentRunResponse(BaseModel):
    """HTTP response containing the agent execution result."""

    thread_id: str
    status: str
    selected_skills: list[str]
    findings: list[Finding]
    generated_output: str | None
    validation_result: ValidationResult | None