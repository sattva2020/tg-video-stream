"""Create admin_audit_logs table

Revision ID: 20240120_admin_audit_logs
Revises: 
Create Date: 2024-01-20

Создаёт таблицу admin_audit_logs для логирования
всех административных действий.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20240120_admin_audit_logs'
down_revision: Union[str, None] = None  # Устанавливается автоматически
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблицы admin_audit_logs."""
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы
    op.create_index('ix_admin_audit_logs_user_id', 'admin_audit_logs', ['user_id'])
    op.create_index('ix_admin_audit_logs_action', 'admin_audit_logs', ['action'])
    op.create_index('ix_admin_audit_logs_resource_type', 'admin_audit_logs', ['resource_type'])
    op.create_index('ix_admin_audit_logs_timestamp', 'admin_audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_user_action', 'admin_audit_logs', ['user_id', 'action'])
    op.create_index('ix_audit_logs_resource', 'admin_audit_logs', ['resource_type', 'resource_id'])


def downgrade() -> None:
    """Удаление таблицы admin_audit_logs."""
    op.drop_index('ix_audit_logs_resource', table_name='admin_audit_logs')
    op.drop_index('ix_audit_logs_user_action', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_timestamp', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_resource_type', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_action', table_name='admin_audit_logs')
    op.drop_index('ix_admin_audit_logs_user_id', table_name='admin_audit_logs')
    op.drop_table('admin_audit_logs')
