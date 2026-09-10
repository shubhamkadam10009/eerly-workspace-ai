from app.agent.state import AgentState
from app.skills.discovery import SkillDiscovery


def discover_skills(
    state: AgentState,
    skill_discovery: SkillDiscovery | None = None,
) -> dict:
    """Discover available skills and store their metadata in graph state."""

    discovery = skill_discovery or SkillDiscovery()
    discovered = discovery.discover()

    discovered_skills = [
        skill.model_dump()
        for skill in discovered
    ]

    return {
        "discovered_skills": discovered_skills,
        "status": "skills_discovered",
        "error": None,
    }
