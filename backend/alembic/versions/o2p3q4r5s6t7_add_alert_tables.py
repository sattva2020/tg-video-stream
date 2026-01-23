"""add_alert_tables

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 15:00:00.000000

Добавляет таблицы для системы алертов (правила алертов, экземпляры алертов и группы алертов).
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
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default=sa.text("'warning'")),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('conditions', sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('cooldown_sec', sa.BigInteger(), nullable=False, server_default=sa.text('300')),
        sa.Column('rate_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('rate_limit_count', sa.Integer(), nullable=True),
        sa.Column('notification_channels', sa.JSON(), nullable=True),
        sa.Column('notify_on_recovery', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('auto_resolve', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('escalation_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('escalation_rules', sa.JSON(), nullable=True),
        sa.Column('active_windows', sa.JSON(), nullable=True),
        sa.Column('silence_windows', sa.JSON(), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_count', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('consecutive_triggers', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('name', name='uq_alert_rule_name'),
    )

    op.create_table(
        'alert_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default=sa.text("'warning'")),
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'firing'")),
        sa.Column('trigger_value', sa.JSON(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('notification_channels', sa.JSON(), nullable=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('fired_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('duration_sec', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['alert_groups.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_alert_instances_rule_id', 'alert_instances', ['rule_id'])
    op.create_index('ix_alert_instances_status', 'alert_instances', ['status'])
    op.create_index('ix_alert_instances_fired_at', 'alert_instances', ['fired_at'])
    op.create_index('ix_alert_instances_severity', 'alert_instances', ['severity'])
    op.create_index('ix_alert_instances_alert_type', 'alert_instances', ['alert_type'])

    op.create_table(
        'alert_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_key', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column('alert_count', sa.BigInteger(), nullable=False, server_default=sa.text('1')),
        sa.Column('first_alert_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_alert_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('notification_sent', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('last_notification_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notification_count', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default=sa.text("'warning'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('rule_id', 'group_key', name='uq_alert_group_rule_key'),
    )
    op.create_index('ix_alert_groups_rule_id', 'alert_groups', ['rule_id'])
    op.create_index('ix_alert_groups_status', 'alert_groups', ['status'])
    op.create_index('ix_alert_groups_severity', 'alert_groups', ['severity'])
    op.create_index('ix_alert_groups_created_at', 'alert_groups', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_alert_groups_created_at', table_name='alert_groups')
    op.drop_index('ix_alert_groups_severity', table_name='alert_groups')
    op.drop_index('ix_alert_groups_status', table_name='alert_groups')
    op.drop_index('ix_alert_groups_rule_id', table_name='alert_groups')
    op.drop_table('alert_groups')

    op.drop_index('ix_alert_instances_alert_type', table_name='alert_instances')
    op.drop_index('ix_alert_instances_severity', table_name='alert_instances')
    op.drop_index('ix_alert_instances_fired_at', table_name='alert_instances')
    op.drop_index('ix_alert_instances_status', table_name='alert_instances')
    op.drop_index('ix_alert_instances_rule_id', table_name='alert_instances')
    op.drop_table('alert_instances')

    op.drop_table('alert_rules')
