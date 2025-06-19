"""ehp-db-2025-6-11-19-22-6

Revision ID: b8c1d81987e7
Revises: 9f571bb19594
Create Date: 2025-06-11 19:22:07.517769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c1d81987e7'
down_revision: Union[str, None] = '9f571bb19594'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
