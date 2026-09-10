from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


AgentEventType = Literal[
    "request_received",
    "request_analyzed",
    "skills_discovered",
    "skills_loaded",
    "workspace_inspected",
    "sources_read",
    "analysis_completed",
    "output_generated",
    "validation_completed",
    "approval_required",
    "approval_received",
    "artifact_delivered",
    "completed",
    "rejected",
    "failed",
]


class AgentEvent(BaseModel):
    event: AgentEventType
    thread_id: str
    status: str
    message: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    data: dict = Field(default_factory=dict)
