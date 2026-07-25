from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Phone = Annotated[str, StringConstraints(pattern=r"^1[3-9]\d{9}$")]


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)
    nick_name: str | None = Field(default=None, alias="nickName", max_length=64)
    avatar_url: str | None = Field(default=None, alias="avatarUrl", max_length=512)

    model_config = ConfigDict(populate_by_name=True)


class PhoneLoginRequest(BaseModel):
    phone: Phone
    verify_code: str | None = Field(default=None, alias="verifyCode", max_length=16)

    model_config = ConfigDict(populate_by_name=True)


class UpdateUserRequest(BaseModel):
    nick_name: str | None = Field(default=None, alias="nickName", max_length=64)
    avatar_url: str | None = Field(default=None, alias="avatarUrl", max_length=512)

    model_config = ConfigDict(populate_by_name=True)


class GenerateCodeRequest(BaseModel):
    love_start_date: date | None = Field(default=None, alias="loveStartDate")

    model_config = ConfigDict(populate_by_name=True)


class BindCoupleRequest(BaseModel):
    couple_code: str = Field(alias="coupleCode", min_length=1, max_length=32)

    model_config = ConfigDict(populate_by_name=True)


class CoupleRankClaimRequest(BaseModel):
    rank: str = Field(min_length=1, max_length=32)


class WaterTreeRequest(BaseModel):
    nutrient_amount: int | None = Field(default=None, alias="nutrientAmount", ge=1, le=1000)
    source_action: str | None = Field(default=None, alias="sourceAction", max_length=64)
    remark: str | None = Field(default=None, max_length=256)

    model_config = ConfigDict(populate_by_name=True)


class DailyGreetingRequest(BaseModel):
    greeting_type: int = Field(alias="greetingType", ge=1, le=2)
    content: str | None = Field(default=None, max_length=512)
    voice_url: str | None = Field(default=None, alias="voiceUrl", max_length=512)
    voice_duration: int | None = Field(default=None, alias="voiceDuration", ge=0, le=3600)

    model_config = ConfigDict(populate_by_name=True)


class UnbindRequest(BaseModel):
    option: str | None = Field(default=None, pattern=r"^(keep|delete)$")


class UserInfoResponse(BaseModel):
    id: int
    openid: str
    nick_name: str | None = Field(default=None, alias="nickName")
    avatar_url: str | None = Field(default=None, alias="avatarUrl")
    phone: str | None = None
    gender: int | None = None
    couple_id: int | None = Field(default=None, alias="coupleId")
    love_start_date: str | None = Field(default=None, alias="loveStartDate")
    member_level: int = Field(alias="memberLevel")
    status: int

    model_config = ConfigDict(populate_by_name=True)


class MenuRequest(BaseModel):
    restaurant_name: str = Field(alias="restaurantName", min_length=1, max_length=256)
    dish_name: str | None = Field(default=None, alias="dishName", max_length=256)
    dish_category: str | None = Field(default=None, alias="dishCategory", max_length=64)
    price: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    location: str | None = Field(default=None, max_length=512)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    note: str | None = Field(default=None, max_length=5000)
    rating: int | None = Field(default=None, ge=1, le=5)
    eater_ids: list[int] | None = Field(default=None, alias="eaterIds", max_length=2)
    eaten_date: date | None = Field(default=None, alias="eatenDate")
    status: int | None = Field(default=None, ge=0, le=2)
    anniversary_id: int | None = Field(default=None, alias="anniversaryId", ge=1)
    photo_urls: list[str] | None = Field(default=None, alias="photoUrls", max_length=20)

    model_config = ConfigDict(populate_by_name=True)


class RecipeIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    amount: str | None = Field(default=None, max_length=128)


class RecipeStep(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=512)

    model_config = ConfigDict(populate_by_name=True)


class RecipeRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    cover_url: str | None = Field(default=None, alias="coverUrl", max_length=512)
    description: str | None = Field(default=None, max_length=2000)
    ingredients: list[RecipeIngredient] | None = Field(default=None, max_length=100)
    steps: list[RecipeStep] | None = Field(default=None, max_length=100)
    difficulty: str | None = Field(default=None, max_length=32)
    cooking_time: int | None = Field(default=None, alias="cookingTime", ge=1, le=1440)
    servings: int | None = Field(default=None, ge=1, le=100)
    publish: bool = False

    model_config = ConfigDict(populate_by_name=True)


class AddToCartRequest(BaseModel):
    recipe_id: int = Field(alias="recipeId", ge=1)
    quantity: int = Field(default=1, ge=1)

    model_config = ConfigDict(populate_by_name=True)


class CreateOrderRequest(BaseModel):
    recipe_id: int = Field(alias="recipeId", ge=1)
    quantity: int = Field(default=1, ge=1)
    address: str | None = Field(default=None, max_length=512)
    remark: str | None = Field(default=None, max_length=512)

    model_config = ConfigDict(populate_by_name=True)


class NoteRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=50_000)
    location: str | None = Field(default=None, max_length=512)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    is_anniversary_linked: int | None = Field(default=None, alias="isAnniversaryLinked", ge=0, le=1)
    anniversary_id: int | None = Field(default=None, alias="anniversaryId", ge=1)
    photo_urls: list[str] | None = Field(default=None, alias="photoUrls", max_length=20)

    model_config = ConfigDict(populate_by_name=True)


class NoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    content: str | None = Field(default=None, min_length=1, max_length=50_000)
    location: str | None = Field(default=None, max_length=512)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    is_anniversary_linked: int | None = Field(default=None, alias="isAnniversaryLinked", ge=0, le=1)
    anniversary_id: int | None = Field(default=None, alias="anniversaryId", ge=1)
    photo_urls: list[str] | None = Field(default=None, alias="photoUrls", max_length=20)

    model_config = ConfigDict(populate_by_name=True)


class AnniversaryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    anniversary_date: date = Field(alias="anniversaryDate")
    is_lunar_date: int = Field(default=0, alias="isLunarDate", ge=0, le=1)
    lunar_month: int | None = Field(default=None, alias="lunarMonth", ge=1, le=12)
    lunar_day: int | None = Field(default=None, alias="lunarDay", ge=1, le=30)
    anniversary_type: int = Field(alias="anniversaryType", ge=1, le=4)
    remind_days_before: int = Field(default=7, alias="remindDaysBefore", ge=0, le=365)
    auto_remind: int = Field(default=1, alias="autoRemind", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class AnniversaryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    anniversary_date: date | None = Field(default=None, alias="anniversaryDate")
    is_lunar_date: int | None = Field(default=None, alias="isLunarDate", ge=0, le=1)
    lunar_month: int | None = Field(default=None, alias="lunarMonth", ge=1, le=12)
    lunar_day: int | None = Field(default=None, alias="lunarDay", ge=1, le=30)
    anniversary_type: int | None = Field(default=None, alias="anniversaryType", ge=1, le=4)
    remind_days_before: int | None = Field(default=None, alias="remindDaysBefore", ge=0, le=365)
    auto_remind: int | None = Field(default=None, alias="autoRemind", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class ReminderConfigRequest(BaseModel):
    anniversary_id: int = Field(alias="anniversaryId", ge=1)
    auto_remind: int | None = Field(default=None, alias="autoRemind", ge=0, le=1)
    remind_days_before: int | None = Field(default=None, alias="remindDaysBefore", ge=0, le=365)
    remind_channels: str | None = Field(default=None, alias="remindChannels", max_length=128)
    remind_hour: int | None = Field(default=None, alias="remindHour", ge=0, le=23)
    wechat_remind_enabled: int | None = Field(default=None, alias="wechatRemindEnabled", ge=0, le=1)
    sms_remind_enabled: int | None = Field(default=None, alias="smsRemindEnabled", ge=0, le=1)
    app_remind_enabled: int | None = Field(default=None, alias="appRemindEnabled", ge=0, le=1)

    model_config = ConfigDict(populate_by_name=True)


class SendFeedRequest(BaseModel):
    feed_type: str = Field(alias="feedType", min_length=1, max_length=32)
    content: str | None = Field(default=None, max_length=50_000)
    image_urls: list[str] | None = Field(default=None, alias="imageUrls", max_length=20)
    message: str | None = Field(default=None, max_length=256)

    model_config = ConfigDict(populate_by_name=True)


class WishCreateRequest(BaseModel):
    wish_type: str = Field(alias="wishType", min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=50_000)
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=1024)
    priority: int | None = Field(default=None, ge=1, le=3)

    model_config = ConfigDict(populate_by_name=True)


class WishUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=50_000)
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=1024)
    priority: int | None = Field(default=None, ge=1, le=3)

    model_config = ConfigDict(populate_by_name=True)


class HeartMomentRequest(BaseModel):
    moment_type: str = Field(alias="momentType", min_length=1, max_length=32)
    content: str | None = Field(default=None, max_length=50_000)
    media_url: str | None = Field(default=None, alias="mediaUrl", max_length=512)

    model_config = ConfigDict(populate_by_name=True)


class TimeCapsuleRequest(BaseModel):
    capsule_type: str = Field(alias="capsuleType", min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=256)
    content: str | None = Field(default=None, max_length=50_000)
    media_urls: list[str] | None = Field(default=None, alias="mediaUrls", max_length=20)
    unlock_date: date = Field(alias="unlockDate")

    model_config = ConfigDict(populate_by_name=True)


class MoodRecordRequest(BaseModel):
    mood_type: str = Field(alias="moodType", min_length=1, max_length=32)
    description: str | None = Field(default=None, max_length=512)

    model_config = ConfigDict(populate_by_name=True)


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    session_id: str | None = Field(default=None, alias="sessionId", max_length=128)

    model_config = ConfigDict(populate_by_name=True)


class AiConfirmRequest(BaseModel):
    session_id: str = Field(alias="sessionId", min_length=1, max_length=128)

    model_config = ConfigDict(populate_by_name=True)


class AiGenerateRequest(BaseModel):
    type: str = Field(min_length=1, max_length=32)
    prompt: str = Field(min_length=1, max_length=10_000)
