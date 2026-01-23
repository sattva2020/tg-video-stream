"""add cdn tables

Revision ID: p2q3r4s5t6u7
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from src.database import GUID


# revision identifiers, used by Alembic.
revision = 'p2q3r4s5t6u7'
down_revision = 'n1o2p3q4r5s6'
branch_labels = None
depends_on = None


def upgrade():
    # Create cdn_configs table
    op.create_table(
        'cdn_configs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('api_token', sa.String(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=True),
        sa.Column('zone_id', sa.String(), nullable=True),
        sa.Column('distribution_id', sa.String(), nullable=True),
        sa.Column('service_id', sa.String(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('health_status', sa.String(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cdn_configs_provider'), 'cdn_configs', ['provider'], unique=False)


def downgrade():
    # Drop indices
    op.drop_index(op.f('ix_cdn_configs_provider'), table_name='cdn_configs')

    # Drop tables
    op.drop_table('cdn_configs')
