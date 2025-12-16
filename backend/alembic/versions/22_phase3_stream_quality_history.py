"""Feature 022 Phase 3: Add stream quality tracking tables

Revision ID: 22_phase3_stream_quality_history
Revises: 58c64dc71747_merge_three_heads
Create Date: 2025-12-16 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '22_phase3_stream_quality_history'
down_revision = '58c64dc71747_merge_three_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create stream_quality_history table
    op.create_table(
        'stream_quality_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stream_url', sa.String(500), nullable=False),
        sa.Column('stream_name', sa.String(255), nullable=True),
        sa.Column('audio_codec', sa.String(50), nullable=True),
        sa.Column('audio_bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('audio_sample_rate_hz', sa.Integer(), nullable=True),
        sa.Column('audio_channels', sa.Integer(), nullable=True),
        sa.Column('audio_quality', sa.String(20), nullable=True),
        sa.Column('video_codec', sa.String(50), nullable=True),
        sa.Column('video_bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('video_resolution', sa.String(20), nullable=True),
        sa.Column('video_fps', sa.Float(), nullable=True),
        sa.Column('video_quality', sa.String(20), nullable=True),
        sa.Column('overall_quality', sa.String(20), nullable=False),
        sa.Column('is_audio_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_video_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('analysis_duration_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_stream_quality_history_analyzed_at'),
        'stream_quality_history',
        ['analyzed_at'],
        unique=False
    )
    op.create_index(
        op.f('ix_stream_quality_history_overall_quality'),
        'stream_quality_history',
        ['overall_quality'],
        unique=False
    )
    op.create_index(
        op.f('ix_stream_quality_history_stream_url'),
        'stream_quality_history',
        ['stream_url'],
        unique=False
    )

    # Create quality_alert_configs table
    op.create_table(
        'quality_alert_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stream_url', sa.String(500), nullable=False),
        sa.Column('stream_name', sa.String(255), nullable=True),
        sa.Column('min_overall_quality', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('min_audio_quality', sa.String(20), nullable=True),
        sa.Column('min_video_quality', sa.String(20), nullable=True),
        sa.Column('min_audio_bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('min_video_bitrate_kbps', sa.Integer(), nullable=True),
        sa.Column('min_video_resolution', sa.String(20), nullable=True),
        sa.Column('min_video_fps', sa.Float(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_degradation', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_recovery', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('alert_channels', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('last_alert_at', sa.DateTime(), nullable=True),
        sa.Column('last_alert_type', sa.String(50), nullable=True),
        sa.Column('consecutive_failures_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stream_url', name=op.f('uq_quality_alert_configs_stream_url'))
    )
    op.create_index(
        op.f('ix_quality_alert_configs_stream_url'),
        'quality_alert_configs',
        ['stream_url'],
        unique=False
    )

    # Create quality_trend_snapshots table
    op.create_table(
        'quality_trend_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stream_url', sa.String(500), nullable=False),
        sa.Column('hour', sa.DateTime(), nullable=False),
        sa.Column('audio_quality_avg', sa.String(20), nullable=True),
        sa.Column('audio_bitrate_avg', sa.Float(), nullable=True),
        sa.Column('audio_quality_min', sa.String(20), nullable=True),
        sa.Column('audio_bitrate_min', sa.Float(), nullable=True),
        sa.Column('video_quality_avg', sa.String(20), nullable=True),
        sa.Column('video_bitrate_avg', sa.Float(), nullable=True),
        sa.Column('video_resolution', sa.String(20), nullable=True),
        sa.Column('video_fps_avg', sa.Float(), nullable=True),
        sa.Column('video_quality_min', sa.String(20), nullable=True),
        sa.Column('video_bitrate_min', sa.Float(), nullable=True),
        sa.Column('overall_quality_avg', sa.String(20), nullable=True),
        sa.Column('overall_quality_min', sa.String(20), nullable=True),
        sa.Column('samples_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_rate', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_quality_trend_snapshots_hour'),
        'quality_trend_snapshots',
        ['hour'],
        unique=False
    )
    op.create_index(
        op.f('ix_quality_trend_snapshots_stream_url'),
        'quality_trend_snapshots',
        ['stream_url'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_quality_trend_snapshots_stream_url'),
        table_name='quality_trend_snapshots'
    )
    op.drop_index(
        op.f('ix_quality_trend_snapshots_hour'),
        table_name='quality_trend_snapshots'
    )
    op.drop_table('quality_trend_snapshots')

    op.drop_index(
        op.f('ix_quality_alert_configs_stream_url'),
        table_name='quality_alert_configs'
    )
    op.drop_table('quality_alert_configs')

    op.drop_index(
        op.f('ix_stream_quality_history_stream_url'),
        table_name='stream_quality_history'
    )
    op.drop_index(
        op.f('ix_stream_quality_history_overall_quality'),
        table_name='stream_quality_history'
    )
    op.drop_index(
        op.f('ix_stream_quality_history_analyzed_at'),
        table_name='stream_quality_history'
    )
    op.drop_table('stream_quality_history')
