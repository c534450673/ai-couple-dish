"""管理员、审计和 analytics 聚合表（仅新增，不改旧表）。"""

import logging

import sqlalchemy as sa
from alembic import op

revision = "0005_admin_analytics"
down_revision = "0004_dining"
branch_labels = None
depends_on = None
LOGGER = logging.getLogger("alembic.admin_analytics")


def upgrade() -> None:
    LOGGER.info("event=admin_analytics_migration_started operation=upgrade result=started")
    op.create_table(
        "admin_user",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("roles_json", sa.String(255), nullable=False, server_default='["admin"]'),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_unique_constraint("uq_admin_user_username", "admin_user", ["username"])
    op.create_table(
        "admin_session",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("admin_user_id", sa.BigInteger(), nullable=False),
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_unique_constraint("uq_admin_session_jti", "admin_session", ["jti"])
    op.create_index("ix_admin_session_user", "admin_session", ["admin_user_id"])
    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("admin_user_id", sa.BigInteger(), nullable=True),
        sa.Column("operation", sa.String(128), nullable=False),
        sa.Column("target_type", sa.String(64)),
        sa.Column("target_id", sa.String(128)),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("metadata_json", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_index("ix_admin_audit_created", "admin_audit_log", ["created_at"])
    op.create_table(
        "analytics_event",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("event_name", sa.String(128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.BigInteger()),
        sa.Column("couple_id", sa.BigInteger()),
        sa.Column("mode", sa.String(16), nullable=False, server_default="couple"),
        sa.Column("duration_ms", sa.Integer()),
    )
    op.create_index("ix_analytics_event_time", "analytics_event", ["occurred_at"])
    for table, period_type in (("analytics_hourly", "hour"), ("analytics_daily", "day")):
        op.create_table(
            table,
            sa.Column("period", sa.String(32), primary_key=True),
            sa.Column("period_type", sa.String(16), nullable=False, server_default=period_type),
            sa.Column("metrics_json", sa.Text(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
    LOGGER.info("event=admin_analytics_migration_completed operation=upgrade result=success")


def downgrade() -> None:
    LOGGER.warning(
        "event=admin_analytics_migration_downgrade_started operation=downgrade result=started"
    )
    for table in (
        "analytics_daily",
        "analytics_hourly",
        "analytics_event",
        "admin_audit_log",
        "admin_session",
        "admin_user",
    ):
        op.drop_table(table)
    LOGGER.warning(
        "event=admin_analytics_migration_downgrade_completed operation=downgrade result=success"
    )
