from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.db.models import User, Workspace
from app.db.session import SessionLocal
from app.workspace.manager import WorkspaceManager


async def ensure_user_workspace(
    user_id: str,
    workspace_manager: WorkspaceManager | None = None,
) -> Workspace:
    """
    Ensure that the authenticated user has both:
    1. a PostgreSQL User row,
    2. a PostgreSQL Workspace row,
    3. a corresponding filesystem workspace.
    """

    if not user_id or not user_id.strip():
        raise ValueError("user_id is required")

    manager = workspace_manager or WorkspaceManager()

    # Validate the identity before using it as a filesystem path.
    manager.validate_user_id(user_id)

    # Ensure the physical workspace exists.
    manager.initialize_user_workspace(user_id)

    async with SessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )

        user = user_result.scalar_one_or_none()

        if user is None:
            user = User(id=user_id)
            session.add(user)
            await session.flush()

        workspace_result = await session.execute(
            select(Workspace).where(
                Workspace.user_id == user_id
            )
        )

        workspace = workspace_result.scalar_one_or_none()

        if workspace is None:
            workspace = Workspace(
                id=str(uuid4()),
                user_id=user_id,
            )
            session.add(workspace)

        await session.commit()
        await session.refresh(workspace)

        return workspace
