from pydantic import BaseModel


class SkillMetadata(BaseModel):
    """Metadata describing an available skill."""

    name: str
    description: str
    skill_path: str
