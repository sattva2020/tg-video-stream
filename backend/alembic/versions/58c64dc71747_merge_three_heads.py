"""merge_three_heads

Revision ID: 58c64dc71747
Revises: bdd925ff9ef7, l1m2n3o4p5q6, d2d1a1551516
Create Date: 2025-12-16 14:51:24.763111

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58c64dc71747'
down_revision: Union[str, None] = ('bdd925ff9ef7', 'l1m2n3o4p5q6', 'd2d1a1551516')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
