"""ehp-db-2025-6-6-16-46-52

Revision ID: 4e9f47ffca44
Revises: 0b877e87b256
Create Date: 2025-06-06 16:46:52.780509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e9f47ffca44'
down_revision: Union[str, None] = '0b877e87b256'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
