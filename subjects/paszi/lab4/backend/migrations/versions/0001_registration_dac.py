"""Пользователи, ресурсы и дискреционные права."""
from alembic import op
import sqlalchemy as sa

revision = "0001_registration_dac"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(32), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("login", name="uq_users_login"))
    op.create_table("resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_resources_owner_id", "resources", ["owner_id"])
    op.create_table("resource_permissions",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("resource_id", sa.Integer(), sa.ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("can_read", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_update", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("can_delete", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    op.drop_table("resource_permissions")
    op.drop_index("ix_resources_owner_id", table_name="resources")
    op.drop_table("resources")
    op.drop_table("users")
