"""Dining service persistence models.

The dining tables deliberately live in this service's module instead of reusing
the legacy ``t_cart``/``t_order`` tables.  This keeps the migration reversible
and lets the new state machine retain immutable menu snapshots and event
history.  The shared ``Base`` is used so the models can be created by the same
Alembic metadata as the existing application during the transition.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base


class SharedCart(Base):
    __tablename__ = "shared_cart"
    __table_args__ = (
        UniqueConstraint("couple_id", name="uq_shared_cart_couple"),
        UniqueConstraint("user_id", name="uq_shared_cart_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Keep a Python-side default as well as the DB default.  asyncmy may expire
    # server-default columns on a freshly flushed row; cart writes increment
    # ``version`` in the same transaction and must not trigger implicit IO.
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    def __init__(self, **kwargs: object) -> None:
        # SQLAlchemy applies ``default`` during INSERT, not object creation.
        # Initialize eagerly so a new cart can be versioned before any
        # server-default refresh (important for asyncmy sessions).
        kwargs.setdefault("version", 0)
        super().__init__(**kwargs)


class SharedCartItem(Base):
    __tablename__ = "shared_cart_item"
    __table_args__ = (UniqueConstraint("cart_id", "dish_id", name="uq_shared_cart_item_dish"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dish_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    dish_name: Mapped[str] = mapped_column(String(256), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(512), nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class DiningOrder(Base):
    __tablename__ = "dining_order"
    __table_args__ = (UniqueConstraint("order_no", name="uq_dining_order_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(40), nullable=False)
    couple_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'pending_confirmation'")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(512), nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("version", 0)
        super().__init__(**kwargs)


class DiningOrderItem(Base):
    __tablename__ = "dining_order_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dish_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    dish_name: Mapped[str] = mapped_column(String(256), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(512), nullable=True)


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    operator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class IdempotencyRecord(Base):
    __tablename__ = "dining_idempotency_record"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_dining_idempotency"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    response_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class OutboxEvent(Base):
    __tablename__ = "dining_outbox_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'pending'")
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    published_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


__all__ = [
    "DiningOrder",
    "DiningOrderItem",
    "IdempotencyRecord",
    "OrderStatusHistory",
    "OutboxEvent",
    "SharedCart",
    "SharedCartItem",
]
