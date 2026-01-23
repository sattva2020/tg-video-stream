"""create_quotas_subscriptions_tables

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-01-23 14:40:00.000000

Creates resource_quotas and subscriptions tables for multi-tenant resource management and billing.
Resource quotas define limits on streams, storage, bandwidth, and other resources per organization.
Subscriptions manage billing plans, trial periods, and payment status per organization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'q3r4s5t6u7v8'
down_revision: Union[str, None] = 'p2q3r4s5t6u7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create resource_quotas table
    op.create_table(
        'resource_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quota_type', sa.String(length=50), nullable=False),
        sa.Column('limit', sa.BigInteger(), nullable=False),
        sa.Column('current_usage', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('period', sa.String(length=20), nullable=True),
        sa.Column('reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', 'quota_type', name='uq_resource_quota_org_type')
    )
    op.create_index('ix_resource_quotas_organization_id', 'resource_quotas', ['organization_id'])
    op.create_index('ix_resource_quotas_quota_type', 'resource_quotas', ['quota_type'])

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'trialing'")),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('billing_address', sa.JSON(), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id', name='uq_subscription_organization')
    )
    op.create_index('ix_subscriptions_organization_id', 'subscriptions', ['organization_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_plan_type', 'subscriptions', ['plan_type'])


def downgrade() -> None:
    op.drop_index('ix_subscriptions_plan_type', table_name='subscriptions')
    op.drop_index('ix_subscriptions_status', table_name='subscriptions')
    op.drop_index('ix_subscriptions_organization_id', table_name='subscriptions')
    op.drop_table('subscriptions')

    op.drop_index('ix_resource_quotas_quota_type', table_name='resource_quotas')
    op.drop_index('ix_resource_quotas_organization_id', table_name='resource_quotas')
    op.drop_table('resource_quotas')
