"""enforce multi channel playback scope

Revision ID: b7c8d9e0f1g
Revises: a1b2c3d4e5f
Create Date: 2025-02-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c8d9e0f1g'
down_revision = 'a1b2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade():
    # backfill null channel identifiers with the default scope (0)
    op.execute("UPDATE playback_settings SET channel_id = COALESCE(channel_id, 0)")

    with op.batch_alter_table('playback_settings') as batch_op:
        batch_op.alter_column(
            'channel_id',
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=True,
            nullable=False,
            server_default='0',
        )

    # replace the legacy unique constraint (user only) with user+channel scope
    op.drop_constraint('playback_settings_user_id_key', 'playback_settings', type_='unique')
    op.create_unique_constraint(
        'uq_playback_user_channel',
        'playback_settings',
        ['user_id', 'channel_id'],
    )

    # add lookup index for faster channel scoped reads
    op.create_index(
        'ix_playback_settings_channel_id',
        'playback_settings',
        ['channel_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_playback_settings_channel_id', table_name='playback_settings')
    op.drop_constraint('uq_playback_user_channel', 'playback_settings', type_='unique')
    op.create_unique_constraint(
        'playback_settings_user_id_key',
        'playback_settings',
        ['user_id'],
    )

    with op.batch_alter_table('playback_settings') as batch_op:
        batch_op.alter_column(
            'channel_id',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
            nullable=True,
            server_default=None,
        )
