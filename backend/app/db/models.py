from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "t_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), nullable=False)
    nick_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[int | None] = mapped_column(Integer, nullable=True)
    couple_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    love_start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    member_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class Couple(Base):
    __tablename__ = "t_couple"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user1_id: Mapped[int] = mapped_column("user_1_id", BigInteger, nullable=False)
    user2_id: Mapped[int | None] = mapped_column("user_2_id", BigInteger, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    love_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    couple_nickname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    unbind_applicant_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    unbind_apply_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CoupleUnbindRecord(Base):
    __tablename__ = "t_couple_unbind_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user1_id: Mapped[int] = mapped_column("user_1_id", BigInteger, nullable=False)
    user2_id: Mapped[int] = mapped_column("user_2_id", BigInteger, nullable=False)
    applicant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    love_start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    love_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    couple_nickname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    unbind_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_expire_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class Notification(Base):
    __tablename__ = "t_notification"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    related_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_read: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    read_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
