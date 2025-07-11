"""ehp-db-2025-7-10-16-32-14

Revision ID: 91b3077cacbe
Revises: 2e755a2bf6eb
Create Date: 2025-07-10 16:32:16.360822

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91b3077cacbe'
down_revision: Union[str, None] = '2e755a2bf6eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert seed data for NewsCategory
    op.bulk_insert(
        sa.table('news_category',
                 sa.column('ncat_cd_id', sa.Integer),
                 sa.column('ncat_tx_name', sa.String)
                 ),
        [
            {'ncat_cd_id': 1, 'ncat_tx_name': 'Politics'},
            {'ncat_cd_id': 2, 'ncat_tx_name': 'Economy'},
            {'ncat_cd_id': 3, 'ncat_tx_name': 'Technology'},
            {'ncat_cd_id': 4, 'ncat_tx_name': 'Sports'},
            {'ncat_cd_id': 5, 'ncat_tx_name': 'Health'}
        ]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove seed data for NewsCategory
    op.execute("DELETE FROM news_category WHERE ncat_cd_id IN (1, 2, 3, 4, 5, 6, 7, 8)")
