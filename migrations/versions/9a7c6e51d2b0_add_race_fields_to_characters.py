"""Add race_kit and race_skin to characters

Revision ID: 9a7c6e51d2b0
Revises: 4f6e2a91ab3c
Create Date: 2026-03-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a7c6e51d2b0"
down_revision: Union[str, Sequence[str], None] = "4f6e2a91ab3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("race_kit", sa.String(length=40), nullable=False, server_default=sa.text("'human'")),
    )
    op.add_column(
        "characters",
        sa.Column("race_skin", sa.String(length=60), nullable=False, server_default=sa.text("'Human'")),
    )


def downgrade() -> None:
    op.drop_column("characters", "race_skin")
    op.drop_column("characters", "race_kit")
