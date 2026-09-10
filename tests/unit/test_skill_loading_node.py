from unittest.mock import MagicMock

import pytest

from app.agent.nodes.skill_loading import load_skills
from app.agent.state import AgentState
from app.skills.models import SkillMetadata


@pytest.fixture
def base_state() -> AgentState:
    return {
        "user_id": "user_a",
        "thread_id": "thread_001",
        "request": "Analyze my documents and create a report.",
        "discovered_skills": [
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
        ],
        "selected_skills": [
            "document_analysis",
            "report_generation",
        ],
        "loaded_skills": {},
        "workspace_files": [],
        "source_contents": {},
        "findings": [],
        "generated_artifact": None,
        "validation_result": None,
        "status": "skills_discovered",
        "error": None,
    }


def test_load_skills_loads_all_selected_skills(
    base_state: AgentState,
):
    mock_loader = MagicMock()

    mock_loader.load.side_effect = [
        "Document analysis instructions",
        "Report generation instructions",
    ]

    result = load_skills(
        base_state,
        skill_loader=mock_loader,
    )

    assert result["loaded_skills"] == {
        "document_analysis": "Document analysis instructions",
        "report_generation": "Report generation instructions",
    }

    assert result["status"] == "skills_loaded"
    assert result["error"] is None

    assert mock_loader.load.call_count == 2

    mock_loader.load.assert_any_call(
        skill_name="document_analysis",
        available_skills=base_state["discovered_skills"],
    )

    mock_loader.load.assert_any_call(
        skill_name="report_generation",
        available_skills=base_state["discovered_skills"],
    )


def test_load_skills_returns_empty_when_nothing_selected(
    base_state: AgentState,
):
    base_state["selected_skills"] = []

    mock_loader = MagicMock()

    result = load_skills(
        base_state,
        skill_loader=mock_loader,
    )

    assert result["loaded_skills"] == {}
    assert result["status"] == "skills_loaded"
    assert result["error"] is None

    mock_loader.load.assert_not_called()


def test_load_skills_loads_only_selected_skills(
    base_state: AgentState,
):
    base_state["selected_skills"] = ["document_analysis"]

    mock_loader = MagicMock()
    mock_loader.load.return_value = "Document analysis instructions"

    result = load_skills(
        base_state,
        skill_loader=mock_loader,
    )

    assert result["loaded_skills"] == {
        "document_analysis": "Document analysis instructions",
    }

    mock_loader.load.assert_called_once_with(
        skill_name="document_analysis",
        available_skills=base_state["discovered_skills"],
    )


def test_load_skills_propagates_loader_failure(
    base_state: AgentState,
):
    mock_loader = MagicMock()

    mock_loader.load.side_effect = FileNotFoundError(
        "Skill not found: document_analysis"
    )

    with pytest.raises(
        FileNotFoundError,
        match="Skill not found",
    ):
        load_skills(
            base_state,
            skill_loader=mock_loader,
        )

    mock_loader.load.assert_called_once()


def test_load_skills_propagates_security_failure(
    base_state: AgentState,
):
    base_state["selected_skills"] = ["unknown_skill"]

    mock_loader = MagicMock()

    mock_loader.load.side_effect = ValueError(
        "Skill is not discovered: unknown_skill"
    )

    with pytest.raises(
        ValueError,
        match="Skill is not discovered",
    ):
        load_skills(
            base_state,
            skill_loader=mock_loader,
        )

    mock_loader.load.assert_called_once_with(
        skill_name="unknown_skill",
        available_skills=base_state["discovered_skills"],
    )


def test_load_skills_does_not_modify_selected_skills(
    base_state: AgentState,
):
    original_selection = list(base_state["selected_skills"])

    mock_loader = MagicMock()
    mock_loader.load.side_effect = [
        "Document analysis instructions",
        "Report generation instructions",
    ]

    load_skills(
        base_state,
        skill_loader=mock_loader,
    )

    assert base_state["selected_skills"] == original_selection
