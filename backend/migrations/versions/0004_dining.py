"""Create the Python dining cart/order tables.

The migration is additive.  Existing ``t_cart`` and ``t_order`` remain owned by
the legacy routes until cutover, so rollback can simply remove the new owner
without touching historical records.
"""

import logging

import sqlalchemy as sa
from alembic import op

revision = "0004_dining"
down_revision = "0003_catalog_media"
branch_labels = None
depends_on = None

LOGGER = logging.getLogger("alembic.dining")


def upgrade() -> None:
    LOGGER.info("event=dining_migration_started operation=upgrade result=started")
    op.create_table(
        "shared_cart",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("couple_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "update_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("couple_id", name="uq_shared_cart_couple"),
        sa.UniqueConstraint("user_id", name="uq_shared_cart_user"),
    )
    op.create_table(
        "shared_cart_item",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cart_id", sa.BigInteger(), nullable=False),
        sa.Column("dish_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("dish_name", sa.String(256), nullable=False),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("remark", sa.String(512), nullable=True),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "update_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cart_id", "dish_id", name="uq_shared_cart_item_dish"),
    )
    op.create_table(
        "dining_order",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_no", sa.String(40), nullable=False),
        sa.Column("couple_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            server_default=sa.text("'pending_confirmation'"),
            nullable=False,
        ),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("remark", sa.String(512), nullable=True),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "update_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_no", name="uq_dining_order_no"),
    )
    op.create_table(
        "dining_order_item",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("dish_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("dish_name", sa.String(256), nullable=False),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("remark", sa.String(512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "order_status_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("operator_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(512), nullable=True),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "dining_idempotency_record",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_dining_idempotency"),
    )
    op.create_table(
        "dining_outbox_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("aggregate_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.BigInteger(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), server_default=sa.text("'pending'"), nullable=False),
        sa.Column(
            "create_time",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("published_time", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    LOGGER.info("event=dining_migration_completed operation=upgrade result=success")


def downgrade() -> None:
    LOGGER.warning("event=dining_migration_downgrade_started operation=downgrade result=started")
    for table in (
        "dining_outbox_event",
        "dining_idempotency_record",
        "order_status_history",
        "dining_order_item",
        "dining_order",
        "shared_cart_item",
        "shared_cart",
    ):
        op.drop_table(table)
    LOGGER.warning("event=dining_migration_downgrade_completed operation=downgrade result=success")
