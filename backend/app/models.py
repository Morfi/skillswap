from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    city: Mapped[str] = mapped_column(String(100), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    skills: Mapped[list["Skill"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Skill(Base):
    """Карточка навыка: пользователь либо предлагает (offer), либо ищет (want) навык."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)  # offer | want
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(50), index=True)
    level: Mapped[str] = mapped_column(String(20), default="beginner")
    format: Mapped[str] = mapped_column(String(20), default="online")
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    owner: Mapped[User] = relationship(back_populates="skills")


class Exchange(Base):
    """Заявка на обмен: «я научу тебя X, а ты меня — Y»."""

    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    offered_skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)
    requested_skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    requester_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # оценка, которую поставил requester
    receiver_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # оценка, которую поставил receiver
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    receiver: Mapped[User] = relationship(foreign_keys=[receiver_id])
    offered_skill: Mapped[Skill | None] = relationship(foreign_keys=[offered_skill_id])
    requested_skill: Mapped[Skill | None] = relationship(foreign_keys=[requested_skill_id])
