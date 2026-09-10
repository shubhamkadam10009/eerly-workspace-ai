from app.agent.state import AgentState
from app.agent.structured_llm import (
    build_request_analysis_messages,
    get_request_analysis_llm,
)
from app.skills.discovery import SkillDiscovery


def analyze_request(
    state: AgentState,
    skill_discovery: SkillDiscovery | None = None,
) -> dict:
    """Analyze the user's request and determine required skills."""

    if not state["request"].strip():
        raise ValueError("request cannot be empty")

    available_skills = state["discovered_skills"]

    if not available_skills:
        discovery = skill_discovery or SkillDiscovery()
        available_skills = [
            skill.model_dump()
            for skill in discovery.discover()
        ]

    available_skills_text = "\n".join(
        f"- {skill["name"]}: {skill["description"]}"
        for skill in available_skills
    )

    messages = build_request_analysis_messages(
        request=state["request"],
        available_skills=available_skills_text,
    )

    llm = get_request_analysis_llm()
    analysis = llm.invoke(messages)

    available_skill_names = {
        skill["name"]
        for skill in available_skills
    }

    invalid_skills = [
        skill
        for skill in analysis.selected_skills
        if skill not in available_skill_names
    ]

    if invalid_skills:
        raise ValueError(
            f"LLM selected unavailable skills: {invalid_skills}"
        )

    return {
        "request_analysis": analysis.model_dump(),
        "selected_skills": analysis.selected_skills,
        "status": "request_analyzed",
        "error": None,
    }