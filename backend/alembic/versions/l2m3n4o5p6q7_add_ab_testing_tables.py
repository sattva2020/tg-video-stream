"""add_ab_testing_tables

Revision ID: l2m3n4o5p6q7
Revises: k0l1m2n3o4p5
Create Date: 2026-01-23 14:20:00.000000

Добавляет таблицы для системы A/B тестирования контента (тесты, варианты, метрики).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'l2m3n4o5p6q7'
down_revision: Union[str, None] = 'k0l1m2n3o4p5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM type for ABTestStatus
    ab_test_status_enum = sa.Enum('draft', 'running', 'paused', 'completed', 'stopped', name='abteststatus')

    # Create ab_tests table first without foreign key to ab_test_variants
    op.create_table(
        'ab_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('hypothesis', sa.Text(), nullable=True),
        sa.Column('status', ab_test_status_enum, nullable=False, server_default=sa.text("'draft'")),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_duration_hours', sa.BigInteger(), nullable=True),
        sa.Column('traffic_config', postgresql.JSONB(), nullable=True),
        sa.Column('winner_variant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confidence_level', sa.Numeric(5, 2), nullable=True),
        sa.Column('is_significant', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('idx_ab_tests_channel_status', 'ab_tests', ['channel_id', 'status'])
    op.create_index('idx_ab_tests_created_at', 'ab_tests', ['created_at'])
    op.create_index('ix_ab_tests_channel_id', 'ab_tests', ['channel_id'])
    op.create_index('ix_ab_tests_status', 'ab_tests', ['status'])

    # Create ab_test_variants table
    op.create_table(
        'ab_test_variants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('test_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('position', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('traffic_allocation', sa.BigInteger(), nullable=False, server_default=sa.text('50')),
        sa.Column('configuration', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('is_winner', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('conversion_rate', sa.Numeric(10, 4), nullable=True),
        sa.Column('improvement', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['test_id'], ['ab_tests.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_ab_test_variants_test_position', 'ab_test_variants', ['test_id', 'position'])
    op.create_index('ix_ab_test_variants_test_id', 'ab_test_variants', ['test_id'])

    # Now add the foreign key constraint from ab_tests to ab_test_variants
    op.create_foreign_key(
        'fk_ab_tests_winner_variant_id',
        'ab_tests', 'ab_test_variants',
        ['winner_variant_id'], ['id'],
        ondelete='SET NULL'
    )

    op.create_table(
        'ab_test_metrics',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('variant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('metric_value', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['variant_id'], ['ab_test_variants.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_ab_test_metrics_variant_type', 'ab_test_metrics', ['variant_id', 'metric_type'])
    op.create_index('idx_ab_test_metrics_recorded_at', 'ab_test_metrics', ['recorded_at'])
    op.create_index('ix_ab_test_metrics_variant_id', 'ab_test_metrics', ['variant_id'])
    op.create_index('ix_ab_test_metrics_metric_type', 'ab_test_metrics', ['metric_type'])


def downgrade() -> None:
    op.drop_index('ix_ab_test_metrics_metric_type', table_name='ab_test_metrics')
    op.drop_index('ix_ab_test_metrics_variant_id', table_name='ab_test_metrics')
    op.drop_index('idx_ab_test_metrics_recorded_at', table_name='ab_test_metrics')
    op.drop_index('idx_ab_test_metrics_variant_type', table_name='ab_test_metrics')
    op.drop_table('ab_test_metrics')

    # Drop foreign key constraint from ab_tests to ab_test_variants first
    op.drop_constraint('fk_ab_tests_winner_variant_id', 'ab_tests', type_='foreignkey')

    op.drop_index('ix_ab_test_variants_test_id', table_name='ab_test_variants')
    op.drop_index('idx_ab_test_variants_test_position', table_name='ab_test_variants')
    op.drop_table('ab_test_variants')

    op.drop_index('ix_ab_tests_status', table_name='ab_tests')
    op.drop_index('ix_ab_tests_channel_id', table_name='ab_tests')
    op.drop_index('idx_ab_tests_created_at', table_name='ab_tests')
    op.drop_index('idx_ab_tests_channel_status', table_name='ab_tests')
    op.drop_table('ab_tests')

    # Drop ENUM type
    sa.Enum(name='abteststatus').drop(op.get_bind(), checkfirst=False)
