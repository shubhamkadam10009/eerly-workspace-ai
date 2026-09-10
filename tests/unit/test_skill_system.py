from pathlib import Path

import pytest

from app.skills import SkillDiscovery, SkillLoader
from app.skills.models import SkillMetadata


def write_skill(
    skills_root: Path,
    directory_name: str,
    content: str,
) -> Path:
    skill_directory = skills_root / directory_name
    skill_directory.mkdir(parents=True, exist_ok=True)

    skill_file = skill_directory / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")

    return skill_file


VALID_DOCUMENT_SKILL = """---
name: document_analysis
description: Analyze workspace documents.
---

# Document Analysis Skill

Analyze documents safely.
"""

VALID_REPORT_SKILL = """---
name: report_generation
description: Generate structured reports.
---

# Report Generation Skill

Generate reports safely.
"""


def test_discovery_finds_both_valid_skills(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )
    write_skill(
        tmp_path,
        "report_generation",
        VALID_REPORT_SKILL,
    )

    discovery = SkillDiscovery(tmp_path)

    skills = discovery.discover()

    assert [skill.name for skill in skills] == [
        "document_analysis",
        "report_generation",
    ]


def test_discovery_returns_skill_metadata(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    skills = SkillDiscovery(tmp_path).discover()

    assert len(skills) == 1
    assert isinstance(skills[0], SkillMetadata)


def test_discovery_returns_correct_description(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    skill = SkillDiscovery(tmp_path).discover()[0]

    assert skill.description == "Analyze workspace documents."


def test_discovery_returns_correct_skill_path(tmp_path: Path) -> None:
    skill_file = write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    skill = SkillDiscovery(tmp_path).discover()[0]

    assert Path(skill.skill_path) == skill_file.resolve()


def test_discovery_ignores_directory_without_skill_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "not_a_skill").mkdir()

    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    skills = SkillDiscovery(tmp_path).discover()

    assert [skill.name for skill in skills] == [
        "document_analysis"
    ]


def test_discovery_ignores_file_directly_under_root(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text(
        "not a skill",
        encoding="utf-8",
    )

    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    skills = SkillDiscovery(tmp_path).discover()

    assert [skill.name for skill in skills] == [
        "document_analysis"
    ]


def test_discovery_returns_empty_when_root_does_not_exist(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "missing"

    skills = SkillDiscovery(missing_root).discover()

    assert skills == []


def test_discovery_rejects_missing_frontmatter(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        "# Document Analysis",
    )

    with pytest.raises(
        ValueError,
        match="must start with frontmatter",
    ):
        SkillDiscovery(tmp_path).discover()


def test_discovery_rejects_unclosed_frontmatter(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        """---
name: document_analysis
description: Analyze documents.
""",
    )

    with pytest.raises(
        ValueError,
        match="frontmatter is not closed",
    ):
        SkillDiscovery(tmp_path).discover()


def test_discovery_rejects_missing_name(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        """---
description: Analyze documents.
---
# Skill
""",
    )

    with pytest.raises(
        ValueError,
        match="missing required 'name'",
    ):
        SkillDiscovery(tmp_path).discover()


def test_discovery_rejects_missing_description(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        """---
name: document_analysis
---
# Skill
""",
    )

    with pytest.raises(
        ValueError,
        match="missing required 'description'",
    ):
        SkillDiscovery(tmp_path).discover()


def test_discovery_rejects_name_directory_mismatch(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        """---
name: wrong_name
description: Analyze documents.
---
# Skill
""",
    )

    with pytest.raises(
        ValueError,
        match="does not match directory",
    ):
        SkillDiscovery(tmp_path).discover()


def test_discovery_handles_utf8_bom(
    tmp_path: Path,
) -> None:
    skill_directory = tmp_path / "document_analysis"
    skill_directory.mkdir()

    skill_file = skill_directory / "SKILL.md"

    content = (
        "\ufeff"
        "---\n"
        "name: document_analysis\n"
        "description: Analyze documents.\n"
        "---\n"
        "# Skill\n"
    )

    skill_file.write_text(content, encoding="utf-8")

    skills = SkillDiscovery(tmp_path).discover()

    assert skills[0].name == "document_analysis"


def test_loader_loads_document_analysis(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    content = SkillLoader(tmp_path).load(
        "document_analysis"
    )

    assert content == VALID_DOCUMENT_SKILL


def test_loader_loads_report_generation(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "report_generation",
        VALID_REPORT_SKILL,
    )

    content = SkillLoader(tmp_path).load(
        "report_generation"
    )

    assert content == VALID_REPORT_SKILL


def test_loader_returns_complete_skill_content(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    content = SkillLoader(tmp_path).load(
        "document_analysis"
    )

    assert "# Document Analysis Skill" in content
    assert "Analyze documents safely." in content


def test_loader_rejects_unknown_skill(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Skill not found",
    ):
        SkillLoader(tmp_path).load("unknown_skill")


def test_loader_rejects_missing_skill_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "document_analysis").mkdir()

    with pytest.raises(
        FileNotFoundError,
        match="Skill not found",
    ):
        SkillLoader(tmp_path).load(
            "document_analysis"
        )


@pytest.mark.parametrize(
    "skill_name",
    [
        "",
        ".",
        "..",
        "../secret",
        "../../secret",
        r"..\secret",
        r"..\..\secret",
        r"C:\secret",
        "/etc/passwd",
        "skills/document_analysis",
        r"skills\document_analysis",
        "document analysis",
        "document.analysis",
    ],
)
def test_loader_rejects_invalid_skill_names(
    tmp_path: Path,
    skill_name: str,
) -> None:
    with pytest.raises(ValueError):
        SkillLoader(tmp_path).load(skill_name)


def test_loader_rejects_path_escape(
    tmp_path: Path,
) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    outside_directory = tmp_path / "outside"
    outside_directory.mkdir()

    loader = SkillLoader(skills_root)

    with pytest.raises(ValueError):
        loader.load("../outside")


def test_loader_rejects_skill_not_in_available_skills(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    available_skills = [
        SkillMetadata(
            name="report_generation",
            description="Generate reports.",
            skill_path=(
                tmp_path
                / "report_generation"
                / "SKILL.md"
            ).as_posix(),
        )
    ]

    with pytest.raises(
        ValueError,
        match="Skill is not discovered",
    ):
        SkillLoader(tmp_path).load(
            "document_analysis",
            available_skills=available_skills,
        )


def test_loader_accepts_discovered_skill(
    tmp_path: Path,
) -> None:
    write_skill(
        tmp_path,
        "document_analysis",
        VALID_DOCUMENT_SKILL,
    )

    available_skills = SkillDiscovery(tmp_path).discover()

    content = SkillLoader(tmp_path).load(
        "document_analysis",
        available_skills=available_skills,
    )

    assert content == VALID_DOCUMENT_SKILL


@pytest.mark.skipif(
    __import__("sys").platform == "win32",
    reason="Windows symlink creation may require elevated privileges",
)
def test_discovery_rejects_symlink_escape(
    tmp_path: Path,
) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()

    outside_file = tmp_path / "secret.md"
    outside_file.write_text(
        "secret data",
        encoding="utf-8",
    )

    skill_directory = skills_root / "evil_skill"
    skill_directory.mkdir()

    symlink = skill_directory / "SKILL.md"
    symlink.symlink_to(outside_file)

    with pytest.raises(
        ValueError,
        match="escapes skills root",
    ):
        SkillDiscovery(skills_root).discover()
