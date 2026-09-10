from app.agent.state import AgentState
from app.agent.structured_llm import (
    build_content_analysis_messages,
    get_content_analysis_llm,
)


MAX_SOURCE_CHARS = 100_000


def analyze_content(state: AgentState) -> dict:
    """Analyze workspace source material using loaded skills."""

    source_contents = state["source_contents"]

    if not source_contents:
        return {
            "findings": [],
            "status": "content_analyzed",
            "error": None,
        }

    skill_instructions = "\n\n".join(
        f"## {name}\n{instructions}"
        for name, instructions in state["loaded_skills"].items()
    )

    source_material = "\n\n".join(
        f"## SOURCE: {path}\n{content}"
        for path, content in source_contents.items()
    )

    source_material = source_material[:MAX_SOURCE_CHARS]

    messages = build_content_analysis_messages(
        request=state["request"],
        skill_instructions=skill_instructions,
        source_material=source_material,
    )

    result = get_content_analysis_llm().invoke(messages)

    findings = [
        finding.model_dump()
        for finding in result.findings
    ]

    return {
        "findings": findings,
        "status": "content_analyzed",
        "error": None,
    }
