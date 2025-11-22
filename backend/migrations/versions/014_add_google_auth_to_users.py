"""Add google_id and profile_picture_url to users table

Revision ID: 014_add_google_auth_to_users
Revises: 013_fix_youtube_sources_schema
Create Date: 2025-11-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014_add_google_auth_to_users'
down_revision: Union[str, None] = '013_fix_youtube_sources_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('profile_picture_url', sa.String(255), nullable=True))
    op.alter_column('users', 'password_hash', existing_type=sa.String(255), nullable=True)
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_google_id', table_name='users')
    op.alter_column('users', 'password_hash', existing_type=sa.String(255), nullable=False)
    op.drop_column('users', 'profile_picture_url')
    op.drop_column('users', 'google_id')
