from unittest.mock import MagicMock, patch

from app.agent.models import FindingCollection, RequestAnalysis
from app.agent.structured_llm import (
    build_content_analysis_messages,
    build_request_analysis_messages,
    get_content_analysis_llm,
    get_request_analysis_llm,
)


def test_request_analysis_message_builder():
    messages = build_request_analysis_messages(
        request="Create a management report.",
        available_skills="document_analysis: Analyze documents",
    )

    assert messages[0][0] == "system"
    assert messages[1][0] == "human"
    assert "Create a management report." in messages[1][1]
    assert "document_analysis" in messages[1][1]


def test_content_analysis_message_builder():
    messages = build_content_analysis_messages(
        request="Analyze the report.",
        skill_instructions="Extract source-grounded findings.",
        source_material="Revenue increased by 10%.",
    )

    assert messages[0][0] == "system"
    assert messages[1][0] == "human"
    assert "Analyze the report." in messages[1][1]
    assert "Revenue increased by 10%." in messages[1][1]


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
        strict=True,
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
        strict=True,
    )
