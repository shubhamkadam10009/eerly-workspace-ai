from typing import Literal

from pydantic import BaseModel, Field


class RequestAnalysis(BaseModel):
    """Structured interpretation of the user's request."""

    intent: str = Field(min_length=1)
    selected_skills: list[str] = Field(default_factory=list)
    requested_output_type: str | None = None


class WorkspaceFile(BaseModel):
    """Metadata describing a file or directory in the workspace."""

    name: str
    path: str
    type: Literal["file", "directory"]


class Finding(BaseModel):
    """A source-grounded finding extracted during analysis."""

    statement: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    confidence: Literal["high", "medium", "low"]


class FindingCollection(BaseModel):
    """Collection of source-grounded findings."""

    findings: list[Finding] = Field(default_factory=list)


class ArtifactReference(BaseModel):
    """Reference to an artifact stored in the user's workspace."""

    filename: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    status: str = Field(min_length=1)


class ValidationResult(BaseModel):
    """Validation result for generated output."""

    valid: bool
    issues: list[str] = Field(default_factory=list)