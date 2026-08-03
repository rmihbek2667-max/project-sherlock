from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select

from app.config import LANGUAGE_LABELS, SEASON_LENGTH_DAYS
from app.database.models import ProgressStatus, Season, User
from app.localization.loader import t
from app.services import journal_service
from app.services.scoring import get_user_rank
from app.utils.menu_filter import MenuButton

router = Router(name="profile")


@router.message(Command("profile"))
@router.message(MenuButton("menu_profile"))
async def cmd_profile(message: Message, db_user: User, session, state: FSMContext) -> None:
    await state.clear()
    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    season = result.scalar_one_or_none()

    completed = 0
    score = 0
    if season:
        entries = await journal_service.get_full_journal(session, db_user.id, season.id)
        completed = sum(1 for e in entries if e.status == ProgressStatus.SOLVED)
        score = sum(e.points_earned for e in entries)

    await message.answer(
        t(
            "profile_header",
            db_user.language,
            name=db_user.full_name,
            language=LANGUAGE_LABELS.get(db_user.language, db_user.language),
            score=score,
            completed=completed,
            total=SEASON_LENGTH_DAYS,
        )
    )


@router.message(Command("myrank"))
async def cmd_myrank(message: Message, db_user: User, session) -> None:
    result = await session.execute(select(Season).where(Season.is_active.is_(True)))
    season = result.scalar_one_or_none()
    if season is None:
        await message.answer(t("no_active_season", db_user.language))
        return

    rank_info = await get_user_rank(session, season.id, db_user.id)
    if rank_info is None:
        await message.answer(t("no_active_season", db_user.language))
        return

    rank, score = rank_info
    await message.answer(t("myrank", db_user.language, rank=rank, score=score))
