"""Add activity_events table for system monitoring

Revision ID: 015_add_activity_events
Revises: 014_add_google_auth_to_users
Create Date: 2025-01-15 12:00:00.000000

Spec: 015-real-system-monitoring
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '015_add_activity_events'
down_revision: Union[str, None] = '014_add_google_auth_to_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаёт таблицу activity_events для хранения событий активности."""
    op.create_table(
        'activity_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('details', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы для эффективных запросов
    op.create_index(
        'idx_activity_events_created_at', 
        'activity_events', 
        ['created_at'],
        postgresql_using='btree'
    )
    op.create_index(
        'idx_activity_events_type', 
        'activity_events', 
        ['type']
    )
    op.create_index(
        'idx_activity_events_type_created', 
        'activity_events', 
        ['type', 'created_at']
    )


def downgrade() -> None:
    """Удаляет таблицу activity_events."""
    op.drop_index('idx_activity_events_type_created', table_name='activity_events')
    op.drop_index('idx_activity_events_type', table_name='activity_events')
    op.drop_index('idx_activity_events_created_at', table_name='activity_events')
    op.drop_table('activity_events')
