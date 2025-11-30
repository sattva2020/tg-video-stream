"""merge_telegram_and_existing

Revision ID: 51380808ac02
Revises: e1f2g3h4i5j6, f5e6d7c8b9a0
Create Date: 2025-11-30 11:38:46.085377

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51380808ac02'
down_revision: Union[str, None] = ('e1f2g3h4i5j6', 'f5e6d7c8b9a0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
