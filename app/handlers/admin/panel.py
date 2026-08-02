"""Admin commands. All are gated by db_user.is_admin (set from config.ADMIN_IDS
at first contact). This file is deliberately a skeleton per action — wire each
one to a small FSM wizard (season name -> description -> 5x clue text/answer/hint)
as the next iteration; the data model and services underneath already support it."""

import csv
import io

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import func, select

from app.database.models import Clue, JournalEntry, ProgressStatus, Season, User
from app.localization.loader import t
from app.services.scoring import get_leaderboard

router = Router(name="admin_panel")


def _require_admin(db_user: User) -> bool:
    return db_user.is_admin


@router.message(Command("admin"))
async def cmd_admin_menu(message: Message, db_user: User) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return
    await message.answer(
        t("admin_menu", db_user.language)
        + "\n\n"
        "/newseason — create a season (data-driven, no deploy needed)\n"
        "/releaseclue — release today's clue\n"
        "/lock — lock submissions\n"
        "/unlock — unlock submissions\n"
        "/stats — season statistics\n"
        "/exportleaderboard — CSV export of the top 3 for certificates\n"
        "/broadcast <message> — announce to all users"
    )


@router.message(Command("lock"))
async def cmd_lock(message: Message, db_user: User, session) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return
    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    season = result.scalar_one_or_none()
    if season:
        season.submissions_locked = True
    await message.answer(t("admin_action_done", db_user.language, action="submissions locked"))


@router.message(Command("unlock"))
async def cmd_unlock(message: Message, db_user: User, session) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return
    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    season = result.scalar_one_or_none()
    if season:
        season.submissions_locked = False
    await message.answer(t("admin_action_done", db_user.language, action="submissions unlocked"))


@router.message(Command("exportleaderboard"))
async def cmd_export_leaderboard(message: Message, db_user: User, session) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return

    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    season = result.scalar_one_or_none()
    if season is None:
        await message.answer(t("no_active_season", db_user.language))
        return

    rows = await get_leaderboard(session, season.id, limit=3)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["rank", "name", "username", "score"])
    for i, row in enumerate(rows, start=1):
        writer.writerow([i, row["full_name"], row["username"], row["total_points"]])

    file = BufferedInputFile(buf.getvalue().encode("utf-8"), filename=f"leaderboard_top3_season_{season.id}.csv")
    await message.answer_document(file)


@router.message(Command("newseason"))
async def cmd_new_season(message: Message, db_user: User, session) -> None:
    """Usage: /newseason Name | Description
    Creates a season as pure data — deactivates any currently active season."""
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return

    payload = message.text.partition(" ")[2].strip()
    if not payload:
        await message.answer("Usage: /newseason Name | Description")
        return
    name, _, description = payload.partition("|")

    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    for old_season in result.scalars().all():
        old_season.is_active = False

    season = Season(name=name.strip(), description=description.strip(), is_active=True, start_date=datetime.now(timezone.utc))
    session.add(season)
    await session.flush()
    await message.answer(t("admin_action_done", db_user.language, action=f"season '{season.name}' created (id={season.id})"))


@router.message(Command("addclue"))
async def cmd_add_clue(message: Message, db_user: User, session) -> None:
    """Usage: /addclue <season_id> <day> | Title | Clue text | answer1,answer2 | hint(optional)"""
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return

    payload = message.text.partition(" ")[2].strip()
    try:
        head, title, clue_text, answers_raw, *rest = [p.strip() for p in payload.split("|")]
        season_id_str, day_str = head.split()
        season_id, day = int(season_id_str), int(day_str)
        answers = [a.strip() for a in answers_raw.split(",") if a.strip()]
        hint = rest[0] if rest else None
    except (ValueError, IndexError):
        await message.answer("Usage: /addclue <season_id> <day> | Title | Clue text | answer1,answer2 | hint(optional)")
        return

    clue = Clue(season_id=season_id, day_number=day, title=title, clue_text=clue_text, correct_answers=answers, hint=hint)
    session.add(clue)
    await session.flush()
    await message.answer(t("admin_action_done", db_user.language, action=f"clue for day {day} added"))


@router.message(Command("releaseclue"))
async def cmd_release_clue(message: Message, db_user: User, session) -> None:
    """Usage: /releaseclue <clue_id> — marks a clue as released immediately."""
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return

    arg = message.text.partition(" ")[2].strip()
    if not arg.isdigit():
        await message.answer("Usage: /releaseclue <clue_id>")
        return

    clue = await session.get(Clue, int(arg))
    if clue is None:
        await message.answer("Clue not found.")
        return
    clue.release_at = datetime.now(timezone.utc)
    await message.answer(t("admin_action_done", db_user.language, action=f"day {clue.day_number} clue released"))


@router.message(Command("stats"))
async def cmd_stats(message: Message, db_user: User, session) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return

    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    season = result.scalar_one_or_none()
    if season is None:
        await message.answer(t("no_active_season", db_user.language))
        return

    solved = await session.scalar(
        select(func.count())
        .select_from(JournalEntry)
        .join(Clue, Clue.id == JournalEntry.clue_id)
        .where(Clue.season_id == season.id, JournalEntry.status == ProgressStatus.SOLVED)
    )
    failed = await session.scalar(
        select(func.count())
        .select_from(JournalEntry)
        .join(Clue, Clue.id == JournalEntry.clue_id)
        .where(Clue.season_id == season.id, JournalEntry.status == ProgressStatus.FAILED)
    )
    await message.answer(f"📊 Season '{season.name}'\nSolved entries: {solved}\nFailed entries: {failed}")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, db_user: User, session) -> None:
    if not _require_admin(db_user):
        await message.answer(t("admin_not_authorized", db_user.language))
        return

    text_to_send = message.text.partition(" ")[2].strip()
    if not text_to_send:
        await message.answer("Usage: /broadcast <message>")
        return

    result = await session.execute(select(User))
    users = result.scalars().all()
    sent = 0
    for user in users:
        try:
            await message.bot.send_message(user.telegram_id, text_to_send)
            sent += 1
        except Exception:
            continue  # user blocked the bot, etc. — skip, don't crash the broadcast

    await message.answer(t("admin_action_done", db_user.language, action=f"broadcast sent to {sent} users"))
