from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from langgraph.types import Command

from app.agent.event_bus import event_bus
from app.agent.events import AgentEvent
from app.agent.graph import get_graph
from app.agent.models import ApprovalDecision
from app.artifacts.service import persist_artifact
from app.db.repository.workspace import ensure_user_workspace


def _effective_thread_id(user_id: str, thread_id: str) -> str:
    return f"{user_id}:{thread_id}"


def _stream_key(user_id: str, thread_id: str) -> str:
    return _effective_thread_id(user_id, thread_id)


def build_initial_state(
    user_id: str,
    thread_id: str,
    request: str,
) -> dict[str, Any]:
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
        "approval_request": None,
        "approval_status": None,
        "approval_decision": None,
        "approval_feedback": None,
        "status": "started",
        "error": None,
    }


def _extract_interrupt(result: Any) -> dict | None:
    interrupts = result.get("__interrupt__", [])

    if not interrupts:
        return None

    interrupt_value = interrupts[0].value

    if isinstance(interrupt_value, dict):
        return interrupt_value

    return {"message": str(interrupt_value)}


def _state_response(
    graph,
    effective_thread_id: str,
    raw_thread_id: str,
    result: Any,
) -> dict[str, Any]:
    snapshot = graph.get_state(
        {
            "configurable": {
                "thread_id": effective_thread_id,
            }
        }
    )

    state = dict(snapshot.values)

    interrupt_payload = _extract_interrupt(result)

    return {
        "thread_id": raw_thread_id,
        "status": state.get("status", "unknown"),
        "selected_skills": state.get("selected_skills", []),
        "findings": state.get("findings", []),
        "generated_output": state.get("generated_output"),
        "generated_artifact": state.get("generated_artifact"),
        "validation_result": state.get("validation_result"),
        "approval_required": bool(interrupt_payload),
        "approval_request": interrupt_payload,
        "approval_decision": state.get("approval_decision"),
        "approval_feedback": state.get("approval_feedback"),
    }


def _make_event(
    *,
    event: str,
    thread_id: str,
    status: str,
    message: str,
    data: dict | None = None,
) -> AgentEvent:
    return AgentEvent(
        event=event,
        thread_id=thread_id,
        status=status,
        message=message,
        timestamp=datetime.now(timezone.utc),
        data=data or {},
    )


def _publish_event(
    *,
    user_id: str,
    thread_id: str,
    event: str,
    status: str,
    message: str,
    data: dict | None = None,
) -> None:
    event_bus.publish(
        _stream_key(user_id, thread_id),
        _make_event(
            event=event,
            thread_id=thread_id,
            status=status,
            message=message,
            data=data,
        ),
    )


def _node_event(node_name: str) -> tuple[str, str]:
    mapping = {
        "discover_skills": (
            "skills_discovered",
            "Skill discovery completed",
        ),
        "analyze_request": (
            "request_analyzed",
            "Request analysis completed",
        ),
        "load_skills": (
            "skills_loaded",
            "Required skills loaded",
        ),
        "inspect_workspace": (
            "workspace_inspected",
            "Workspace inspection completed",
        ),
        "read_sources": (
            "sources_read",
            "Source files read",
        ),
        "analyze_content": (
            "analysis_completed",
            "Content analysis completed",
        ),
        "generate_output": (
            "output_generated",
            "Output generation completed",
        ),
        "validate_output": (
            "validation_completed",
            "Output validation completed",
        ),
        "prepare_approval": (
            "approval_required",
            "Human approval is required",
        ),
        "mark_approved": (
            "approval_received",
            "Agent execution approved",
        ),
        "deliver_artifact": (
            "artifact_delivered",
            "Artifact delivered to workspace",
        ),
        "mark_rejected": (
            "rejected",
            "Agent execution was rejected",
        ),
    }

    return mapping.get(
        node_name,
        (
            "request_analyzed",
            f"Agent node '{node_name}' completed",
        ),
    )


