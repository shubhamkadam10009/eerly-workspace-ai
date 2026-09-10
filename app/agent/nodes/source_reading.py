from app.agent.state import AgentState
from app.tools.filesystem import read_workspace_file


def read_sources(state: AgentState) -> dict:
    """Read all file entries discovered in the user's workspace."""

    user_id = state["user_id"]
    workspace_files = state["workspace_files"]

    if not user_id.strip():
        raise ValueError("user_id cannot be empty")

    source_contents: dict[str, str] = {}

    for workspace_file in workspace_files:
        if workspace_file["type"] != "file":
            continue

        source_contents[workspace_file["path"]] = read_workspace_file(
            user_id=user_id,
            relative_path=workspace_file["path"],
        )

    return {
        "source_contents": source_contents,
        "status": "sources_read",
        "error": None,
    }
