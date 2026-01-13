"""add_enabled_namespaces_to_functions

Revision ID: f3a1b496bb36
Revises: c54e8e36968b
Create Date: 2026-01-12 10:56:39.182959

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a1b496bb36'
down_revision = 'c54e8e36968b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add enabled_namespaces column to functions table
    op.add_column('functions', sa.Column('enabled_namespaces', sa.JSON(), nullable=True))

    # Set default to empty list for existing rows
    op.execute("UPDATE functions SET enabled_namespaces = '[]'::json WHERE enabled_namespaces IS NULL")


def downgrade() -> None:
    # Remove enabled_namespaces column
    op.drop_column('functions', 'enabled_namespaces')