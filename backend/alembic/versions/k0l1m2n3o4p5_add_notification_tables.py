"""add_notification_tables

Revision ID: k0l1m2n3o4p5
Revises: j9k0l1m2n3o4
Create Date: 2026-01-15 12:00:00.000000

Добавляет таблицы для системы уведомлений (каналы, шаблоны, получатели, правила и логи доставок).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'k0l1m2n3o4p5'
down_revision: Union[str, None] = 'j9k0l1m2n3o4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notification_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'ok'")),
        sa.Column('test_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('concurrency_limit', sa.Integer(), nullable=True),
        sa.Column('retry_attempts', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('retry_interval_sec', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('timeout_sec', sa.Integer(), nullable=False, server_default=sa.text('10')),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('name', name='uq_notification_channel_name'),
    )

    op.create_table(
        'notification_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('locale', sa.String(length=5), nullable=False, server_default=sa.text("'en'")),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['notification_channels.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('name', name='uq_notification_template_name'),
    )

    op.create_table(
        'notification_recipients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column('silence_windows', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('type', 'address', name='uq_notification_recipient_address'),
    )

    op.create_table(
        'notification_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('severity_filter', sa.JSON(), nullable=True),
        sa.Column('tag_filter', sa.JSON(), nullable=True),
        sa.Column('host_filter', sa.JSON(), nullable=True),
        sa.Column('failover_timeout_sec', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('silence_windows', sa.JSON(), nullable=True),
        sa.Column('rate_limit', sa.JSON(), nullable=True),
        sa.Column('dedup_window_sec', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('test_channel_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['notification_templates.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('name', name='uq_notification_rule_name'),
    )

    op.create_table(
        'notification_rule_recipients',
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['recipient_id'], ['notification_recipients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['notification_rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('rule_id', 'recipient_id')
    )

    op.create_table(
        'notification_rule_channels',
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['channel_id'], ['notification_channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['notification_rules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('rule_id', 'channel_id')
    )
    op.create_index('ix_notification_rule_channels_order', 'notification_rule_channels', ['rule_id', 'priority'])

    op.create_table(
        'notification_delivery_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('response_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['channel_id'], ['notification_channels.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recipient_id'], ['notification_recipients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rule_id'], ['notification_rules.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_notification_delivery_logs_event', 'notification_delivery_logs', ['event_id'])
    op.create_index('ix_notification_delivery_logs_status', 'notification_delivery_logs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_notification_delivery_logs_status', table_name='notification_delivery_logs')
    op.drop_index('ix_notification_delivery_logs_event', table_name='notification_delivery_logs')
    op.drop_table('notification_delivery_logs')

    op.drop_index('ix_notification_rule_channels_order', table_name='notification_rule_channels')
    op.drop_table('notification_rule_channels')
    op.drop_table('notification_rule_recipients')

    op.drop_table('notification_rules')
    op.drop_table('notification_recipients')
    op.drop_table('notification_templates')
    op.drop_table('notification_channels')
