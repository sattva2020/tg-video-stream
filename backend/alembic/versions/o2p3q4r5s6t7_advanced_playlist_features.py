"""Advanced playlist features

Add nested folders, repeat modes, templates, and smart playlists

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 21:00:00.000000

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
    # Add parent_id column to playlist_groups for nested folders
    op.add_column(
        'playlist_groups',
        sa.Column('parent_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_playlist_groups_parent_id',
        'playlist_groups', 'playlist_groups',
        ['parent_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_playlist_groups_parent_id', 'playlist_groups', ['parent_id'], unique=False)

    # Add repeat_mode column to playlists table
    op.add_column(
        'playlists',
        sa.Column(
            'repeat_mode',
            sa.Enum('none', 'one', 'all', name='playlistrepeatmode', create_type=True),
            nullable=False,
            server_default='none'
        )
    )

    # Create playlist_templates table
    op.create_table(
        'playlist_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('channel_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('items', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('total_duration', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('items_count', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_playlist_templates_user_id', 'playlist_templates', ['user_id'], unique=False)
    op.create_index('ix_playlist_templates_channel_id', 'playlist_templates', ['channel_id'], unique=False)

    # Create smart_playlists table
    op.create_table(
        'smart_playlists',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('channel_id', sa.UUID(), nullable=True),
        sa.Column('group_id', sa.UUID(), nullable=True),
        sa.Column('playlist_id', sa.UUID(), nullable=True),
        sa.Column('position', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), server_default='#10B981', nullable=False),
        sa.Column('criteria', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('auto_update', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('auto_update_interval', sa.Integer(), server_default='24', nullable=False),
        sa.Column('last_refreshed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('items_count', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('total_duration', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['group_id'], ['playlist_groups.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['playlist_id'], ['playlists.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_smart_playlists_user_id', 'smart_playlists', ['user_id'], unique=False)
    op.create_index('ix_smart_playlists_channel_id', 'smart_playlists', ['channel_id'], unique=False)
    op.create_index('ix_smart_playlists_group_id', 'smart_playlists', ['group_id'], unique=False)
    op.create_index('ix_smart_playlists_playlist_id', 'smart_playlists', ['playlist_id'], unique=False)


def downgrade() -> None:
    # Drop smart_playlists table
    op.drop_index('ix_smart_playlists_playlist_id', table_name='smart_playlists')
    op.drop_index('ix_smart_playlists_group_id', table_name='smart_playlists')
    op.drop_index('ix_smart_playlists_channel_id', table_name='smart_playlists')
    op.drop_index('ix_smart_playlists_user_id', table_name='smart_playlists')
    op.drop_table('smart_playlists')

    # Drop playlist_templates table
    op.drop_index('ix_playlist_templates_channel_id', table_name='playlist_templates')
    op.drop_index('ix_playlist_templates_user_id', table_name='playlist_templates')
    op.drop_table('playlist_templates')

    # Remove repeat_mode from playlists
    op.execute('ALTER TABLE playlists ALTER COLUMN repeat_mode DROP DEFAULT')
    op.execute('DROP TYPE IF EXISTS playlistrepeatmode')
    op.drop_column('playlists', 'repeat_mode')

    # Remove parent_id from playlist_groups
    op.drop_index('ix_playlist_groups_parent_id', table_name='playlist_groups')
    op.drop_constraint('fk_playlist_groups_parent_id', 'playlist_groups', type_='foreignkey')
    op.drop_column('playlist_groups', 'parent_id')
