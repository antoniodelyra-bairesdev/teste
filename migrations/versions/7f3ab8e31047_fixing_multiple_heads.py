"""Fixing multiple heads

Revision ID: 7f3ab8e31047
Revises: 182ea29eabf5, 97403192758c
Create Date: 2025-07-09 13:30:25.120560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3ab8e31047'
down_revision: Union[str, None] = ('182ea29eabf5', '97403192758c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
