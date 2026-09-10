import asyncio
import selectors

import pytest
from sqlalchemy import select

from app.agent.models import ArtifactReference
from app.agent.nodes.artifact_delivery import deliver_artifact
from app.artifacts.service import ArtifactService, persist_artifact
from app.db.models import Artifact
from app.db.session import SessionLocal
from app.workspace.manager import WorkspaceManager


def run_async(coro):
    """Run async database operations with a Windows-compatible event loop."""
    loop_factory = lambda: asyncio.SelectorEventLoop(
        selectors.SelectSelector()
    )
    return asyncio.run(coro, loop_factory=loop_factory)


@pytest.fixture
def workspace_root(tmp_path, monkeypatch):
    """Use an isolated temporary filesystem root for each test."""
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "workspace_root", tmp_path)

    return tmp_path


def test_artifact_delivery_writes_file_to_user_workspace(workspace_root):
    manager = WorkspaceManager()
    service = ArtifactService(workspace_manager=manager)

    result = service.deliver(
        user_id="user_a",
        filename="report.md",
        content="# Workspace Report\n\nAnalysis complete.",
    )

    expected = (
        workspace_root
        / "user_a"
        / "delivered"
        / "report.md"
    )

    assert result["filename"] == "report.md"
    assert result["path"] == "delivered/report.md"
    assert result["status"] == "delivered"

    assert expected.exists()
    assert expected.is_file()
    assert expected.read_text(encoding="utf-8") == (
        "# Workspace Report\n\nAnalysis complete."
    )


def test_artifact_delivery_rejects_path_traversal(workspace_root):
    manager = WorkspaceManager()
    service = ArtifactService(workspace_manager=manager)

    malicious_filenames = [
        "../secret.md",
        "..\\secret.md",
        "nested/report.md",
        "nested\\report.md",
        "/tmp/evil.md",
        "\\tmp\\evil.md",
        "..",
        ".",
    ]

    for filename in malicious_filenames:
        with pytest.raises(ValueError):
            service.deliver(
                user_id="user_a",
                filename=filename,
                content="malicious content",
            )

    assert not (workspace_root / "secret.md").exists()
    assert not (
        workspace_root / "user_a" / "secret.md"
    ).exists()


def test_artifact_delivery_rejects_empty_content(workspace_root):
    manager = WorkspaceManager()
    service = ArtifactService(workspace_manager=manager)

    with pytest.raises(ValueError):
        service.deliver(
            user_id="user_a",
            filename="report.md",
            content="",
        )

    with pytest.raises(ValueError):
        service.deliver(
            user_id="user_a",
            filename="report.md",
            content="   ",
        )


def test_artifact_delivery_isolated_between_users(workspace_root):
    manager = WorkspaceManager()
    service = ArtifactService(workspace_manager=manager)

    service.deliver(
        user_id="user_a",
        filename="report.md",
        content="USER A SECRET",
    )

    user_a_file = (
        workspace_root
        / "user_a"
        / "delivered"
        / "report.md"
    )

    user_b_file = (
        workspace_root
        / "user_b"
        / "delivered"
        / "report.md"
    )

    assert user_a_file.exists()
    assert user_a_file.read_text(encoding="utf-8") == "USER A SECRET"
    assert not user_b_file.exists()


def test_artifact_delivery_node_returns_artifact_reference(
    workspace_root,
    monkeypatch,
):
    manager = WorkspaceManager()

    monkeypatch.setattr(
        "app.agent.nodes.artifact_delivery.artifact_service",
        ArtifactService(workspace_manager=manager),
    )

    state = {
        "user_id": "user_a",
        "generated_output": "# Generated Report\n\nFinal output.",
    }

    result = deliver_artifact(state)

    assert isinstance(
        result["generated_artifact"],
        ArtifactReference,
    )

    artifact = result["generated_artifact"]

    assert artifact.filename == "report.md"
    assert artifact.relative_path == "delivered/report.md"
    assert artifact.artifact_type == "markdown_report"
    assert artifact.status == "delivered"


