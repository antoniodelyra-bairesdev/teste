"""merging differing heads 7e4174519044 ab0ecdfc1b9a

Revision ID: 9f571bb19594
Revises: ab0ecdfc1b9a, 7e4174519044
Create Date: 2025-06-11 16:21:36.079432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f571bb19594'
down_revision: Union[str, None] = ('ab0ecdfc1b9a', '7e4174519044')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
