"""Detective Journal is a first-class gameplay feature, so it gets its own
service rather than being inlined into a handler. This is what a future web
dashboard or /journal export command would also call."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database.models import Clue, JournalEntry, ProgressStatus


async def get_or_create_entry(session: AsyncSession, user_id: int, clue_id: int) -> JournalEntry:
    result = await session.execute(
        select(JournalEntry).where(JournalEntry.user_id == user_id, JournalEntry.clue_id == clue_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        entry = JournalEntry(user_id=user_id, clue_id=clue_id, status=ProgressStatus.AVAILABLE)
        session.add(entry)
        await session.flush()
    return entry


async def record_attempt(
    session: AsyncSession,
    entry: JournalEntry,
    submitted_answer: str,
    is_correct: bool,
    points_awarded: int,
    used_hint: bool = False,
) -> None:
    from app.database.models import Attempt

    entry.attempts_used += 1
    entry.last_submitted_answer = submitted_answer
    entry.hint_used = entry.hint_used or used_hint

    attempt = Attempt(
        journal_entry_id=entry.id,
        attempt_number=entry.attempts_used,
        submitted_answer=submitted_answer,
        is_correct=is_correct,
        points_awarded=points_awarded,
    )
    session.add(attempt)

    if is_correct:
        entry.status = ProgressStatus.SOLVED
        entry.points_earned = points_awarded
        entry.completed_at = datetime.utcnow()
    elif entry.attempts_used >= 3:
        entry.status = ProgressStatus.FAILED
        entry.points_earned = 0


async def get_full_journal(session: AsyncSession, user_id: int, season_id: int) -> list[JournalEntry]:
    """All journal entries for a user across a season's clues, ordered by day —
    including days not yet started (rendered as locked by the caller)."""
    result = await session.execute(
        select(JournalEntry)
        .options(joinedload(JournalEntry.clue))
        .join(Clue, Clue.id == JournalEntry.clue_id)
        .where(JournalEntry.user_id == user_id, Clue.season_id == season_id)
        .order_by(Clue.day_number)
    )
    return list(result.scalars().all())