def test_artifact_metadata_persists_in_postgresql():
    async def scenario():
        user_id = "artifact_test_user"

        from app.db.repository.workspace import ensure_user_workspace

        workspace = await ensure_user_workspace(user_id)

        artifact = await persist_artifact(
            user_id=user_id,
            filename="report.md",
            relative_path="delivered/report.md",
            artifact_type="markdown_report",
            status="delivered",
        )

        assert artifact.workspace_id == workspace.id
        assert artifact.filename == "report.md"
        assert artifact.relative_path == "delivered/report.md"
        assert artifact.artifact_type == "markdown_report"
        assert artifact.status == "delivered"

        async with SessionLocal() as session:
            result = await session.execute(
                select(Artifact).where(
                    Artifact.id == artifact.id
                )
            )

            stored = result.scalar_one()

            assert stored.workspace_id == workspace.id
            assert stored.relative_path == "delivered/report.md"

    run_async(scenario())


def test_artifact_metadata_persistence_is_idempotent():
    async def scenario():
        user_id = "artifact_idempotent_user"

        from app.db.repository.workspace import ensure_user_workspace

        workspace = await ensure_user_workspace(user_id)

        first = await persist_artifact(
            user_id=user_id,
            filename="report.md",
            relative_path="delivered/report.md",
            artifact_type="markdown_report",
            status="delivered",
        )

        second = await persist_artifact(
            user_id=user_id,
            filename="report.md",
            relative_path="delivered/report.md",
            artifact_type="markdown_report",
            status="delivered",
        )

        assert first.id == second.id
        assert first.workspace_id == workspace.id

        async with SessionLocal() as session:
            result = await session.execute(
                select(Artifact).where(
                    Artifact.workspace_id == workspace.id,
                    Artifact.relative_path == "delivered/report.md",
                )
            )

            artifacts = result.scalars().all()

            assert len(artifacts) == 1

    run_async(scenario())
from unittest.mock import patch

from app.agent.models import ApprovalDecision
from app.agent.service import resume_agent


class FakeGraph:
    """Minimal graph double for testing resume_agent orchestration."""

    def stream(self, input_data, config, stream_mode):
        yield {
            "deliver_artifact": {
                "generated_artifact": {
                    "filename": "report.md",
                    "relative_path": "delivered/report.md",
                    "artifact_type": "markdown_report",
                    "status": "delivered",
                },
                "generated_output": "# Approved Report",
                "validation_result": {
                    "valid": True,
                    "issues": [],
                },
                "approval_decision": "approve",
                "status": "delivered",
            }
        }

    def get_state(self, config):
        class State:
            values = {
                "generated_output": "# Approved Report",
                "generated_artifact": {
                    "filename": "report.md",
                    "relative_path": "delivered/report.md",
                    "artifact_type": "markdown_report",
                    "status": "delivered",
                },
                "validation_result": {
                    "valid": True,
                    "issues": [],
                },
                "approval_decision": "approve",
                "approval_feedback": None,
                "approval_request": None,
                "selected_skills": [],
                "findings": [],
                "status": "completed",
            }

        return State()


def test_resume_agent_persists_approved_artifact():
    decision = ApprovalDecision(
        decision="approve",
    )

    with patch(
        "app.agent.service._ensure_user_workspace"
    ), patch(
        "app.agent.service.get_graph",
        return_value=FakeGraph(),
    ), patch(
        "app.agent.service._persist_generated_artifact"
    ) as persist_mock:

        result = resume_agent(
            user_id="user_a",
            thread_id="thread-123",
            decision=decision,
        )

    assert result["generated_artifact"]["filename"] == "report.md"
    assert result["generated_artifact"]["relative_path"] == (
        "delivered/report.md"
    )
    assert result["approval_decision"] == "approve"

    persist_mock.assert_called_once()

    call_kwargs = persist_mock.call_args.kwargs

    assert call_kwargs["user_id"] == "user_a"
    assert call_kwargs["response"]["generated_artifact"]["filename"] == (
        "report.md"
    )
