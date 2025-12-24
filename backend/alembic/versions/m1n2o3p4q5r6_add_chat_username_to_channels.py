"""Add chat_username to channels

Revision ID: m1n2o3p4q5r6
Revises: 22_phase3_stream_quality_history
Create Date: 2025-12-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'm1n2o3p4q5r6'
down_revision = '22_phase3_stream_quality_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('channels', sa.Column('chat_username', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('channels', 'chat_username')
