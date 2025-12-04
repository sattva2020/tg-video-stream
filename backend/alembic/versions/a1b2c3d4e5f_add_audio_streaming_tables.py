"""add audio streaming tables

Revision ID: a1b2c3d4e5f
Revises: d9e4f1a2b3c
Create Date: 2025-12-01 18:03:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f'
down_revision = 'd9e4f1a2b3c'
branch_labels = None
depends_on = None


def upgrade():
    # Create playback_settings table
    op.create_table(
        'playback_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=True),
        sa.Column('speed', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('pitch_correction', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('equalizer_preset', sa.String(50), nullable=True, server_default='flat'),
        sa.Column('equalizer_custom', sa.JSON(), nullable=True),
        sa.Column('language', sa.String(5), nullable=True, server_default='ru'),
        sa.Column('theme', sa.String(20), nullable=True, server_default='light'),
        sa.Column('auto_play', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('shuffle', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('repeat_mode', sa.String(10), nullable=True, server_default='off'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_playback_settings_user_id'), 'playback_settings', ['user_id'], unique=False)

    # Create radio_streams table
    op.create_table(
        'radio_streams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('genre', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('added_by', sa.Integer(), nullable=True),
        sa.Column('play_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_played', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url')
    )
    op.create_index(op.f('ix_radio_streams_name'), 'radio_streams', ['name'], unique=False)

    # Create scheduled_playlists table
    op.create_table(
        'scheduled_playlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('playlist_id', sa.Integer(), nullable=False),
        sa.Column('schedule_time', sa.String(5), nullable=False),
        sa.Column('days_of_week', sa.JSON(), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True, server_default='UTC'),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('last_triggered', sa.DateTime(), nullable=True),
        sa.Column('trigger_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create lyrics_cache table
    op.create_table(
        'lyrics_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_title', sa.String(500), nullable=False),
        sa.Column('artist_name', sa.String(255), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('lyrics_text', sa.Text(), nullable=False),
        sa.Column('lyrics_html', sa.Text(), nullable=True),
        sa.Column('synced_lyrics', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(2048), nullable=True),
        sa.Column('source_api', sa.String(50), nullable=True, server_default='genius'),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=True, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id')
    )
    op.create_index(op.f('ix_lyrics_cache_artist_name'), 'lyrics_cache', ['artist_name'], unique=False)
    op.create_index(op.f('ix_lyrics_cache_track_title'), 'lyrics_cache', ['track_title'], unique=False)


def downgrade():
    # Drop indices
    op.drop_index(op.f('ix_lyrics_cache_track_title'), table_name='lyrics_cache')
    op.drop_index(op.f('ix_lyrics_cache_artist_name'), table_name='lyrics_cache')
    op.drop_index(op.f('ix_radio_streams_name'), table_name='radio_streams')
    op.drop_index(op.f('ix_playback_settings_user_id'), table_name='playback_settings')
    
    # Drop tables
    op.drop_table('lyrics_cache')
    op.drop_table('scheduled_playlists')
    op.drop_table('radio_streams')
    op.drop_table('playback_settings')
