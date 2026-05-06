from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey,
    Integer, String, Text, func, ARRAY,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Gender(str, enum.Enum):
    male = "male"
    female = "female"


INTERESTS_LIST = [
    "музыка", "спорт", "игры", "кино", "аниме",
    "технологии", "путешествия", "книги", "искусство", "кулинария"
]

ROOM_LIST = [
    "общение", "флирт", "дружба", "помощь", "юмор"
]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender))
    age: Mapped[int | None] = mapped_column(Integer)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reputation: Mapped[int] = mapped_column(Integer, default=0)
    total_chats: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Filter preferences
    pref_gender: Mapped[Gender | None] = mapped_column(Enum(Gender), nullable=True)
    pref_age_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pref_age_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interests: Mapped[str | None] = mapped_column(String(256), nullable=True)  # comma-separated
    preferred_room: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Captcha
    captcha_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Last partner (for "continue chat")
    last_partner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    referral_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relations
    sent_reports: Mapped[list[Report]] = relationship(
        "Report", foreign_keys="Report.reporter_id", back_populates="reporter"
    )
    received_reports: Mapped[list[Report]] = relationship(
        "Report", foreign_keys="Report.reported_id", back_populates="reported"
    )


class Session(Base):
    """Active or past chat sessions between two users."""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_a: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    user_b: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage", back_populates="session"
    )


class ChatMessage(Base):
    """Last N messages per session for moderation."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"))
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[Session] = relationship("Session", back_populates="messages")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    reported_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sessions.id"))
    reason: Mapped[str | None] = mapped_column(String(256))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reporter: Mapped[User] = relationship("User", foreign_keys=[reporter_id], back_populates="sent_reports")
    reported: Mapped[User] = relationship("User", foreign_keys=[reported_id], back_populates="received_reports")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    telegram_charge_id: Mapped[str] = mapped_column(String(128))
    amount: Mapped[int] = mapped_column(Integer)        # in Stars
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)