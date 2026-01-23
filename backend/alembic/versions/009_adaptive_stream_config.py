"""Feature 009 Phase 3: Add adaptive stream config table

Revision ID: 009_adaptive_stream_config
Revises: 22_phase3_stream_quality_history
Create Date: 2026-01-23 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_adaptive_stream_config'
down_revision = '22_phase3_stream_quality_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create adaptive_stream_config table
    op.create_table(
        'adaptive_stream_config',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('stream_id', postgresql.UUID(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_quality', sa.String(20), nullable=False, server_default='high'),
        sa.Column('min_quality', sa.String(20), nullable=False, server_default='low'),
        sa.Column('max_quality', sa.String(20), nullable=False, server_default='ultra'),
        sa.Column('bandwidth_threshold_low_kbps', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('bandwidth_threshold_medium_kbps', sa.Integer(), nullable=False, server_default='1500'),
        sa.Column('bandwidth_threshold_high_kbps', sa.Integer(), nullable=False, server_default='3000'),
        sa.Column('bandwidth_threshold_ultra_kbps', sa.Integer(), nullable=False, server_default='6000'),
        sa.Column('adaptation_interval_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('bandwidth_smoothing_factor', sa.Float(), nullable=False, server_default='0.3'),
        sa.Column('consecutive_measurements_required', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('device_rules', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('quality_profiles', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('enable_bandwidth_monitoring', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('enable_quality_logging', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('statistics', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stream_id', name=op.f('uq_adaptive_stream_config_stream_id')),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE')
    )
    op.create_index(
        op.f('ix_adaptive_stream_config_stream_id'),
        'adaptive_stream_config',
        ['stream_id'],
        unique=False
    )

    # Add check constraints for quality levels
    op.create_check_constraint(
        'ck_asc_default_quality',
        'adaptive_stream_config',
        "default_quality IN ('low', 'medium', 'high', 'ultra')"
    )
    op.create_check_constraint(
        'ck_asc_min_quality',
        'adaptive_stream_config',
        "min_quality IN ('low', 'medium', 'high', 'ultra')"
    )
    op.create_check_constraint(
        'ck_asc_max_quality',
        'adaptive_stream_config',
        "max_quality IN ('low', 'medium', 'high', 'ultra')"
    )


def downgrade() -> None:
    # Drop check constraints
    op.drop_constraint('ck_asc_max_quality', 'adaptive_stream_config')
    op.drop_constraint('ck_asc_min_quality', 'adaptive_stream_config')
    op.drop_constraint('ck_asc_default_quality', 'adaptive_stream_config')

    # Drop index
    op.drop_index(
        op.f('ix_adaptive_stream_config_stream_id'),
        table_name='adaptive_stream_config'
    )

    # Drop table
    op.drop_table('adaptive_stream_config')
