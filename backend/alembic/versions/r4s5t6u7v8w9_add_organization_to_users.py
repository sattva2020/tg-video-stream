"""add organization to users

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-01-23 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import src.database


# revision identifiers, used by Alembic.
revision: str = 'r4s5t6u7v8w9'
down_revision: Union[str, None] = 'q3r4s5t6u7v8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add organization_id column to users table
    op.add_column(
        'users',
        sa.Column(
            'organization_id',
            src.database.GUID(),
            nullable=True
        )
    )

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_users_organization',
        'users',
        'organizations',
        ['organization_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index for better query performance
    op.create_index(
        op.f('ix_users_organization_id'),
        'users',
        ['organization_id']
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_users_organization_id'), table_name='users')
    op.drop_constraint('fk_users_organization', 'users', type_='foreignkey')
    op.drop_column('users', 'organization_id')
