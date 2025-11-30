"""add_telegram_login_widget_fields

Revision ID: f5e6d7c8b9a0
Revises: e1f2g3h4i5j6
Create Date: 2025-11-30 15:00:00.000000

Добавляет поля telegram_id и telegram_username в таблицу users
для поддержки авторизации через Telegram Login Widget.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5e6d7c8b9a0'
down_revision: Union[str, None] = '3ca9c3980420'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite требует batch mode для ALTER constraints
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Добавляем поле telegram_id (BigInteger, unique, index)
        batch_op.add_column(sa.Column('telegram_id', sa.BigInteger(), nullable=True))
        batch_op.create_unique_constraint('uq_users_telegram_id', ['telegram_id'])
        batch_op.create_index('ix_users_telegram_id', ['telegram_id'], unique=True)
        
        # Добавляем поле telegram_username (String(255), nullable)
        batch_op.add_column(sa.Column('telegram_username', sa.String(length=255), nullable=True))
        
        # Делаем email nullable для Telegram-only пользователей
        batch_op.alter_column('email', nullable=True)


def downgrade() -> None:
    # Откат: SQLite batch mode
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Делаем email NOT NULL (только если нет NULL значений)
        # ВНИМАНИЕ: может упасть если есть пользователи без email
        batch_op.alter_column('email', nullable=False)
        
        # Удаляем telegram_username
        batch_op.drop_column('telegram_username')
        
        # Удаляем telegram_id с индексом и constraint
        batch_op.drop_index('ix_users_telegram_id')
        batch_op.drop_constraint('uq_users_telegram_id', type_='unique')
        batch_op.drop_column('telegram_id')
