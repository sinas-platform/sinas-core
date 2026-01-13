"""rename_webhooks_to_functions_add_chat_metadata

Revision ID: c54e8e36968b
Revises: 7463d1f50763
Create Date: 2026-01-09 11:20:47.877268

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c54e8e36968b'
down_revision = '7463d1f50763'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename agents table columns
    op.execute('ALTER TABLE agents RENAME COLUMN enabled_webhooks TO enabled_functions')
    op.execute('ALTER TABLE agents RENAME COLUMN webhook_parameters TO function_parameters')

    # Rename messages table column
    op.execute('ALTER TABLE messages RENAME COLUMN enabled_webhooks TO enabled_functions')

    # Add chat_metadata column to chats table
    op.add_column('chats', sa.Column('chat_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove chat_metadata column from chats
    op.drop_column('chats', 'chat_metadata')

    # Rename messages table column back
    op.execute('ALTER TABLE messages RENAME COLUMN enabled_functions TO enabled_webhooks')

    # Rename agents table columns back
    op.execute('ALTER TABLE agents RENAME COLUMN function_parameters TO webhook_parameters')
    op.execute('ALTER TABLE agents RENAME COLUMN enabled_functions TO enabled_webhooks')