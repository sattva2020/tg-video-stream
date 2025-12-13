"""add last_login to users

Revision ID: d2d1a1551516
Revises: 51380808ac02
Create Date: 2025-12-13 19:46:57.869505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2d1a1551516'
down_revision: Union[str, None] = '51380808ac02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_login')
