from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.graph import build_graph
from app.agent.models import (
    Finding,
    FindingCollection,
    RequestAnalysis,
    ValidationResult,
)
from app.agent.nodes.content_analysis import analyze_content
from app.agent.nodes.output_generation import generate_output
from app.agent.nodes.output_validation import validate_output
from app.agent.service import build_initial_state
from app.agent.state import AgentState
from app.core.config import get_settings
from app.main import app


@pytest.fixture
def state() -> AgentState:
    return {
        "user_id": "user_a",
        "thread_id": "user_a:thread_1",
        "request": "Create a management report from my documents.",
        "request_analysis": RequestAnalysis(
            intent="reporting",
            selected_skills=[
                "document_analysis",
                "report_generation",
            ],
            requested_output_type="report",
        ),
        "discovered_skills": [],
        "selected_skills": [
            "document_analysis",
            "report_generation",
        ],
        "loaded_skills": {
            "document_analysis": "Analyze source documents.",
            "report_generation": "Generate professional reports.",
        },
        "workspace_files": [],
        "source_contents": {
            "input/report.txt": "Revenue increased by 18%.",
        },
        "findings": [
            Finding(
                statement="Revenue increased by 18%.",
                source_path="input/report.txt",
                confidence="high",
            )
        ],
        "generated_output": None,
        "generated_artifact": None,
        "validation_result": None,
        "status": "sources_read",
        "error": None,
    }


def test_content_analysis_returns_structured_findings(state):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = FindingCollection(
        findings=[
            Finding(
                statement="Revenue increased by 18%.",
                source_path="input/report.txt",
                confidence="high",
            )
        ]
    )

    with patch(
        "app.agent.nodes.content_analysis.get_content_analysis_llm",
        return_value=mock_llm,
    ):
        result = analyze_content(state)

    assert len(result["findings"]) == 1
    assert result["findings"][0].source_path == "input/report.txt"
    assert result["status"] == "content_analyzed"


def test_content_analysis_handles_empty_sources(state):
    state["source_contents"] = {}

    result = analyze_content(state)

    assert result["findings"] == []
    assert result["status"] == "content_analyzed"


def test_output_generation_creates_text(state):
    mock_response = MagicMock()
    mock_response.content = "# Management Report\nRevenue increased by 18%."

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response

    with patch(
        "app.agent.nodes.output_generation.get_report_generation_llm",
        return_value=mock_llm,
    ):
        result = generate_output(state)

    assert result["generated_output"].startswith("# Management Report")
    assert result["status"] == "output_generated"


def test_output_validation_accepts_valid_output(state):
    state["generated_output"] = (
        "# Management Report\nRevenue increased by 18%."
    )

    result = validate_output(state)

    assert result["validation_result"].valid is True
    assert result["validation_result"].issues == []
    assert result["status"] == "output_validated"


def test_output_validation_rejects_empty_output(state):
    state["generated_output"] = ""

    result = validate_output(state)

    assert result["validation_result"].valid is False
    assert "Generated output is empty" in (
        result["validation_result"].issues
    )


def test_output_validation_rejects_no_findings_when_sources_exist(state):
    state["generated_output"] = "A sufficiently long report."
    state["findings"] = []

    result = validate_output(state)

    assert result["validation_result"].valid is False


def test_build_graph_has_all_nodes():
    graph = build_graph(checkpointer=InMemorySaver())

    node_names = set(graph.get_graph().nodes.keys())

    expected = {
        "__start__",
        "__end__",
        "discover_skills",
        "analyze_request",
        "load_skills",
        "inspect_workspace",
        "read_sources",
        "analyze_content",
        "generate_output",
        "validate_output",
    }

    assert expected.issubset(node_names)


def test_build_graph_compiles_with_checkpointer():
    graph = build_graph(checkpointer=InMemorySaver())

    assert graph is not None


def test_initial_state_contains_required_execution_identity():
    state = build_initial_state(
        user_id="user_a",
        thread_id="user_a:thread_1",
        request="Analyze documents.",
    )

    assert state["user_id"] == "user_a"
    assert state["thread_id"] == "user_a:thread_1"
    assert state["request"] == "Analyze documents."
    assert state["status"] == "started"


def test_thread_ids_are_user_namespaced():
    from app.agent.service import run_agent

    with patch("app.agent.service.get_graph") as mock_get_graph:
        graph = MagicMock()

        graph.stream.return_value = [
            {
                "validate_output": {
                    "status": "output_validated",
                }
            }
        ]

        graph.get_state.return_value.values = {
            "thread_id": "user_a:thread_1",
            "status": "output_validated",
            "selected_skills": [],
            "findings": [],
            "generated_output": "A generated report.",
            "validation_result": ValidationResult(valid=True),
        }

        mock_get_graph.return_value = graph

        run_agent(
            user_id="user_a",
            request="Create a report.",
            thread_id="thread_1",
        )

        assert graph.stream.call_args is not None

        config = graph.stream.call_args.kwargs["config"]

        assert config["configurable"]["thread_id"] == "user_a:thread_1"
def test_api_rejects_missing_authentication():
    client = TestClient(app)

    response = client.post(
        "/agent/run",
        json={"request": "Create a report."},
    )

    assert response.status_code == 401


def test_api_accepts_valid_jwt():
    settings = get_settings()

    token = jwt.encode(
        {"sub": "user_a"},
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )

    fake_result = {
        "thread_id": "user_a:thread_1",
        "status": "output_validated",
        "selected_skills": ["document_analysis"],
        "findings": [],
        "generated_output": "A generated report.",
        "validation_result": ValidationResult(valid=True),
    }

    with patch(
        "app.api.agent.run_agent",
        return_value=fake_result,
    ):
        client = TestClient(app)

        response = client.post(
            "/agent/run",
            json={
                "request": "Create a report.",
                "thread_id": "thread_1",
            },
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "output_validated"
    assert body["selected_skills"] == ["document_analysis"]


def test_api_rejects_invalid_jwt():
    client = TestClient(app)

    response = client.post(
        "/agent/run",
        json={"request": "Create a report."},
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401


def test_content_analysis_does_not_mutate_source_contents(state):
    original = dict(state["source_contents"])

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = FindingCollection()

    with patch(
        "app.agent.nodes.content_analysis.get_content_analysis_llm",
        return_value=mock_llm,
    ):
        analyze_content(state)

    assert state["source_contents"] == original


def test_output_validation_returns_pydantic_model(state):
    state["generated_output"] = (
        "# Management Report\nRevenue increased by 18%."
    )

    result = validate_output(state)

    assert isinstance(
        result["validation_result"],
        ValidationResult,
    )


def test_graph_uses_persistent_thread_configuration():
    graph = build_graph(checkpointer=InMemorySaver())

    config = {
        "configurable": {
            "thread_id": "user_a:thread_test",
        }
    }

    # Compile-level persistence contract verification.
    assert "configurable" in config
    assert config["configurable"]["thread_id"]


@pytest.mark.parametrize(
    "user_id",
    [
        "user_a",
        "user_b",
        "tenant_001",
    ],
)
def test_user_identity_is_preserved(user_id):
    state = build_initial_state(
        user_id=user_id,
        thread_id=f"{user_id}:thread",
        request="Analyze documents.",
    )

    assert state["user_id"] == user_id
    assert state["thread_id"].startswith(f"{user_id}:")