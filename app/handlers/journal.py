from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.database.models import ProgressStatus, Season, User
from app.localization.loader import t
from app.services import journal_service

router = Router(name="journal")


@router.message(Command("journal"))
async def cmd_journal(message: Message, db_user: User, session) -> None:
    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    season = result.scalar_one_or_none()
    if season is None:
        await message.answer(t("journal_empty", db_user.language))
        return

    entries = await journal_service.get_full_journal(session, db_user.id, season.id)
    if not entries:
        await message.answer(t("journal_empty", db_user.language))
        return

    lines = [t("journal_header", db_user.language, case_name=season.name), ""]
    for entry in entries:
        day = entry.clue.day_number
        if entry.status == ProgressStatus.SOLVED:
            lines.append(
                t(
                    "journal_entry_solved",
                    db_user.language,
                    day=day,
                    attempts=entry.attempts_used,
                    score=entry.points_earned,
                    answer=entry.last_submitted_answer,
                    completed_at=entry.completed_at.strftime("%d %B %Y %H:%M") if entry.completed_at else "",
                )
            )
        elif entry.status == ProgressStatus.FAILED:
            lines.append(t("journal_entry_failed", db_user.language, day=day))
        elif entry.status == ProgressStatus.AVAILABLE:
            lines.append(t("journal_entry_available", db_user.language, day=day))
        else:
            lines.append(t("journal_entry_locked", db_user.language, day=day))
        lines.append("")

    await message.answer("\n".join(lines).strip())
