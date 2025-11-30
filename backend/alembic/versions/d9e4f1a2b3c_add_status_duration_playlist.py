"""add status and duration to playlist_items

Revision ID: d9e4f1a2b3c
Revises: c7f9a88e3b2
Create Date: 2025-11-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9e4f1a2b3c'
down_revision = 'c7f9a88e3b2'
branch_labels = None
depends_on = None


def upgrade():
    # Add status with a safe default and duration.
    with op.batch_alter_table('playlist_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(), nullable=False, server_default='queued'))
        batch_op.add_column(sa.Column('duration', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('playlist_items', schema=None) as batch_op:
        batch_op.drop_column('duration')
        batch_op.drop_column('status')
