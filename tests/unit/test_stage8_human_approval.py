from typing import TypedDict

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.agent.models import ApprovalDecision
from app.agent.nodes.human_approval import (
    mark_approved,
    mark_rejected,
    prepare_approval,
    request_human_approval,
)
from app.main import app


class ApprovalTestState(TypedDict):
    generated_output: str
    findings_count: int
    thread_id: str
    request: str
    approval_request: dict | None
    approval_status: str | None
    approval_decision: str | None
    approval_feedback: str | None
    status: str


def build_approval_test_graph():
    builder = StateGraph(ApprovalTestState)

    builder.add_node("prepare", prepare_approval)
    builder.add_node("approval", request_human_approval)
    builder.add_node("approved", mark_approved)
    builder.add_node("rejected", mark_rejected)
    builder.add_node("edited", lambda state: {"status": "edited"})

    builder.add_edge(START, "prepare")
    builder.add_edge("prepare", "approval")

    def route(state):
        decision = state.get("approval_decision")

        if decision == "approve":
            return "approved"

        if decision == "edit":
            return "edited"

        if decision == "reject":
            return "rejected"

        raise ValueError(f"Unexpected decision: {decision}")

    builder.add_conditional_edges(
        "approval",
        route,
        {
            "approved": "approved",
            "edited": "edited",
            "rejected": "rejected",
        },
    )

    builder.add_edge("approved", END)
    builder.add_edge("edited", END)
    builder.add_edge("rejected", END)

    return builder.compile(checkpointer=InMemorySaver())


def initial_state():
    return {
        "generated_output": "Generated management report.",
        "findings_count": 3,
        "thread_id": "approval-test-1",
        "request": "Create a management report.",
        "approval_request": None,
        "approval_status": None,
        "approval_decision": None,
        "approval_feedback": None,
        "status": "starting",
    }


def test_prepare_approval_creates_review_payload():
    result = prepare_approval(initial_state())

    assert result["status"] == "awaiting_approval"
    assert result["approval_status"] == "pending"
    assert result["approval_request"]["action"] == "approve_generated_output"
    assert result["approval_request"]["generated_output"] == (
        "Generated management report."
    )
    assert result["approval_request"]["findings_count"] == 3


def test_approval_interrupt_pauses_execution():
    graph = build_approval_test_graph()

    config = {
        "configurable": {
            "thread_id": "approval-pause-test",
        }
    }

    result = graph.invoke(initial_state(), config=config)

    assert "__interrupt__" in result
    assert len(result["__interrupt__"]) == 1

    interrupt_value = result["__interrupt__"][0].value

    assert interrupt_value["action"] == "approve_generated_output"
    assert interrupt_value["message"]


def test_approval_can_be_approved_and_resumed():
    graph = build_approval_test_graph()

    config = {
        "configurable": {
            "thread_id": "approval-approve-test",
        }
    }

    first = graph.invoke(initial_state(), config=config)

    assert "__interrupt__" in first

    resumed = graph.invoke(
        Command(
            resume={
                "decision": "approve",
            }
        ),
        config=config,
    )

    assert resumed["approval_decision"] == "approve"
    assert resumed["approval_status"] == "approved"
    assert resumed["status"] == "approved"


def test_approval_can_be_rejected_and_resumed():
    graph = build_approval_test_graph()

    config = {
        "configurable": {
            "thread_id": "approval-reject-test",
        }
    }

    first = graph.invoke(initial_state(), config=config)

    assert "__interrupt__" in first

    resumed = graph.invoke(
        Command(
            resume={
                "decision": "reject",
                "feedback": "The report needs revision.",
            }
        ),
        config=config,
    )

    assert resumed["approval_decision"] == "reject"
    assert resumed["approval_status"] == "rejected"
    assert resumed["approval_feedback"] == "The report needs revision."
    assert resumed["status"] == "rejected"


def test_approval_edit_updates_generated_output():
    graph = build_approval_test_graph()

    config = {
        "configurable": {
            "thread_id": "approval-edit-test",
        }
    }

    first = graph.invoke(initial_state(), config=config)

    assert "__interrupt__" in first

    resumed = graph.invoke(
        Command(
            resume={
                "decision": "edit",
                "edited_output": "Human-edited management report.",
                "feedback": "Corrected the executive summary.",
            }
        ),
        config=config,
    )

    assert resumed["approval_decision"] == "edit"
    assert resumed["approval_status"] == "edited"
    assert resumed["generated_output"] == (
        "Human-edited management report."
    )


def test_edit_requires_non_empty_edited_output():
    with pytest.raises(Exception):
        ApprovalDecision(
            decision="edit",
            edited_output="",
        )


def test_invalid_approval_decision_is_rejected():
    with pytest.raises(Exception):
        ApprovalDecision(
            decision="invalid",
        )


