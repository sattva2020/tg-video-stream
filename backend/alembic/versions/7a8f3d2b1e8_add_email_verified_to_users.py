"""Add email_verified to users table

Revision ID: 7a8f3d2b1e8
Revises: 615a2b1e9c2b
Create Date: 2025-11-19 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7a8f3d2b1e8'
down_revision: Union[str, None] = '615a2b1e9c2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('users', 'email_verified')
