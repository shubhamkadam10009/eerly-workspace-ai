from app.agent.models import WorkspaceFile
from app.agent.state import AgentState
from app.tools.filesystem import list_workspace_files


def inspect_workspace(state: AgentState) -> dict:
    """Inspect the authenticated user's workspace input directory."""

    user_id = state["user_id"]

    if not user_id.strip():
        raise ValueError("user_id cannot be empty")

    entries = list_workspace_files(
        user_id=user_id,
        relative_directory="input",
    )

    workspace_files = [
        WorkspaceFile.model_validate(entry).model_dump()
        for entry in entries
    ]

    return {
        "workspace_files": workspace_files,
        "status": "workspace_inspected",
        "error": None,
    }
