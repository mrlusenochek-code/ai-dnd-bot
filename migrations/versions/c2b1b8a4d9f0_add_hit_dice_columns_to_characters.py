"""Add PHB hit dice columns to characters

Revision ID: c2b1b8a4d9f0
Revises: 81f0f0157862
Create Date: 2026-03-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2b1b8a4d9f0"
down_revision: Union[str, Sequence[str], None] = "81f0f0157862"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column("hit_die", sa.Integer(), nullable=False, server_default=sa.text("8")),
    )
    op.add_column(
        "characters",
        sa.Column("hit_dice_max", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "characters",
        sa.Column("hit_dice_remaining", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )

    op.execute(
        """
        UPDATE characters
        SET hit_dice_max = GREATEST(COALESCE(level, 1), 1)
        """
    )
    op.execute(
        """
        UPDATE characters
        SET hit_dice_remaining = hit_dice_max
        """
    )
    op.execute(
        """
        UPDATE characters
        SET hit_die = CASE
            WHEN LOWER(TRIM(COALESCE(class_kit, ''))) = 'fighter' THEN 10
            WHEN LOWER(TRIM(COALESCE(class_kit, ''))) = 'rogue' THEN 8
            WHEN LOWER(TRIM(COALESCE(class_kit, ''))) = 'ranger' THEN 10
            WHEN LOWER(TRIM(COALESCE(class_kit, ''))) = 'mage' THEN 6
            WHEN LOWER(TRIM(COALESCE(class_kit, ''))) = 'cleric' THEN 8
            WHEN LOWER(TRIM(COALESCE(class_kit, ''))) = 'bard' THEN 8
            WHEN LOWER(TRIM(COALESCE(class_skin, ''))) = 'fighter' THEN 10
            WHEN LOWER(TRIM(COALESCE(class_skin, ''))) = 'rogue' THEN 8
            WHEN LOWER(TRIM(COALESCE(class_skin, ''))) = 'ranger' THEN 10
            WHEN LOWER(TRIM(COALESCE(class_skin, ''))) = 'mage' THEN 6
            WHEN LOWER(TRIM(COALESCE(class_skin, ''))) = 'cleric' THEN 8
            WHEN LOWER(TRIM(COALESCE(class_skin, ''))) = 'bard' THEN 8
            ELSE 8
        END
        """
    )


def downgrade() -> None:
    op.drop_column("characters", "hit_dice_remaining")
    op.drop_column("characters", "hit_dice_max")
    op.drop_column("characters", "hit_die")
