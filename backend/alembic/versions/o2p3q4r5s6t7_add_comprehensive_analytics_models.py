"""add_comprehensive_analytics_models

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 20:00:00.000000

Добавляет таблицы для комплексной аналитики:
- engagement_events: события вовлеченности (сообщения чата, реакции, комментарии)
- viewer_sessions: сессии просмотра и точки отказа (drop-off points)
- buffering_percentage: поле в stream_quality_history для отслеживания буферизации
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'o2p3q4r5s6t7'
down_revision: Union[str, None] = 'n1o2p3q4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create engagement_events table
    op.create_table(
        'engagement_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False, comment='Тип события: chat_message, reaction, comment'),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Ссылка на channels.id'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='Telegram user ID'),
        sa.Column('username', sa.String(length=255), nullable=True, comment='Имя пользователя'),
        sa.Column('content', sa.Text(), nullable=True, comment='Содержимое события'),
        sa.Column('metadata', postgresql.JSON(), nullable=True, comment='Дополнительные метаданные'),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='Время события'),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_engagement_events_event_type', 'engagement_events', ['event_type'])
    op.create_index('idx_engagement_events_channel_id', 'engagement_events', ['channel_id'])
    op.create_index('idx_engagement_events_user_id', 'engagement_events', ['user_id'])
    op.create_index('idx_engagement_events_event_timestamp', 'engagement_events', ['event_timestamp'])
    op.create_index('idx_engagement_events_type_timestamp', 'engagement_events', ['event_type', 'event_timestamp'])
    op.create_index('idx_engagement_events_channel_timestamp', 'engagement_events', ['channel_id', 'event_timestamp'])
    op.create_index('idx_engagement_events_user_timestamp', 'engagement_events', ['user_id', 'event_timestamp'])

    # Create viewer_sessions table
    op.create_table(
        'viewer_sessions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Уникальный идентификатор сессии'),
        sa.Column('playlist_item_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Ссылка на playlist_items.id'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='Идентификатор пользователя'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='Время начала сессии'),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True, comment='Время окончания сессии'),
        sa.Column('drop_off_position_seconds', sa.Integer(), nullable=True, comment='Точка отказа в секундах'),
        sa.Column('content_duration_seconds', sa.Integer(), nullable=True, comment='Полная длительность контента'),
        sa.Column('completion_percentage', sa.Integer(), nullable=True, comment='Процент просмотра'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IP-адрес пользователя'),
        sa.Column('user_agent', sa.String(length=255), nullable=True, comment='User Agent'),
        sa.ForeignKeyConstraint(['playlist_item_id'], ['playlist_items.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_viewer_sessions_session_id')
    )
    op.create_index('idx_viewer_sessions_session_id', 'viewer_sessions', ['session_id'])
    op.create_index('idx_viewer_sessions_playlist_item_id', 'viewer_sessions', ['playlist_item_id'])
    op.create_index('idx_viewer_sessions_user_id', 'viewer_sessions', ['user_id'])
    op.create_index('idx_viewer_sessions_started_at', 'viewer_sessions', ['started_at'])

    # Add buffering_percentage column to stream_quality_history
    op.add_column('stream_quality_history', sa.Column('buffering_percentage', sa.Float(), nullable=True, comment='Процент буферизации (0-100)'))


def downgrade() -> None:
    # Remove buffering_percentage column from stream_quality_history
    op.drop_column('stream_quality_history', 'buffering_percentage')

    # Drop viewer_sessions table
    op.drop_index('idx_viewer_sessions_started_at', table_name='viewer_sessions')
    op.drop_index('idx_viewer_sessions_user_id', table_name='viewer_sessions')
    op.drop_index('idx_viewer_sessions_playlist_item_id', table_name='viewer_sessions')
    op.drop_index('idx_viewer_sessions_session_id', table_name='viewer_sessions')
    op.drop_table('viewer_sessions')

    # Drop engagement_events table
    op.drop_index('idx_engagement_events_user_timestamp', table_name='engagement_events')
    op.drop_index('idx_engagement_events_channel_timestamp', table_name='engagement_events')
    op.drop_index('idx_engagement_events_type_timestamp', table_name='engagement_events')
    op.drop_index('idx_engagement_events_event_timestamp', table_name='engagement_events')
    op.drop_index('idx_engagement_events_user_id', table_name='engagement_events')
    op.drop_index('idx_engagement_events_channel_id', table_name='engagement_events')
    op.drop_index('idx_engagement_events_event_type', table_name='engagement_events')
    op.drop_table('engagement_events')
