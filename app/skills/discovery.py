from pathlib import Path

from app.skills.models import SkillMetadata


class SkillDiscovery:
    """Discover available SKILL.md definitions without loading their instructions."""

    def __init__(self, skills_root: Path | None = None) -> None:
        configured_root = (
            skills_root
            if skills_root is not None
            else Path("skills")
        )
        self.skills_root = configured_root.resolve()

    def discover(self) -> list[SkillMetadata]:
        """Discover valid skill directories containing SKILL.md files."""

        if not self.skills_root.exists():
            return []

        if not self.skills_root.is_dir():
            raise ValueError("Skills root must be a directory")

        discovered: list[SkillMetadata] = []

        for skill_directory in sorted(
            self.skills_root.iterdir(),
            key=lambda path: path.name.lower(),
        ):
            if not skill_directory.is_dir():
                continue

            skill_file = skill_directory / "SKILL.md"

            if not skill_file.is_file():
                continue

            resolved_skill_file = skill_file.resolve()

            try:
                resolved_skill_file.relative_to(self.skills_root)
            except ValueError as exc:
                raise ValueError(
                    "Skill file escapes skills root"
                ) from exc

            metadata = self._read_metadata(
                resolved_skill_file
            )

            discovered.append(metadata)

        return discovered

    def _read_metadata(self, skill_file: Path) -> SkillMetadata:
        """Read only the metadata required for discovery."""

        content = skill_file.read_text(encoding="utf-8")

        frontmatter = self._extract_frontmatter(content)

        name = frontmatter.get("name")
        description = frontmatter.get("description")

        if not name:
            raise ValueError(
                f"Skill is missing required 'name': {skill_file}"
            )

        if not description:
            raise ValueError(
                f"Skill is missing required 'description': {skill_file}"
            )

        expected_directory = skill_file.parent.name

        if name != expected_directory:
            raise ValueError(
                f"Skill name '{name}' does not match directory "
                f"'{expected_directory}'"
            )

        return SkillMetadata(
            name=name,
            description=description,
            skill_path=skill_file.as_posix(),
        )

    @staticmethod
    def _extract_frontmatter(content: str) -> dict[str, str]:
        """Extract simple YAML-style frontmatter from SKILL.md."""

        lines = content.lstrip("\ufeff").splitlines()

        if not lines or lines[0].strip() != "---":
            raise ValueError(
                "SKILL.md must start with frontmatter"
            )

        try:
            end_index = lines.index("---", 1)
        except ValueError as exc:
            raise ValueError(
                "SKILL.md frontmatter is not closed"
            ) from exc

        metadata: dict[str, str] = {}

        for line in lines[1:end_index]:
            if ":" not in line:
                continue

            key, value = line.split(":", 1)

            key = key.strip()
            value = value.strip()

            if key and value:
                metadata[key] = value

        return metadata


skill_discovery = SkillDiscovery()
