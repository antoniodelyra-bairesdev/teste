"""Fixing multiple heads

Revision ID: 2e755a2bf6eb
Revises: 106230e7a116, f145d8fb0689
Create Date: 2025-07-10 14:24:48.825045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e755a2bf6eb'
down_revision: Union[str, None] = ('106230e7a116', 'f145d8fb0689')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
