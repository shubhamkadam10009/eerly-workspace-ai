from typing import Any

from langgraph.types import interrupt

from app.agent.models import ApprovalDecision
from app.agent.state import AgentState


def prepare_approval(state: AgentState) -> dict[str, Any]:
    generated_output = state.get("generated_output")

    if not generated_output:
        return {
            "approval_request": None,
            "approval_status": "error",
            "status": "error",
            "error": "Cannot request approval for empty generated output.",
        }

    thread_id = state["thread_id"]

    approval_request = {
        "action": "approve_generated_output",
        "thread_id": thread_id,
        "request": state["request"],
        "generated_output": generated_output,
        "findings_count": state.get("findings_count", len(state.get("findings", []))),
        "message": "Review the generated output. Approve, edit, or reject it.",
    }

    return {
        "approval_request": approval_request,
        "approval_status": "pending",
        "approval_decision": None,
        "approval_feedback": None,
        "status": "awaiting_approval",
        "error": None,
    }


def request_human_approval(state: AgentState) -> dict[str, Any]:
    approval_request = state.get("approval_request")

    if not approval_request:
        raise ValueError("Approval request is missing.")

    # IMPORTANT:
    # Do not wrap interrupt() in try/except.
    #
    # LangGraph persists the checkpoint when this interrupt fires.
    # When resumed with Command(resume=...), this same node starts
    # again and interrupt() returns the supplied resume value.
    decision_payload = interrupt(approval_request)

    decision = ApprovalDecision.model_validate(decision_payload)

    if decision.decision == "approve":
        return {
            "approval_status": "approved",
            "approval_decision": "approve",
            "approval_feedback": None,
            "status": "approved",
            "error": None,
        }

    if decision.decision == "edit":
        if not decision.edited_output or not decision.edited_output.strip():
            raise ValueError(
                "edited_output is required when decision is 'edit'."
            )

        return {
            "generated_output": decision.edited_output,
            "approval_status": "edited",
            "approval_decision": "edit",
            "approval_feedback": decision.feedback,
            "status": "edited",
            "error": None,
        }

    return {
        "approval_status": "rejected",
        "approval_decision": "reject",
        "approval_feedback": decision.feedback,
        "status": "rejected",
        "error": None,
    }


def mark_approved(state: AgentState) -> dict[str, Any]:
    return {
        "status": "approved",
        "approval_status": "approved",
        "error": None,
    }


def mark_rejected(state: AgentState) -> dict[str, Any]:
    return {
        "status": "rejected",
        "approval_status": "rejected",
        "error": None,
    }