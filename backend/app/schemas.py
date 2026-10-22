from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["user", "admin"]
Kind = Literal["offer", "want"]
Level = Literal["beginner", "intermediate", "expert"]
Format = Literal["online", "offline", "both"]
ExchangeStatus = Literal["pending", "accepted", "declined", "completed", "cancelled"]

CATEGORIES = ["languages", "music", "it", "sport", "art", "cooking", "science", "crafts", "business", "other"]


# ---------- Auth / users ----------
class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128)
    city: str = Field(default="", max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: Role
    city: str = ""
    bio: str = ""
    is_blocked: bool = False
    created_at: datetime | None = None


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    city: str = ""
    bio: str = ""
    rating: float | None = None
    reviews: int = 0


class ProfileUpdate(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    city: str = Field(default="", max_length=100)
    bio: str = Field(default="", max_length=2000)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RoleUpdate(BaseModel):
    role: Role


class BlockUpdate(BaseModel):
    is_blocked: bool


# ---------- Skills ----------
class SkillIn(BaseModel):
    kind: Kind
    title: str = Field(min_length=2, max_length=120)
    category: str = "other"
    level: Level = "beginner"
    format: Format = "online"
    description: str = Field(default="", max_length=2000)
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("title is too short")
        return v

    @field_validator("category")
    @classmethod
    def check_category(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}")
        return v


class SkillOut(SkillIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner_name: str | None = None
    owner_city: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Match(BaseModel):
    user: UserPublic
    they_offer: list[SkillOut]  # что партнёр может дать мне
    they_want: list[SkillOut]  # что партнёр хочет и что я могу дать
    mutual: bool
    score: int


# ---------- Exchanges ----------
class ExchangeIn(BaseModel):
    requested_skill_id: int
    offered_skill_id: int | None = None
    message: str = Field(default="", max_length=2000)


class ExchangeUpdate(BaseModel):
    offered_skill_id: int | None = None
    message: str = Field(default="", max_length=2000)


class StatusUpdate(BaseModel):
    status: ExchangeStatus


class RatingIn(BaseModel):
    rating: int = Field(ge=1, le=5)


class ExchangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requester_id: int
    receiver_id: int
    requester_name: str | None = None
    receiver_name: str | None = None
    offered_skill_id: int | None
    requested_skill_id: int | None
    offered_skill_title: str | None = None
    requested_skill_title: str | None = None
    message: str
    status: ExchangeStatus
    requester_rating: int | None = None
    receiver_rating: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
