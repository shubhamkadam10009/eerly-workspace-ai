from app.agent.state import AgentState
from app.skills.loader import SkillLoader
from app.skills.models import SkillMetadata


def load_skills(
    state: AgentState,
    skill_loader: SkillLoader | None = None,
) -> dict:
    """Load full instructions for the skills selected by request analysis."""

    selected_skills = state["selected_skills"]
    discovered_skills = state["discovered_skills"]

    if not selected_skills:
        return {
            "loaded_skills": {},
            "status": "skills_loaded",
            "error": None,
        }

    loader = skill_loader or SkillLoader()

    available_skill_models = [
        SkillMetadata.model_validate(skill)
        for skill in discovered_skills
    ]

    loaded_skills: dict[str, str] = {}

    for skill_name in selected_skills:
        loaded_skills[skill_name] = loader.load(
            skill_name=skill_name,
            available_skills=available_skill_models,
        )

    return {
        "loaded_skills": loaded_skills,
        "status": "skills_loaded",
        "error": None,
    }
