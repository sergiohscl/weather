"""add city to weather insights

Revision ID: b26f2da59193
Revises: 738d1c8f872e
Create Date: 2026-08-19 16:34:11.328938

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b26f2da59193'
down_revision: Union[str, Sequence[str], None] = '738d1c8f872e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        'weather_insights',
        sa.Column(
            'city',
            sa.String(length=100),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column(
        'weather_insights',
        'city',
    )
