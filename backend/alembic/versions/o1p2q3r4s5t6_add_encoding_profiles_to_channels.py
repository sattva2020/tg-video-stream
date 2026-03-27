"""Add encoding profiles to channels

Revision ID: o1p2q3r4s5t6
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'o1p2q3r4s5t6'
down_revision: Union[str, None] = 'n1o2p3q4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('channels', sa.Column('video_codec', sa.String(), server_default='h264', nullable=True))
    op.add_column('channels', sa.Column('audio_codec', sa.String(), server_default='aac', nullable=True))
    op.add_column('channels', sa.Column('video_bitrate', sa.Integer(), nullable=True))
    op.add_column('channels', sa.Column('audio_bitrate', sa.Integer(), nullable=True))
    op.add_column('channels', sa.Column('resolution', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('channels', 'resolution')
    op.drop_column('channels', 'audio_bitrate')
    op.drop_column('channels', 'video_bitrate')
    op.drop_column('channels', 'audio_codec')
    op.drop_column('channels', 'video_codec')