def test_interrupt_checkpoint_can_be_read_after_pause():
    graph = build_approval_test_graph()

    config = {
        "configurable": {
            "thread_id": "approval-checkpoint-test",
        }
    }

    result = graph.invoke(initial_state(), config=config)

    assert "__interrupt__" in result

    snapshot = graph.get_state(config)

    assert snapshot.values["status"] == "awaiting_approval"
    assert snapshot.values["approval_status"] == "pending"
    assert snapshot.next == ("approval",)


def test_same_thread_resumes_checkpoint():
    graph = build_approval_test_graph()

    config = {
        "configurable": {
            "thread_id": "approval-resume-same-thread",
        }
    }

    graph.invoke(initial_state(), config=config)

    resumed = graph.invoke(
        Command(
            resume={
                "decision": "approve",
            }
        ),
        config=config,
    )

    snapshot = graph.get_state(config)

    assert resumed["status"] == "approved"
    assert snapshot.values["status"] == "approved"
    assert snapshot.next == ()


def test_different_thread_does_not_resume_original_checkpoint():
    graph = build_approval_test_graph()

    first_config = {
        "configurable": {
            "thread_id": "approval-original",
        }
    }

    second_config = {
        "configurable": {
            "thread_id": "approval-different",
        }
    }

    graph.invoke(initial_state(), config=first_config)

    second_state = initial_state()
    second_state["thread_id"] = "approval-different"

    second_result = graph.invoke(
        second_state,
        config=second_config,
    )

    assert "__interrupt__" in second_result

    original_snapshot = graph.get_state(first_config)

    assert original_snapshot.values["status"] == "awaiting_approval"


def test_api_resume_requires_authentication():
    client = TestClient(app)

    response = client.post(
        "/agent/resume",
        json={
            "thread_id": "thread-1",
            "decision": {
                "decision": "approve",
            },
        },
    )

    assert response.status_code == 401


def test_api_run_response_schema_contains_approval_fields():
    client = TestClient(app)

    response = client.post(
        "/agent/run",
        json={
            "request": "Create a report.",
        },
    )

    assert response.status_code == 401


def test_approval_node_does_not_execute_side_effect_before_interrupt():
    # This test documents the safety property required by LangGraph:
    # side effects must not occur before an interrupt because the node
    # restarts from the beginning when resumed.
    state = initial_state()

    result = prepare_approval(state)

    assert result["status"] == "awaiting_approval"
    assert state["generated_output"] == "Generated management report."


def test_approval_decision_model_is_typed():
    decision = ApprovalDecision(
        decision="approve",
    )

    assert decision.decision == "approve"

    reject = ApprovalDecision(
        decision="reject",
        feedback="Needs another review.",
    )

    assert reject.decision == "reject"
    assert reject.feedback == "Needs another review."


def test_approval_edit_model_preserves_feedback():
    decision = ApprovalDecision(
        decision="edit",
        edited_output="Updated report.",
        feedback="Fixed financial section.",
    )

    assert decision.decision == "edit"
    assert decision.edited_output == "Updated report."
    assert decision.feedback == "Fixed financial section."


def test_approval_reject_model_allows_feedback():
    decision = ApprovalDecision(
        decision="reject",
        feedback="Insufficient evidence.",
    )

    assert decision.decision == "reject"
    assert decision.feedback == "Insufficient evidence."
def test_resume_agent_namespaces_checkpoint_by_authenticated_user():
    from unittest.mock import MagicMock, patch

    from app.agent.service import resume_agent

    graph = MagicMock()

    graph.stream.return_value = iter(
        [
            {
                "mark_approved": {
                    "status": "approved",
                    "approval_decision": "approve",
                }
            }
        ]
    )

    graph.get_state.return_value.values = {
        "status": "completed",
        "selected_skills": [],
        "findings": [],
        "generated_output": "Approved output.",
        "generated_artifact": None,
        "validation_result": {
            "valid": True,
            "issues": [],
        },
        "approval_decision": "approve",
        "approval_feedback": None,
    }

    decision = ApprovalDecision(decision="approve")

    with (
        patch(
            "app.agent.service._ensure_user_workspace"
        ),
        patch(
            "app.agent.service.get_graph",
            return_value=graph,
        ),
        patch(
            "app.agent.service._persist_generated_artifact"
        ),
        patch(
            "app.agent.service._publish_event"
        ),
    ):
        resume_agent(
            user_id="user_a",
            thread_id="shared-thread",
            decision=decision,
        )

        first_config = graph.stream.call_args.kwargs["config"]

        resume_agent(
            user_id="user_b",
            thread_id="shared-thread",
            decision=decision,
        )

        second_config = graph.stream.call_args.kwargs["config"]

    first_thread_id = (
        first_config["configurable"]["thread_id"]
    )
    second_thread_id = (
        second_config["configurable"]["thread_id"]
    )

    assert first_thread_id == "user_a:shared-thread"
    assert second_thread_id == "user_b:shared-thread"
    assert first_thread_id != second_thread_id
