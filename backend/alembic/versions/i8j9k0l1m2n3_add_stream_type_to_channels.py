"""Add stream_type to channels

Revision ID: i8j9k0l1m2n3
Revises: h7i8j9k0l1m2
Create Date: 2025-12-08 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i8j9k0l1m2n3'
down_revision: Union[str, None] = ('h7i8j9k0l1m2', '015_add_activity_events', 'b7c8d9e0f1g')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('channels', sa.Column('stream_type', sa.String(), server_default='video', nullable=True))


def downgrade() -> None:
    op.drop_column('channels', 'stream_type')
