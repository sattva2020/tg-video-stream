"""add_analytics_tables

Revision ID: g6h7i8j9k0l1
Revises: f5e6d7c8b9a0
Create Date: 2025-01-07 12:00:00.000000

Добавляет таблицы для аналитики:
- track_plays: записи о воспроизведении треков
- monthly_analytics: агрегированные данные за месяц
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'g6h7i8j9k0l1'
down_revision: Union[str, None] = 'f5e6d7c8b9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create track_plays table
    op.create_table(
        'track_plays',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('playlist_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('played_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('listeners_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['playlist_item_id'], ['playlist_items.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_track_plays_played_at', 'track_plays', ['played_at'])
    op.create_index('idx_track_plays_playlist_item', 'track_plays', ['playlist_item_id'])
    
    # Create monthly_analytics table
    op.create_table(
        'monthly_analytics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('total_plays', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_duration_seconds', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('peak_listeners', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_listeners', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('unique_tracks', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('month', name='uq_monthly_analytics_month')
    )
    op.create_index('idx_monthly_analytics_month', 'monthly_analytics', ['month'])


def downgrade() -> None:
    op.drop_index('idx_monthly_analytics_month', table_name='monthly_analytics')
    op.drop_table('monthly_analytics')
    op.drop_index('idx_track_plays_playlist_item', table_name='track_plays')
    op.drop_index('idx_track_plays_played_at', table_name='track_plays')
    op.drop_table('track_plays')
