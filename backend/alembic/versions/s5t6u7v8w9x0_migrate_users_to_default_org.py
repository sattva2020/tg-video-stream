"""migrate users to default org

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-01-23 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import uuid


# revision identifiers, used by Alembic.
revision: str = 's5t6u7v8w9x0'
down_revision: Union[str, None] = 'r4s5t6u7v8w9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Generate a UUID for the default organization
    default_org_id = str(uuid.uuid4())

    # Insert default organization
    op.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, slug, is_active, created_at, updated_at)
            VALUES (:org_id, 'Default Organization', 'default-org', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(org_id=default_org_id)
    )

    # Update all users without an organization to the default one
    op.execute(
        sa.text(
            """
            UPDATE users
            SET organization_id = :org_id
            WHERE organization_id IS NULL
            """
        ).bindparams(org_id=default_org_id)
    )


def downgrade() -> None:
    # Remove the default organization from users
    op.execute(
        sa.text(
            """
            UPDATE users
            SET organization_id = NULL
            WHERE organization_id IN (
                SELECT id FROM organizations WHERE slug = 'default-org'
            )
            """
        )
    )

    # Delete the default organization
    op.execute(
        sa.text(
            """
            DELETE FROM organizations WHERE slug = 'default-org'
            """
        )
    )
