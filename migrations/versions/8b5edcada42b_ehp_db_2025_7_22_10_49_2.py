"""ehp-db-2025-7-22-10-49-2

Revision ID: 8b5edcada42b
Revises: c975579b9924
Create Date: 2025-07-22 10:49:03.134446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8b5edcada42b'
down_revision: Union[str, None] = 'c975579b9924'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('user_bl_onboarding_complete', sa.Boolean(), nullable=False, server_default=sa.false()))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'user_bl_onboarding_complete')
    # ### end Alembic commands ###
