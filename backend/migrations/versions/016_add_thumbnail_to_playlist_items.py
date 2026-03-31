"""Add thumbnail field to playlist_items

Revision ID: 016_add_thumbnail_to_playlist_items
Revises: 015_add_activity_events
Create Date: 2025-01-23 12:00:00.000000

Spec: 008-advanced-playlist-management-with-smart-features
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016_add_thumbnail_to_playlist_items'
down_revision: Union[str, None] = '015_add_activity_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет поле thumbnail в таблицу playlist_items."""
    op.add_column(
        'playlist_items',
        sa.Column('thumbnail', sa.String(length=2048), nullable=True)
    )


def downgrade() -> None:
    """Удаляет поле thumbnail из таблицы playlist_items."""
    op.drop_column('playlist_items', 'thumbnail')
