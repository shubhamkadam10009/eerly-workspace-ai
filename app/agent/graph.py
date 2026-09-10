from functools import lru_cache

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.agent.checkpoint import get_checkpointer
from app.agent.nodes import (
    analyze_content,
    analyze_request,
    discover_skills,
    generate_output,
    inspect_workspace,
    load_skills,
    read_sources,
    validate_output,
)
from app.agent.state import AgentState


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Build the complete Workspace Consultant graph."""

    builder = StateGraph(AgentState)

    builder.add_node("discover_skills", discover_skills)
    builder.add_node("analyze_request", analyze_request)
    builder.add_node("load_skills", load_skills)
    builder.add_node("inspect_workspace", inspect_workspace)
    builder.add_node("read_sources", read_sources)
    builder.add_node("analyze_content", analyze_content)
    builder.add_node("generate_output", generate_output)
    builder.add_node("validate_output", validate_output)

    builder.add_edge(START, "discover_skills")
    builder.add_edge("discover_skills", "analyze_request")
    builder.add_edge("analyze_request", "load_skills")
    builder.add_edge("load_skills", "inspect_workspace")
    builder.add_edge("inspect_workspace", "read_sources")
    builder.add_edge("read_sources", "analyze_content")
    builder.add_edge("analyze_content", "generate_output")
    builder.add_edge("generate_output", "validate_output")
    builder.add_edge("validate_output", END)

    return builder.compile(
        checkpointer=checkpointer,
    )


@lru_cache
def get_graph():
    """Return the production graph with PostgreSQL checkpointing."""

    return build_graph(
        checkpointer=get_checkpointer(),
    )