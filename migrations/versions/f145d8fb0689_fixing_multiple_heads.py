"""Fixing multiple heads

Revision ID: f145d8fb0689
Revises: 59f18bdce0f7, 7a58aaa176c3
Create Date: 2025-07-10 11:10:11.821482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f145d8fb0689'
down_revision: Union[str, None] = ('59f18bdce0f7', '7a58aaa176c3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
