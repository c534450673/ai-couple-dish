"""目录领域模型。

模型独立于旧单体表，迁移时可直接映射到 catalog_* 表；来源和图片授权信息
保留在行级，保证审核和下架操作可追溯。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class Cuisine(Base):
    __tablename__ = "catalog_cuisine"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")


class DishRecord(Base):
    __tablename__ = "catalog_dish"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cuisine_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    allergens_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    spicy_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    __table_args__ = (UniqueConstraint("slug", name="uk_catalog_dish_slug"),)


class DishImage(Base):
    __tablename__ = "catalog_dish_image"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dish_slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    license_name: Mapped[str] = mapped_column(String(128), nullable=False)
    attribution: Mapped[str] = mapped_column(String(512), nullable=False)
    license_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)


class CatalogImportBatch(Base):
    __tablename__ = "catalog_import_batch"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_report_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
