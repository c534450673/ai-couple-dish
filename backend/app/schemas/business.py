from datetime import date
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
