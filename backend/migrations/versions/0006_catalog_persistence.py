"""将目录价格和逐条授权资料落到数据库。"""

import logging

import sqlalchemy as sa
from alembic import op

revision = "0006_catalog_persistence"
down_revision = "0005_admin_analytics"
branch_labels = None
depends_on = None

LOGGER = logging.getLogger("alembic.catalog_persistence")


def upgrade() -> None:
    LOGGER.info("event=catalog_persistence_migration_started operation=upgrade result=started")
    inspector = sa.inspect(op.get_bind())
    dish_columns = {column["name"] for column in inspector.get_columns("catalog_dish")}
    if "unit_price" not in dish_columns:
        op.add_column("catalog_dish", sa.Column("unit_price", sa.Numeric(10, 2), nullable=True))
        LOGGER.info("event=catalog_unit_price_added operation=upgrade result=success")
    else:
        LOGGER.info("event=catalog_unit_price_skipped operation=upgrade result=already_exists")

    if "catalog_dish_source" not in inspector.get_table_names():
        op.create_table(
            "catalog_dish_source",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("dish_id", sa.BigInteger(), nullable=False),
            sa.Column("source_url", sa.String(1024), nullable=False),
            sa.Column("source_url_fingerprint", sa.String(64), nullable=False),
            sa.Column("license_name", sa.String(128), nullable=False),
            sa.Column("attribution", sa.String(512), nullable=False),
            sa.Column("review_status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("collected_at", sa.DateTime(), nullable=True),
            sa.Column("license_expires_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["dish_id"], ["catalog_dish.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "dish_id",
                "source_url_fingerprint",
                name="uk_catalog_dish_source_fingerprint",
            ),
        )
        op.create_index("ix_catalog_dish_source_dish_id", "catalog_dish_source", ["dish_id"])
        op.create_index(
            "ix_catalog_dish_source_review_status", "catalog_dish_source", ["review_status"]
        )
        LOGGER.info("event=catalog_dish_source_created operation=upgrade result=success")
    else:
        LOGGER.info("event=catalog_dish_source_skipped operation=upgrade result=already_exists")
    LOGGER.info("event=catalog_persistence_migration_completed operation=upgrade result=success")


def downgrade() -> None:
    LOGGER.warning("event=catalog_persistence_migration_started operation=downgrade result=started")
    inspector = sa.inspect(op.get_bind())
    if "catalog_dish_source" in inspector.get_table_names():
        indexes = {index["name"] for index in inspector.get_indexes("catalog_dish_source")}
        for index_name in (
            "ix_catalog_dish_source_review_status",
            "ix_catalog_dish_source_dish_id",
        ):
            if index_name in indexes:
                op.drop_index(index_name, table_name="catalog_dish_source")
        op.drop_table("catalog_dish_source")
    if "unit_price" in {column["name"] for column in inspector.get_columns("catalog_dish")}:
        op.drop_column("catalog_dish", "unit_price")
    LOGGER.warning(
        "event=catalog_persistence_migration_completed operation=downgrade result=success"
    )
