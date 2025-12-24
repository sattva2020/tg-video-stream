"""add_error_message_to_channel

Revision ID: 3214ca479b93
Revises: m1n2o3p4q5r6
Create Date: 2025-12-22 15:24:04.326151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '3214ca479b93'
down_revision: Union[str, None] = 'm1n2o3p4q5r6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('channels', sa.Column('error_message', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('channels', 'error_message')
