from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.db.models import Artifact, Workspace
from app.db.session import SessionLocal
from app.workspace.manager import WorkspaceManager


class ArtifactService:
    """Create and persist artifacts inside isolated user workspaces."""

    def __init__(
        self,
        workspace_manager: WorkspaceManager | None = None,
    ) -> None:
        self.workspace_manager = (
            workspace_manager or WorkspaceManager()
        )

    def validate_filename(self, filename: str) -> str:
        """Validate a final artifact filename."""

        if not filename or not filename.strip():
            raise ValueError("Artifact filename cannot be empty.")

        filename = filename.strip()

        path = Path(filename)

        if path.name != filename:
            raise ValueError(
                "Artifact filename must be a single filename."
            )

        if filename in {".", ".."}:
            raise ValueError("Invalid artifact filename.")

        if "/" in filename or "\\" in filename:
            raise ValueError(
                "Artifact filename cannot contain path separators."
            )

        if len(filename) > 255:
            raise ValueError(
                "Artifact filename exceeds maximum length."
            )

        return filename

    def deliver(
        self,
        user_id: str,
        filename: str,
        content: str,
    ) -> dict[str, str]:
        """Write an artifact to the user's delivered directory."""

        filename = self.validate_filename(filename)

        if not content or not content.strip():
            raise ValueError(
                "Artifact content cannot be empty."
            )

        relative_path = f"delivered/{filename}"

        path = self.workspace_manager.validate_write_path(
            user_id=user_id,
            relative_path=relative_path,
        )

        user_root = self.workspace_manager.user_root(user_id)

        if not user_root.exists():
            self.workspace_manager.initialize_user_workspace(
                user_id
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Idempotent delivery:
        # writing the same approved artifact again produces
        # the same filesystem result rather than accumulating files.
        path.write_text(
            content,
            encoding="utf-8",
        )

        return {
            "path": path.relative_to(user_root).as_posix(),
            "filename": filename,
            "status": "delivered",
        }


async def persist_artifact(
    *,
    user_id: str,
    filename: str,
    relative_path: str,
    artifact_type: str,
    status: str = "created",
) -> Artifact:
    """Persist artifact metadata in PostgreSQL."""

    async with SessionLocal() as session:
        result = await session.execute(
            select(Workspace).where(
                Workspace.user_id == user_id
            )
        )

        workspace = result.scalar_one_or_none()

        if workspace is None:
            raise ValueError(
                f"Workspace does not exist for user: {user_id}"
            )

        # Avoid duplicate metadata rows for the same delivered artifact.
        existing_result = await session.execute(
            select(Artifact).where(
                Artifact.workspace_id == workspace.id,
                Artifact.relative_path == relative_path,
            )
        )

        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            existing.filename = filename
            existing.artifact_type = artifact_type
            existing.status = status

            await session.commit()
            await session.refresh(existing)

            return existing

        artifact = Artifact(
            id=str(uuid4()),
            workspace_id=workspace.id,
            filename=filename,
            relative_path=relative_path,
            artifact_type=artifact_type,
            status=status,
        )

        session.add(artifact)

        await session.commit()
        await session.refresh(artifact)

        return artifact