def _run_stream(
    graph,
    input_data: Any,
    config: dict[str, Any],
    user_id: str,
    raw_thread_id: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for chunk in graph.stream(
        input_data,
        config=config,
        stream_mode="updates",
    ):
        result.update(chunk)

        for node_name in chunk:
            event_name, message = _node_event(node_name)

            status = (
                "waiting_for_approval"
                if event_name == "approval_required"
                else "running"
            )

            _publish_event(
                user_id=user_id,
                thread_id=raw_thread_id,
                event=event_name,
                status=status,
                message=message,
                data={"node": node_name},
            )

    return result


def _ensure_user_workspace(user_id: str) -> None:
    """Ensure the authenticated user has a database and filesystem workspace."""

    async def provision() -> None:
        await ensure_user_workspace(user_id)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(provision())
        return

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(asyncio.run, provision()).result()

def _persist_generated_artifact(
    *,
    user_id: str,
    response: dict[str, Any],
) -> None:
    """Persist delivered artifact metadata in PostgreSQL."""

    artifact = response.get("generated_artifact")

    if not artifact:
        return

    async def persist() -> None:
        await persist_artifact(
            user_id=user_id,
            filename=artifact["filename"],
            relative_path=artifact["relative_path"],
            artifact_type=artifact["artifact_type"],
            status=artifact["status"],
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(persist())
        return

    # The current agent service is synchronous. If this helper is ever
    # called from an already-running event loop, execute the async
    # persistence operation in a separate worker thread.
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(asyncio.run, persist()).result()


def _publish_terminal_event(
    *,
    user_id: str,
    thread_id: str,
    response: dict[str, Any],
) -> None:
    if response["approval_required"]:
        _publish_event(
            user_id=user_id,
            thread_id=thread_id,
            event="approval_required",
            status="waiting_for_approval",
            message="Waiting for human approval",
            data={
                "approval_request": response["approval_request"],
            },
        )
    elif response["status"] == "rejected":
        _publish_event(
            user_id=user_id,
            thread_id=thread_id,
            event="rejected",
            status="rejected",
            message="Agent execution was rejected",
        )
    elif response["status"] == "completed":
        _publish_event(
            user_id=user_id,
            thread_id=thread_id,
            event="completed",
            status="completed",
            message="Agent execution completed",
        )


def run_agent(
    user_id: str,
    request: str,
    thread_id: str | None = None,
) -> dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required")

    _ensure_user_workspace(user_id)

    if not request or not request.strip():
        raise ValueError("request must not be empty")

    raw_thread_id = thread_id or str(uuid4())

    effective_thread_id = _effective_thread_id(
        user_id,
        raw_thread_id,
    )

    graph = get_graph()

    _publish_event(
        user_id=user_id,
        thread_id=raw_thread_id,
        event="request_received",
        status="running",
        message="Agent request received",
    )

    config = {
        "configurable": {
            "thread_id": effective_thread_id,
        }
    }

    try:
        result = _run_stream(
            graph=graph,
            input_data=build_initial_state(
                user_id=user_id,
                thread_id=raw_thread_id,
                request=request,
            ),
            config=config,
            user_id=user_id,
            raw_thread_id=raw_thread_id,
        )

        response = _state_response(
            graph=graph,
            effective_thread_id=effective_thread_id,
            raw_thread_id=raw_thread_id,
            result=result,
        )

        if not response["approval_required"]:
            _persist_generated_artifact(
                user_id=user_id,
                response=response,
            )

        _publish_terminal_event(
            user_id=user_id,
            thread_id=raw_thread_id,
            response=response,
        )

        return response

    except Exception as exc:
        _publish_event(
            user_id=user_id,
            thread_id=raw_thread_id,
            event="failed",
            status="failed",
            message="Agent execution failed",
            data={"error": str(exc)},
        )
        raise


def resume_agent(
    user_id: str,
    thread_id: str,
    decision: ApprovalDecision,
) -> dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required")

    _ensure_user_workspace(user_id)

    if not thread_id or not thread_id.strip():
        raise ValueError("thread_id is required")

    effective_thread_id = _effective_thread_id(
        user_id,
        thread_id,
    )

    graph = get_graph()

    _publish_event(
        user_id=user_id,
        thread_id=thread_id,
        event="approval_received",
        status="resuming",
        message="Human approval decision received",
        data={
            "decision": decision.decision,
        },
    )

    config = {
        "configurable": {
            "thread_id": effective_thread_id,
        }
    }

    try:
        result = _run_stream(
            graph=graph,
            input_data=Command(
                resume=decision.model_dump()
            ),
            config=config,
            user_id=user_id,
            raw_thread_id=thread_id,
        )

        response = _state_response(
            graph=graph,
            effective_thread_id=effective_thread_id,
            raw_thread_id=thread_id,
            result=result,
        )

        if not response["approval_required"]:
            _persist_generated_artifact(
                user_id=user_id,
                response=response,
            )

        _publish_terminal_event(
            user_id=user_id,
            thread_id=thread_id,
            response=response,
        )

        return response

    except Exception as exc:
        _publish_event(
            user_id=user_id,
            thread_id=thread_id,
            event="failed",
            status="failed",
            message="Agent resume failed",
            data={"error": str(exc)},
        )
        raise










