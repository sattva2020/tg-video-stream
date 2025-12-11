"""Add playlist sharing fields

Revision ID: l1m2n3o4p5q6
Revises: k0l1m2n3o4p5
Create Date: 2025-12-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'l1m2n3o4p5q6'
down_revision = 'k0l1m2n3o4p5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_public column
    op.add_column('playlists', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add share_code column
    op.add_column('playlists', sa.Column('share_code', sa.String(length=32), nullable=True))
    
    # Create unique constraint on share_code
    op.create_index('idx_playlists_share_code', 'playlists', ['share_code'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_playlists_share_code', table_name='playlists')
    op.drop_column('playlists', 'share_code')
    op.drop_column('playlists', 'is_public')
