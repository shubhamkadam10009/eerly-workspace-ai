import re
from pathlib import Path

from app.skills.models import SkillMetadata


class SkillLoader:
    """Load complete skill instructions on demand."""

    def __init__(self, skills_root: Path | None = None) -> None:
        configured_root = (
            skills_root
            if skills_root is not None
            else Path("skills")
        )
        self.skills_root = configured_root.resolve()

    def load(
        self,
        skill_name: str,
        available_skills: list[SkillMetadata] | None = None,
    ) -> str:
        """Load the complete SKILL.md for a requested skill."""

        self._validate_skill_name(skill_name)

        skill_directory = (self.skills_root / skill_name).resolve()

        try:
            skill_directory.relative_to(self.skills_root)
        except ValueError as exc:
            raise ValueError("Skill path escapes skills root") from exc

        skill_file = skill_directory / "SKILL.md"

        if not skill_file.is_file():
            raise FileNotFoundError(
                f"Skill not found: {skill_name}"
            )

        if available_skills is not None:
            known_names = {
                skill.name
                for skill in available_skills
            }

            if skill_name not in known_names:
                raise ValueError(
                    f"Skill is not discovered: {skill_name}"
                )

        return skill_file.read_text(encoding="utf-8")

    @staticmethod
    def _validate_skill_name(skill_name: str) -> None:
        """Validate a skill name before resolving its filesystem path."""

        if not skill_name:
            raise ValueError("skill_name cannot be empty")

        if not re.fullmatch(r"[A-Za-z0-9_-]+", skill_name):
            raise ValueError("Invalid skill_name")


skill_loader = SkillLoader()
