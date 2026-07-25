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
