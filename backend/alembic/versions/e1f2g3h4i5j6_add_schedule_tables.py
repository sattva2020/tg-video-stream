"""add schedule tables

Revision ID: e1f2g3h4i5j6
Revises: d9e4f1a2b3c
Create Date: 2025-11-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = 'e1f2g3h4i5j6'
down_revision = 'd9e4f1a2b3c'
branch_labels = None
depends_on = None


def upgrade():
    # Create playlists table
    op.create_table(
        'playlists',
        sa.Column('id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('channel_id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), sa.ForeignKey('channels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), default='#8B5CF6'),
        sa.Column('source_type', sa.String(50), default='manual'),
        sa.Column('source_url', sa.String(2048), nullable=True),
        sa.Column('items', JSONB() if op.get_bind().dialect.name == 'postgresql' else sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('total_duration', sa.Integer(), default=0),
        sa.Column('items_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_shuffled', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create schedule_slots table
    op.create_table(
        'schedule_slots',
        sa.Column('id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), primary_key=True),
        sa.Column('channel_id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), sa.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('playlist_id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), sa.ForeignKey('playlists.id', ondelete='SET NULL'), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False, index=True),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('repeat_type', sa.Enum('none', 'daily', 'weekly', 'weekdays', 'weekends', 'custom', name='repeattype'), default='none'),
        sa.Column('repeat_days', JSONB() if op.get_bind().dialect.name == 'postgresql' else sa.JSON(), nullable=True),
        sa.Column('repeat_until', sa.Date(), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(7), default='#3B82F6'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('priority', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    # Create schedule_templates table
    op.create_table(
        'schedule_templates',
        sa.Column('id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('channel_id', UUID(as_uuid=True) if op.get_bind().dialect.name == 'postgresql' else sa.String(36), sa.ForeignKey('channels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('slots', JSONB() if op.get_bind().dialect.name == 'postgresql' else sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create indexes for better query performance
    op.create_index('ix_schedule_slots_date_channel', 'schedule_slots', ['start_date', 'channel_id'])
    op.create_index('ix_playlists_user_active', 'playlists', ['user_id', 'is_active'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_playlists_user_active', table_name='playlists')
    op.drop_index('ix_schedule_slots_date_channel', table_name='schedule_slots')
    
    # Drop tables in reverse order
    op.drop_table('schedule_templates')
    op.drop_table('schedule_slots')
    op.drop_table('playlists')
    
    # Drop enum type if PostgreSQL
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS repeattype')
