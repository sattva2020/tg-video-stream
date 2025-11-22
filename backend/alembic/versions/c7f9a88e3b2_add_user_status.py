"""add status to users

Revision ID: c7f9a88e3b2
Revises: b2c3d4e5f6g7
Create Date: 2025-11-22 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7f9a88e3b2'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Add column with a safe default so existing users are approved
    op.add_column('users', sa.Column('status', sa.String(), nullable=False, server_default='approved'))
    # 2) As a safety ensure existing rows are explicitly set (may be redundant)
    op.execute("UPDATE users SET status='approved' WHERE status IS NULL")
    # 3) Change server default for future inserts to 'pending'
    op.alter_column('users', 'status', server_default='pending')


def downgrade():
    op.drop_column('users', 'status')
