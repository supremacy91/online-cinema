"""Add movie price

Revision ID: c804ca0d785a
Revises: 6239f60e3da5
Create Date: 2026-09-15 14:19:52.647889

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c804ca0d785a"
down_revision: Union[str, Sequence[str], None] = "6239f60e3da5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "movies",
        sa.Column(
            "price",
            sa.Numeric(
                precision=10,
                scale=2,
            ),
            nullable=True,
        ),
    )

    op.execute(
        "UPDATE movies SET price = 0.00 "
        "WHERE price IS NULL"
    )

    op.alter_column(
        "movies",
        "price",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(
        "movies",
        "price",
    )
