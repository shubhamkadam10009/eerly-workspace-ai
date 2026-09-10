from unittest.mock import MagicMock, patch

import pytest

from app.agent.nodes.request_analysis import analyze_request
from app.agent.state import AgentState
from app.skills.models import SkillMetadata


@pytest.fixture
def base_state() -> AgentState:
    return {
        "user_id": "user_a",
        "thread_id": "thread_001",
        "request": "Analyze my documents and create a report.",
        "discovered_skills": [],
        "selected_skills": [],
        "loaded_skills": {},
        "workspace_files": [],
        "source_contents": {},
        "findings": [],
        "generated_artifact": None,
        "validation_result": None,
        "status": "started",
        "error": None,
    }


@pytest.fixture
def discovered_skills() -> list[SkillMetadata]:
    return [
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


def test_analyze_request_selects_valid_skills(
    base_state: AgentState,
    discovered_skills: list[SkillMetadata],
):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        selected_skills=[
            "document_analysis",
            "report_generation",
        ],
        intent="reporting",
        requested_output_type="report",
    )

    mock_discovery = MagicMock()
    mock_discovery.discover.return_value = discovered_skills

    with patch(
        "app.agent.nodes.request_analysis.get_request_analysis_llm",
        return_value=mock_llm,
    ):
        result = analyze_request(
            base_state,
            skill_discovery=mock_discovery,
        )

    assert result["selected_skills"] == [
        "document_analysis",
        "report_generation",
    ]
    assert result["status"] == "request_analyzed"
    assert result["error"] is None

    mock_discovery.discover.assert_called_once()
    mock_llm.invoke.assert_called_once()


def test_analyze_request_passes_available_skills_to_llm(
    base_state: AgentState,
    discovered_skills: list[SkillMetadata],
):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        selected_skills=["document_analysis"],
        intent="analysis",
        requested_output_type=None,
    )

    mock_discovery = MagicMock()
    mock_discovery.discover.return_value = discovered_skills

    with patch(
        "app.agent.nodes.request_analysis.get_request_analysis_llm",
        return_value=mock_llm,
    ):
        analyze_request(
            base_state,
            skill_discovery=mock_discovery,
        )

    messages = mock_llm.invoke.call_args.args[0]

    combined_messages = "\n".join(
        message[1]
        for message in messages
    )

    assert "document_analysis" in combined_messages
    assert "report_generation" in combined_messages
    assert "Analyze my documents and create a report." in combined_messages


def test_analyze_request_rejects_unknown_skill(
    base_state: AgentState,
    discovered_skills: list[SkillMetadata],
):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        selected_skills=["unknown_skill"],
        intent="analysis",
        requested_output_type=None,
    )

    mock_discovery = MagicMock()
    mock_discovery.discover.return_value = discovered_skills

    with patch(
        "app.agent.nodes.request_analysis.get_request_analysis_llm",
        return_value=mock_llm,
    ):
        with pytest.raises(
            ValueError,
            match="LLM selected unavailable skills",
        ):
            analyze_request(
                base_state,
                skill_discovery=mock_discovery,
            )


def test_analyze_request_rejects_empty_request(
    base_state: AgentState,
):
    base_state["request"] = "   "

    mock_discovery = MagicMock()

    with pytest.raises(
        ValueError,
        match="request cannot be empty",
    ):
        analyze_request(
            base_state,
            skill_discovery=mock_discovery,
        )

    mock_discovery.discover.assert_not_called()


def test_analyze_request_propagates_skill_discovery_failure(
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
        analyze_request(
            base_state,
            skill_discovery=mock_discovery,
        )


def test_analyze_request_propagates_llm_failure(
    base_state: AgentState,
    discovered_skills: list[SkillMetadata],
):
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError(
        "LLM unavailable"
    )

    mock_discovery = MagicMock()
    mock_discovery.discover.return_value = discovered_skills

    with patch(
        "app.agent.nodes.request_analysis.get_request_analysis_llm",
        return_value=mock_llm,
    ):
        with pytest.raises(
            RuntimeError,
            match="LLM unavailable",
        ):
            analyze_request(
                base_state,
                skill_discovery=mock_discovery,
            )
