from unittest.mock import MagicMock

import pytest

from app.agent.nodes.skill_discovery import discover_skills
from app.agent.state import AgentState
from app.skills.models import SkillMetadata


@pytest.fixture
def base_state() -> AgentState:
    return {
        "user_id": "user_a",
        "thread_id": "thread_001",
        "request": "Analyze my documents.",
        "discovered_skills": [],
        "selected_skills": [],
        "loaded_skills": {},
        "workspace_files": [],
        "source_contents": {},
        "findings": [],
        "generated_artifact": None,
        "validation_result": None,
        "status": "request_analyzed",
        "error": None,
    }


def test_discover_skills_returns_discovered_metadata(
    base_state: AgentState,
):
    expected_skills = [
        SkillMetadata(
            name="document_analysis",
            description="Analyze workspace documents.",
            skill_path="/skills/document_analysis/SKILL.md",
        ),
        SkillMetadata(
            name="report_generation",
            description="Generate structured reports.",
            skill_path="/skills/report_generation/SKILL.md",
        ),
    ]

    mock_discovery = MagicMock()
    mock_discovery.discover.return_value = expected_skills

    result = discover_skills(
        base_state,
        skill_discovery=mock_discovery,
    )

    assert result["discovered_skills"] == expected_skills
    assert result["status"] == "skills_discovered"
    assert result["error"] is None

    mock_discovery.discover.assert_called_once()


def test_discover_skills_returns_empty_list_when_none_exist(
    base_state: AgentState,
):
    mock_discovery = MagicMock()
    mock_discovery.discover.return_value = []

    result = discover_skills(
        base_state,
        skill_discovery=mock_discovery,
    )

    assert result["discovered_skills"] == []
    assert result["status"] == "skills_discovered"
    assert result["error"] is None


def test_discover_skills_propagates_discovery_error(
    base_state: AgentState,
):
    mock_discovery = MagicMock()
    mock_discovery.discover.side_effect = ValueError(
        "Skills root must be a directory"
    )

    with pytest.raises(
        ValueError,
        match="Skills root must be a directory",
    ):
        discover_skills(
            base_state,
            skill_discovery=mock_discovery,
        )

    mock_discovery.discover.assert_called_once()


def test_discover_skills_does_not_modify_request(
    base_state: AgentState,
):
    mock_discovery = MagicMock()
    mock_discovery.discover.return_value = []

    original_request = base_state["request"]

    discover_skills(
        base_state,
        skill_discovery=mock_discovery,
    )

    assert base_state["request"] == original_request
