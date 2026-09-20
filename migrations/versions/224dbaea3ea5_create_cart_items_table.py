"""Create cart items table

Revision ID: 224dbaea3ea5
Revises: c804ca0d785a
Create Date: 2026-09-15 14:25:22.453349

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "224dbaea3ea5"
down_revision: Union[str, Sequence[str], None] = "c804ca0d785a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cart_items",
        sa.Column(
            "user_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "movie_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["movie_id"],
            ["movies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id",
            "movie_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table(
        "cart_items",
    )
