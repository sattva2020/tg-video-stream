"""add totp fields to users

Revision ID: n1o2p3q4r5s6
Revises: d2d1a1551516
Create Date: 2025-12-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n1o2p3q4r5s6'
down_revision: Union[str, None] = '3214ca479b93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('totp_secret', sa.String(), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
