"""make google_id nullable

Revision ID: a1b2c3d4e5f6
Revises: 7a8f3d2b1e8
Create Date: 2025-11-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7a8f3d2b1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make google_id nullable to allow email/password registration
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('google_id',
               existing_type=sa.VARCHAR(),
               nullable=True)


def downgrade() -> None:
    # Revert google_id to not nullable
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('google_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
