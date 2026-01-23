"""add_scheduled_reports

Revision ID: p5q6r7s8t9u0
Revises: o2p3q4r5s6t7
Create Date: 2026-01-23 22:00:00.000000

Добавляет таблицу для планирования отчётов:
- scheduled_reports: конфигурация автоматической генерации и отправки отчётов по email
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'p5q6r7s8t9u0'
down_revision: Union[str, None] = 'o2p3q4r5s6t7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create scheduled_reports table
    op.create_table(
        'scheduled_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False, comment='Тип отчёта: summary, listeners, top_tracks, engagement, stream_performance, content_insights'),
        sa.Column('frequency', sa.String(length=20), nullable=False, server_default='weekly', comment='Частота: daily, weekly, monthly'),
        sa.Column('period', sa.String(length=10), nullable=False, server_default='7d', comment='Период данных: 7d, 30d, 90d, all'),
        sa.Column('email', sa.String(length=255), nullable=False, comment='Email для отправки отчёта'),
        sa.Column('email_subject', sa.String(length=500), nullable=True, comment='Кастомная тема письма'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Активен ли отчёт'),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True, comment='Время следующего запуска'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True, comment='Время последнего запуска'),
        sa.Column('last_status', sa.String(length=20), nullable=True, comment='Статус последнего запуска: pending, sent, failed'),
        sa.Column('last_error', sa.String(length=1000), nullable=True, comment='Ошибка последнего запуска'),
        sa.Column('total_runs', sa.BigInteger(), nullable=False, server_default='0', comment='Всего запусков'),
        sa.Column('successful_runs', sa.BigInteger(), nullable=False, server_default='0', comment='Успешных запусков'),
        sa.Column('failed_runs', sa.BigInteger(), nullable=False, server_default='0', comment='Неудачных запусков'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='Кто создал'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scheduled_reports_active', 'scheduled_reports', ['is_active'])
    op.create_index('idx_scheduled_reports_next_run', 'scheduled_reports', ['next_run_at'])
    op.create_index('idx_scheduled_reports_type', 'scheduled_reports', ['report_type'])


def downgrade() -> None:
    op.drop_index('idx_scheduled_reports_type', table_name='scheduled_reports')
    op.drop_index('idx_scheduled_reports_next_run', table_name='scheduled_reports')
    op.drop_index('idx_scheduled_reports_active', table_name='scheduled_reports')
    op.drop_table('scheduled_reports')
