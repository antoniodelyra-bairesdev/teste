"""Fixing multiple heads

Revision ID: c975579b9924
Revises: 5680bf2d3c61, c7c42f602d1d
Create Date: 2025-07-21 14:22:18.765829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c975579b9924'
down_revision: Union[str, None] = ('5680bf2d3c61', 'c7c42f602d1d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
