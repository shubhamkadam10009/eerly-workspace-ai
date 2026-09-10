from __future__ import annotations

from typing import Any
from uuid import uuid4

from langgraph.types import Command

from app.agent.graph import get_graph
from app.agent.models import ApprovalDecision


def _effective_thread_id(user_id: str, thread_id: str) -> str:
    return f"{user_id}:{thread_id}"


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
        "validation_result": state.get("validation_result"),
        "approval_required": bool(interrupt_payload),
        "approval_request": interrupt_payload,
        "approval_decision": state.get("approval_decision"),
        "approval_feedback": state.get("approval_feedback"),
    }


def run_agent(
    user_id: str,
    request: str,
    thread_id: str | None = None,
) -> dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required")

    if not request or not request.strip():
        raise ValueError("request must not be empty")

    raw_thread_id = thread_id or str(uuid4())
    effective_thread_id = _effective_thread_id(
        user_id,
        raw_thread_id,
    )

    graph = get_graph()

    result = graph.invoke(
        build_initial_state(
            user_id=user_id,
            thread_id=raw_thread_id,
            request=request,
        ),
        config={
            "configurable": {
                "thread_id": effective_thread_id,
            }
        },
    )

    return _state_response(
        graph=graph,
        effective_thread_id=effective_thread_id,
        raw_thread_id=raw_thread_id,
        result=result,
    )


def resume_agent(
    user_id: str,
    thread_id: str,
    decision: ApprovalDecision,
) -> dict[str, Any]:
    if not user_id:
        raise ValueError("user_id is required")

    if not thread_id or not thread_id.strip():
        raise ValueError("thread_id is required")

    effective_thread_id = _effective_thread_id(
        user_id,
        thread_id,
    )

    graph = get_graph()

    result = graph.invoke(
        Command(resume=decision.model_dump()),
        config={
            "configurable": {
                "thread_id": effective_thread_id,
            }
        },
    )

    return _state_response(
        graph=graph,
        effective_thread_id=effective_thread_id,
        raw_thread_id=thread_id,
        result=result,
    )