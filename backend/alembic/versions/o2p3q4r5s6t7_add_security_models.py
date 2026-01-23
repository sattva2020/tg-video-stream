"""add_security_models

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 12:00:00.000000

Adds security and compliance tables:
- saml_configs: SAML/SSO identity provider configurations
- ip_whitelist: IP address whitelist for network access control
- security_policies: Security policies including 2FA enforcement
- compliance_logs: Security and compliance event logging
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
    # Create saml_configs table
    op.create_table(
        'saml_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        # Identity Provider settings
        sa.Column('idp_entity_id', sa.String(length=500), nullable=False),
        sa.Column('idp_sso_url', sa.String(length=500), nullable=False),
        sa.Column('idp_x509_cert', sa.String(), nullable=False),
        sa.Column('idp_slo_url', sa.String(length=500), nullable=True),
        sa.Column('idp_metadata_url', sa.String(length=500), nullable=True),
        # Service Provider settings
        sa.Column('sp_entity_id', sa.String(length=500), nullable=False),
        sa.Column('sp_acs_url', sa.String(length=500), nullable=False),
        sa.Column('sp_slo_url', sa.String(length=500), nullable=True),
        # Security settings
        sa.Column('name_id_format', sa.String(length=255), nullable=True, server_default=sa.text("'urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified'")),
        sa.Column('security_config', sa.JSON(), nullable=True),
        # User provisioning and role mapping
        sa.Column('attribute_mapping', sa.JSON(), nullable=True),
        sa.Column('role_mapping', sa.JSON(), nullable=True),
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create ip_whitelist table
    op.create_table(
        'ip_whitelist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('cidr', sa.String(length=45), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_ip_whitelist_cidr', 'ip_whitelist', ['cidr'])

    # Create security_policies table
    op.create_table(
        'security_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('policy_type', sa.String(length=50), nullable=False, server_default=sa.text("'2fa_enforcement'")),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('enforcement_level', sa.String(length=50), nullable=False, server_default=sa.text("'optional'")),
        sa.Column('affected_roles', sa.JSON(), nullable=True),
        # 2FA-specific settings
        sa.Column('grace_period_hours', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('allow_exempt_alternative_auth', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        # Additional policy configuration
        sa.Column('policy_config', sa.JSON(), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        # Audit tracking
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create compliance_logs table
    op.create_table(
        'compliance_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('compliance_status', sa.String(length=30), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes for compliance_logs for performance
    op.create_index('ix_compliance_logs_event_type', 'compliance_logs', ['event_type'])
    op.create_index('ix_compliance_logs_category', 'compliance_logs', ['category'])
    op.create_index('ix_compliance_logs_severity', 'compliance_logs', ['severity'])
    op.create_index('ix_compliance_logs_status', 'compliance_logs', ['compliance_status'])
    op.create_index('ix_compliance_logs_user', 'compliance_logs', ['user_id', 'timestamp'])
    op.create_index('ix_compliance_logs_resource', 'compliance_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_compliance_logs_timestamp', 'compliance_logs', ['timestamp'])
    op.create_index('ix_compliance_logs_unresolved', 'compliance_logs', ['compliance_status', 'timestamp'])


def downgrade() -> None:
    # Drop compliance_logs table and indexes
    op.drop_index('ix_compliance_logs_unresolved', table_name='compliance_logs')
    op.drop_index('ix_compliance_logs_timestamp', table_name='compliance_logs')
    op.drop_index('ix_compliance_logs_resource', table_name='compliance_logs')
    op.drop_index('ix_compliance_logs_user', table_name='compliance_logs')
    op.drop_index('ix_compliance_logs_status', table_name='compliance_logs')
    op.drop_index('ix_compliance_logs_severity', table_name='compliance_logs')
    op.drop_index('ix_compliance_logs_category', table_name='compliance_logs')
    op.drop_index('ix_compliance_logs_event_type', table_name='compliance_logs')
    op.drop_table('compliance_logs')

    # Drop security_policies table
    op.drop_table('security_policies')

    # Drop ip_whitelist table and index
    op.drop_index('ix_ip_whitelist_cidr', table_name='ip_whitelist')
    op.drop_table('ip_whitelist')

    # Drop saml_configs table
    op.drop_table('saml_configs')
