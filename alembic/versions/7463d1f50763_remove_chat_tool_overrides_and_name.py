"""remove_chat_tool_overrides_and_name

Revision ID: 7463d1f50763
Revises: 8ed216c988c3
Create Date: 2026-01-07 08:58:16.187131

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7463d1f50763'
down_revision = '8ed216c988c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop chat tool override fields and name field
    op.drop_column('chats', 'enabled_agents')
    op.drop_column('chats', 'enabled_mcp_tools')
    op.drop_column('chats', 'enabled_webhooks')
    op.drop_column('chats', 'name')


def downgrade() -> None:
    # Restore removed fields
    op.add_column('chats', sa.Column('name', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('chats', sa.Column('enabled_webhooks', postgresql.JSON(astext_type=sa.Text()), server_default='[]', autoincrement=False, nullable=False))
    op.add_column('chats', sa.Column('enabled_mcp_tools', postgresql.JSON(astext_type=sa.Text()), server_default='[]', autoincrement=False, nullable=False))
    op.add_column('chats', sa.Column('enabled_agents', postgresql.JSON(astext_type=sa.Text()), server_default='[]', autoincrement=False, nullable=False))