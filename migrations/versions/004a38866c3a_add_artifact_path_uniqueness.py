"""add artifact path uniqueness

Revision ID: 004a38866c3a
Revises: f7ccfc3d2e7f
Create Date: 2026-09-10 19:50:41.050902

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "004a38866c3a"
down_revision: Union[str, Sequence[str], None] = "f7ccfc3d2e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database-level uniqueness for artifact paths."""
    op.create_unique_constraint(
        "uq_artifacts_workspace_relative_path",
        "artifacts",
        ["workspace_id", "relative_path"],
    )


def downgrade() -> None:
    """Remove database-level uniqueness for artifact paths."""
    op.drop_constraint(
        "uq_artifacts_workspace_relative_path",
        "artifacts",
        type_="unique",
    )
