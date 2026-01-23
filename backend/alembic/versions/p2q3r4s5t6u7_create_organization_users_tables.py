"""create organization_users_tables

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-01-23 14:35:00.000000

Creates organization_users and organization_roles tables for multi-tenant user management.
Organization roles define custom roles per organization with flexible permissions.
Organization users link users to organizations with specific roles and status tracking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'p2q3r4s5t6u7'
down_revision: Union[str, None] = 'o1p2q3r4s5t6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'organization_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('is_system_role', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_organization_role_name'),
    )
    op.create_index('ix_organization_roles_organization_id', 'organization_roles', ['organization_id'])

    op.create_table(
        'organization_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['organization_roles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_organization_user'),
    )
    op.create_index('ix_organization_users_organization_id', 'organization_users', ['organization_id'])
    op.create_index('ix_organization_users_user_id', 'organization_users', ['user_id'])
    op.create_index('ix_organization_users_status', 'organization_users', ['status'])


def downgrade() -> None:
    op.drop_index('ix_organization_users_status', table_name='organization_users')
    op.drop_index('ix_organization_users_user_id', table_name='organization_users')
    op.drop_index('ix_organization_users_organization_id', table_name='organization_users')
    op.drop_table('organization_users')

    op.drop_index('ix_organization_roles_organization_id', table_name='organization_roles')
    op.drop_table('organization_roles')
