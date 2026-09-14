"""菜品目录、来源授权与媒体对象表。"""
from alembic import op
import sqlalchemy as sa

revision = "0003_catalog_media"
down_revision = "0002_daily_greeting_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_cuisine",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
    )
    op.create_table(
        "catalog_dish",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("cuisine_slug", sa.String(64), nullable=False),
        sa.Column("tags_json", sa.Text(), nullable=False),
        sa.Column("allergens_json", sa.Text(), nullable=False),
        sa.Column("spicy_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("image_url", sa.String(512)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_catalog_dish_cuisine_slug", "catalog_dish", ["cuisine_slug"])
    op.create_index("ix_catalog_dish_status", "catalog_dish", ["status"])
    op.create_table(
        "catalog_dish_image",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("dish_slug", sa.String(128), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=False),
        sa.Column("license_name", sa.String(128), nullable=False),
        sa.Column("attribution", sa.String(512), nullable=False),
        sa.Column("license_expires_at", sa.DateTime()),
        sa.Column("review_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("thumbnail_key", sa.String(512)),
    )
    op.create_index("ix_catalog_dish_image_dish_slug", "catalog_dish_image", ["dish_slug"])
    op.create_table(
        "catalog_import_batch",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_report_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("catalog_import_batch")
    op.drop_index("ix_catalog_dish_image_dish_slug", table_name="catalog_dish_image")
    op.drop_table("catalog_dish_image")
    op.drop_index("ix_catalog_dish_status", table_name="catalog_dish")
    op.drop_index("ix_catalog_dish_cuisine_slug", table_name="catalog_dish")
    op.drop_table("catalog_dish")
    op.drop_table("catalog_cuisine")
