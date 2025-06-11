"""ehp-db-2025-6-6-16-47-37

Revision ID: 05165e3052a4
Revises: 4e9f47ffca44
Create Date: 2025-06-06 16:47:37.550545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05165e3052a4'
down_revision: Union[str, None] = '4e9f47ffca44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
