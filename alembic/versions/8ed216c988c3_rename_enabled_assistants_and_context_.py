"""rename_enabled_assistants_and_context_namespaces

Revision ID: 8ed216c988c3
Revises: c09b0af1c107
Create Date: 2026-01-07 08:40:07.351430

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8ed216c988c3'
down_revision = 'c09b0af1c107'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename columns using ALTER TABLE
    op.execute('ALTER TABLE agents RENAME COLUMN enabled_assistants TO enabled_agents')
    op.execute('ALTER TABLE agents RENAME COLUMN context_namespaces TO state_namespaces')


def downgrade() -> None:
    # Rename columns back
    op.execute('ALTER TABLE agents RENAME COLUMN enabled_agents TO enabled_assistants')
    op.execute('ALTER TABLE agents RENAME COLUMN state_namespaces TO context_namespaces')