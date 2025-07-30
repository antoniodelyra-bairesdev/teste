"""Fixing multiple heads

Revision ID: 0b9b325ad2cb
Revises: 338eb8f993c8, 6a92660baab5
Create Date: 2025-07-23 00:27:13.938786

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b9b325ad2cb'
down_revision: Union[str, None] = ('338eb8f993c8', '6a92660baab5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
