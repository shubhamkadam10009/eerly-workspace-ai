from uuid import uuid4

from app.agent.graph import get_graph


def build_initial_state(
    user_id: str,
    thread_id: str,
    request: str,
) -> dict:
    """Create a clean initial state for one authenticated execution."""

    return {
        "user_id": user_id,
        "thread_id": thread_id,
        "request": request,
        "request_analysis": None,
        "discovered_skills": [],
        "selected_skills": [],
        "loaded_skills": {},
        "workspace_files": [],
        "source_contents": {},
        "findings": [],
        "generated_output": None,
        "generated_artifact": None,
        "validation_result": None,
        "status": "started",
        "error": None,
    }


def run_agent(
    user_id: str,
    request: str,
    thread_id: str | None = None,
) -> dict:
    """Execute one agent run using a user-scoped checkpoint thread."""

    requested_thread_id = thread_id or str(uuid4())

    # Namespace checkpoint threads by authenticated user.
    effective_thread_id = f"{user_id}:{requested_thread_id}"

    initial_state = build_initial_state(
        user_id=user_id,
        thread_id=effective_thread_id,
        request=request,
    )

    graph = get_graph()

    config = {
        "configurable": {
            "thread_id": effective_thread_id,
        }
    }

    return graph.invoke(
        initial_state,
        config=config,
    )