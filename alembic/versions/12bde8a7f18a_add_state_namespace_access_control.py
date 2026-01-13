"""add_state_namespace_access_control

Revision ID: 12bde8a7f18a
Revises: f3a1b496bb36
Create Date: 2026-01-12 11:25:56.734828

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '12bde8a7f18a'
down_revision = 'f3a1b496bb36'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add state_namespaces_readonly column
    op.add_column('agents', sa.Column('state_namespaces_readonly', sa.JSON(), nullable=True))

    # Rename state_namespaces to state_namespaces_readwrite
    op.execute('ALTER TABLE agents RENAME COLUMN state_namespaces TO state_namespaces_readwrite')

    # Set defaults for existing rows (handle NULL values)
    op.execute("UPDATE agents SET state_namespaces_readonly = '[]'::json WHERE state_namespaces_readonly IS NULL")
    op.execute("UPDATE agents SET state_namespaces_readwrite = '[]'::json WHERE state_namespaces_readwrite IS NULL")


def downgrade() -> None:
    # Rename back
    op.execute('ALTER TABLE agents RENAME COLUMN state_namespaces_readwrite TO state_namespaces')

    # Remove readonly column
    op.drop_column('agents', 'state_namespaces_readonly')