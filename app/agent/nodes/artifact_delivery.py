from typing import Any

from app.agent.models import ArtifactReference
from app.agent.state import AgentState
from app.artifacts.service import ArtifactService


artifact_service = ArtifactService()


def deliver_artifact(state: AgentState) -> dict[str, Any]:
    """Deliver the approved generated report to the user's workspace."""

    user_id = state["user_id"]
    generated_output = state.get("generated_output")

    if not generated_output or not generated_output.strip():
        raise ValueError(
            "Cannot deliver an empty generated output."
        )

    result = artifact_service.deliver(
        user_id=user_id,
        filename="report.md",
        content=generated_output,
    )

    artifact = ArtifactReference(
        filename=result["filename"],
        relative_path=result["path"],
        artifact_type="markdown_report",
        status=result["status"],
    )

    return {
        "generated_artifact": artifact,
        "status": "delivered",
        "error": None,
    }
