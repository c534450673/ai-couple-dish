from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Integer, Numeric, String, Text, text
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


class CoupleRank(Base):
    __tablename__ = "t_couple_rank"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_rank: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'bronze'")
    )
    rank_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    consecutive_interaction_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    temperature_score: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("60")
    )
    promotion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    demotion_warning: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class CoupleTree(Base):
    __tablename__ = "t_couple_tree"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    total_nutrient: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    current_level_nutrient: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    skin_id: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("'default'")
    )
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class TreeNutrientLog(Base):
    __tablename__ = "t_tree_nutrient_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    nutrient_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    source_action: Mapped[str] = mapped_column(String(64), nullable=False)
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class DailyGreeting(Base):
    __tablename__ = "t_daily_greeting"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    greeting_type: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(String(512), nullable=True)
    voice_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    voice_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    greeting_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class GreetingStreak(Base):
    __tablename__ = "t_greeting_streak"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    streak_type: Mapped[int] = mapped_column(Integer, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class DailyTask(Base):
    __tablename__ = "t_daily_task"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    task_date: Mapped[date] = mapped_column(Date, nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    reward_nutrient: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class UserTaskProgress(Base):
    __tablename__ = "t_user_task_progress"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    current_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_completed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    complete_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_reward_claimed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    reward_claim_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


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


class Feed(Base):
    __tablename__ = "t_feed"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    receiver_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    feed_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    expire_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reject_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    receive_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Wish(Base):
    __tablename__ = "t_wish"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wish_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("2"))
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    viewer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    view_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    in_progress_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    achieved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class FoodNote(Base):
    __tablename__ = "t_food_note"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)
    is_anniversary_linked: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    anniversary_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    photo_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class NoteLike(Base):
    __tablename__ = "t_note_like"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Anniversary(Base):
    __tablename__ = "t_anniversary"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    anniversary_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_lunar_date: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lunar_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lunar_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anniversary_type: Mapped[int] = mapped_column(Integer, nullable=False)
    remind_days_before: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("7")
    )
    auto_remind: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    last_remind_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    remind_channels: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remind_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wechat_remind_enabled: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    sms_remind_enabled: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    app_remind_enabled: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class CoupleMenu(Base):
    __tablename__ = "t_couple_menu"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    restaurant_name: Mapped[str] = mapped_column(String(256), nullable=False)
    dish_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    dish_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eater_ids: Mapped[str | None] = mapped_column(String(512), nullable=True)
    eaten_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_favorite: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    photo_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    anniversary_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    delete_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Recipe(Base):
    __tablename__ = "t_recipe"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingredients: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cooking_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    servings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    collect_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class RecipeLike(Base):
    __tablename__ = "t_recipe_like"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class RecipeCollect(Base):
    __tablename__ = "t_recipe_collect"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Cart(Base):
    __tablename__ = "t_cart"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recipe_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Order(Base):
    __tablename__ = "t_order"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    buyer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seller_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recipe_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recipe_name: Mapped[str] = mapped_column(String(256), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    pay_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accept_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    complete_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancel_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class HeartMoment(Base):
    __tablename__ = "t_heart_moment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class MoodRecord(Base):
    __tablename__ = "t_mood_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mood_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mood_icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mood_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_read: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    read_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class TimeCapsule(Base):
    """情侣时光胶囊；媒体地址以 JSON 数组存储以兼容 Spring 表结构。"""

    __tablename__ = "t_time_capsule"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    capsule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    unlock_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_deleted: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    unlock_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
