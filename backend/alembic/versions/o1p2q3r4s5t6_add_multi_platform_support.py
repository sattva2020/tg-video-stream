"""add multi-platform support to playlist_items

Revision ID: o1p2q3r4s5t6
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'o1p2q3r4s5t6'
down_revision: Union[str, None] = 'n1o2p3q4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for multi-platform video source support
    # Using batch_alter_table for SQLite compatibility
    with op.batch_alter_table('playlist_items', schema=None) as batch_op:
        # Thumbnail URL for video preview
        batch_op.add_column(sa.Column('thumbnail_url', sa.String(), nullable=True))

        # JSON metadata for platform-specific data (video IDs, channel info, etc.)
        # Uses JSON on SQLite, JSONB on PostgreSQL
        batch_op.add_column(sa.Column('source_metadata', sa.JSON(), nullable=True))

        # Live stream flag for HLS/DASH streams
        batch_op.add_column(sa.Column('is_live', sa.Boolean(), server_default=sa.text('false'), nullable=False))

        # Authentication flag for cloud storage sources
        batch_op.add_column(sa.Column('requires_auth', sa.Boolean(), server_default=sa.text('false'), nullable=False))

        # Encrypted token for cloud storage access
        batch_op.add_column(sa.Column('auth_token', sa.String(), nullable=True))

        # Preferred video quality
        batch_op.add_column(sa.Column('quality', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('playlist_items', schema=None) as batch_op:
        batch_op.drop_column('quality')
        batch_op.drop_column('auth_token')
        batch_op.drop_column('requires_auth')
        batch_op.drop_column('is_live')
        batch_op.drop_column('source_metadata')
        batch_op.drop_column('thumbnail_url')
