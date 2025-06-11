"""ehp-db-2025-6-6-16-48-53

Revision ID: 40049d758cec
Revises: 7e4174519044
Create Date: 2025-06-06 16:48:54.485046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40049d758cec'
down_revision: Union[str, None] = '7e4174519044'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
