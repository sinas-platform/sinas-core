"""add packages table, rename installed_packages to dependencies

Revision ID: fe05de67fg89
Revises: fe04cd56ef78
Create Date: 2026-03-01
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fe05de67fg89"
down_revision = "fe04cd56ef78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename installed_packages table to dependencies
    op.rename_table("installed_packages", "dependencies")

    # Drop old unique constraint and create new one
    op.drop_constraint("uix_package_name", "dependencies", type_="unique")
    op.create_unique_constraint("uix_dependency_package_name", "dependencies", ["package_name"])

    # Create packages table
    op.create_table(
        "packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("source_yaml", sa.Text(), nullable=False),
        sa.Column("installed_by", sa.Uuid(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["installed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_packages_name", "packages", ["name"])


def downgrade() -> None:
    # Drop packages table
    op.drop_index("ix_packages_name", table_name="packages")
    op.drop_table("packages")

    # Rename dependencies back to installed_packages
    op.drop_constraint("uix_dependency_package_name", "dependencies", type_="unique")
    op.create_unique_constraint("uix_package_name", "dependencies", ["package_name"])
    op.rename_table("dependencies", "installed_packages")
