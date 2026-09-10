from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RequestAnalysis(BaseModel):
    intent: str = Field(min_length=1)
    selected_skills: list[str] = Field(default_factory=list)
    requested_output_type: str | None = None


class WorkspaceFile(BaseModel):
    name: str
    path: str
    type: Literal["file", "directory"]


class Finding(BaseModel):
    statement: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    confidence: Literal["high", "medium", "low"]


class FindingCollection(BaseModel):
    findings: list[Finding] = Field(default_factory=list)


class ArtifactReference(BaseModel):
    filename: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    status: str = Field(min_length=1)


class ValidationResult(BaseModel):
    valid: bool
    issues: list[str] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    edited_output: str | None = None
    feedback: str | None = None

    @model_validator(mode="after")
    def validate_edit_payload(self):
        if self.decision == "edit":
            if not self.edited_output or not self.edited_output.strip():
                raise ValueError(
                    "edited_output is required when decision is 'edit'."
                )

        return self


class ApprovalRequest(BaseModel):
    action: Literal["approve_generated_output"] = "approve_generated_output"
    thread_id: str
    request: str
    generated_output: str
    findings_count: int
    message: str


class ApprovalResponse(BaseModel):
    thread_id: str
    status: str
    approval_required: bool
    approval_request: dict | None = None
    approval_decision: str | None = None
    generated_output: str | None = None
    validation_result: ValidationResult | None = None