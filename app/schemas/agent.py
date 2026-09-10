from pydantic import BaseModel, Field

from app.agent.models import ApprovalDecision, Finding, ValidationResult


class AgentRunRequest(BaseModel):
    request: str = Field(min_length=1)
    thread_id: str | None = Field(default=None, min_length=1, max_length=200)


class AgentRunResponse(BaseModel):
    thread_id: str
    status: str
    selected_skills: list[str]
    findings: list[Finding]
    generated_output: str | None
    validation_result: ValidationResult | None

    approval_required: bool = False
    approval_request: dict | None = None
    approval_decision: str | None = None
    approval_feedback: str | None = None


class AgentResumeRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=200)
    decision: ApprovalDecision


class AgentResumeResponse(BaseModel):
    thread_id: str
    status: str
    approval_required: bool
    approval_request: dict | None = None
    approval_decision: str | None = None
    generated_output: str | None = None
    validation_result: ValidationResult | None = None