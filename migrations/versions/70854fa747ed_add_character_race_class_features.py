"""add character race/class features

Revision ID: 70854fa747ed
Revises: 9a7c6e51d2b0
Create Date: 2026-03-07 17:20:41.042155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '70854fa747ed'
down_revision: Union[str, Sequence[str], None] = '9a7c6e51d2b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column(
            "race_features",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "characters",
        sa.Column(
            "class_features",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("characters", "class_features")
    op.drop_column("characters", "race_features")
