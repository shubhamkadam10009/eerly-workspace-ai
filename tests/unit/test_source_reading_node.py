from unittest.mock import patch

import pytest

from app.agent.nodes.source_reading import read_sources
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
        "workspace_files": [
            {
                "name": "report.txt",
                "path": "input/report.txt",
                "type": "file",
            },
            {
                "name": "notes.md",
                "path": "input/notes.md",
                "type": "file",
            },
            {
                "name": "archive",
                "path": "input/archive",
                "type": "directory",
            },
        ],
        "source_contents": {},
        "findings": [],
        "generated_artifact": None,
        "validation_result": None,
        "status": "workspace_inspected",
        "error": None,
    }


def test_read_sources_reads_files(
    base_state: AgentState,
):
    def fake_read(
        user_id: str,
        relative_path: str,
    ) -> str:
        assert user_id == "user_a"

        contents = {
            "input/report.txt": "Revenue increased by 18%.",
            "input/notes.md": "Management meeting notes.",
        }

        return contents[relative_path]

    with patch(
        "app.agent.nodes.source_reading.read_workspace_file",
        side_effect=fake_read,
    ) as mock_read:
        result = read_sources(base_state)

    assert result["source_contents"] == {
        "input/report.txt": "Revenue increased by 18%.",
        "input/notes.md": "Management meeting notes.",
    }

    assert result["status"] == "sources_read"
    assert result["error"] is None

    assert mock_read.call_count == 2


def test_read_sources_uses_authenticated_user_id(
    base_state: AgentState,
):
    with patch(
        "app.agent.nodes.source_reading.read_workspace_file",
        return_value="content",
    ) as mock_read:
        read_sources(base_state)

    calls = mock_read.call_args_list

    assert calls[0].kwargs["user_id"] == "user_a"
    assert calls[1].kwargs["user_id"] == "user_a"


def test_read_sources_skips_directories(
    base_state: AgentState,
):
    with patch(
        "app.agent.nodes.source_reading.read_workspace_file",
        return_value="content",
    ) as mock_read:
        result = read_sources(base_state)

    assert "input/archive" not in result["source_contents"]

    paths_read = [
        call.kwargs["relative_path"]
        for call in mock_read.call_args_list
    ]

    assert "input/report.txt" in paths_read
    assert "input/notes.md" in paths_read
    assert "input/archive" not in paths_read


def test_read_sources_returns_empty_when_no_files():
    state: AgentState = {
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
        "status": "workspace_inspected",
        "error": None,
    }

    with patch(
        "app.agent.nodes.source_reading.read_workspace_file",
    ) as mock_read:
        result = read_sources(state)

    assert result["source_contents"] == {}
    assert result["status"] == "sources_read"
    mock_read.assert_not_called()


def test_read_sources_rejects_empty_user_id(
    base_state: AgentState,
):
    base_state["user_id"] = "   "

    with pytest.raises(
        ValueError,
        match="user_id cannot be empty",
    ):
        read_sources(base_state)


def test_read_sources_propagates_filesystem_error(
    base_state: AgentState,
):
    with patch(
        "app.agent.nodes.source_reading.read_workspace_file",
        side_effect=FileNotFoundError(
            "File does not exist: input/report.txt"
        ),
    ):
        with pytest.raises(
            FileNotFoundError,
            match="File does not exist",
        ):
            read_sources(base_state)


def test_read_sources_does_not_modify_workspace_files(
    base_state: AgentState,
):
    original_files = list(base_state["workspace_files"])

    with patch(
        "app.agent.nodes.source_reading.read_workspace_file",
        return_value="content",
    ):
        read_sources(base_state)

    assert base_state["workspace_files"] == original_files
