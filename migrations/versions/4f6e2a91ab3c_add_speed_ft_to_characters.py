"""Add speed_ft to characters

Revision ID: 4f6e2a91ab3c
Revises: c2b1b8a4d9f0
Create Date: 2026-03-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f6e2a91ab3c"
down_revision: Union[str, Sequence[str], None] = "c2b1b8a4d9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("speed_ft", sa.Integer(), nullable=False, server_default=sa.text("30")),
    )


def downgrade() -> None:
    op.drop_column("characters", "speed_ft")
