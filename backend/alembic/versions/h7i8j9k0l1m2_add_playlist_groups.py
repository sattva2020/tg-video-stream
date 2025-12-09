"""Add playlist groups table and update playlists

Revision ID: h7i8j9k0l1m2
Revises: g6h7i8j9k0l1
Create Date: 2025-12-08 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'h7i8j9k0l1m2'
down_revision: Union[str, None] = 'g6h7i8j9k0l1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create playlist_groups table
    op.create_table(
        'playlist_groups',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('channel_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), server_default='#6366F1', nullable=True),
        sa.Column('icon', sa.String(length=50), server_default='folder', nullable=True),
        sa.Column('position', sa.Integer(), server_default='0', nullable=True),
        sa.Column('is_expanded', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_playlist_groups_user_id', 'playlist_groups', ['user_id'], unique=False)
    op.create_index('ix_playlist_groups_channel_id', 'playlist_groups', ['channel_id'], unique=False)

    # Add group_id and position columns to playlists table
    op.add_column('playlists', sa.Column('group_id', sa.UUID(), nullable=True))
    op.add_column('playlists', sa.Column('position', sa.Integer(), server_default='0', nullable=True))
    
    op.create_foreign_key(
        'fk_playlists_group_id',
        'playlists', 'playlist_groups',
        ['group_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_playlists_group_id', 'playlists', ['group_id'], unique=False)


def downgrade() -> None:
    # Remove foreign key and columns from playlists
    op.drop_index('ix_playlists_group_id', table_name='playlists')
    op.drop_constraint('fk_playlists_group_id', 'playlists', type_='foreignkey')
    op.drop_column('playlists', 'position')
    op.drop_column('playlists', 'group_id')
    
    # Drop playlist_groups table
    op.drop_index('ix_playlist_groups_channel_id', table_name='playlist_groups')
    op.drop_index('ix_playlist_groups_user_id', table_name='playlist_groups')
    op.drop_table('playlist_groups')
