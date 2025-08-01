"""ehp-db-2025-7-8-7-53-52

Revision ID: 106230e7a116
Revises: c778e605ca80
Create Date: 2025-07-08 07:53:52.937765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '106230e7a116'
down_revision: Union[str, None] = '9a5c5172b3a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('news_category',
    sa.Column('ncat_cd_id', sa.Integer(), nullable=False),
    sa.Column('ncat_tx_name', sa.String(length=150), nullable=False),
    sa.PrimaryKeyConstraint('ncat_cd_id')
    )
    op.add_column('user', sa.Column('user_js_preferred_news_categories', sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'user_js_preferred_news_categories')
    op.drop_table('news_category')
    # ### end Alembic commands ###
