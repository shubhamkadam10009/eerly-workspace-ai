from unittest.mock import MagicMock, patch

from app.agent.models import FindingCollection, RequestAnalysis
from app.agent.structured_llm import (
    build_content_analysis_messages,
    build_report_generation_messages,
    build_request_analysis_messages,
    get_content_analysis_llm,
    get_report_generation_llm,
    get_request_analysis_llm,
)


@patch("app.agent.structured_llm.get_llm")
def test_request_analysis_llm_uses_expected_schema(mock_get_llm):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = structured_llm

    result = get_request_analysis_llm()

    assert result is structured_llm
    mock_llm.with_structured_output.assert_called_once_with(
        RequestAnalysis,
        method="json_schema",
    )


@patch("app.agent.structured_llm.get_llm")
def test_content_analysis_llm_uses_expected_schema(mock_get_llm):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = structured_llm

    result = get_content_analysis_llm()

    assert result is structured_llm
    mock_llm.with_structured_output.assert_called_once_with(
        FindingCollection,
        method="json_schema",
    )


@patch("app.agent.structured_llm.get_llm")
def test_report_generation_llm_returns_base_llm(mock_get_llm):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    result = get_report_generation_llm()

    assert result is mock_llm
    mock_get_llm.assert_called_once()


def test_build_request_analysis_messages():
    messages = build_request_analysis_messages(
        request="Analyze my files",
        available_skills="document_analysis",
    )

    assert len(messages) == 2
    assert messages[0][0] == "system"
    assert messages[1][0] == "human"
    assert "Analyze my files" in messages[1][1]
    assert "document_analysis" in messages[1][1]


def test_build_content_analysis_messages():
    messages = build_content_analysis_messages(
        request="Find important issues",
        skill_instructions="Analyze documents carefully.",
        source_material="Sample source content.",
    )

    assert len(messages) == 2
    assert messages[0][0] == "system"
    assert messages[1][0] == "human"
    assert "Find important issues" in messages[1][1]
    assert "Analyze documents carefully." in messages[1][1]
    assert "Sample source content." in messages[1][1]


def test_build_report_generation_messages():
    messages = build_report_generation_messages(
        request="Create a report",
        skill_instructions="Use concise professional language.",
        findings="Finding one.",
    )

    assert len(messages) == 2
    assert messages[0][0] == "system"
    assert messages[1][0] == "human"
    assert "Create a report" in messages[1][1]
    assert "Use concise professional language." in messages[1][1]
    assert "Finding one." in messages[1][1]
