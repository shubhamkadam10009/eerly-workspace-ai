from unittest.mock import patch

import pytest

from app.agent.nodes.workspace_inspection import inspect_workspace
from app.agent.state import AgentState


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
        "status": "skills_loaded",
        "error": None,
    }


def test_inspect_workspace_returns_workspace_files(
    base_state: AgentState,
):
    entries = [
        {
            "name": "report.txt",
            "path": "input/report.txt",
            "type": "file",
        },
        {
            "name": "data.csv",
            "path": "input/data.csv",
            "type": "file",
        },
    ]

    with patch(
        "app.agent.nodes.workspace_inspection.list_workspace_files",
        return_value=entries,
    ) as mock_list:
        result = inspect_workspace(base_state)

    assert len(result["workspace_files"]) == 2
    assert result["workspace_files"][0]["name"] == "report.txt"
    assert result["workspace_files"][0]["path"] == "input/report.txt"
    assert result["workspace_files"][1]["name"] == "data.csv"
    assert result["status"] == "workspace_inspected"
    assert result["error"] is None

    mock_list.assert_called_once_with(
        user_id="user_a",
        relative_directory="input",
    )


def test_inspect_workspace_uses_user_id_from_state(
    base_state: AgentState,
):
    with patch(
        "app.agent.nodes.workspace_inspection.list_workspace_files",
        return_value=[],
    ) as mock_list:
        inspect_workspace(base_state)

    mock_list.assert_called_once_with(
        user_id="user_a",
        relative_directory="input",
    )


def test_inspect_workspace_rejects_empty_user_id(
    base_state: AgentState,
):
    base_state["user_id"] = "   "

    with pytest.raises(
        ValueError,
        match="user_id cannot be empty",
    ):
        inspect_workspace(base_state)


def test_inspect_workspace_propagates_filesystem_error(
    base_state: AgentState,
):
    with patch(
        "app.agent.nodes.workspace_inspection.list_workspace_files",
        side_effect=FileNotFoundError(
            "Directory does not exist: input"
        ),
    ):
        with pytest.raises(
            FileNotFoundError,
            match="Directory does not exist",
        ):
            inspect_workspace(base_state)


def test_inspect_workspace_rejects_invalid_file_metadata(
    base_state: AgentState,
):
    invalid_entries = [
        {
            "name": "report.txt",
            "path": "input/report.txt",
            "type": "unknown",
        }
    ]

    with patch(
        "app.agent.nodes.workspace_inspection.list_workspace_files",
        return_value=invalid_entries,
    ):
        with pytest.raises(ValueError):
            inspect_workspace(base_state)


def test_inspect_workspace_does_not_modify_user_id(
    base_state: AgentState,
):
    original_user_id = base_state["user_id"]

    with patch(
        "app.agent.nodes.workspace_inspection.list_workspace_files",
        return_value=[],
    ):
        inspect_workspace(base_state)

    assert base_state["user_id"] == original_user_id
