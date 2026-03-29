"""create import_jobs table

Revision ID: p2q3r4s5t6u7
Revises: n1o2p3q4r5s6
Create Date: 2026-01-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import src.database


# revision identifiers, used by Alembic.
revision: str = 'p2q3r4s5t6u7'
down_revision: Union[str, None] = 'n1o2p3q4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    import_status = sa.Enum('pending', 'in_progress', 'completed', 'failed', 'cancelled', 'paused', name='import_status')
    import_platform = sa.Enum('youtube', 'vimeo', 'local', name='import_platform')

    # Create import_jobs table
    op.create_table('import_jobs',
        sa.Column('id', src.database.GUID(), primary_key=True, nullable=False),
        sa.Column('user_id', src.database.GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel_id', src.database.GUID(), sa.ForeignKey('channels.id', ondelete='SET NULL'), nullable=True),
        sa.Column('platform', import_platform, nullable=False),
        sa.Column('source_url', sa.String(2000), nullable=True),
        sa.Column('source_path', sa.String(2000), nullable=True),
        sa.Column('status', import_status, nullable=False, server_default='pending'),
        sa.Column('total_items', sa.BigInteger(), nullable=True),
        sa.Column('processed_items', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('successful_items', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('failed_items', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('skipped_items', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('progress_percentage', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('options', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('results', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index('ix_import_jobs_user_id', 'import_jobs', ['user_id'])
    op.create_index('ix_import_jobs_channel_id', 'import_jobs', ['channel_id'])
    op.create_index('ix_import_jobs_platform', 'import_jobs', ['platform'])
    op.create_index('ix_import_jobs_status', 'import_jobs', ['status'])
    op.create_index('ix_import_jobs_created_at', 'import_jobs', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_import_jobs_created_at', table_name='import_jobs')
    op.drop_index('ix_import_jobs_status', table_name='import_jobs')
    op.drop_index('ix_import_jobs_platform', table_name='import_jobs')
    op.drop_index('ix_import_jobs_channel_id', table_name='import_jobs')
    op.drop_index('ix_import_jobs_user_id', table_name='import_jobs')

    # Drop table
    op.drop_table('import_jobs')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS import_status')
    op.execute('DROP TYPE IF EXISTS import_platform')
