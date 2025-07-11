"""ehp-db-2025-7-9-10-25-19

Revision ID: 59f18bdce0f7
Revises: 9a5c5172b3a0
Create Date: 2025-07-09 10:25:20.404055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59f18bdce0f7'
down_revision: Union[str, None] = '9a5c5172b3a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add email change fields to authentication table
    op.add_column('authentication', sa.Column('auth_tx_pending_email', sa.String(300), nullable=True))
    op.add_column('authentication', sa.Column('auth_tx_email_change_token', sa.String(255), nullable=True))
    op.add_column('authentication', sa.Column('auth_dt_email_change_token_expires', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove email change fields from authentication table
    op.drop_column('authentication', 'auth_dt_email_change_token_expires')
    op.drop_column('authentication', 'auth_tx_email_change_token')
    op.drop_column('authentication', 'auth_tx_pending_email')
