from functools import lru_cache

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.agent.checkpoint import get_checkpointer
from app.agent.nodes import (
    analyze_content,
    analyze_request,
    deliver_artifact,
    discover_skills,
    generate_output,
    inspect_workspace,
    load_skills,
    mark_approved,
    mark_rejected,
    prepare_approval,
    read_sources,
    request_human_approval,
    validate_output,
)
from app.agent.state import AgentState


def route_after_validation(state: AgentState) -> str:
    validation_result = state.get("validation_result")

    if validation_result and validation_result["valid"]:
        return "prepare_approval"

    return "end"

def route_after_approval(state: AgentState) -> str:
    decision = state.get("approval_decision")

    if decision == "approve":
        return "mark_approved"

    if decision == "edit":
        return "validate_output"

    if decision == "reject":
        return "mark_rejected"

    raise ValueError(
        f"Unsupported approval decision: {decision!r}"
    )


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
):
    builder = StateGraph(AgentState)

    builder.add_node("discover_skills", discover_skills)
    builder.add_node("analyze_request", analyze_request)
    builder.add_node("load_skills", load_skills)
    builder.add_node("inspect_workspace", inspect_workspace)
    builder.add_node("read_sources", read_sources)
    builder.add_node("analyze_content", analyze_content)
    builder.add_node("generate_output", generate_output)
    builder.add_node("validate_output", validate_output)

    builder.add_node("prepare_approval", prepare_approval)
    builder.add_node("request_human_approval", request_human_approval)
    builder.add_node("mark_approved", mark_approved)
    builder.add_node("mark_rejected", mark_rejected)
    builder.add_node("deliver_artifact", deliver_artifact)

    builder.add_edge(START, "discover_skills")
    builder.add_edge("discover_skills", "analyze_request")
    builder.add_edge("analyze_request", "load_skills")
    builder.add_edge("load_skills", "inspect_workspace")
    builder.add_edge("inspect_workspace", "read_sources")
    builder.add_edge("read_sources", "analyze_content")
    builder.add_edge("analyze_content", "generate_output")
    builder.add_edge("generate_output", "validate_output")

    builder.add_conditional_edges(
        "validate_output",
        route_after_validation,
        {
            "prepare_approval": "prepare_approval",
            "end": END,
        },
    )

    builder.add_edge(
        "prepare_approval",
        "request_human_approval",
    )

    builder.add_conditional_edges(
        "request_human_approval",
        route_after_approval,
        {
            "mark_approved": "mark_approved",
            "validate_output": "validate_output",
            "mark_rejected": "mark_rejected",
        },
    )

    builder.add_edge(
        "mark_approved",
        "deliver_artifact",
    )

    builder.add_edge(
        "deliver_artifact",
        END,
    )

    builder.add_edge(
        "mark_rejected",
        END,
    )

    return builder.compile(checkpointer=checkpointer)


@lru_cache
def get_graph():
    return build_graph(checkpointer=get_checkpointer())
