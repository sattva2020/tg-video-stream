"""Add placeholder_image to channels

Revision ID: j9k0l1m2n3o4
Revises: i8j9k0l1m2n3
Create Date: 2025-12-08 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j9k0l1m2n3o4'
down_revision: Union[str, None] = 'i8j9k0l1m2n3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('channels', sa.Column('placeholder_image', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('channels', 'placeholder_image')
