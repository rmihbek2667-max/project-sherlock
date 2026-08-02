"""ORM models. Keep gameplay content (seasons/clues) fully data-driven so new
seasons never require a code change — only rows."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ClueMediaType(str, enum.Enum):
    """Pre-built so image/audio/video/qr/location clues need no migration later."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    QR = "qr"
    LOCATION = "location"


class ProgressStatus(str, enum.Enum):
    LOCKED = "locked"       # not yet released / previous day unfinished
    AVAILABLE = "available"  # released, not yet attempted
    SOLVED = "solved"
    FAILED = "failed"       # 3 wrong attempts, no points


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(128))
    language: Mapped[str | None] = mapped_column(String(2), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    progress: Mapped[list["JournalEntry"]] = relationship(back_populates="user")


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    submissions_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    clues: Mapped[list["Clue"]] = relationship(back_populates="season", order_by="Clue.day_number")


class Clue(Base):
    __tablename__ = "clues"
    __table_args__ = (UniqueConstraint("season_id", "day_number", name="uq_season_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    day_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(128))
    clue_text: Mapped[str] = mapped_column(Text)
    media_type: Mapped[ClueMediaType] = mapped_column(Enum(ClueMediaType), default=ClueMediaType.TEXT)
    media_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    # list of acceptable answers (synonyms/variants), matched case/space-insensitively
    correct_answers: Mapped[list[str]] = mapped_column(JSON, default=list)
    release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    season: Mapped["Season"] = relationship(back_populates="clues")


class JournalEntry(Base):
    """One row per (user, clue) — this IS the Detective Journal's backing store.
    Updated as attempts come in; read directly by /journal."""

    __tablename__ = "journal_entries"
    __table_args__ = (UniqueConstraint("user_id", "clue_id", name="uq_user_clue"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    clue_id: Mapped[int] = mapped_column(ForeignKey("clues.id"))
    status: Mapped[ProgressStatus] = mapped_column(Enum(ProgressStatus), default=ProgressStatus.LOCKED)
    attempts_used: Mapped[int] = mapped_column(Integer, default=0)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    hint_used: Mapped[bool] = mapped_column(Boolean, default=False)
    last_submitted_answer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # future: free-form investigation notes
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="progress")
    clue: Mapped["Clue"] = relationship()
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="journal_entry", order_by="Attempt.attempt_number")


class Attempt(Base):
    """Every individual guess, for audit + attempts-left calculation."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"))
    attempt_number: Mapped[int] = mapped_column(Integer)
    submitted_answer: Mapped[str] = mapped_column(String(256))
    is_correct: Mapped[bool] = mapped_column(Boolean)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    journal_entry: Mapped["JournalEntry"] = relationship(back_populates="attempts")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(32))  # new_clue, reminder, season_ending, winner, etc.
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_telegram_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
